import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from versa.llm.codex_cli import (
    CodexCLIClient,
    CodexCLIConfig,
    CodexExecError,
    _safe_extra_args,
    _strip_markdown_fences,
)
from versa.models.delta import TurnDelta


def test_build_argv_includes_ephemeral_and_sandbox():
    client = CodexCLIClient(CodexCLIConfig(executable="codex", model="gpt-5"))
    argv = client._build_argv(Path("/tmp/out.txt"))
    assert argv[0] == "codex"
    assert "exec" in argv
    assert "--ephemeral" in argv
    assert "--skip-git-repo-check" in argv
    assert "-m" in argv and "gpt-5" in argv
    assert "-s" in argv and "read-only" in argv


def test_safe_extra_args_strips_sandbox_override():
    args = _safe_extra_args(["-s", "danger-full-access", "--model", "gpt-5"])
    assert "-s" not in args
    assert "danger-full-access" not in args
    assert args == ["--model", "gpt-5"]


def test_strip_markdown_fences():
    assert _strip_markdown_fences("```python\nx=1\n```") == "x=1"


@pytest.mark.asyncio
async def test_generate_json_raises_on_nonzero_exit():
    with patch("versa.llm.codex_cli.asyncio.create_subprocess_exec") as mock_exec:
        proc = AsyncMock()
        proc.returncode = 1
        proc.communicate = AsyncMock(return_value=(b"", b"boom"))
        mock_exec.return_value = proc

        client = CodexCLIClient(CodexCLIConfig(timeout_s=5))
        with pytest.raises(CodexExecError) as exc_info:
            await client.generate_json("test", TurnDelta)
        assert exc_info.value.exit_code == 1


@pytest.mark.asyncio
async def test_generate_json_parses_response():
    client = CodexCLIClient()

    payload = {
        "user_intent_summary": "intent",
        "fact_patches": [],
        "assumption_patches": [],
        "new_questions_for_user": [],
    }

    async def fake_run(prompt, schema_model=None):
        return json.dumps(payload)

    with patch.object(client, "_run_codex", side_effect=fake_run):
        delta = await client.generate_json("prompt", TurnDelta)
        assert delta.user_intent_summary == "intent"


@pytest.mark.asyncio
async def test_generate_json_argv_includes_output_schema(tmp_path):
    captured: dict = {}

    async def fake_exec(*args, **kwargs):
        captured["args"] = list(args)
        captured["stdin"] = kwargs.get("stdin")
        proc = AsyncMock()
        proc.returncode = 0
        proc.communicate = AsyncMock(return_value=(b"", b""))

        out_idx = list(args).index("-o") + 1
        out_path = args[out_idx]
        schema_idx = list(args).index("--output-schema") + 1
        schema_path = args[schema_idx]
        captured["schema_exists"] = Path(schema_path).exists()

        Path(out_path).write_text(
            json.dumps(
                {
                    "fact_patches": [],
                    "assumption_patches": [],
                    "new_questions_for_user": [],
                }
            ),
            encoding="utf-8",
        )
        return proc

    with patch("versa.llm.codex_cli.asyncio.create_subprocess_exec", side_effect=fake_exec):
        client = CodexCLIClient(CodexCLIConfig(timeout_s=5))
        await client.generate_json("full extractor prompt body", TurnDelta)

    assert "--output-schema" in captured["args"]
    assert "--ephemeral" in captured["args"]
    assert captured.get("schema_exists") is True
    assert captured["stdin"] is asyncio.subprocess.PIPE


@pytest.mark.asyncio
async def test_run_codex_sends_prompt_on_stdin():
    captured: dict = {}

    async def fake_exec(*args, **kwargs):
        captured["stdin"] = kwargs.get("stdin")
        proc = AsyncMock()
        proc.returncode = 0

        async def communicate(data):
            captured["stdin_bytes"] = data
            out_idx = list(args).index("-o") + 1
            Path(args[out_idx]).write_text("ok", encoding="utf-8")
            return b"", b""

        proc.communicate = communicate
        return proc

    with patch("versa.llm.codex_cli.asyncio.create_subprocess_exec", side_effect=fake_exec):
        client = CodexCLIClient(CodexCLIConfig(timeout_s=5))
        await client.generate("prompt sent via stdin")

    assert captured["stdin"] is asyncio.subprocess.PIPE
    assert captured["stdin_bytes"] == b"prompt sent via stdin"
