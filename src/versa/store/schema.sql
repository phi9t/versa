-- Event-sourced persistence for Versa conversation state compiler.

CREATE TABLE IF NOT EXISTS raw_messages (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_raw_messages_task_id ON raw_messages (task_id);

CREATE TABLE IF NOT EXISTS task_states (
    task_id TEXT PRIMARY KEY,
    version INTEGER NOT NULL,
    state_json JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS state_events (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    state_version_before INTEGER NOT NULL,
    state_version_after INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    event_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_state_events_task_id ON state_events (task_id);

CREATE TABLE IF NOT EXISTS artifacts (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    based_on_state_version INTEGER NOT NULL,
    content TEXT NOT NULL,
    verification_ids JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_artifacts_task_id ON artifacts (task_id);

CREATE TABLE IF NOT EXISTS verifications (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    passed BOOLEAN NOT NULL,
    result_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_verifications_task_id ON verifications (task_id);

-- Optimistic locking example:
-- UPDATE task_states
-- SET version = version + 1, state_json = $new_state, updated_at = now()
-- WHERE task_id = $task_id AND version = $expected_version;
