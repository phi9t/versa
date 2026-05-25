# RFC 0001: Codex App-Server SDK as Versa LLM Substrate

| Field | Value |
|-------|-------|
| Status | **Proposed / Not implemented** |
| Versa v1 | `codex exec` via `CodexCLIClient` only |
| Authors | Versa |

## 1. Summary

Versa v1 uses **`codex exec`** ([`CodexCLIClient`](../src/versa/llm/codex_cli.py)). This RFC specifies a future **`CodexAppServerClient`** implementing the same [`LLMClient`](../src/versa/llm/base.py) interface for lower latency, streaming UX, and structured errors—without violating Versa state invariants.

## 2. Motivation

- CLI spawns 2–4 processes per user turn (extract, solve, retries).
- `versa chat` cannot show turn progress without JSONL hacks.
- Eval/debug benefits from `RunResult.items`, token usage, `TurnError`.
- Monorepo users may have `codex_app_server` at `codex/sdk/python`.

## 3. Non-goals

- Replacing `TaskState` with Codex thread history.
- Using `thread_resume` for multi-turn memory.
- Required SDK dependency on PyPI v1.

## 4. SDK surface

**Package:** `openai-codex-app-server-sdk` (local: `codex/sdk/python`)

```python
from codex_app_server import AsyncCodex, TextInput

async with AsyncCodex() as codex:
    thread = await codex.thread_start(ephemeral=True, sandbox="read-only")
    result = await thread.run(
        TextInput(prompt),
        output_schema=schema_dict,
        cwd=repo,
    )
```

| Param | Extractor | Solver |
|-------|-----------|--------|
| `output_schema` | `TurnDelta` strict schema | omit |
| `cwd` | optional read-only | repo root |
| `sandbox_policy` | read-only | read-only / workspace-write (agentic) |

**Constraint:** one active turn consumer per client (experimental API).

## 5. Invariant contract

```text
Versa TaskState is the only authoritative multi-turn memory.
Codex threads are disposable single-turn workers.
```

1. Every `LLMClient` call → `thread_start(ephemeral=True)`.
2. **Never** `thread_resume` from Versa.
3. Prompt = only `build_extractor_prompt` / `build_solver_context`.
4. Never pass `RawMessageLog` or assistant artifacts into SDK input.
5. Do not store Codex thread ids in `TaskState`.
6. CI: forbid `thread_resume` under `src/versa/`.

## 6. Proposed adapter (v2)

**File:** `src/versa/llm/codex_app_server.py`

```python
class CodexAppServerClient(LLMClient):
    async def generate(self, prompt: str) -> str:
        return await self._run_turn(prompt, output_schema=None)

    async def generate_json(self, prompt, schema) -> dict:
        return json.loads(
            await self._run_turn(
                prompt,
                output_schema=pydantic_model_to_codex_schema(schema),
            )
        )

    async def _run_turn(self, prompt, *, output_schema):
        thread = await self._codex.thread_start(ephemeral=True, ...)
        result = await thread.run(TextInput(prompt), output_schema=output_schema, ...)
        if result.error:
            raise CodexTurnError(result.error)
        return result.final_response or ""
```

**Session:** one `AsyncCodex` per `versa chat` REPL; still **new ephemeral thread per LLM call**.

**Factory (v2):** `VERSA_CODEX_BACKEND=cli|sdk` (default `cli`).

## 7. CLI ↔ SDK mapping

| CLI | SDK |
|-----|-----|
| `--ephemeral` | `thread_start(ephemeral=True)` |
| `--output-schema file` | `output_schema=dict` |
| `-o file` | `final_response` |
| `--sandbox` | `sandbox_policy` |
| `-C` | `cwd` |
| `--json` | `TurnHandle.stream()` |

## 8. Streaming (v2 `versa chat`)

Stream via `turn(...).stream()` for UX; only verified artifacts become authoritative.

## 9. Error handling

| Failure | CLI | SDK v2 |
|---------|-----|--------|
| Auth | exit 1 | `Codex()` init fails |
| Turn failed | exit 1, `-o` may be stale | `RunResult.error` |
| Timeout | kill subprocess | turn cancel |

Retry: Versa regenerates from `TaskState` + verifier failures—not Codex resume.

## 10. Testing (v2)

- Mock `AsyncCodex` unit tests
- Contract: no `thread_resume` in adapter
- Parity: same fixture, CLI vs SDK backends

## 11. Packaging

```toml
[project.optional-dependencies]
codex-sdk = ["openai-codex-app-server-sdk>=0.116.0a1"]
```

## 12. Open questions

- One `AsyncCodex` for extractor+solver or two?
- Approval policy for CI automation?
- Deprecate CLI when SDK stabilizes?
- Agentic solver: who runs pytest—Versa or Codex?

## 13. Acceptance criteria (v2 done)

- [ ] `VERSA_CODEX_BACKEND=sdk versa chat` completes clamp-style task
- [ ] Deleting assistant messages does not change behavior
- [ ] No `thread_resume` in codebase
- [ ] CLI/SDK parity integration test
- [ ] RFC status → Accepted

## 14. References

- `codex/sdk/python/docs/getting-started.md`
- `codex/sdk/python/docs/api-reference.md`
- `.workstreams/codex-cli-substrate/design.md`
