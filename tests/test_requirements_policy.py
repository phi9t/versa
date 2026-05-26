from versa.models.delta import FactPatch, TurnDelta
from versa.models.state import FactKind, TaskState
from versa.policy import REQUIREMENTS_DOC_SLOTS, NextAction, choose_next_action, infer_required_slots
from versa.reducer import apply_delta


def _state_with_objective(value: str) -> TaskState:
    return apply_delta(
        TaskState(),
        TurnDelta(
            fact_patches=[
                FactPatch(
                    op="add",
                    kind=FactKind.OBJECTIVE,
                    key="objective",
                    value=value,
                    evidence_quote=value,
                )
            ]
        ),
        "msg-1",
    )


def test_requirements_doc_missing_slots():
    state = _state_with_objective("write_requirements_doc")
    assert choose_next_action(state) == NextAction.ASK_CLARIFICATION
    assert infer_required_slots(state) == REQUIREMENTS_DOC_SLOTS
    assert "scope" in infer_required_slots(state)


def test_requirements_doc_waits_for_synthesis_gate():
    state = _state_with_objective("write_requirements_doc")
    for key, value in [
        ("scope", "CLI backup tool"),
        ("target_users", "developers"),
        ("functional_requirements", ["sync"]),
        ("non_functional_requirements", ["fast"]),
        ("constraints", ["no cloud lock-in"]),
        ("success_criteria", ["restore works"]),
    ]:
        state = apply_delta(
            state,
            TurnDelta(
                fact_patches=[
                    FactPatch(
                        op="add",
                        kind=FactKind.REQUIREMENT,
                        key=key,
                        value=value,
                        evidence_quote=str(value),
                    )
                ]
            ),
            f"msg-{key}",
        )
    assert choose_next_action(state) == NextAction.ASK_CLARIFICATION
    assert "synthesis_requested" in infer_required_slots(state)


def test_requirements_doc_generates_after_synthesis_requested():
    state = _state_with_objective("write_requirements_doc")
    for key, value in [
        ("scope", "CLI backup tool"),
        ("target_users", "developers"),
        ("functional_requirements", ["sync"]),
        ("non_functional_requirements", ["fast"]),
        ("constraints", ["no cloud lock-in"]),
        ("success_criteria", ["restore works"]),
        ("synthesis_requested", True),
    ]:
        kind = FactKind.DECISION if key == "synthesis_requested" else FactKind.REQUIREMENT
        state = apply_delta(
            state,
            TurnDelta(
                fact_patches=[
                    FactPatch(
                        op="add",
                        kind=kind,
                        key=key,
                        value=value,
                        evidence_quote=str(value),
                    )
                ]
            ),
            f"msg-{key}",
        )
    assert choose_next_action(state) == NextAction.GENERATE_CANDIDATE
