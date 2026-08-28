"""Pydantic models shared across the agent, API, and evals."""

from __future__ import annotations

import time
from typing import Literal, Optional

from pydantic import BaseModel, Field

ConnectionType = Literal["heat_pump", "solar_pv", "ev_charger", "new_home"]
Outcome = Literal["approve", "approve_with_conditions", "request_documents", "reject"]
Track = Literal["notification", "approval"]


class ApplicationInput(BaseModel):
    """What arrives from the customer — free text plus optional structure."""

    country: str = "DE"
    applicant_name: str
    address: str
    description: str = Field(description="Free-text description of what the customer wants to connect")
    documents: list[str] = Field(default_factory=list, description="Document types provided")


class ExtractedApplication(BaseModel):
    """Structured fields the agent extracts from the free-text application."""

    connection_type: ConnectionType
    requested_power_kw: float = Field(gt=0, le=500)
    summary: str = Field(description="One-sentence summary of the request")


class DecisionDraft(BaseModel):
    """What the LLM drafts after all deterministic checks are done."""

    outcome: Outcome
    justification: str = Field(description="2-4 sentences citing specific rule IDs")
    cited_rules: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class Decision(BaseModel):
    """Final decision object shown in the review queue."""

    outcome: Outcome
    track: Track
    justification: str
    cited_rules: list[str]
    conditions: list[str]
    missing_documents: list[str]
    fee_eur: Optional[float]
    sla_days: Optional[int]
    confidence: float
    needs_human_review: bool
    status: str = "pending_review"


class TraceEvent(BaseModel):
    """One step in the agent's visible execution trace."""

    step: str
    title: str
    detail: str
    data: dict | None = None
    ts: float = Field(default_factory=time.time)
