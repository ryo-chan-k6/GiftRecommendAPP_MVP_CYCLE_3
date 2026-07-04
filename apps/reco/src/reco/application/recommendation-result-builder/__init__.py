"""MOD-RECO-021 Recommendation Result Builder package.

Physical path uses kebab-case per module spec. Import as
``reco.application.recommendation_result_builder``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.recommendation_result_builder"
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

from .build_engine import (  # noqa: E402
    build_recommendation_result,
    resolve_version_ids,
    to_domain_recommendation_result,
)
from .constants import MODULE_ID, PHASE_NAME, SURFACE_ERROR_CODE  # noqa: E402
from .errors import (  # noqa: E402
    MODULE_ERROR_MODULE_ID,
    RecommendationResultBuilderError,
)
from .executor import (  # noqa: E402
    RecommendationResultBuilder,
    build_default_recommendation_result_builder,
)
from .factory import build_scaffold_recommendation_result_builder  # noqa: E402
from .in_memory_repository import InMemoryRecommendationResultRepository  # noqa: E402
from .models import (  # noqa: E402
    BuiltRecommendationResult,
    BuiltRecommendationResultItem,
    RecommendationResultBuilderRunMetrics,
    RecommendationResultHeaderInsertRow,
    ResultHeaderStatus,
)

__all__ = [
    "BuiltRecommendationResult",
    "BuiltRecommendationResultItem",
    "InMemoryRecommendationResultRepository",
    "MODULE_ERROR_MODULE_ID",
    "MODULE_ID",
    "PHASE_NAME",
    "RecommendationResultBuilder",
    "RecommendationResultBuilderError",
    "RecommendationResultBuilderRunMetrics",
    "RecommendationResultHeaderInsertRow",
    "ResultHeaderStatus",
    "SURFACE_ERROR_CODE",
    "build_default_recommendation_result_builder",
    "build_recommendation_result",
    "build_scaffold_recommendation_result_builder",
    "resolve_version_ids",
    "to_domain_recommendation_result",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
