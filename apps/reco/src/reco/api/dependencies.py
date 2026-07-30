"""FastAPI DI: Orchestrator (CompositionMode.PRODUCTION) and app state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from reco.application.recommendation_orchestrator import RecommendationOrchestrator
from reco.composition.builder import build_composition_ports
from reco.composition.config import CompositionMode
from reco.infrastructure.db.session import DatabaseSession


@dataclass(frozen=True)
class ProductionRuntime:
    """Production runtime wiring shared by lifespan and health probe."""

    orchestrator: RecommendationOrchestrator
    database_session: DatabaseSession


def build_production_runtime() -> ProductionRuntime:
    """Build PRODUCTION orchestrator and the shared database session."""

    ports, helpers = build_composition_ports(CompositionMode.PRODUCTION)
    session = helpers.get("database_session")
    if session is None:
        raise RuntimeError("database_session is missing from production helpers")
    return ProductionRuntime(
        orchestrator=RecommendationOrchestrator(ports=ports),
        database_session=session,  # type: ignore[arg-type]
    )


def build_production_orchestrator() -> RecommendationOrchestrator:
    """Backward-compatible helper; prefer ``build_production_runtime`` for lifespan."""

    return build_production_runtime().orchestrator


def get_orchestrator(request: Request) -> RecommendationOrchestrator:
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is None:
        raise RuntimeError("RecommendationOrchestrator is not initialized")
    return orchestrator


def get_database_session(request: Request) -> DatabaseSession | None:
    """Return the shared database session when lifespan has initialized it."""

    return getattr(request.app.state, "database_session", None)


OrchestratorDep = Annotated[RecommendationOrchestrator, Depends(get_orchestrator)]
