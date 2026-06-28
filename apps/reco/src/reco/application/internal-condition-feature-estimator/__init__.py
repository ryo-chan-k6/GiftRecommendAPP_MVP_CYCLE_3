"""MOD-RECO-006 Internal Condition Feature Estimator package.

Physical path uses kebab-case per module spec. Import as
``reco.application.internal_condition_feature_estimator``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.internal_condition_feature_estimator"
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
    CONFIDENCE_THRESHOLD,
    DEFAULT_FREE_TEXT_WEIGHT,
    ESTIMATION_METHOD_RULE,
    MODULE_ID,
    PHASE_NAME,
    SURFACE_ERROR_CODE,
)
from .errors import InternalFeatureEstimateError  # noqa: E402
from .estimator import (  # noqa: E402
    InternalConditionFeatureEstimator,
    build_default_internal_condition_feature_estimator,
)
from .factory import (  # noqa: E402
    build_scaffold_internal_condition_feature_estimator,
)
from .in_memory_repository import (  # noqa: E402
    InMemoryConceptFeatureRuleRepository,
    InMemoryRunValidation,
    build_default_concept_feature_rule_repository,
    build_default_in_memory_repositories,
)
from .models import (  # noqa: E402
    ConceptFeatureRuleRecord,
    InternalFeatureEstimate,
    InternalFeatureIntegrationWeights,
)
from .rule_engine import (  # noqa: E402
    merge_internal_feature_delta,
    zero_feature_vector,
)

__all__ = [
    "CONFIDENCE_THRESHOLD",
    "DEFAULT_FREE_TEXT_WEIGHT",
    "ESTIMATION_METHOD_RULE",
    "ConceptFeatureRuleRecord",
    "InternalConditionFeatureEstimator",
    "InternalFeatureEstimate",
    "InternalFeatureEstimateError",
    "InternalFeatureIntegrationWeights",
    "InMemoryConceptFeatureRuleRepository",
    "InMemoryRunValidation",
    "MODULE_ID",
    "PHASE_NAME",
    "SURFACE_ERROR_CODE",
    "build_default_concept_feature_rule_repository",
    "build_default_in_memory_repositories",
    "build_default_internal_condition_feature_estimator",
    "build_scaffold_internal_condition_feature_estimator",
    "merge_internal_feature_delta",
    "zero_feature_vector",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
