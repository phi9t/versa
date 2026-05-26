import pytest

from tests.fixtures import REQUIREMENTS_OPENING, REQUIREMENTS_SLOTS, SYNTHESIS_TRIGGER
from tests.fixtures import is_clarification


@pytest.mark.asyncio
async def test_requirements_gather_and_synthesize(mock_runtime):
    reply = await mock_runtime.handle_user_turn("req-flow", REQUIREMENTS_OPENING)
    assert reply
    assert is_clarification(reply) or "scope" in reply.lower()

    for key, value in REQUIREMENTS_SLOTS:
        if isinstance(value, list):
            text = f"Use {key}: {value}"
        else:
            text = f"Use {key}: {value}"
        await mock_runtime.handle_user_turn("req-flow", text)

    reply = await mock_runtime.handle_user_turn("req-flow", SYNTHESIS_TRIGGER)
    assert reply
    assert "# Overview" in reply or "scope" in reply.lower()

    state = await mock_runtime.store.load_state("req-flow")
    assert state.active_artifact_id is not None
