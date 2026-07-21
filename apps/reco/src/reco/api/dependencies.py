"""FastAPI DI: Orchestrator (CompositionMode.PRODUCTION) and app state."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from reco.application.recommendation_orchestrator import RecommendationOrchestrator
from reco.composition.builder import build_composition_ports
from reco.composition.config import CompositionMode


def build_production_orchestrator() -> RecommendationOrchestrator:
    ports, _helpers = build_composition_ports(CompositionMode.PRODUCTION)
    return RecommendationOrchestrator(ports=ports)


def get_orchestrator(request: Request) -> RecommendationOrchestrator:
    orchestrator = getattr(request.app.state, "orchestrator", None)
    if orchestrator is None:
        raise RuntimeError("RecommendationOrchestrator is not initialized")
    return orchestrator


OrchestratorDep = Annotated[RecommendationOrchestrator, Depends(get_orchestrator)]
