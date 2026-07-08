"""MOD-RECO-020 Final Ranker package.

Physical path uses kebab-case per module spec. Import as
``reco.application.final_ranker``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.final_ranker"
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
    DEFAULT_DIVERSITY_METHOD,
    DEFAULT_LAMBDA_MMR,
    DEFAULT_MMR_CANDIDATE_LIMIT,
    DEFAULT_TOP_K_DEFAULT,
    MODULE_ID,
    PHASE_NAME,
    SURFACE_ERROR_CODE,
)
from .errors import FinalRankerError, MODULE_ERROR_MODULE_ID  # noqa: E402
from .executor import FinalRanker, build_default_final_ranker  # noqa: E402
from .factory import build_scaffold_final_ranker  # noqa: E402
from .models import (  # noqa: E402
    FinalRankerRunMetrics,
    RankedItemEntry,
    RankedItems,
    RankingParams,
)
from .ranking_engine import item_similarity, run_final_ranking  # noqa: E402

__all__ = [
    "DEFAULT_DIVERSITY_METHOD",
    "DEFAULT_LAMBDA_MMR",
    "DEFAULT_MMR_CANDIDATE_LIMIT",
    "DEFAULT_TOP_K_DEFAULT",
    "FinalRanker",
    "FinalRankerError",
    "FinalRankerRunMetrics",
    "MODULE_ERROR_MODULE_ID",
    "MODULE_ID",
    "PHASE_NAME",
    "RankedItemEntry",
    "RankedItems",
    "RankingParams",
    "SURFACE_ERROR_CODE",
    "build_default_final_ranker",
    "build_scaffold_final_ranker",
    "item_similarity",
    "run_final_ranking",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
