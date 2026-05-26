from __future__ import annotations

from typing import Literal

from versa.api.dtos import ExportResponse, SessionSnapshot, TurnResponse
from versa.api.mappers import snapshot_from_state
from versa.export.renderer import render_requirements_markdown
from versa.models.state import ArtifactStatus, TaskState
from versa.orchestrator import AgentRuntime


class SessionService:
    def __init__(self, runtime: AgentRuntime) -> None:
        self._runtime = runtime

    @property
    def runtime(self) -> AgentRuntime:
        return self._runtime

    async def get_snapshot(self, task_id: str) -> SessionSnapshot:
        state = await self._runtime.store.load_state(task_id)
        messages = await self._runtime.store.list_messages(task_id)
        artifact = await self._load_active_artifact(task_id, state)
        return snapshot_from_state(state, messages, artifact)

    async def handle_turn(self, task_id: str, text: str) -> TurnResponse:
        reply = await self._runtime.handle_user_turn(task_id, text)
        snapshot = await self.get_snapshot(task_id)
        return TurnResponse(snapshot=snapshot, assistant_reply=reply)

    async def export(self, task_id: str, fmt: Literal["md", "json"]) -> ExportResponse:
        state = await self._runtime.store.load_state(task_id)
        if fmt == "md":
            content = render_requirements_markdown(state)
        else:
            snapshot = await self.get_snapshot(task_id)
            content = snapshot.model_dump_json(indent=2)
        return ExportResponse(format=fmt, content=content)

    async def _load_active_artifact(self, task_id: str, state: TaskState | None = None):
        if state is None:
            state = await self._runtime.store.load_state(task_id)
        if not state.active_artifact_id:
            return None
        artifact = await self._runtime.store.get_artifact(task_id, state.active_artifact_id)
        if artifact and artifact.status in {ArtifactStatus.VERIFIED, ArtifactStatus.FAILED, ArtifactStatus.DRAFT}:
            return artifact
        return artifact
