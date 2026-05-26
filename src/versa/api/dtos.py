from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel


class Readiness(str, Enum):
    GATHERING = "gathering"
    READY_TO_SYNTHESIZE = "ready_to_synthesize"
    SYNTHESIZED = "synthesized"


class MessageView(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: str


class FactView(BaseModel):
    id: str
    kind: str
    key: str
    value: Any
    evidence_quote: str
    message_id: str


class SlotStatus(BaseModel):
    key: str
    label: str
    filled: bool
    value_preview: str | None = None


class SessionSnapshot(BaseModel):
    task_id: str
    version: int
    objective: str | None
    facts: list[FactView]
    messages: list[MessageView]
    open_questions: list[str]
    slots: list[SlotStatus]
    missing_slot_keys: list[str]
    readiness: Readiness
    active_artifact: str | None
    artifact_status: Literal["none", "draft", "verified", "failed"] | None = None


class TurnRequest(BaseModel):
    text: str


class TurnResponse(BaseModel):
    snapshot: SessionSnapshot
    assistant_reply: str


class ExportResponse(BaseModel):
    format: Literal["md", "json"]
    content: str
