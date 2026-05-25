import pytest

from versa.llm.codex_cli import codex_is_ready
from versa.llm.factory import make_codex_clients
from versa.orchestrator import AgentRuntime
from versa.store.memory import InMemoryStore

from tests.fixtures import CLAMP_USER_PROMPT, is_clarification


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not codex_is_ready(), reason="codex CLI not available or not authed")
async def test_codex_extract_and_clarify():
    extractor, solver = make_codex_clients()
    runtime = AgentRuntime(solver, InMemoryStore(), extractor_llm=extractor)

    reply = await runtime.handle_user_turn("codex-e2e", CLAMP_USER_PROMPT)
    assert reply
    state = await runtime.store.load_state("codex-e2e")
    has_facts = any(f.key in ("objective", "function_name") for f in state.facts)
    assert has_facts or is_clarification(reply)
