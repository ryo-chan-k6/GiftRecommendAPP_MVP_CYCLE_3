"""MOD-RECO-018 Risk Scorer package.

Physical path uses kebab-case per module spec. Import as
``reco.application.risk_scorer``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.risk_scorer"
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
    DEFAULT_SOCIAL_THRESHOLD,
    DEFAULT_W_AVOID,
    DEFAULT_W_DATA_QUALITY,
    DEFAULT_W_SOCIAL,
    MODULE_ID,
    PHASE_NAME,
    RISK_FORMULA_AVOID_SOCIAL_DATA_QUALITY_WEIGHTED,
    RISK_FORMULA_DEFAULT,
    SURFACE_ERROR_CODE,
)
from .errors import MODULE_ERROR_MODULE_ID, RiskScorerError  # noqa: E402
from .executor import RiskScorer, build_default_risk_scorer  # noqa: E402
from .factory import build_scaffold_risk_scorer  # noqa: E402
from .models import (  # noqa: E402
    RiskPenaltyEntry,
    RiskPenaltyResult,
    RiskScorerRunMetrics,
    RiskWeights,
)
from .scoring_engine import (  # noqa: E402
    guard_clip,
    round_to_scale,
    run_risk_scoring,
)

__all__ = [
    "DEFAULT_SOCIAL_THRESHOLD",
    "DEFAULT_W_AVOID",
    "DEFAULT_W_DATA_QUALITY",
    "DEFAULT_W_SOCIAL",
    "MODULE_ERROR_MODULE_ID",
    "MODULE_ID",
    "PHASE_NAME",
    "RISK_FORMULA_AVOID_SOCIAL_DATA_QUALITY_WEIGHTED",
    "RISK_FORMULA_DEFAULT",
    "RiskPenaltyEntry",
    "RiskPenaltyResult",
    "RiskScorer",
    "RiskScorerError",
    "RiskScorerRunMetrics",
    "RiskWeights",
    "SURFACE_ERROR_CODE",
    "build_default_risk_scorer",
    "build_scaffold_risk_scorer",
    "guard_clip",
    "round_to_scale",
    "run_risk_scoring",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
