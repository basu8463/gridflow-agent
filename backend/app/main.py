"""GridFlow API — process applications, stream the agent trace, review queue."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from . import config, rules, store
from .agent import run_application, stream_application
from .llm import provider_label
from .schemas import ApplicationInput, ReviewRequest

app = FastAPI(
    title="GridFlow",
    description="Vertical AI agent for grid connection applications.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.FRONTEND_ORIGINS,
    allow_origin_regex=config.FRONTEND_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GOLDEN_PATH = Path(__file__).resolve().parent.parent / "evals" / "golden_cases.json"


@app.get("/health")
def health():
    return {
        "ok": True,
        "provider": provider_label(),
        "countries": config.available_countries(),
        "confidence_threshold": config.CONFIDENCE_THRESHOLD,
    }


@app.get("/stats")
def case_stats():
    return store.stats()


@app.get("/countries")
def countries():
    packs = []
    for code in config.available_countries():
        rb = config.load_rulebook(code)
        packs.append(
            {
                "code": code,
                "name": rb["country_name"],
                "currency": rb["currency"],
                "connection_types": {
                    k: {
                        "label": v["label"],
                        "notify_only_max_kw": v["notify_only_max_kw"],
                        "hard_limit_kw": v["hard_limit_kw"],
                        "required_documents": v["required_documents"],
                    }
                    for k, v in rb["connection_types"].items()
                },
                "fees": rb["fees"],
                "sla": rb["sla"],
            }
        )
    return packs


@app.get("/rulebooks/{country}")
def rulebook(country: str):
    try:
        rb = config.load_rulebook(country)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    docs = [{"filename": n, "content": c} for n, c in config.rulebook_documents(country)]
    return {"config": rb, "documents": docs}


@app.post("/applications")
def submit_application(application: ApplicationInput):
    try:
        config.load_rulebook(application.country)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    record = store.create_case(application)
    state = run_application(application)
    updated = store.update_case(
        record.id,
        extracted=state.get("extracted"),
        decision=state.get("decision"),
        trace=state.get("trace", []),
        status="pending_review" if state["decision"]["needs_human_review"] else "auto_approved",
    )
    return updated.model_dump()


@app.post("/applications/stream")
async def stream_app(application: ApplicationInput):
    try:
        config.load_rulebook(application.country)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    record = store.create_case(application)

    def events():
        yield {"event": "case", "data": json.dumps({"id": record.id})}
        last_trace: list = []
        last_state: dict = {}
        for update in stream_application(application):
            last_state.update({k: v for k, v in update.items() if k != "trace"})
            if "trace" in update:
                last_trace.extend(update["trace"])
                for event in update["trace"]:
                    yield {"event": "trace", "data": json.dumps(event)}
        decision = last_state.get("decision")
        store.update_case(
            record.id,
            extracted=last_state.get("extracted"),
            decision=decision,
            trace=last_trace,
            status="pending_review" if decision and decision.get("needs_human_review") else "auto_approved",
        )
        yield {"event": "done", "data": json.dumps(store.get_case(record.id).model_dump())}

    return EventSourceResponse(events())


@app.get("/cases")
def cases(status: str | None = None):
    items = store.list_cases()
    if status:
        items = [c for c in items if c.decision and c.decision.status == status]
    return [c.model_dump() for c in items]


@app.get("/cases/{case_id}")
def get_case(case_id: str):
    try:
        return store.get_case(case_id).model_dump()
    except KeyError:
        raise HTTPException(404, "Case not found")


@app.post("/cases/{case_id}/review")
def review_case(case_id: str, body: ReviewRequest):
    try:
        record = store.get_case(case_id)
    except KeyError:
        raise HTTPException(404, "Case not found")
    if not record.decision:
        raise HTTPException(400, "Case has no decision yet")

    decision = record.decision.model_dump()
    if body.action == "approve":
        decision["status"] = "approved"
    elif body.action == "override_reject":
        decision["status"] = "rejected"
        decision["outcome"] = body.override_outcome or "reject"
    else:
        decision["status"] = "needs_more_info"

    updated = store.update_case(
        case_id,
        decision=decision,
        status=decision["status"],
        reviewer_note=body.note,
    )
    return updated.model_dump()


@app.get("/evals/golden")
def golden_cases():
    return json.loads(GOLDEN_PATH.read_text())


@app.on_event("startup")
def warmup():
    for country in config.available_countries():
        rules.index_country(country)
