from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from versa.models.state import Artifact, TaskState, Verification
from versa.store.base import Store


class InMemoryStore(Store):
    """MVP append-only log + state + artifact stores."""

    def __init__(self) -> None:
        self._messages: dict[str, list[dict[str, Any]]] = {}
        self._states: dict[str, TaskState] = {}
        self._artifacts: dict[str, dict[str, Artifact]] = {}
        self._verifications: dict[str, list[Verification]] = {}
        self._events: dict[str, list[dict[str, Any]]] = {}

    async def append_message(self, task_id: str, role: str, content: str) -> str:
        message_id = str(uuid4())
        self._messages.setdefault(task_id, []).append(
            {
                "id": message_id,
                "task_id": task_id,
                "role": role,
                "content": content,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        return message_id

    async def list_messages(self, task_id: str) -> list[dict[str, Any]]:
        return list(self._messages.get(task_id, []))

    async def load_state(self, task_id: str) -> TaskState:
        if task_id not in self._states:
            self._states[task_id] = TaskState(task_id=task_id)
        return self._states[task_id].model_copy(deep=True)

    async def save_state(
        self,
        task_id: str,
        state: TaskState,
        expected_version: int | None = None,
    ) -> None:
        current = self._states.get(task_id)
        if expected_version is not None and current is not None:
            if current.version != expected_version:
                raise ValueError(
                    f"Optimistic lock failed: expected {expected_version}, "
                    f"got {current.version}"
                )
        self._states[task_id] = state.model_copy(deep=True)

    async def append_state_event(
        self,
        task_id: str,
        event_type: str,
        event_json: dict[str, Any],
        version_before: int,
        version_after: int,
    ) -> str:
        event_id = str(uuid4())
        self._events.setdefault(task_id, []).append(
            {
                "id": event_id,
                "task_id": task_id,
                "state_version_before": version_before,
                "state_version_after": version_after,
                "event_type": event_type,
                "event_json": event_json,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
        return event_id

    async def save_artifact(self, task_id: str, artifact: Artifact) -> None:
        self._artifacts.setdefault(task_id, {})[artifact.id] = artifact.model_copy(deep=True)

    async def get_artifact(self, task_id: str, artifact_id: str) -> Artifact | None:
        artifact = self._artifacts.get(task_id, {}).get(artifact_id)
        return artifact.model_copy(deep=True) if artifact else None

    async def save_verification(self, task_id: str, verification: Verification) -> None:
        self._verifications.setdefault(task_id, []).append(verification.model_copy(deep=True))
