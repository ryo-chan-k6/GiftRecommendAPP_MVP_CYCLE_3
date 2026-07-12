"""MOD-RECO-023 Reason Generator package.

Physical path uses kebab-case per module spec. Import as
``reco.application.reason_generator``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.reason_generator"
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
    BUILDER_ITEMS_VERSION_INFO_KEY,
    FEATURE_BADGE_MAP,
    GENERATION_METHOD_INTERNAL_FALLBACK,
    GENERATION_METHOD_TEMPLATE,
    GENERIC_REASON_SUMMARY,
    LLM_REFINEMENT_ENV,
    MODULE_ID,
    PHASE_NAME,
    STRONG_MATCH_THRESHOLD,
)
from .errors import MODULE_ERROR_MODULE_ID, ReasonGeneratorError  # noqa: E402
from .executor import ReasonGenerator, build_default_reason_generator  # noqa: E402
from .factory import build_scaffold_reason_generator  # noqa: E402
from .in_memory_repository import (  # noqa: E402
    InMemoryItemSemanticReadRepository,
    InMemoryReasonTemplateReadRepository,
    InMemoryRecommendationReasonRepository,
    build_default_in_memory_item_semantic_read_repository,
    build_default_in_memory_reason_template_repository,
)
from .input_parser import parse_reason_generator_input  # noqa: E402
from .models import (  # noqa: E402
    GeneratedReason,
    ItemSemanticRecord,
    ReasonGeneratorInput,
    ReasonGeneratorInputItem,
    ReasonGeneratorRunMetrics,
    ReasonTemplateRecord,
    RecommendationReasonInsertRow,
    SelectedFeature,
    SemanticEvidence,
)
from .reason_engine import aggregate_outcome, generate_reasons_for_run  # noqa: E402

__all__ = [
    "BUILDER_ITEMS_VERSION_INFO_KEY",
    "FEATURE_BADGE_MAP",
    "GENERATION_METHOD_INTERNAL_FALLBACK",
    "GENERATION_METHOD_TEMPLATE",
    "GENERIC_REASON_SUMMARY",
    "GeneratedReason",
    "InMemoryItemSemanticReadRepository",
    "InMemoryReasonTemplateReadRepository",
    "InMemoryRecommendationReasonRepository",
    "ItemSemanticRecord",
    "LLM_REFINEMENT_ENV",
    "MODULE_ERROR_MODULE_ID",
    "MODULE_ID",
    "PHASE_NAME",
    "ReasonGenerator",
    "ReasonGeneratorError",
    "ReasonGeneratorInput",
    "ReasonGeneratorInputItem",
    "ReasonGeneratorRunMetrics",
    "ReasonTemplateRecord",
    "RecommendationReasonInsertRow",
    "STRONG_MATCH_THRESHOLD",
    "SelectedFeature",
    "SemanticEvidence",
    "aggregate_outcome",
    "build_default_in_memory_item_semantic_read_repository",
    "build_default_in_memory_reason_template_repository",
    "build_default_reason_generator",
    "build_scaffold_reason_generator",
    "generate_reasons_for_run",
    "parse_reason_generator_input",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
