from __future__ import annotations

from versa.models.delta import TurnDelta
from versa.models.state import Fact, FactStatus, OpenQuestion, SourceSpan, TaskState


def find_active_fact(state: TaskState, key: str) -> Fact | None:
    for fact in reversed(state.facts):
        if fact.key == key and fact.status == FactStatus.ACTIVE:
            return fact
    return None


def active_facts(state: TaskState) -> list[Fact]:
    return [f for f in state.facts if f.status == FactStatus.ACTIVE]


def active_fact_keys(state: TaskState) -> set[str]:
    return {f.key for f in active_facts(state)}


def apply_delta(state: TaskState, delta: TurnDelta, message_id: str) -> TaskState:
    state = state.model_copy(deep=True)

    for patch in delta.fact_patches:
        source = SourceSpan(
            message_id=message_id,
            quote=patch.evidence_quote,
        )

        existing = find_active_fact(state, patch.key)

        if patch.op == "add":
            if existing and existing.value != patch.value:
                existing.status = FactStatus.CONFLICTED
                state.open_questions.append(
                    OpenQuestion(
                        question=(
                            f"I have conflicting values for `{patch.key}`: "
                            f"`{existing.value}` vs `{patch.value}`. Which should I use?"
                        ),
                        related_keys=[patch.key],
                    )
                )
            elif not existing:
                state.facts.append(
                    Fact(
                        kind=patch.kind,
                        key=patch.key,
                        value=patch.value,
                        source=source,
                    )
                )

        elif patch.op in {"update", "supersede"}:
            supersedes: list[str] = []
            if existing:
                existing.status = FactStatus.SUPERSEDED
                supersedes.append(existing.id)

            state.facts.append(
                Fact(
                    kind=patch.kind,
                    key=patch.key,
                    value=patch.value,
                    source=source,
                    supersedes=supersedes,
                )
            )

        elif patch.op == "reject":
            if existing:
                existing.status = FactStatus.REJECTED

    for patch in delta.assumption_patches:
        status = "confirmed" if patch.op == "confirm" else "rejected"
        for assumption in state.assumptions:
            if patch.target_assumption_id and assumption.id == patch.target_assumption_id:
                assumption.status = status
                break
            if assumption.key == patch.key:
                assumption.status = status
                break

    for q in delta.new_questions_for_user:
        state.open_questions.append(
            OpenQuestion(question=q, related_keys=[], blocks_progress=False)
        )

    state.open_questions = prune_resolved_questions(state)

    state.version += 1
    return state


def prune_resolved_questions(state: TaskState) -> list[OpenQuestion]:
    keys = active_fact_keys(state)
    return [
        q
        for q in state.open_questions
        if not q.related_keys or not set(q.related_keys).issubset(keys)
    ]
