"""MOD-RECO-001 composition root for Orchestrator DI."""

from .bootstrap import ensure_composition_application_packages

ensure_composition_application_packages()

from .builder import build_composition_ports, build_production_ports
from .config import CompositionMode, resolve_database_url
from .observability import ObservabilityRepositories, build_observability_repositories

__all__ = [
    "CompositionMode",
    "ObservabilityRepositories",
    "build_composition_ports",
    "build_observability_repositories",
    "build_production_ports",
    "resolve_database_url",
]
