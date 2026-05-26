# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What Versa is

Versa is a conversation **state compiler** sitting between raw chat transcripts and solver
models. Its central invariant governs every design decision:

> Authoritative task state is built **only** from user-stated facts (with evidence spans),
> verified tool results, and user-confirmed decisions. Assistant outputs are *candidates* —
> never facts — until verified.

This invariant is enforced two ways at once, and changes must preserve both:
- **Structurally** — LLM-extracted info flows only through `TurnDelta` → `reducer.apply_delta`;
  assistant generations become `Artifact`s with `status=DRAFT` that must pass `verifier` before
  becoming `state.active_artifact_id`.
- **In prompts** — `solver.py` re-renders context from *active facts only* each turn and tells
  the model "do not rely on previous assistant drafts."

## Commands

```bash
pip install -e ".[dev]"          # dev install (Python 3.12+)
pytest -q -m "not integration"   # unit tests — no Codex/network needed (this is what CI runs)
pytest -q -m integration         # e2e tests — require `codex login` + the codex binary
pytest tests/test_reducer.py -q  # single file
pytest tests/test_reducer.py::test_name -q   # single test
python -m build                  # build wheel + sdist
```

There is **no linter/formatter configured** and no type-check step in CI; `pytest` is the only gate.
`asyncio_mode = "auto"` is set, so `async def test_*` functions need no `@pytest.mark.asyncio`.

CLI (entry point `versa = versa.cli:main`):
```bash
versa doctor                     # exits 0 iff `codex doctor` succeeds
versa chat --task-id demo        # interactive REPL (in-memory state, this process only)
versa turn "write a clamp fn"    # single turn
```

## The turn loop (the spine of the system)

`AgentRuntime.handle_user_turn` (`orchestrator.py`) is a thin state machine; the intelligence
lives in pure, independently-tested functions. One user turn runs:

1. `store.append_message` — record raw user text in the append-only log.
2. `extract_delta` → `extractor_llm.generate_json(schema=TurnDelta)` — the **only** place user
   text becomes structured state. Every fact patch carries a verbatim `evidence_quote`.
3. `reducer.apply_delta` — **deterministic, the sole mutator of facts.** Handles the fact
   lifecycle (`add`/`update`/`supersede`/`reject`), raises an `OpenQuestion` on conflicting
   values, and prunes questions whose `related_keys` are now satisfied. Bumps `state.version`.
4. `policy.choose_next_action` — readiness gate returning one of:
   - `ASK_CLARIFICATION` — blocking questions exist or required slots are missing.
   - `GENERATE_CANDIDATE` — state is ready; build + verify an artifact.
   - `FINALIZE_VERIFIED_ARTIFACT` — a verified artifact is already active.
5. On `GENERATE_CANDIDATE`: `_generate_verify_respond` loops up to `max_retries` (default 2):
   `solver.build_coding_solver_context` → `solver_llm.generate` → `verifier.verify_artifact` →
   `verifier.commit_artifact`. Failed verifications feed their `failures` back into the next
   prompt; only a passing verification sets `active_artifact_id`.

Every state transition also writes a `state_event` (`delta_applied`, `artifact_committed`) with
`version_before`/`version_after` for event-sourced replay.

## Module map and where logic lives

| Module | Role / what to know |
|--------|--------------------|
| `models/state.py` | `TaskState`, `Fact` (+ `FactStatus`/`FactKind` lifecycle), `Artifact`, `Verification`, `OpenQuestion`. `CodeTaskState` is a richer subclass for repo edits. |
| `models/delta.py` | `TurnDelta` — the extractor's output schema (`FactPatch`/`AssumptionPatch`). |
| `reducer.py` | Deterministic delta application + fact queries (`find_active_fact`, `active_facts`). Pure; no I/O. |
| `policy.py` | `choose_next_action` + `infer_required_slots`. **Required slots are keyed off the `objective` fact's value** (e.g. `write_python_function` requires `function_name`, `input_format`, …). Add new task types here. |
| `solver.py` | Builds the *clean* solver prompt and `classify_artifact_kind` (objective value → artifact kind). Prompts are deliberately amnesiac. |
| `verifier.py` | `verify_artifact` dispatches by `artifact.kind`: `code`→`ast.parse` + fact checks, `sql`→SELECT/table checks, else an LLM-judge rubric. Verifiers are heuristic, not sandboxed execution. |
| `orchestrator.py` | `AgentRuntime` — the turn loop above. |
| `llm/base.py` | `LLMClient` ABC: `generate` (free text) + `generate_json` (typed). Two roles wired in `AgentRuntime`: extractor + solver (default to the same client). |
| `llm/codex_cli.py` | Default substrate: shells out to `codex exec`. See safety notes below. |
| `llm/schema.py` | Converts Pydantic models to the strict JSON Schema `codex exec --output-schema` requires (inlines `$refs`, forces `additionalProperties:false`, all-required). |
| `llm/mock.py` | `MockLLM` for tests — no network. Used in `tests/conftest.py`'s `mock_runtime`. |
| `store/base.py` | `Store` ABC. `store/memory.py` `InMemoryStore` is the only implementation. `store/schema.sql` is the event-sourced Postgres DDL (not yet wired — `[postgres]` extra exists but no client). |

## Codex CLI substrate — safety constraints

`CodexCLIClient` runs `codex exec` as a subprocess with **sandbox hard-locked to `read-only`**.
`_safe_extra_args` strips any user-supplied `-s`/`--sandbox`/`--dangerously-bypass-...` flags from
`VERSA_CODEX_EXTRA_ARGS` so the sandbox cannot be widened via env. Preserve this when touching
arg-building. Output is read from a temp `-o last-message.txt` file (not stdout);
`_strip_markdown_fences` cleans fenced responses. Relevant env vars: `CODEX_EXECUTABLE`,
`VERSA_CODEX_MODEL`, `VERSA_CODEX_PROFILE`, `VERSA_CODEX_EXTRA_ARGS`.

## Conventions

- All modules start with `from __future__ import annotations`; models are Pydantic v2.
- State is **immutable-by-copy**: mutators do `state.model_copy(deep=True)` then bump `version`.
- New requirement types are added by extending `infer_required_slots` (policy) +
  `classify_artifact_kind` (solver) + a verifier branch — these three must stay in sync.
- Tests split on the `integration` marker (registered in `pyproject.toml`); keep network/Codex
  needs behind it so the default `pytest -q -m "not integration"` stays hermetic.

## State persistence caveat

`versa chat`/`turn` use `InMemoryStore`, so state lives only for one process. Reusing a
`--task-id` across separate invocations does nothing until a persistent `Store` is wired up.
