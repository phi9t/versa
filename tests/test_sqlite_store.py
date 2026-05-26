from __future__ import annotations

import pytest

from versa.models.state import Artifact, ArtifactStatus, TaskState
from versa.store.memory import InMemoryStore
from versa.store.sqlite import SQLiteStore


@pytest.fixture
def sqlite_db(tmp_path):
    yield SQLiteStore(tmp_path / "test.db")


@pytest.mark.asyncio
async def test_sqlite_message_and_state_round_trip(sqlite_db: SQLiteStore):
    task_id = "t-sqlite"
    msg_id = await sqlite_db.append_message(task_id, "user", "hello")
    assert msg_id

    messages = await sqlite_db.list_messages(task_id)
    assert len(messages) == 1
    assert messages[0]["content"] == "hello"

    state = TaskState(task_id=task_id, version=1)
    await sqlite_db.save_state(task_id, state)
    loaded = await sqlite_db.load_state(task_id)
    assert loaded.task_id == task_id
    assert loaded.version == 1


@pytest.mark.asyncio
async def test_sqlite_artifact_and_verification(sqlite_db: SQLiteStore):
    task_id = "t-artifact"
    artifact = Artifact(
        id="art-1",
        kind="document",
        content="# Doc",
        status=ArtifactStatus.VERIFIED,
        based_on_state_version=2,
    )
    await sqlite_db.save_artifact(task_id, artifact)
    loaded = await sqlite_db.get_artifact(task_id, "art-1")
    assert loaded is not None
    assert loaded.content == "# Doc"
    assert loaded.status == ArtifactStatus.VERIFIED


@pytest.mark.asyncio
async def test_sqlite_optimistic_lock_failure(sqlite_db: SQLiteStore):
    task_id = "t-lock"
    state = TaskState(task_id=task_id, version=1)
    await sqlite_db.save_state(task_id, state)

    with pytest.raises(ValueError, match="Optimistic lock failed"):
        await sqlite_db.save_state(task_id, TaskState(task_id=task_id, version=2), expected_version=0)


@pytest.mark.asyncio
async def test_sqlite_restart_simulation(tmp_path):
    db_path = tmp_path / "restart.db"
    task_id = "t-restart"

    store_a = SQLiteStore(db_path)
    await store_a.append_message(task_id, "user", "Use scope: demo project")
    await store_a.save_state(task_id, TaskState(task_id=task_id, version=3))
    del store_a

    store_b = SQLiteStore(db_path)
    loaded = await store_b.load_state(task_id)
    assert loaded.version == 3
    messages = await store_b.list_messages(task_id)
    assert messages[0]["content"] == "Use scope: demo project"


@pytest.mark.asyncio
async def test_sqlite_matches_memory_empty_state(tmp_path):
    mem = InMemoryStore()
    db = SQLiteStore(tmp_path / "empty.db")
    mem_state = await mem.load_state("new-task")
    db_state = await db.load_state("new-task")
    assert mem_state.task_id == db_state.task_id
    assert mem_state.version == db_state.version
