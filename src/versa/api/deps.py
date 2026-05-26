from __future__ import annotations

from versa.api.session_service import SessionService
from versa.gather.factory import make_gather_session
from versa.llm.base import LLMClient
from versa.llm.mock import MockLLM
from versa.orchestrator import AgentRuntime
from versa.store.memory import InMemoryStore

_service: SessionService | None = None


def get_session_service() -> SessionService:
    global _service
    if _service is None:
        raise RuntimeError("SessionService not initialized")
    return _service


def init_session_service(runtime: AgentRuntime) -> SessionService:
    global _service
    _service = SessionService(runtime)
    return _service


def build_default_runtime(extractor: LLMClient | None = None, solver: LLMClient | None = None) -> AgentRuntime:
    llm = MockLLM()
    return AgentRuntime(solver or llm, InMemoryStore(), extractor_llm=extractor or llm)


def build_test_gather_session(*, mock: bool = True) -> SessionService:
    """In-memory gather session for API tests."""
    session = make_gather_session(mock=mock)
    init_session_service(session.service.runtime)
    return session.service
