from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SourceSpan(BaseModel):
    message_id: str
    quote: str
    start_char: int | None = None
    end_char: int | None = None


class FactStatus(str, Enum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    CONFLICTED = "conflicted"
    REJECTED = "rejected"


class FactKind(str, Enum):
    OBJECTIVE = "objective"
    REQUIREMENT = "requirement"
    CONSTRAINT = "constraint"
    PREFERENCE = "preference"
    EXAMPLE = "example"
    RESOURCE = "resource"
    DECISION = "decision"
    CORRECTION = "correction"
    TEST = "test"
    ENVIRONMENT = "environment"


class Fact(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    kind: FactKind
    key: str
    value: Any
    status: FactStatus = FactStatus.ACTIVE
    confidence: float = 1.0
    source: SourceSpan
    created_at: datetime = Field(default_factory=_utcnow)
    supersedes: list[str] = Field(default_factory=list)


class Assumption(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    key: str
    value: Any
    reason: str
    status: Literal["open", "confirmed", "rejected"] = "open"
    source: str = "assistant"


class OpenQuestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    question: str
    blocks_progress: bool = True
    related_keys: list[str] = Field(default_factory=list)


class ToolResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    tool_name: str
    input: dict[str, Any]
    output_summary: str
    verified: bool = False
    created_at: datetime = Field(default_factory=_utcnow)


class ArtifactStatus(str, Enum):
    DRAFT = "draft"
    VERIFIED = "verified"
    FAILED = "failed"
    SUPERSEDED = "superseded"


class Artifact(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    kind: Literal["code", "sql", "plan", "answer", "patch", "document"]
    content: str
    status: ArtifactStatus = ArtifactStatus.DRAFT
    based_on_state_version: int
    verification_ids: list[str] = Field(default_factory=list)


class Verification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    artifact_id: str
    passed: bool
    checks: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


class TaskState(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    version: int = 0

    facts: list[Fact] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    open_questions: list[OpenQuestion] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)

    active_artifact_id: str | None = None


class CodeTaskState(TaskState):
    repo_root: str | None = None
    target_files: list[str] = Field(default_factory=list)
    relevant_symbols: list[str] = Field(default_factory=list)
    user_requirements: list[Fact] = Field(default_factory=list)
    acceptance_tests: list[Fact] = Field(default_factory=list)
    forbidden_changes: list[Fact] = Field(default_factory=list)
    verified_observations: list[ToolResult] = Field(default_factory=list)
