from __future__ import annotations

from versa.extractor_normalizer import normalize_turn_delta
from versa.models.delta import FactPatch, TurnDelta
from versa.models.state import FactKind, TaskState
from versa.reducer import apply_delta, find_active_fact


def _apply(state: TaskState, delta: TurnDelta, user_text: str, **kwargs) -> TaskState:
    normalized = normalize_turn_delta(state, delta, user_text, **kwargs)
    return apply_delta(state, normalized, message_id="m1")


def test_infers_python_function_objective_from_codex_style_delta():
    state = TaskState(task_id="t")
    delta = TurnDelta(
        fact_patches=[
            FactPatch(
                op="add",
                kind=FactKind.REQUIREMENT,
                key="function_name",
                value="clamp",
                evidence_quote="Write a Python function named clamp",
            )
        ]
    )
    next_state = _apply(state, delta, "Write a Python function named clamp that bounds a number.")
    objective = find_active_fact(next_state, "objective")
    assert objective is not None
    assert objective.value == "write_python_function"


def test_rekeys_miskeyed_objective_patch():
    state = TaskState(task_id="t")
    delta = TurnDelta(
        fact_patches=[
            FactPatch(
                op="add",
                kind=FactKind.OBJECTIVE,
                key="collect_requirements_for_new_api",
                value="Collect requirements for a new API.",
                evidence_quote="Collect requirements for a new API.",
            )
        ]
    )
    next_state = _apply(state, delta, "I want to collect requirements for a new API.")
    objective = find_active_fact(next_state, "objective")
    assert objective is not None
    assert objective.value == "write_requirements_doc"


def test_default_objective_for_gather_ui_first_message():
    state = TaskState(task_id="t")
    delta = TurnDelta(fact_patches=[])
    next_state = _apply(
        state,
        delta,
        "The billing API should support webhooks.",
        default_objective="write_requirements_doc",
    )
    objective = find_active_fact(next_state, "objective")
    scope = find_active_fact(next_state, "scope")
    assert objective is not None
    assert objective.value == "write_requirements_doc"
    assert scope is not None
    assert "billing API" in str(scope.value)


def test_auto_fills_next_missing_requirements_slot():
    state = TaskState(task_id="t")
    state = apply_delta(
        state,
        TurnDelta(
            fact_patches=[
                FactPatch(
                    op="add",
                    kind=FactKind.OBJECTIVE,
                    key="objective",
                    value="write_requirements_doc",
                    evidence_quote="gather requirements",
                ),
                FactPatch(
                    op="add",
                    kind=FactKind.REQUIREMENT,
                    key="scope",
                    value="backup CLI",
                    evidence_quote="backup CLI",
                ),
            ]
        ),
        message_id="m0",
    )
    delta = TurnDelta(fact_patches=[])
    next_state = _apply(state, delta, "Individual developers on macOS and Linux.")
    target_users = find_active_fact(next_state, "target_users")
    assert target_users is not None
    assert "developers" in str(target_users.value).lower()


def test_parse_use_slot_message():
    state = TaskState(task_id="t")
    state = apply_delta(
        state,
        TurnDelta(
            fact_patches=[
                FactPatch(
                    op="add",
                    kind=FactKind.OBJECTIVE,
                    key="objective",
                    value="write_requirements_doc",
                    evidence_quote="gather",
                )
            ]
        ),
        message_id="m0",
    )
    delta = TurnDelta(fact_patches=[])
    next_state = _apply(state, delta, "Use scope: cross-platform CLI backing up ~/Documents to S3")
    scope = find_active_fact(next_state, "scope")
    assert scope is not None
    assert "S3" in str(scope.value)


def test_does_not_override_existing_objective():
    state = TaskState(task_id="t")
    state = apply_delta(
        state,
        TurnDelta(
            fact_patches=[
                FactPatch(
                    op="add",
                    kind=FactKind.OBJECTIVE,
                    key="objective",
                    value="write_python_function",
                    evidence_quote="Write a Python function",
                )
            ]
        ),
        message_id="m0",
    )
    delta = TurnDelta(fact_patches=[])
    next_state = _apply(
        state,
        delta,
        "Use scope: demo",
        default_objective="write_requirements_doc",
    )
    assert find_active_fact(next_state, "objective").value == "write_python_function"
