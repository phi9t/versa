from __future__ import annotations

import pytest

from versa.models.delta import TurnDelta
from versa.models.state import OpenQuestion, TaskState
from versa.orchestrator import AgentRuntime
from versa.reducer import apply_delta, find_active_fact
from versa.store.memory import InMemoryStore
from tests.fixtures import REQUIREMENTS_SLOTS


@pytest.mark.asyncio
async def test_extractor_questions_do_not_block_progress(mock_runtime: AgentRuntime):
    state = TaskState(task_id="t")
    state = apply_delta(
        state,
        TurnDelta(
            fact_patches=[],
            new_questions_for_user=["Who are the target users for the API?"],
        ),
        message_id="m1",
    )
    assert not any(q.blocks_progress for q in state.open_questions)

    await mock_runtime.store.save_state("t", state)
    reply = await mock_runtime.handle_user_turn("t", "Use scope: demo API")
    assert "target users" not in reply.lower() or "functional" in reply.lower()


@pytest.mark.asyncio
async def test_render_clarification_follows_missing_slots(mock_runtime: AgentRuntime):
    await mock_runtime.handle_user_turn(
        "t-clarify",
        "Gather requirements for backup CLI. Objective: write_requirements_doc.",
    )
    state = await mock_runtime.store.load_state("t-clarify")
    reply = mock_runtime.render_clarification(state)
    assert "scope" in reply.lower() or "building" in reply.lower()


@pytest.mark.asyncio
async def test_requirements_slots_advance_without_repeating(mock_runtime: AgentRuntime):
    task_id = "t-advance"
    await mock_runtime.handle_user_turn(
        task_id,
        "Gather requirements for backup CLI. Objective: write_requirements_doc.",
    )
    replies: list[str] = []
    for key, value in REQUIREMENTS_SLOTS:
        reply = await mock_runtime.handle_user_turn(task_id, f"Use {key}: {value!r}" if isinstance(value, str) else f"Use {key}: {value}")
        replies.append(reply)
    assert len(set(replies)) == len(replies)

    state = await mock_runtime.store.load_state(task_id)
    assert find_active_fact(state, "success_criteria") is not None
