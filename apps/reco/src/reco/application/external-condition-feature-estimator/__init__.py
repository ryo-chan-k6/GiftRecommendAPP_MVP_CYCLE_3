"""MOD-RECO-005 External Condition Feature Estimator package.

Physical path uses kebab-case per module spec. Import as
``reco.application.external_condition_feature_estimator``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.external_condition_feature_estimator"
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
    DEFAULT_OCCASION_WEIGHT,
    DEFAULT_RELATIONSHIP_WEIGHT,
    ESTIMATION_METHOD_RULE,
    MODULE_ID,
    PHASE_NAME,
    SURFACE_ERROR_CODE,
)
from .errors import ExternalFeatureEstimateError  # noqa: E402
from .estimator import (  # noqa: E402
    ExternalConditionFeatureEstimator,
    build_default_external_condition_feature_estimator,
)
from .factory import (  # noqa: E402
    build_scaffold_external_condition_feature_estimator,
)
from .in_memory_repository import (  # noqa: E402
    InMemoryFeatureRuleRepository,
    InMemoryRunValidation,
    build_default_feature_rule_repository,
    build_default_in_memory_repositories,
)
from .models import ExternalFeatureEstimate, FeatureIntegrationWeights  # noqa: E402
from .rule_engine import merge_external_feature_raw, zero_feature_vector  # noqa: E402

__all__ = [
    "DEFAULT_OCCASION_WEIGHT",
    "DEFAULT_RELATIONSHIP_WEIGHT",
    "ESTIMATION_METHOD_RULE",
    "ExternalConditionFeatureEstimator",
    "ExternalFeatureEstimate",
    "ExternalFeatureEstimateError",
    "FeatureIntegrationWeights",
    "InMemoryFeatureRuleRepository",
    "InMemoryRunValidation",
    "MODULE_ID",
    "PHASE_NAME",
    "SURFACE_ERROR_CODE",
    "build_default_external_condition_feature_estimator",
    "build_default_feature_rule_repository",
    "build_default_in_memory_repositories",
    "build_scaffold_external_condition_feature_estimator",
    "merge_external_feature_raw",
    "zero_feature_vector",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
