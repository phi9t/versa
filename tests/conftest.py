import pytest

from versa.llm.mock import MockLLM
from versa.orchestrator import AgentRuntime
from versa.store.memory import InMemoryStore


@pytest.fixture
def mock_runtime() -> AgentRuntime:
    return AgentRuntime(MockLLM(), InMemoryStore())
