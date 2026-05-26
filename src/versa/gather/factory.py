from __future__ import annotations

from versa.api.session_service import SessionService
from versa.gather.session import GatherSession
from versa.llm.factory import make_codex_clients
from versa.llm.mock import MockLLM
from versa.orchestrator import AgentRuntime
from versa.store.factory import make_store, resolve_db_path

GATHER_DEFAULT_OBJECTIVE = "write_requirements_doc"


def build_runtime(
    *,
    db_path: str | None = None,
    mock: bool = False,
    repo_root: str | None = None,
    model: str | None = None,
    profile: str | None = None,
    default_objective: str | None = GATHER_DEFAULT_OBJECTIVE,
) -> AgentRuntime:
    store = make_store(resolve_db_path(db_path))
    if mock:
        llm = MockLLM()
        return AgentRuntime(
            llm,
            store,
            extractor_llm=llm,
            default_objective=default_objective,
        )
    extractor, solver = make_codex_clients(
        repo_root=repo_root,
        model=model,
        profile=profile,
    )
    return AgentRuntime(
        solver,
        store,
        extractor_llm=extractor,
        default_objective=default_objective,
    )


def make_gather_session(
    *,
    db_path: str | None = None,
    mock: bool = False,
    repo_root: str | None = None,
    model: str | None = None,
    profile: str | None = None,
    default_objective: str | None = GATHER_DEFAULT_OBJECTIVE,
) -> GatherSession:
    runtime = build_runtime(
        db_path=db_path,
        mock=mock,
        repo_root=repo_root,
        model=model,
        profile=profile,
        default_objective=default_objective,
    )
    return GatherSession(SessionService(runtime))


def make_gather_runtime_from_args(args, *, mock: bool = False) -> AgentRuntime:
    """Build runtime from argparse Namespace (cli turn args + db)."""
    return build_runtime(
        db_path=getattr(args, "db", None),
        mock=mock,
        repo_root=getattr(args, "repo", None),
        model=getattr(args, "model", None),
        profile=getattr(args, "profile", None),
        default_objective=None,
    )
