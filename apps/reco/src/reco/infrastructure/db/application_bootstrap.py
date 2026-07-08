"""Bootstrap hyphenated reco.application packages for infrastructure imports."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_APPLICATION_ROOT = Path(__file__).resolve().parents[2] / "application"


def ensure_application_package(import_root: str, package_dir: str) -> None:
    """Load a hyphenated application package under ``reco.application``."""

    if import_root in sys.modules:
        return

    init_path = _APPLICATION_ROOT / package_dir / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        import_root,
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load application package: {import_root}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def ensure_observability_application_packages() -> None:
    """Load observability application packages used by Postgres repositories."""

    ensure_application_package(
        "reco.application.phase_log_writer",
        "phase-log-writer",
    )
    ensure_application_package(
        "reco.application.error_log_writer",
        "error-log-writer",
    )
    ensure_application_package(
        "reco.application.metric_logger",
        "metric-logger",
    )
