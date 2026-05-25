from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from versa.models.state import FactKind


class FactPatch(BaseModel):
    op: Literal["add", "update", "supersede", "reject"]
    kind: FactKind
    key: str
    value: Any
    target_fact_id: str | None = None
    evidence_quote: str


class AssumptionPatch(BaseModel):
    op: Literal["confirm", "reject"]
    key: str
    value: Any | None = None
    target_assumption_id: str | None = None
    evidence_quote: str


class TurnDelta(BaseModel):
    user_intent_summary: str | None = None
    fact_patches: list[FactPatch] = Field(default_factory=list)
    assumption_patches: list[AssumptionPatch] = Field(default_factory=list)
    new_questions_for_user: list[str] = Field(default_factory=list)
