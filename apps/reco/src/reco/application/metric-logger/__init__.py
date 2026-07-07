"""MOD-RECO-025 Metric Logger package.

Physical path uses kebab-case per module spec. Import as
``reco.application.metric_logger``.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.metric_logger"
_PKG_DIR = Path(__file__).resolve().parent


def _ensure_import_aliases() -> None:
    if _IMPORT_ROOT in sys.modules:
        return

    application_pkg = sys.modules.get("reco.application")
    if application_pkg is None:
        application_pkg = types.ModuleType("reco.application")
        application_pkg.__path__ = [str(_PKG_DIR.parent)]  # type: ignore[attr-defined]
        application_pkg.__package__ = "reco.application"
        sys.modules["reco.application"] = application_pkg

    pkg = types.ModuleType(_IMPORT_ROOT)
    pkg.__path__ = [str(_PKG_DIR)]  # type: ignore[attr-defined]
    pkg.__package__ = _IMPORT_ROOT
    sys.modules[_IMPORT_ROOT] = pkg


_ensure_import_aliases()


def _ensure_orchestrator_package_loaded() -> None:
    orchestrator_root = "reco.application.recommendation_orchestrator"
    if orchestrator_root in sys.modules:
        return

    orchestrator_dir = _PKG_DIR.parent / "recommendation-orchestrator"
    init_path = orchestrator_dir / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        orchestrator_root,
        init_path,
        submodule_search_locations=[str(orchestrator_dir)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load reco.application.recommendation_orchestrator")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_ensure_orchestrator_package_loaded()

from .constants import METRIC_SOURCE, MODULE_ID, TIER_2_METRIC_PREFIXES  # noqa: E402
from .factory import (  # noqa: E402
    build_default_metric_logger,
    build_scaffold_metric_logger,
)
from .logger import MetricLogger  # noqa: E402
from .models import MetricRecord  # noqa: E402
from .ports import MetricLoggerRepository  # noqa: E402
from .repository import InMemoryMetricLoggerRepository  # noqa: E402

__all__ = [
    "METRIC_SOURCE",
    "MetricLogger",
    "MetricLoggerRepository",
    "MetricRecord",
    "InMemoryMetricLoggerRepository",
    "MODULE_ID",
    "TIER_2_METRIC_PREFIXES",
    "build_default_metric_logger",
    "build_scaffold_metric_logger",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
