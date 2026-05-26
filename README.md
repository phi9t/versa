# Versa

Conversation **state compiler** between raw chat transcripts and solver models.

## Invariant

Authoritative task state is built only from:

- User-stated facts (with evidence spans)
- Verified tool results
- User-confirmed decisions

Assistant outputs are **candidates** in `ArtifactStore`, never facts, until verified.

## Architecture

```text
RawMessageLog     append-only transcript (audit / replay)
TaskState         authoritative user-grounded state
ArtifactStore     untrusted drafts until verification
```

## Install

Requires **Python 3.12+**.

From a [GitHub release](https://github.com/phi9t/versa/releases) wheel:

```bash
pip install https://github.com/phi9t/versa/releases/download/v0.1.0/versa-0.1.0-py3-none-any.whl
```

From source (development):

```bash
git clone https://github.com/phi9t/versa.git
cd versa
pip install -e ".[dev]"
```

## Quick start (Codex CLI)

```bash
codex login   # once
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
versa doctor
versa chat --task-id demo
```

## Requirements gathering UI

Interactive web UI for evidence-backed requirements collection and document synthesis:

```bash
pip install -e ".[dev,api]"
versa serve --mock --port 8000 --db .versa/state.db   # or omit --mock when Codex is ready

cd ui && npm install && npm run dev
```

Terminal TUI (same controller and snapshot model as the web UI):

```bash
pip install -e ".[dev,tui]"
versa gather --mock --db .versa/state.db --task-id demo
```

Tabs: Chat, Facts, Slots, Questions, Document, Export. Keys: `1`–`6` switch tabs, `Ctrl+E` export markdown, `m`/`j` in Export tab.

E2E tests (Playwright):

```bash
cd ui && npm run build && npm run test:e2e:install && npm run test:e2e
```

See [docs/gather-playbook.md](docs/gather-playbook.md) for the full session workflow.

`versa chat` uses an in-memory store by default: state persists for the REPL session only, not across separate CLI invocations. Use the same `--task-id` in a new process only after Postgres persistence is wired up.

Single turn:

```bash
versa turn "Write a Python function named clamp that bounds a number."
```

### Environment

| Variable | Purpose |
|----------|---------|
| `VERSA_DB_PATH` | SQLite database path (used with `--db`) |
| `CODEX_EXECUTABLE` | Path to `codex` binary (default: `codex`) |
| `VERSA_CODEX_MODEL` | `-m` model override |
| `VERSA_CODEX_PROFILE` | `-p` config profile |
| `VERSA_CODEX_EXTRA_ARGS` | Extra `codex exec` args (shell-quoted; cannot override sandbox) |

### Tests without Codex

```bash
pytest -q -m "not integration"
```

With Codex auth:

```bash
pytest -q -m integration
```

### Mock LLM (development)

```python
from versa.llm.mock import MockLLM
from versa.orchestrator import AgentRuntime
from versa.store.memory import InMemoryStore

runtime = AgentRuntime(MockLLM(), InMemoryStore())  # MockLLM acts as solver
```

## Future: App-Server SDK

See [docs/rfc/0001-codex-app-server-sdk.md](docs/rfc/0001-codex-app-server-sdk.md) for the proposed `codex_app_server` adapter (v2, not implemented in v1).

## Workstream

Engineering design and task tracker: [.workstreams/codex-cli-substrate/](.workstreams/codex-cli-substrate/)

## Layout

| Module | Role |
|--------|------|
| `versa.models` | Pydantic `TaskState`, `TurnDelta`, artifacts |
| `versa.reducer` | Deterministic delta application |
| `versa.policy` | Readiness gate (`choose_next_action`) |
| `versa.solver` | Clean solver context builder |
| `versa.verifier` | Artifact verification hooks |
| `versa.orchestrator` | `AgentRuntime` turn loop |
| `versa.llm.codex_cli` | `codex exec` substrate |
| `versa.cli` | `versa doctor \| chat \| turn \| gather \| serve` |
| `versa.gather` | Shared gather session factory, formatters, Textual TUI |
| `versa.store` | In-memory MVP store + SQLite + Postgres DDL |

## Postgres

Apply `src/versa/store/schema.sql` for event-sourced persistence.

## Releases

CI runs on every push to `main` and on pull requests. Pushing a semver tag (`v0.1.0`) builds wheel/sdist artifacts and publishes a GitHub Release.

See [docs/RELEASING.md](docs/RELEASING.md) for the maintainer checklist.
