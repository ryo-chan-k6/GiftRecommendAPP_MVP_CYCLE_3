"""MOD-RECO-017 Popularity Scorer package.

Physical path uses kebab-case per module spec. Import as
``reco.application.popularity_scorer``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.popularity_scorer"
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
    DEFAULT_W_RATING,
    DEFAULT_W_REVIEW_COUNT,
    MODULE_ID,
    PHASE_NAME,
    POPULARITY_FORMULA_DEFAULT,
    POPULARITY_FORMULA_RATING_REVIEW_COUNT_WEIGHTED,
    SURFACE_ERROR_CODE,
)
from .errors import MODULE_ERROR_MODULE_ID, PopularityScorerError  # noqa: E402
from .executor import PopularityScorer, build_default_popularity_scorer  # noqa: E402
from .factory import build_scaffold_popularity_scorer  # noqa: E402
from .in_memory_repository import (  # noqa: E402
    InMemoryItemReviewSummaryRepository,
    build_default_in_memory_item_review_summary_repository,
)
from .models import (  # noqa: E402
    ItemReviewSummary,
    PopularityScoreEntry,
    PopularityScoreResult,
    PopularityScorerRunMetrics,
    PopularityWeights,
)
from .ports import ItemReviewSummaryRepositoryPort  # noqa: E402
from .scoring_engine import (  # noqa: E402
    guard_clip,
    round_to_scale,
    run_popularity_scoring,
)

__all__ = [
    "DEFAULT_W_RATING",
    "DEFAULT_W_REVIEW_COUNT",
    "InMemoryItemReviewSummaryRepository",
    "ItemReviewSummary",
    "ItemReviewSummaryRepositoryPort",
    "MODULE_ERROR_MODULE_ID",
    "MODULE_ID",
    "PHASE_NAME",
    "POPULARITY_FORMULA_DEFAULT",
    "POPULARITY_FORMULA_RATING_REVIEW_COUNT_WEIGHTED",
    "PopularityScoreEntry",
    "PopularityScoreResult",
    "PopularityScorer",
    "PopularityScorerError",
    "PopularityScorerRunMetrics",
    "PopularityWeights",
    "SURFACE_ERROR_CODE",
    "build_default_in_memory_item_review_summary_repository",
    "build_default_popularity_scorer",
    "build_scaffold_popularity_scorer",
    "guard_clip",
    "round_to_scale",
    "run_popularity_scoring",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
