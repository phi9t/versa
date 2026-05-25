from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from versa.models.state import Artifact, TaskState, Verification


class Store(ABC):
    @abstractmethod
    async def append_message(
        self,
        task_id: str,
        role: str,
        content: str,
    ) -> str:
        ...

    @abstractmethod
    async def list_messages(self, task_id: str) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    async def load_state(self, task_id: str) -> TaskState:
        ...

    @abstractmethod
    async def save_state(
        self,
        task_id: str,
        state: TaskState,
        expected_version: int | None = None,
    ) -> None:
        ...

    @abstractmethod
    async def append_state_event(
        self,
        task_id: str,
        event_type: str,
        event_json: dict[str, Any],
        version_before: int,
        version_after: int,
    ) -> str:
        ...

    @abstractmethod
    async def save_artifact(self, task_id: str, artifact: Artifact) -> None:
        ...

    @abstractmethod
    async def get_artifact(self, task_id: str, artifact_id: str) -> Artifact | None:
        ...

    @abstractmethod
    async def save_verification(self, task_id: str, verification: Verification) -> None:
        ...
