from __future__ import annotations

import pytest

from versa.gather.factory import GATHER_DEFAULT_OBJECTIVE, make_gather_session
from versa.gather.session import GatherSession


@pytest.mark.asyncio
async def test_make_gather_session_sets_default_objective():
    session = make_gather_session(mock=True)
    assert isinstance(session, GatherSession)
    assert session.service.runtime._default_objective == GATHER_DEFAULT_OBJECTIVE


@pytest.mark.asyncio
async def test_gather_session_load_and_send():
    session = make_gather_session(mock=True)
    task_id = "gather-session-test"

    snapshot = await session.load(task_id)
    assert snapshot.task_id == task_id
    assert snapshot.readiness.value == "gathering"

    turn = await session.send(
        task_id,
        "Gather requirements for backup CLI. Objective: write_requirements_doc.",
    )
    assert turn.assistant_reply
    assert turn.snapshot.task_id == task_id
    assert turn.snapshot.objective == "write_requirements_doc" or turn.snapshot.missing_slot_keys


@pytest.mark.asyncio
async def test_gather_session_export_markdown():
    session = make_gather_session(mock=True)
    task_id = "gather-export"
    await session.send(task_id, "Use scope: demo scope")
    export = await session.export(task_id, "md")
    assert export.format == "md"
    assert export.content
