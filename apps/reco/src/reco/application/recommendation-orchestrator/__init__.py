"""MOD-RECO-001 Recommendation Orchestrator package.

Physical path uses kebab-case per module spec. Import as
``reco.application.recommendation_orchestrator``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.recommendation_orchestrator"
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

from .constants import (  # noqa: E402
    GENERIC_REASON_SUMMARY,
    ORCHESTRATOR_MODULE_ORDER,
    PIPELINE_HARD_TIMEOUT_MS,
    PIPELINE_SOFT_TIMEOUT_MS,
)
from .errors import ModuleExecutionError, RecoError  # noqa: E402
from .execution_context import ExecutionContext  # noqa: E402
from .orchestrator import OrchestratorOutcome, RecommendationOrchestrator  # noqa: E402
from .ports import OrchestratorPorts, PhaseStatus, ReasonGenerationOutcome  # noqa: E402
from .stubs import build_default_stub_ports  # noqa: E402

__all__ = [
    "ExecutionContext",
    "GENERIC_REASON_SUMMARY",
    "ModuleExecutionError",
    "ORCHESTRATOR_MODULE_ORDER",
    "OrchestratorOutcome",
    "OrchestratorPorts",
    "PIPELINE_HARD_TIMEOUT_MS",
    "PIPELINE_SOFT_TIMEOUT_MS",
    "PhaseStatus",
    "ReasonGenerationOutcome",
    "RecoError",
    "RecommendationOrchestrator",
    "build_default_stub_ports",
]

# Re-export under virtual package name for ``from reco.application...`` imports.
_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
