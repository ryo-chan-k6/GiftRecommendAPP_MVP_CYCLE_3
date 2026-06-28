"""MOD-RECO-007 User Feature Generator package.

Physical path uses kebab-case per module spec. Import as
``reco.application.user_feature_generator``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.user_feature_generator"
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
    DEFAULT_CENTER_FEATURE,
    DEFAULT_FEATURE_NORMALIZATION_VERSION_ID,
    DEFAULT_K_FEATURE,
    MODULE_ID,
    NORMALIZATION_METHOD_SIGMOID,
    PHASE_NAME,
    SOURCE_TYPE_AGGREGATED,
    SURFACE_ERROR_CODE,
)
from .errors import UserFeatureGenerationError  # noqa: E402
from .factory import (  # noqa: E402
    build_scaffold_user_feature_generator,
)
from .generator import (  # noqa: E402
    UserFeatureGenerator,
    build_default_user_feature_generator,
)
from .in_memory_repository import (  # noqa: E402
    InMemoryNormalizationRuleRepository,
    InMemoryRunValidation,
    InMemoryUserFeatureRepository,
    build_default_in_memory_repositories,
    build_default_normalization_binding,
    build_default_user_feature_repository,
)
from .models import (  # noqa: E402
    FeatureNormalizationParameters,
    NormalizationBinding,
    UserFeature,
    UserFeatureInsertRow,
)
from .rule_engine import (  # noqa: E402
    merge_user_feature_raw,
    normalize_user_features,
)

__all__ = [
    "DEFAULT_CENTER_FEATURE",
    "DEFAULT_FEATURE_NORMALIZATION_VERSION_ID",
    "DEFAULT_K_FEATURE",
    "FeatureNormalizationParameters",
    "InMemoryNormalizationRuleRepository",
    "InMemoryRunValidation",
    "InMemoryUserFeatureRepository",
    "MODULE_ID",
    "NORMALIZATION_METHOD_SIGMOID",
    "NormalizationBinding",
    "PHASE_NAME",
    "SOURCE_TYPE_AGGREGATED",
    "SURFACE_ERROR_CODE",
    "UserFeature",
    "UserFeatureGenerationError",
    "UserFeatureGenerator",
    "UserFeatureInsertRow",
    "build_default_in_memory_repositories",
    "build_default_normalization_binding",
    "build_default_user_feature_generator",
    "build_default_user_feature_repository",
    "build_scaffold_user_feature_generator",
    "merge_user_feature_raw",
    "normalize_user_features",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
