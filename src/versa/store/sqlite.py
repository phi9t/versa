from __future__ import annotations

import asyncio
import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from versa.models.state import Artifact, ArtifactStatus, TaskState, Verification
from versa.store.base import Store

_SCHEMA_PATH = Path(__file__).with_name("schema.sqlite.sql")


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


class SQLiteStore(Store):
    """File-backed Store using stdlib sqlite3."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        schema = _SCHEMA_PATH.read_text(encoding="utf-8")
        with self._lock, self._connect() as conn:
            conn.executescript(schema)
            conn.commit()

    async def _run(self, fn):
        return await asyncio.to_thread(fn)

    async def append_message(self, task_id: str, role: str, content: str) -> str:
        message_id = str(uuid4())
        created_at = _utcnow_iso()

        def _write() -> str:
            with self._lock, self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO raw_messages (id, task_id, role, content, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (message_id, task_id, role, content, created_at),
                )
                conn.commit()
            return message_id

        return await self._run(_write)

    async def list_messages(self, task_id: str) -> list[dict[str, Any]]:
        def _read() -> list[dict[str, Any]]:
            with self._lock, self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT id, task_id, role, content, created_at
                    FROM raw_messages
                    WHERE task_id = ?
                    ORDER BY created_at ASC
                    """,
                    (task_id,),
                ).fetchall()
            return [dict(row) for row in rows]

        return await self._run(_read)

    async def load_state(self, task_id: str) -> TaskState:
        def _read() -> TaskState:
            with self._lock, self._connect() as conn:
                row = conn.execute(
                    "SELECT state_json FROM task_states WHERE task_id = ?",
                    (task_id,),
                ).fetchone()
            if row is None:
                return TaskState(task_id=task_id)
            return TaskState.model_validate_json(row["state_json"])

        return await self._run(_read)

    async def save_state(
        self,
        task_id: str,
        state: TaskState,
        expected_version: int | None = None,
    ) -> None:
        state_json = state.model_dump_json()
        updated_at = _utcnow_iso()

        def _write() -> None:
            with self._lock, self._connect() as conn:
                if expected_version is not None:
                    result = conn.execute(
                        """
                        UPDATE task_states
                        SET version = ?, state_json = ?, updated_at = ?
                        WHERE task_id = ? AND version = ?
                        """,
                        (state.version, state_json, updated_at, task_id, expected_version),
                    )
                    if result.rowcount == 0:
                        existing = conn.execute(
                            "SELECT version FROM task_states WHERE task_id = ?",
                            (task_id,),
                        ).fetchone()
                        if existing is None:
                            conn.execute(
                                """
                                INSERT INTO task_states (task_id, version, state_json, updated_at)
                                VALUES (?, ?, ?, ?)
                                """,
                                (task_id, state.version, state_json, updated_at),
                            )
                            conn.commit()
                            return
                        raise ValueError(
                            f"Optimistic lock failed: expected {expected_version}, "
                            f"got {existing['version']}"
                        )
                else:
                    conn.execute(
                        """
                        INSERT INTO task_states (task_id, version, state_json, updated_at)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(task_id) DO UPDATE SET
                            version = excluded.version,
                            state_json = excluded.state_json,
                            updated_at = excluded.updated_at
                        """,
                        (task_id, state.version, state_json, updated_at),
                    )
                conn.commit()

        await self._run(_write)

    async def append_state_event(
        self,
        task_id: str,
        event_type: str,
        event_json: dict[str, Any],
        version_before: int,
        version_after: int,
    ) -> str:
        event_id = str(uuid4())
        created_at = _utcnow_iso()
        payload = json.dumps(event_json)

        def _write() -> str:
            with self._lock, self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO state_events (
                        id, task_id, state_version_before, state_version_after,
                        event_type, event_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        task_id,
                        version_before,
                        version_after,
                        event_type,
                        payload,
                        created_at,
                    ),
                )
                conn.commit()
            return event_id

        return await self._run(_write)

    async def save_artifact(self, task_id: str, artifact: Artifact) -> None:
        created_at = _utcnow_iso()

        def _write() -> None:
            with self._lock, self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO artifacts (
                        id, task_id, kind, status, based_on_state_version,
                        content, verification_ids, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        task_id = excluded.task_id,
                        kind = excluded.kind,
                        status = excluded.status,
                        based_on_state_version = excluded.based_on_state_version,
                        content = excluded.content,
                        verification_ids = excluded.verification_ids,
                        created_at = excluded.created_at
                    """,
                    (
                        artifact.id,
                        task_id,
                        artifact.kind,
                        artifact.status.value,
                        artifact.based_on_state_version,
                        artifact.content,
                        json.dumps(artifact.verification_ids),
                        created_at,
                    ),
                )
                conn.commit()

        await self._run(_write)

    async def get_artifact(self, task_id: str, artifact_id: str) -> Artifact | None:
        def _read() -> Artifact | None:
            with self._lock, self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT id, kind, status, based_on_state_version, content, verification_ids
                    FROM artifacts
                    WHERE task_id = ? AND id = ?
                    """,
                    (task_id, artifact_id),
                ).fetchone()
            if row is None:
                return None
            return Artifact(
                id=row["id"],
                kind=row["kind"],
                status=ArtifactStatus(row["status"]),
                based_on_state_version=row["based_on_state_version"],
                content=row["content"],
                verification_ids=json.loads(row["verification_ids"]),
            )

        return await self._run(_read)

    async def save_verification(self, task_id: str, verification: Verification) -> None:
        created_at = verification.created_at.astimezone(UTC).isoformat()
        result_json = verification.model_dump_json()

        def _write() -> None:
            with self._lock, self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO verifications (
                        id, task_id, artifact_id, passed, result_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        task_id = excluded.task_id,
                        artifact_id = excluded.artifact_id,
                        passed = excluded.passed,
                        result_json = excluded.result_json,
                        created_at = excluded.created_at
                    """,
                    (
                        verification.id,
                        task_id,
                        verification.artifact_id,
                        int(verification.passed),
                        result_json,
                        created_at,
                    ),
                )
                conn.commit()

        await self._run(_write)
