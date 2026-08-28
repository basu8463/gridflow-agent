"""SQLite case store — the review queue survives API restarts."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path

from . import config
from .schemas import ApplicationInput, CaseRecord, Decision, TraceEvent

_lock = threading.Lock()
DB_PATH = Path(config.DATA_DIR) / "gridflow.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init() -> None:
    with _lock:
        conn = _connect()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                created_at REAL NOT NULL,
                application_json TEXT NOT NULL,
                extracted_json TEXT,
                decision_json TEXT,
                trace_json TEXT NOT NULL DEFAULT '[]',
                reviewer_note TEXT NOT NULL DEFAULT '',
                reviewed_at REAL
            )
            """
        )
        conn.commit()
        conn.close()


_init()


def _row_to_case(row: sqlite3.Row) -> CaseRecord:
    extracted = json.loads(row["extracted_json"]) if row["extracted_json"] else None
    decision_raw = json.loads(row["decision_json"]) if row["decision_json"] else None
    return CaseRecord(
        id=row["id"],
        created_at=row["created_at"],
        application=ApplicationInput(**json.loads(row["application_json"])),
        extracted=extracted,
        decision=Decision(**decision_raw) if decision_raw else None,
        trace=[TraceEvent(**e) for e in json.loads(row["trace_json"] or "[]")],
        reviewer_note=row["reviewer_note"] or "",
        reviewed_at=row["reviewed_at"],
    )


def create_case(application: ApplicationInput) -> CaseRecord:
    record = CaseRecord(id=str(uuid.uuid4())[:8], created_at=time.time(), application=application)
    with _lock:
        conn = _connect()
        conn.execute(
            """
            INSERT INTO cases (id, created_at, application_json, trace_json, reviewer_note)
            VALUES (?, ?, ?, '[]', '')
            """,
            (record.id, record.created_at, application.model_dump_json()),
        )
        conn.commit()
        conn.close()
    return record


def update_case(
    case_id: str,
    *,
    extracted: dict | None = None,
    decision: dict | None = None,
    trace: list[dict] | None = None,
    status: str | None = None,
    reviewer_note: str | None = None,
) -> CaseRecord:
    with _lock:
        conn = _connect()
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        if row is None:
            conn.close()
            raise KeyError(case_id)
        record = _row_to_case(row)
        if extracted is not None:
            record.extracted = extracted
        if decision is not None:
            record.decision = Decision(**decision)
            if status:
                record.decision.status = status
        if trace is not None:
            record.trace = [TraceEvent(**e) if not isinstance(e, TraceEvent) else e for e in trace]
        if reviewer_note is not None:
            record.reviewer_note = reviewer_note
            record.reviewed_at = time.time()
        conn.execute(
            """
            UPDATE cases SET
                extracted_json = ?,
                decision_json = ?,
                trace_json = ?,
                reviewer_note = ?,
                reviewed_at = ?
            WHERE id = ?
            """,
            (
                json.dumps(record.extracted) if record.extracted else None,
                record.decision.model_dump_json() if record.decision else None,
                json.dumps([e.model_dump() if isinstance(e, TraceEvent) else e for e in record.trace]),
                record.reviewer_note,
                record.reviewed_at,
                case_id,
            ),
        )
        conn.commit()
        conn.close()
        return record


def get_case(case_id: str) -> CaseRecord:
    with _lock:
        conn = _connect()
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
        conn.close()
        if row is None:
            raise KeyError(case_id)
        return _row_to_case(row)


def list_cases() -> list[CaseRecord]:
    with _lock:
        conn = _connect()
        rows = conn.execute("SELECT * FROM cases ORDER BY created_at DESC").fetchall()
        conn.close()
        return [_row_to_case(r) for r in rows]


def stats() -> dict:
    cases = list_cases()
    counts: dict[str, int] = {}
    for c in cases:
        key = c.decision.status if c.decision else "processing"
        counts[key] = counts.get(key, 0) + 1
    return {"total": len(cases), "by_status": counts}
