"""MOD-RECO-014 Feature Matcher package.

Physical path uses kebab-case per module spec. Import as
``reco.application.feature_matcher``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.feature_matcher"
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
    AVOID_FEATURE_BASELINE,
    IMPUTED_FEATURE_VALUE,
    MATCH_METHOD_ONE_MINUS_DISTANCE,
    MODULE_ID,
    PHASE_NAME,
    SURFACE_ERROR_CODE,
)
from .errors import MODULE_ERROR_MODULE_ID, FeatureMatcherError  # noqa: E402
from .executor import FeatureMatcher, build_default_feature_matcher  # noqa: E402
from .factory import build_scaffold_feature_matcher  # noqa: E402
from .in_memory_repository import (  # noqa: E402
    InMemoryFeatureNormalizationRepository,
    InMemoryItemFeatureRecord,
    InMemoryItemFeatureRepository,
    build_default_in_memory_item_feature_repository,
    build_default_in_memory_repositories,
    build_uniform_item_features,
)
from .match_engine import run_feature_matching  # noqa: E402
from .models import (  # noqa: E402
    FeatureAxisMatch,
    FeatureMatchEntry,
    FeatureMatchResult,
    FeatureMatcherRunMetrics,
)
from .ports import FeatureNormalizationPort, ItemFeatureRepositoryPort  # noqa: E402

__all__ = [
    "AVOID_FEATURE_BASELINE",
    "FeatureAxisMatch",
    "FeatureMatchEntry",
    "FeatureMatchResult",
    "FeatureMatcher",
    "FeatureMatcherError",
    "FeatureMatcherRunMetrics",
    "FeatureNormalizationPort",
    "IMPUTED_FEATURE_VALUE",
    "InMemoryFeatureNormalizationRepository",
    "InMemoryItemFeatureRecord",
    "InMemoryItemFeatureRepository",
    "ItemFeatureRepositoryPort",
    "MATCH_METHOD_ONE_MINUS_DISTANCE",
    "MODULE_ERROR_MODULE_ID",
    "MODULE_ID",
    "PHASE_NAME",
    "SURFACE_ERROR_CODE",
    "build_default_feature_matcher",
    "build_default_in_memory_item_feature_repository",
    "build_default_in_memory_repositories",
    "build_scaffold_feature_matcher",
    "build_uniform_item_features",
    "run_feature_matching",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
