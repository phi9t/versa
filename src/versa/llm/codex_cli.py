from __future__ import annotations

import asyncio
import json
import os
import re
import shlex
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel

from versa.llm.base import LLMClient
from versa.llm.schema import codex_schema_json

T = TypeVar("T", bound=BaseModel)


def _default_extra_args() -> list[str]:
    raw = os.environ.get("VERSA_CODEX_EXTRA_ARGS", "").strip()
    if not raw:
        return []
    return shlex.split(raw)


class CodexExecError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        exit_code: int,
        stderr: str = "",
        stdout: str = "",
    ) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.stderr = stderr
        self.stdout = stdout


@dataclass
class CodexCLIConfig:
    executable: str = field(
        default_factory=lambda: os.environ.get("CODEX_EXECUTABLE", "codex")
    )
    model: str | None = field(
        default_factory=lambda: os.environ.get("VERSA_CODEX_MODEL") or None
    )
    profile: str | None = field(
        default_factory=lambda: os.environ.get("VERSA_CODEX_PROFILE") or None
    )
    cwd: str | None = None
    sandbox: Literal["read-only"] = "read-only"
    skip_git_repo_check: bool = True
    ephemeral: bool = True
    timeout_s: float = 600.0
    extra_args: list[str] = field(default_factory=_default_extra_args)


def codex_is_ready() -> bool:
    import shutil
    import subprocess

    codex = shutil.which("codex")
    if not codex:
        return False
    return subprocess.run([codex, "doctor"], capture_output=True, check=False).returncode == 0


class CodexCLIClient(LLMClient):
    def __init__(self, config: CodexCLIConfig | None = None) -> None:
        self.config = config or CodexCLIConfig()

    async def generate(self, prompt: str) -> str:
        text = await self._run_codex(prompt, schema_model=None)
        return _strip_markdown_fences(text)

    async def generate_json(self, prompt: str, schema: type[T]) -> T:
        text = await self._run_codex(prompt, schema_model=schema)
        return schema.model_validate(json.loads(_strip_markdown_fences(text, json_mode=True)))

    async def _run_codex(self, prompt: str, *, schema_model: type[BaseModel] | None) -> str:
        with tempfile.TemporaryDirectory(prefix="versa-codex-") as tmp:
            tmp_path = Path(tmp)
            out_file = tmp_path / "last-message.txt"

            argv = self._build_argv(out_file)

            if schema_model is not None:
                schema_path = tmp_path / "schema.json"
                schema_path.write_text(codex_schema_json(schema_model), encoding="utf-8")
                argv.extend(["--output-schema", str(schema_path)])

            argv.append("Versa state-compiler call. Follow instructions in stdin exactly.")

            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(prompt.encode("utf-8")),
                    timeout=self.config.timeout_s,
                )
            except asyncio.TimeoutError as exc:
                proc.kill()
                await proc.wait()
                raise CodexExecError(
                    f"codex exec timed out after {self.config.timeout_s}s",
                    exit_code=-1,
                    stderr="timeout",
                ) from exc

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            exit_code = 0 if proc.returncode is None else proc.returncode

            if exit_code != 0:
                raise CodexExecError(
                    f"codex exec failed with exit code {exit_code}",
                    exit_code=exit_code,
                    stderr=stderr,
                    stdout=stdout,
                )

            if not out_file.exists():
                raise CodexExecError(
                    "codex exec succeeded but -o output file is missing",
                    exit_code=exit_code,
                    stderr=stderr,
                    stdout=stdout,
                )

            return out_file.read_text(encoding="utf-8")

    def _build_argv(self, out_file: Path) -> list[str]:
        cfg = self.config
        argv: list[str] = [
            cfg.executable,
            "exec",
            "-o",
            str(out_file),
            "-s",
            cfg.sandbox,
        ]

        if cfg.ephemeral:
            argv.append("--ephemeral")
        if cfg.skip_git_repo_check:
            argv.append("--skip-git-repo-check")
        if cfg.model:
            argv.extend(["-m", cfg.model])
        if cfg.profile:
            argv.extend(["-p", cfg.profile])
        if cfg.cwd:
            argv.extend(["-C", cfg.cwd])
        argv.extend(_safe_extra_args(cfg.extra_args))
        return argv


_FORBIDDEN_EXTRA_PREFIXES = (
    "-s",
    "--sandbox",
    "--dangerously-bypass-approvals-and-sandbox",
)


def _safe_extra_args(extra_args: list[str]) -> list[str]:
    safe: list[str] = []
    i = 0
    while i < len(extra_args):
        arg = extra_args[i]
        if any(arg == prefix or arg.startswith(f"{prefix}=") for prefix in _FORBIDDEN_EXTRA_PREFIXES):
            i += 2 if i + 1 < len(extra_args) and not extra_args[i + 1].startswith("-") else 1
            continue
        safe.append(arg)
        i += 1
    return safe


def _strip_markdown_fences(text: str, *, json_mode: bool = False) -> str:
    stripped = text.strip()
    pattern = r"```(?:json)?\s*([\s\S]*?)\s*```" if json_mode else r"```[\w]*\s*([\s\S]*?)\s*```"
    fence = re.search(pattern, stripped, re.I if json_mode else 0)
    if fence:
        return fence.group(1).strip()
    return stripped
