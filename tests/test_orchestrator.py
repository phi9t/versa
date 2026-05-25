import pytest

from tests.fixtures import CLAMP_USER_PROMPT, PYTHON_FUNCTION_SLOTS, is_clarification


@pytest.mark.asyncio
async def test_clarification_before_full_answer(mock_runtime):
    reply = await mock_runtime.handle_user_turn(task_id="t1", user_text=CLAMP_USER_PROMPT)
    assert is_clarification(reply)

    state = await mock_runtime.store.load_state("t1")
    assert any(f.key == "objective" for f in state.facts)
    assert any(f.key == "function_name" for f in state.facts)


@pytest.mark.asyncio
async def test_full_turn_generates_when_ready(mock_runtime):
    await mock_runtime.handle_user_turn("t2", CLAMP_USER_PROMPT)

    for key, value in PYTHON_FUNCTION_SLOTS:
        await mock_runtime.handle_user_turn("t2", f"Use {key}: {value}")

    reply = await mock_runtime.handle_user_turn("t2", "Proceed with implementation.")
    assert "def clamp" in reply
    assert "blocking failure" not in reply.lower()

    messages = await mock_runtime.store.list_messages("t2")
    assert any(m["role"] == "user" for m in messages)
    assert any(m["role"] == "assistant" for m in messages)

    state = await mock_runtime.store.load_state("t2")
    assert state.active_artifact_id is not None


@pytest.mark.asyncio
async def test_solver_context_excludes_assistant_drafts():
    from versa.solver import build_solver_context
    from versa.models.state import Fact, FactKind, FactStatus, SourceSpan, TaskState

    state = TaskState(
        facts=[
            Fact(
                kind=FactKind.OBJECTIVE,
                key="objective",
                value="write_python_function",
                status=FactStatus.ACTIVE,
                source=SourceSpan(message_id="u1", quote="write function"),
            )
        ]
    )
    ctx = build_solver_context(state)
    assert "authoritative" in ctx.lower()
    assert "previous assistant drafts" in ctx.lower()
