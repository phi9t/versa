from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from versa.api.deps import get_session_service
from versa.api.dtos import ExportResponse, SessionSnapshot, TurnRequest, TurnResponse
from versa.llm.codex_cli import CodexExecError

router = APIRouter(prefix="/sessions")


@router.get("/{task_id}", response_model=SessionSnapshot)
async def get_session(task_id: str) -> SessionSnapshot:
    service = get_session_service()
    return await service.get_snapshot(task_id)


@router.post("/{task_id}/turns", response_model=TurnResponse)
async def post_turn(task_id: str, body: TurnRequest) -> TurnResponse:
    service = get_session_service()
    try:
        return await service.handle_turn(task_id, body.text)
    except (CodexExecError, ValidationError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{task_id}/export", response_model=ExportResponse)
async def export_session(task_id: str, format: str = "md") -> ExportResponse:
    if format not in {"md", "json"}:
        raise HTTPException(status_code=422, detail="format must be md or json")
    service = get_session_service()
    return await service.export(task_id, format)  # type: ignore[arg-type]
