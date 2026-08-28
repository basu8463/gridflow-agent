"""The GridFlow agent: a LangGraph state machine that processes a grid
connection application end-to-end.

    extract → retrieve_rules → validate_documents ─┬→ decide (docs missing)
                                                   └→ capacity → fee → decide

Design principles (mirroring how production vertical agents are built):
- Deterministic checks (documents, track, fees, capacity) run as tools —
  the LLM never invents numbers.
- The LLM does what LLMs are good at: extracting structure from free text
  and writing a justified decision that cites rules.
- Every step emits a TraceEvent — the agent's work is fully inspectable.
- Low confidence or missing documents always route to a human.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph

from . import config, rules, tools
from .llm import get_chat_model, provider_label
from .schemas import ApplicationInput, Decision, DecisionDraft, ExtractedApplication, TraceEvent


def _append(left: list, right: list) -> list:
    return left + right


class AgentState(TypedDict, total=False):
    application: dict
    country: str
    rulebook: dict
    extracted: dict
    retrieved_rules: list
    dso: dict
    documents: dict
    track: dict
    capacity: dict
    fee: dict
    decision: dict
    trace: Annotated[list, _append]


def _event(step: str, title: str, detail: str, data: dict | None = None) -> dict:
    return TraceEvent(step=step, title=title, detail=detail, data=data).model_dump()


# --------------------------------------------------------------------------
# Nodes
# --------------------------------------------------------------------------

def extract_node(state: AgentState) -> dict:
    app = ApplicationInput(**state["application"])
    model = get_chat_model().with_structured_output(ExtractedApplication)
    extracted: ExtractedApplication = model.invoke(
        [
            (
                "system",
                "You extract structured data from grid connection applications. "
                "Classify the connection type and the requested electrical power in kW. "
                "If power is stated in unusual units, convert to kW.",
            ),
            (
                "human",
                f"Application text:\n{app.description}\n\nAddress: {app.address}",
            ),
        ]
    )
    return {
        "extracted": extracted.model_dump(),
        "trace": [
            _event(
                "extract",
                "Extracted application data",
                f"{extracted.summary} — classified as {extracted.connection_type}, "
                f"{extracted.requested_power_kw} kW (model: {provider_label()})",
                extracted.model_dump(),
            )
        ],
    }


def retrieve_node(state: AgentState) -> dict:
    extracted = state["extracted"]
    country = state["country"]
    query = (
        f"{extracted['connection_type']} {extracted['requested_power_kw']} kW "
        "notification approval required documents fees"
    )
    hits = rules.retrieve(country, query, k=4)
    dso = tools.lookup_dso(state["application"]["address"], country)
    return {
        "retrieved_rules": hits,
        "dso": dso,
        "trace": [
            _event(
                "retrieve",
                f"Retrieved {len(hits)} rules from {country} rulebook",
                "Top rules: " + ", ".join(h["rule_id"] for h in hits),
                {"rules": [{"rule_id": h["rule_id"], "title": h["title"]} for h in hits], "dso": dso},
            )
        ],
    }


def validate_node(state: AgentState) -> dict:
    rulebook = state["rulebook"]
    extracted = state["extracted"]
    docs = tools.validate_documents(
        rulebook, extracted["connection_type"], state["application"].get("documents", [])
    )
    track = tools.determine_track(rulebook, extracted["connection_type"], extracted["requested_power_kw"])
    detail = (
        f"Track: {track['track']}"
        + (" (exceeds hard limit!)" if track["exceeds_hard_limit"] else "")
        + f" · missing documents: {docs['missing'] or 'none'}"
    )
    return {
        "documents": docs,
        "track": track,
        "trace": [_event("validate", "Validated documents & determined track", detail, {**docs, **track})],
    }


def capacity_node(state: AgentState) -> dict:
    extracted = state["extracted"]
    cap = tools.check_grid_capacity(state["application"]["address"], extracted["requested_power_kw"])
    detail = (
        f"Substation {cap['substation_id']}: {cap['headroom_kw']} kW headroom vs "
        f"{cap['requested_kw']} kW requested → {'sufficient' if cap['sufficient'] else 'INSUFFICIENT'}"
    )
    return {"capacity": cap, "trace": [_event("capacity", "Checked local grid capacity", detail, cap)]}


def fee_node(state: AgentState) -> dict:
    fee = tools.calculate_fee(state["rulebook"], state["extracted"]["requested_power_kw"])
    detail = f"EUR {fee['total_eur']:.2f} (base {fee['base_fee']} + {fee['surcharge_kw']} kW × {fee['per_kw_rate']})"
    return {"fee": fee, "trace": [_event("fee", "Calculated connection fee", detail, fee)]}


def decide_node(state: AgentState) -> dict:
    rulebook = state["rulebook"]
    extracted = state["extracted"]
    docs = state["documents"]
    track = state["track"]
    capacity = state.get("capacity")
    fee = state.get("fee")

    rules_context = "\n\n".join(h["text"] for h in state["retrieved_rules"])
    facts = {
        "country": state["country"],
        "connection_type": extracted["connection_type"],
        "requested_power_kw": extracted["requested_power_kw"],
        "track": track["track"],
        "exceeds_hard_limit": track["exceeds_hard_limit"],
        "missing_documents": docs["missing"],
        "capacity_sufficient": capacity["sufficient"] if capacity else None,
        "capacity_headroom_kw": capacity["headroom_kw"] if capacity else None,
        "fee_eur": fee["total_eur"] if fee else None,
    }

    model = get_chat_model().with_structured_output(DecisionDraft)
    draft: DecisionDraft = model.invoke(
        [
            (
                "system",
                "You are a grid connection case officer's assistant. Draft a decision "
                "based ONLY on the verified facts and the retrieved rules below. "
                "Cite rule IDs (e.g. DE-HP-2) in your justification.\n"
                "Decision policy:\n"
                "- missing_documents non-empty → outcome 'request_documents'\n"
                "- exceeds_hard_limit true → outcome 'reject'\n"
                "- capacity_sufficient false → 'approve_with_conditions' (load management "
                "condition) unless rules require rejection\n"
                "- otherwise → 'approve'\n"
                "Confidence reflects how clearly the rules determine this outcome.",
            ),
            (
                "human",
                f"VERIFIED FACTS:\n{facts}\n\nRETRIEVED RULES:\n{rules_context}",
            ),
        ]
    )

    # Deterministic guardrails: policy outcomes are enforced, not hoped for.
    outcome = draft.outcome
    if docs["missing"]:
        outcome = "request_documents"
    elif track["exceeds_hard_limit"]:
        outcome = "reject"

    sla_key = "notification_days" if track["track"] == "notification" else "approval_days"
    needs_review = draft.confidence < config.CONFIDENCE_THRESHOLD or outcome != "approve"

    decision = Decision(
        outcome=outcome,
        track=track["track"],
        justification=draft.justification,
        cited_rules=draft.cited_rules,
        conditions=draft.conditions,
        missing_documents=docs["missing"],
        fee_eur=fee["total_eur"] if fee else None,
        sla_days=rulebook["sla"][sla_key],
        confidence=draft.confidence,
        needs_human_review=needs_review,
    )
    return {
        "decision": decision.model_dump(),
        "trace": [
            _event(
                "decide",
                f"Drafted decision: {outcome}",
                f"Confidence {draft.confidence:.2f} · "
                + ("routed to human review" if needs_review else "auto-approvable")
                + f" · cites {', '.join(draft.cited_rules) or 'no rules'}",
                decision.model_dump(),
            )
        ],
    }


# --------------------------------------------------------------------------
# Graph wiring
# --------------------------------------------------------------------------

def _after_validation(state: AgentState) -> str:
    if state["documents"]["missing"]:
        return "decide"  # incomplete application: skip capacity & fee
    return "capacity"


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("extract", extract_node)
    g.add_node("retrieve", retrieve_node)
    g.add_node("validate", validate_node)
    g.add_node("capacity", capacity_node)
    g.add_node("fee", fee_node)
    g.add_node("decide", decide_node)

    g.set_entry_point("extract")
    g.add_edge("extract", "retrieve")
    g.add_edge("retrieve", "validate")
    g.add_conditional_edges("validate", _after_validation, {"capacity": "capacity", "decide": "decide"})
    g.add_edge("capacity", "fee")
    g.add_edge("fee", "decide")
    g.add_edge("decide", END)
    return g.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_application(application: ApplicationInput) -> dict:
    """Run one application through the agent. Returns final state."""
    rulebook = config.load_rulebook(application.country)
    initial: AgentState = {
        "application": application.model_dump(),
        "country": application.country.upper(),
        "rulebook": rulebook,
        "trace": [
            _event(
                "start",
                f"Processing application — {rulebook['country_name']} rulebook",
                f"Applicant: {application.applicant_name} · {application.address}",
            )
        ],
    }
    return get_graph().invoke(initial)


def stream_application(application: ApplicationInput):
    """Yield state updates as the agent progresses (for SSE streaming)."""
    rulebook = config.load_rulebook(application.country)
    initial: AgentState = {
        "application": application.model_dump(),
        "country": application.country.upper(),
        "rulebook": rulebook,
        "trace": [
            _event(
                "start",
                f"Processing application — {rulebook['country_name']} rulebook",
                f"Applicant: {application.applicant_name} · {application.address}",
            )
        ],
    }
    yield {"trace": initial["trace"]}
    for update in get_graph().stream(initial, stream_mode="updates"):
        for node_output in update.values():
            yield node_output
