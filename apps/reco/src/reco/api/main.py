"""FastAPI application entry for apps/reco Internal API."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

# kebab-case application パッケージを import 可能にする（pytest conftest と同趣旨）
from reco.composition.bootstrap import ensure_composition_application_packages

ensure_composition_application_packages()

from reco.api.dependencies import build_production_runtime
from reco.api.exception_handlers.reco_errors import register_exception_handlers
from reco.api.routes.health import router as health_router
from reco.api.routes.recommendations import router as recommendations_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # MVP オンライン推薦は CompositionMode.PRODUCTION 固定（実装仕様書 §3.3）。
    runtime = build_production_runtime()
    app.state.orchestrator = runtime.orchestrator
    app.state.database_session = runtime.database_session
    open_fn = getattr(runtime.database_session, "open", None)
    if callable(open_fn):
        open_fn()
    try:
        yield
    finally:
        close_fn = getattr(runtime.database_session, "close", None)
        if callable(close_fn):
            close_fn()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Gift Recommendation Service Reco Internal API",
        version="0.1.0",
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(recommendations_router)
    return app


app = create_app()
