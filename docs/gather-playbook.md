# Requirements Gathering Playbook

Interactive workflow for building a verified requirements document with Versa.

## Start the stack (prod)

```bash
source .venv/bin/activate
pip install -e ".[dev,api]"
codex login
versa doctor

mkdir -p .versa
cd ui && npm install && npm run build && cd ..
versa serve --port 8000 --db .versa/state.db
```

Open **http://localhost:8000** (built UI served from `ui/dist`).

Offline demo with MockLLM:

```bash
versa serve --mock --port 8000 --db .versa/state.db
```

Dev UI iteration (optional — Vite proxies `/api`):

```bash
versa serve --port 8000 --db .versa/state.db   # terminal 1
cd ui && npm run dev                            # terminal 2 → http://localhost:5173
```

## Session flow

### 1. Seed

In **Chat**, send:

```text
Gather requirements for [project name].
Objective: write a requirements specification document.
Ask one blocking question at a time. Do not synthesize until I say "Proceed with synthesis".
```

### 2. Fill slots

Use explicit shard messages:

```text
Use scope: REST API for invoice PDF generation
Use target_users: finance operations teams
Use functional_requirements: ["idempotent POST /invoices", "webhook on completion"]
Use non_functional_requirements: ["p99 latency under 500ms"]
Use constraints: ["no PII in logs"]
Use success_criteria: ["100% delivery rate for valid requests"]
```

Watch progress in **Slots** and audit evidence in **Facts**.

### 3. Synthesize

When **Slots** shows ready:

```text
Proceed with synthesis.
```

The verified document appears in **Document**. **Export** provides deterministic markdown without another LLM call.

## E2E tests

Requires Codex auth locally (`codex login`, `versa doctor`):

```bash
pip install -e ".[dev,api]"
cd ui && npm install && npm run build
npm run test:e2e:install
npm run test:e2e
```

Playwright starts the prod stack: `versa serve --db ui/e2e/.test-state.db` (real Codex). Offline fallback:

```bash
VERSA_E2E_MOCK=1 npm run test:e2e
```

## Architecture note

- **Model** — Python domain (`TaskState`, reducer, policy, verifier)
- **Controller** — FastAPI + `SessionService` (`src/versa/api/`)
- **View** — React app (`ui/src/`) — never mutates facts directly
- **Store** — SQLite file via `--db` / `VERSA_DB_PATH` (default in-memory without flag)

## CLI alternatives

```bash
versa turn --db .versa/state.db --task-id demo "Use scope: demo"
versa state --db .versa/state.db --task-id demo --format json
versa export --db .versa/state.db --task-id demo --format md
```

Sessions persist in the SQLite file across API restarts when `--db` is set.
