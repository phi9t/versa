from __future__ import annotations

from pathlib import Path

from versa.llm.base import LLMClient
from versa.llm.codex_cli import CodexCLIClient, CodexCLIConfig


def _client(*, cwd: str | None, model: str | None, profile: str | None) -> CodexCLIClient:
    return CodexCLIClient(
        CodexCLIConfig(
            model=model,
            profile=profile,
            sandbox="read-only",
            cwd=cwd,
        )
    )


def make_codex_clients(
    *,
    repo_root: Path | str | None = None,
    model: str | None = None,
    profile: str | None = None,
) -> tuple[LLMClient, LLMClient]:
    """Build extractor (read-only) and solver (optional repo cwd) Codex CLI clients."""
    cwd = str(repo_root) if repo_root else None
    return _client(cwd=None, model=model, profile=profile), _client(
        cwd=cwd, model=model, profile=profile
    )
