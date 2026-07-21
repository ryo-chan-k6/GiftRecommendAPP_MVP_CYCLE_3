"""MOD-RECO-019 Final Score Calculator package.

Physical path uses kebab-case per module spec. Import as
``reco.application.final_score_calculator``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.final_score_calculator"
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
    DEFAULT_W_CONTEXT,
    DEFAULT_W_POPULARITY,
    DEFAULT_W_RISK,
    FINAL_SCORE_FORMULA_DEFAULT,
    FINAL_SCORE_FORMULA_LINEAR_WEIGHTED_V1,
    MODULE_ID,
    PHASE_NAME,
    SURFACE_ERROR_CODE,
)
from .errors import FinalScoreCalculatorError, MODULE_ERROR_MODULE_ID  # noqa: E402
from .executor import (  # noqa: E402
    FinalScoreCalculator,
    build_default_final_score_calculator,
)
from .factory import build_scaffold_final_score_calculator  # noqa: E402
from .models import (  # noqa: E402
    FinalScoreCalculatorRunMetrics,
    FinalScoreEntry,
    FinalScoreResult,
    RankingWeightsUsed,
)
from .scoring_engine import (  # noqa: E402
    guard_clip,
    round_to_scale,
    run_final_score_calculation,
)

__all__ = [
    "DEFAULT_W_CONTEXT",
    "DEFAULT_W_POPULARITY",
    "DEFAULT_W_RISK",
    "FINAL_SCORE_FORMULA_DEFAULT",
    "FINAL_SCORE_FORMULA_LINEAR_WEIGHTED_V1",
    "FinalScoreCalculator",
    "FinalScoreCalculatorError",
    "FinalScoreCalculatorRunMetrics",
    "FinalScoreEntry",
    "FinalScoreResult",
    "MODULE_ERROR_MODULE_ID",
    "MODULE_ID",
    "PHASE_NAME",
    "RankingWeightsUsed",
    "SURFACE_ERROR_CODE",
    "build_default_final_score_calculator",
    "build_scaffold_final_score_calculator",
    "guard_clip",
    "round_to_scale",
    "run_final_score_calculation",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
