from versa.models.delta import FactPatch, TurnDelta
from versa.models.state import FactKind, FactStatus, TaskState
from versa.reducer import apply_delta, find_active_fact


def test_add_fact():
    state = TaskState()
    delta = TurnDelta(
        fact_patches=[
            FactPatch(
                op="add",
                kind=FactKind.OBJECTIVE,
                key="objective",
                value="write_python_function",
                evidence_quote="write a python function",
            )
        ]
    )
    new_state = apply_delta(state, delta, message_id="msg-1")
    fact = find_active_fact(new_state, "objective")
    assert fact is not None
    assert fact.value == "write_python_function"
    assert fact.source.message_id == "msg-1"
    assert new_state.version == 1


def test_supersede_fact():
    state = TaskState()
    delta1 = TurnDelta(
        fact_patches=[
            FactPatch(
                op="add",
                kind=FactKind.CONSTRAINT,
                key="edge_cases",
                value="empty list",
                evidence_quote="empty list",
            )
        ]
    )
    state = apply_delta(state, delta1, "msg-1")

    delta2 = TurnDelta(
        fact_patches=[
            FactPatch(
                op="supersede",
                kind=FactKind.CONSTRAINT,
                key="edge_cases",
                value="return False for empty",
                evidence_quote="return False for empty",
            )
        ]
    )
    state = apply_delta(state, delta2, "msg-2")

    active = find_active_fact(state, "edge_cases")
    assert active is not None
    assert active.value == "return False for empty"
    superseded = [f for f in state.facts if f.status == FactStatus.SUPERSEDED]
    assert len(superseded) == 1


def test_conflict_emits_question():
    state = TaskState()
    state = apply_delta(
        state,
        TurnDelta(
            fact_patches=[
                FactPatch(
                    op="add",
                    kind=FactKind.REQUIREMENT,
                    key="function_name",
                    value="foo",
                    evidence_quote="foo",
                )
            ]
        ),
        "msg-1",
    )
    state = apply_delta(
        state,
        TurnDelta(
            fact_patches=[
                FactPatch(
                    op="add",
                    kind=FactKind.REQUIREMENT,
                    key="function_name",
                    value="bar",
                    evidence_quote="bar",
                )
            ]
        ),
        "msg-2",
    )
    assert any("conflicting" in q.question.lower() for q in state.open_questions)
    conflicted = [f for f in state.facts if f.status == FactStatus.CONFLICTED]
    assert len(conflicted) == 1
