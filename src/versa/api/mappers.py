from __future__ import annotations

import json
from typing import Any

from versa.api.dtos import FactView, MessageView, Readiness, SessionSnapshot, SlotStatus
from versa.models.state import Artifact, ArtifactStatus, TaskState
from versa.policy import REQUIREMENTS_DOC_SLOTS, SLOT_LABELS, infer_required_slots, missing_required_slots
from versa.reducer import active_facts, find_active_fact


def _preview(value: Any, limit: int = 80) -> str:
    text = json.dumps(value) if not isinstance(value, str) else value
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _artifact_status(artifact: Artifact | None) -> str | None:
    if artifact is None:
        return "none"
    if artifact.status == ArtifactStatus.VERIFIED:
        return "verified"
    if artifact.status == ArtifactStatus.FAILED:
        return "failed"
    return "draft"


def infer_readiness(state: TaskState, artifact: Artifact | None) -> Readiness:
    objective = find_active_fact(state, "objective")
    if not objective or objective.value != "write_requirements_doc":
        if artifact and artifact.status == ArtifactStatus.VERIFIED:
            return Readiness.SYNTHESIZED
        missing = missing_required_slots(state)
        if missing:
            return Readiness.GATHERING
        return Readiness.READY_TO_SYNTHESIZE

    content_slots = [slot for slot in REQUIREMENTS_DOC_SLOTS if slot != "synthesis_requested"]
    missing_content = [slot for slot in missing_required_slots(state) if slot in content_slots]
    if missing_content:
        return Readiness.GATHERING

    if artifact and artifact.status == ArtifactStatus.VERIFIED:
        return Readiness.SYNTHESIZED

    if find_active_fact(state, "synthesis_requested"):
        return Readiness.READY_TO_SYNTHESIZE

    return Readiness.READY_TO_SYNTHESIZE


def snapshot_from_state(
    state: TaskState,
    messages: list[dict[str, Any]],
    artifact: Artifact | None,
) -> SessionSnapshot:
    objective_fact = find_active_fact(state, "objective")
    required = infer_required_slots(state)
    missing = missing_required_slots(state)
    active_keys = {fact.key for fact in active_facts(state)}

    slots: list[SlotStatus] = []
    for key in required:
        fact = find_active_fact(state, key)
        slots.append(
            SlotStatus(
                key=key,
                label=SLOT_LABELS.get(key, key.replace("_", " ").title()),
                filled=key in active_keys,
                value_preview=_preview(fact.value) if fact else None,
            )
        )

    fact_views = [
        FactView(
            id=fact.id,
            kind=fact.kind.value,
            key=fact.key,
            value=fact.value,
            evidence_quote=fact.source.quote,
            message_id=fact.source.message_id,
        )
        for fact in active_facts(state)
    ]

    message_views = [
        MessageView(
            id=message["id"],
            role=message["role"],
            content=message["content"],
            created_at=message["created_at"],
        )
        for message in messages
    ]

    blocking = [q.question for q in state.open_questions if q.blocks_progress]

    return SessionSnapshot(
        task_id=state.task_id,
        version=state.version,
        objective=str(objective_fact.value) if objective_fact else None,
        facts=fact_views,
        messages=message_views,
        open_questions=blocking,
        slots=slots,
        missing_slot_keys=missing,
        readiness=infer_readiness(state, artifact),
        active_artifact=artifact.content if artifact and artifact.status == ArtifactStatus.VERIFIED else None,
        artifact_status=_artifact_status(artifact),
    )
