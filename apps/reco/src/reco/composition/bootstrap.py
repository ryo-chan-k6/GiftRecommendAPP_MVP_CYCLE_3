"""Bootstrap hyphenated reco.application packages for composition imports."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_APPLICATION_ROOT = Path(__file__).resolve().parents[1] / "application"


def _is_fully_loaded(import_root: str, marker_attr: str) -> bool:
    existing = sys.modules.get(import_root)
    return existing is not None and hasattr(existing, marker_attr)


def _load_package(
    import_root: str,
    package_dir: str,
    *,
    marker_attr: str,
) -> None:
    if _is_fully_loaded(import_root, marker_attr):
        return

    if import_root in sys.modules:
        del sys.modules[import_root]

    init_path = _APPLICATION_ROOT / package_dir / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        import_root,
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load package: {import_root}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[import_root] = module
    spec.loader.exec_module(module)


def ensure_composition_application_packages() -> None:
    """Load application packages required by the composition root."""

    _load_package(
        "reco.application.recommendation_orchestrator",
        "recommendation-orchestrator",
        marker_attr="build_default_stub_ports",
    )
    _load_package(
        "reco.application.recommendation_run_recorder",
        "recommendation-run-recorder",
        marker_attr="RecommendationRunRecorder",
    )
    _load_package(
        "reco.application.reco_error_handler",
        "reco-error-handler",
        marker_attr="RecoErrorHandler",
    )
    _load_package(
        "reco.application.error_log_writer",
        "error-log-writer",
        marker_attr="ErrorLogWriter",
    )
    _load_package(
        "reco.application.phase_log_writer",
        "phase-log-writer",
        marker_attr="PhaseLogWriter",
    )
    _load_package(
        "reco.application.metric_logger",
        "metric-logger",
        marker_attr="MetricLogger",
    )
