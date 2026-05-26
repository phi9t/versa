# Requirements Gathering Playbook

Interactive workflow for building a verified requirements document with Versa.

## Start the stack

```bash
# Terminal 1 — API (MockLLM for offline demo)
source .venv/bin/activate
pip install -e ".[dev,api]"
versa serve --mock --port 8000

# Terminal 2 — UI
cd ui && npm install && npm run dev
```

Open the Vite dev URL (usually http://localhost:5173). The UI proxies `/api` to the Python server.

With Codex instead of MockLLM:

```bash
versa serve --port 8000
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

```bash
pip install -e ".[dev,api]"
cd ui && npm install && npm run build
npm run test:e2e:install
npm run test:e2e
```

Tests live in `ui/e2e/` and use Playwright against `versa serve --mock` (single server: API + static UI).

## Architecture note

- **Model** — Python domain (`TaskState`, reducer, policy, verifier)
- **Controller** — FastAPI + `SessionService` (`src/versa/api/`)
- **View** — React app (`ui/src/`) — never mutates facts directly

## CLI alternatives

```bash
versa turn --task-id demo "Use scope: demo"
versa state --task-id demo --format json
versa export --task-id demo --format md
```

State is in-memory per process until Postgres persistence is wired.
