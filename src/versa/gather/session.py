from __future__ import annotations

from typing import Literal

from versa.api.dtos import ExportResponse, SessionSnapshot, TurnResponse
from versa.api.session_service import SessionService


class GatherSession:
    """Presentation-agnostic facade for requirements gathering sessions."""

    def __init__(self, service: SessionService) -> None:
        self._service = service

    @property
    def service(self) -> SessionService:
        return self._service

    async def load(self, task_id: str) -> SessionSnapshot:
        return await self._service.get_snapshot(task_id)

    async def send(self, task_id: str, text: str) -> TurnResponse:
        return await self._service.handle_turn(task_id, text)

    async def export(self, task_id: str, fmt: Literal["md", "json"]) -> ExportResponse:
        return await self._service.export(task_id, fmt)
