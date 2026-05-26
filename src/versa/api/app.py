from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from versa.api.deps import build_default_runtime, init_session_service
from versa.api.routes import router as sessions_router
from versa.llm.factory import make_codex_clients
from versa.orchestrator import AgentRuntime
from versa.store.memory import InMemoryStore


def create_app(runtime: AgentRuntime | None = None, *, use_codex: bool = False) -> FastAPI:
    if runtime is None:
        store = InMemoryStore()
        if use_codex:
            extractor, solver = make_codex_clients()
            runtime = AgentRuntime(solver, store, extractor_llm=extractor)
        else:
            runtime = build_default_runtime()
    init_session_service(runtime)

    app = FastAPI(title="Versa Requirements Gatherer", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    app.include_router(sessions_router, prefix="/api")

    ui_dist = Path(__file__).resolve().parents[3] / "ui" / "dist"
    if ui_dist.is_dir():
        app.mount("/", StaticFiles(directory=ui_dist, html=True), name="ui")

    return app
