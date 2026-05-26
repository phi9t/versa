import pytest
from httpx import ASGITransport, AsyncClient

from tests.fixtures import REQUIREMENTS_OPENING, REQUIREMENTS_SLOTS, SYNTHESIS_TRIGGER, is_clarification
from versa.api.app import create_app
from versa.api.deps import build_default_runtime


@pytest.fixture
def app():
    runtime = build_default_runtime()
    return create_app(runtime)


@pytest.mark.asyncio
async def test_get_empty_session(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/sessions/demo")
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == "demo"
    assert data["facts"] == []


@pytest.mark.asyncio
async def test_turn_and_snapshot(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/sessions/gather-demo/turns",
            json={"text": REQUIREMENTS_OPENING},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert is_clarification(body["assistant_reply"]) or body["snapshot"]["objective"]

        for key, value in REQUIREMENTS_SLOTS:
            slot_text = f"Use {key}: {value!r}" if isinstance(value, str) else f"Use {key}: {value}"
            resp = await client.post(
                "/api/sessions/gather-demo/turns",
                json={"text": slot_text},
            )
            assert resp.status_code == 200

        resp = await client.post(
            "/api/sessions/gather-demo/turns",
            json={"text": SYNTHESIS_TRIGGER},
        )
        assert resp.status_code == 200
        final = resp.json()
        assert final["snapshot"]["readiness"] in {"ready_to_synthesize", "synthesized"}


@pytest.mark.asyncio
async def test_export_markdown(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/sessions/export-demo/turns",
            json={"text": "Use scope: demo scope"},
        )
        resp = await client.get("/api/sessions/export-demo/export?format=md")
    assert resp.status_code == 200
    assert "# Overview" in resp.json()["content"] or "No requirements" in resp.json()["content"]
