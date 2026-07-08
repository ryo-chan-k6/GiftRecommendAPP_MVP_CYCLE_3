"""Composition root builders for MOD-RECO-001 Orchestrator ports."""

from __future__ import annotations

from dataclasses import replace

from reco.application.recommendation_orchestrator import (
    OrchestratorPorts,
    build_default_stub_ports,
)
from reco.infrastructure.db.session import DatabaseSession, create_database_session

from .config import CompositionMode, resolve_database_url
from .observability import build_production_observability_modules


def build_production_ports(
    *,
    database_url: str | None = None,
    database_session: DatabaseSession | None = None,
) -> tuple[OrchestratorPorts, dict[str, object]]:
    """Build production composition with Postgres observability and MVP default elsewhere."""

    base_ports, base_helpers = build_default_stub_ports()
    session = database_session or create_database_session(
        resolve_database_url(database_url),
    )
    observability = build_production_observability_modules(session)

    ports = replace(
        base_ports,
        run_recorder=observability["run_recorder"],  # type: ignore[arg-type]
        phase_log_writer=observability["phase_log_writer"],  # type: ignore[arg-type]
        error_handler=observability["error_handler"],  # type: ignore[arg-type]
        metric_logger=observability["metric_logger"],  # type: ignore[arg-type]
    )
    helpers = {
        **base_helpers,
        **observability,
    }
    return ports, helpers


def build_composition_ports(
    mode: CompositionMode = CompositionMode.DEFAULT,
    *,
    database_url: str | None = None,
    database_session: DatabaseSession | None = None,
) -> tuple[OrchestratorPorts, dict[str, object]]:
    """Select MVP default or production composition at the composition boundary."""

    if mode is CompositionMode.DEFAULT:
        return build_default_stub_ports()
    return build_production_ports(
        database_url=database_url,
        database_session=database_session,
    )
