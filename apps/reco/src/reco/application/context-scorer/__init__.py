"""MOD-RECO-016 Context Scorer package.

Physical path uses kebab-case per module spec. Import as
``reco.application.context_scorer``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.context_scorer"
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
    CONTEXT_SCORE_FORMULA_LAMBDA_CTX_WEIGHTED,
    MODULE_ID,
    PHASE_NAME,
    SURFACE_ERROR_CODE,
)
from .errors import MODULE_ERROR_MODULE_ID, ContextScorerError  # noqa: E402
from .executor import ContextScorer, build_default_context_scorer  # noqa: E402
from .factory import build_scaffold_context_scorer  # noqa: E402
from .models import (  # noqa: E402
    ContextScoreEntry,
    ContextScoreResult,
    ContextScorerRunMetrics,
)
from .scoring_engine import (  # noqa: E402
    guard_clip,
    round_to_scale,
    run_context_scoring,
)

__all__ = [
    "CONTEXT_SCORE_FORMULA_LAMBDA_CTX_WEIGHTED",
    "MODULE_ERROR_MODULE_ID",
    "MODULE_ID",
    "ContextScoreEntry",
    "ContextScoreResult",
    "ContextScorer",
    "ContextScorerError",
    "ContextScorerRunMetrics",
    "PHASE_NAME",
    "SURFACE_ERROR_CODE",
    "build_default_context_scorer",
    "build_scaffold_context_scorer",
    "guard_clip",
    "round_to_scale",
    "run_context_scoring",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
