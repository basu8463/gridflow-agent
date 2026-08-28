"""In-memory case store. Demo-sized on purpose — swap for Postgres later."""

from __future__ import annotations

import threading
import time
import uuid

from .schemas import ApplicationInput, CaseRecord, Decision, TraceEvent

_lock = threading.Lock()
_cases: dict[str, CaseRecord] = {}


def create_case(application: ApplicationInput) -> CaseRecord:
    record = CaseRecord(id=str(uuid.uuid4())[:8], created_at=time.time(), application=application)
    with _lock:
        _cases[record.id] = record
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
        record = _cases[case_id]
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
        _cases[case_id] = record
        return record


def get_case(case_id: str) -> CaseRecord:
    with _lock:
        if case_id not in _cases:
            raise KeyError(case_id)
        return _cases[case_id]


def list_cases() -> list[CaseRecord]:
    with _lock:
        return sorted(_cases.values(), key=lambda c: c.created_at, reverse=True)
