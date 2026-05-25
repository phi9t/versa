# Engineering Design: Codex CLI LLM Substrate

**Workstream:** `codex-cli-substrate`  
**Status:** Complete (v1)  
**Owner:** Versa  
**v1 scope:** CLI only (`codex exec`). SDK deferred to [RFC 0001](../../docs/rfc/0001-codex-app-server-sdk.md).

## 1. Problem statement

Versa compiles user turns into authoritative `TaskState` and generates solver artifacts from clean context. Production requires a real LLM backend. **Codex CLI** is the v1 substrate: each Versa LLM call maps to an isolated `codex exec` invocation.

**Non-goal:** Pass raw chat transcripts to Codex (SHARDED failure mode).  
**Goal:** CONCAT-style compiled prompts per call with `--ephemeral` isolation.

## 2. Architecture

```text
User ──► versa chat/turn ──► AgentRuntime.handle_user_turn
                              │
                              ├─► extract_delta ──► CodexCLIClient.generate_json(TurnDelta)
                              │                      codex exec --output-schema --ephemeral
                              ├─► apply_delta (deterministic)
                              ├─► choose_next_action
                              └─► generate_candidate ──► CodexCLIClient.generate
                                                       codex exec -o artifact --ephemeral
                              └─► verify_artifact (local, unchanged)
```

### Component map

| Component | Path | Responsibility |
|-----------|------|----------------|
| `LLMClient` | `src/versa/llm/base.py` | Abstract `generate` / `generate_json` |
| `CodexCLIClient` | `src/versa/llm/codex_cli.py` | Subprocess `codex exec` |
| `pydantic_model_to_codex_schema` | `src/versa/llm/schema.py` | Strict JSON Schema for `--output-schema` |
| `make_codex_clients` | `src/versa/llm/factory.py` | Extractor (read-only) + solver (optional cwd) |
| `AgentRuntime` | `src/versa/orchestrator.py` | `extractor_llm` / `solver_llm` split |
| `versa` CLI | `src/versa/cli.py` | `doctor`, `chat`, `turn` |

## 3. CodexCLIClient design

### 3.1 Configuration

```python
@dataclass
class CodexCLIConfig:
    executable: str = "codex"          # or CODEX_EXECUTABLE env
    model: str | None = None           # VERSA_CODEX_MODEL
    profile: str | None = None         # VERSA_CODEX_PROFILE
    cwd: str | None = None             # -C / --cd
    sandbox: Literal["read-only", "workspace-write", "danger-full-access"] = "read-only"
    skip_git_repo_check: bool = True
    ephemeral: bool = True
    timeout_s: float = 600.0
    extra_args: list[str] = field(default_factory=list)
```

### 3.2 Invocation contract

Base argv for every call:

```text
codex exec --ephemeral --skip-git-repo-check -s <sandbox> -o <tmp_out> [ -m model ] [ -p profile ] [ -C cwd ] [ --output-schema schema.json ] [ extra_args... ] <short_prompt>
```

- Long prompts: also pipe full prompt on **stdin** (Codex appends stdin block after arg prompt).
- Read result from `-o` file only on exit code 0.
- On failure: raise `CodexExecError(exit_code, stderr, stdout)`; do not treat stale `-o` as success.

### 3.3 Response parsing

| Method | Output handling |
|--------|-----------------|
| `generate` | Strip whitespace from `-o` file; strip markdown fences if present |
| `generate_json` | `json.loads` + `schema.model_validate`; tolerate ```json fences |

## 4. JSON Schema (TurnDelta)

Codex requires **strict** schema (`additionalProperties: false`).

`pydantic_model_to_codex_schema()` inlines `$defs`, strictifies objects, sets `required` on all property keys.

## 5. AgentRuntime changes

- `extract_delta` → `extractor_llm`
- `generate_candidate` → `solver_llm`

## 6. CLI (`versa`)

| Command | Behavior |
|---------|----------|
| `versa doctor` | Run `codex doctor` |
| `versa chat` | REPL loop |
| `versa turn MSG` | Single shot |

## 7. Security

- Default sandbox: `read-only`
- Auth via `codex login`; no secrets in repo

## 8. Testing

- Unit: mock subprocess
- Integration: `@pytest.mark.integration`, requires codex

## 9. References

- RFC 0001: SDK follow-up
- `codex exec --help`
