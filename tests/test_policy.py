from versa.models.delta import FactPatch, TurnDelta
from versa.models.state import FactKind, TaskState
from versa.policy import NextAction, choose_next_action, infer_required_slots
from versa.reducer import apply_delta, find_active_fact


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


def test_missing_objective_asks_clarification():
    state = TaskState()
    assert choose_next_action(state) == NextAction.ASK_CLARIFICATION


def test_python_function_missing_slots():
    state = _state_with_objective("write_python_function")
    assert choose_next_action(state) == NextAction.ASK_CLARIFICATION
    assert "function_name" in infer_required_slots(state)


def test_ready_when_slots_filled():
    state = _state_with_objective("write_python_function")
    for key, value in [
        ("function_name", "clamp"),
        ("input_format", "number, lo, hi"),
        ("output_format", "number"),
        ("edge_cases", "none"),
        ("examples_or_tests", []),
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
    assert choose_next_action(state) == NextAction.GENERATE_CANDIDATE
