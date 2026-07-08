"""Bootstrap hyphenated reco.application packages for infrastructure imports."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_APPLICATION_ROOT = Path(__file__).resolve().parents[2] / "application"


def _ensure_package_namespace(import_root: str, package_dir: str) -> Path:
    """Register a hyphenated package namespace without executing ``__init__.py``."""

    pkg_dir = _APPLICATION_ROOT / package_dir

    application_pkg = sys.modules.get("reco.application")
    if application_pkg is None:
        application_pkg = types.ModuleType("reco.application")
        application_pkg.__path__ = [str(_APPLICATION_ROOT)]  # type: ignore[attr-defined]
        application_pkg.__package__ = "reco.application"
        sys.modules["reco.application"] = application_pkg

    if import_root not in sys.modules:
        pkg = types.ModuleType(import_root)
        pkg.__path__ = [str(pkg_dir)]  # type: ignore[attr-defined]
        pkg.__package__ = import_root
        sys.modules[import_root] = pkg

    return pkg_dir


def _load_application_module(import_root: str, package_dir: str, module_name: str) -> None:
    """Load a single application submodule under a hyphenated package root."""

    full_name = f"{import_root}.{module_name}"
    if full_name in sys.modules:
        return

    pkg_dir = _ensure_package_namespace(import_root, package_dir)
    module_path = pkg_dir / f"{module_name}.py"
    spec = importlib.util.spec_from_file_location(
        full_name,
        module_path,
        submodule_search_locations=[str(pkg_dir)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load application module: {full_name}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)


def ensure_observability_application_packages() -> None:
    """Load observability application models/ports used by Postgres repositories.

    Package ``__init__.py`` files pull in orchestrator/stubs and break unrelated
    imports, so infrastructure loads only the submodules it needs.
    """

    _load_application_module(
        "reco.application.phase_log_writer",
        "phase-log-writer",
        "models",
    )
    _load_application_module(
        "reco.application.error_log_writer",
        "error-log-writer",
        "models",
    )
    _load_application_module(
        "reco.application.metric_logger",
        "metric-logger",
        "models",
    )
    _load_application_module(
        "reco.application.metric_logger",
        "metric-logger",
        "ports",
    )
