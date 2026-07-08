"""Test bootstrap for hyphenated application package paths."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_APPLICATION_TESTS = Path(__file__).resolve().parent
_APPLICATION_ROOT = Path(__file__).resolve().parents[3] / "src/reco/application"
if str(_APPLICATION_TESTS) not in sys.path:
    sys.path.insert(0, str(_APPLICATION_TESTS))


def _load_package(import_root: str, init_relative: str) -> None:
    init_path = Path(__file__).resolve().parents[3] / init_relative
    spec = importlib.util.spec_from_file_location(
        import_root,
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load package: {import_root}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def _is_fully_loaded(import_root: str, marker_attr: str) -> bool:
    existing = sys.modules.get(import_root)
    return existing is not None and hasattr(existing, marker_attr)


def _load_observability_package(
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


def _load_orchestrator_package() -> None:
    _load_package(
        "reco.application.recommendation_orchestrator",
        "src/reco/application/recommendation-orchestrator/__init__.py",
    )


def _load_run_recorder_package() -> None:
    _load_package(
        "reco.application.recommendation_run_recorder",
        "src/reco/application/recommendation-run-recorder/__init__.py",
    )


def _load_config_version_resolver_package() -> None:
    _load_package(
        "reco.application.config_version_resolver",
        "src/reco/application/config-version-resolver/__init__.py",
    )


def _load_observability_packages() -> None:
    """Reload observability packages after infrastructure bootstrap stubs."""

    _load_observability_package(
        "reco.application.reco_error_handler",
        "reco-error-handler",
        marker_attr="RecoErrorHandler",
    )
    _load_observability_package(
        "reco.application.error_log_writer",
        "error-log-writer",
        marker_attr="ErrorLogWriter",
    )
    _load_observability_package(
        "reco.application.phase_log_writer",
        "phase-log-writer",
        marker_attr="PhaseLogWriter",
    )
    _load_observability_package(
        "reco.application.metric_logger",
        "metric-logger",
        marker_attr="MetricLogger",
    )


_load_run_recorder_package()
_load_orchestrator_package()
_load_config_version_resolver_package()
_load_observability_packages()
