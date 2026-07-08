"""MOD-RECO-013 Post Hard Filter Executor package.

Physical path uses kebab-case per module spec. Import as
``reco.application.post_hard_filter_executor``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.post_hard_filter_executor"
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
    AVOID_CONFIDENCE_THRESHOLD,
    INPUT_INTENT_AVOID,
    INPUT_INTENT_NG_CANDIDATE,
    MODULE_ID,
    NG_CONFIDENCE_THRESHOLD,
    PHASE_NAME,
    REASON_DISPLAY_VALIDATION,
    REASON_DUPLICATE,
    REASON_INCONSISTENCY,
    REASON_SEMANTIC_NG,
    SURFACE_ERROR_CODE,
    VALIDATION_STATUS_PASSED,
)
from .errors import MODULE_ERROR_MODULE_ID, PostHardFilterError  # noqa: E402
from .executor import (  # noqa: E402
    PostHardFilterExecutor,
    build_default_post_hard_filter_executor,
)
from .factory import build_scaffold_post_hard_filter_executor  # noqa: E402
from .filter_engine import run_post_hard_filter  # noqa: E402
from .in_memory_repository import (  # noqa: E402
    InMemoryItemRecord,
    InMemoryItemRepository,
    build_default_in_memory_item_repository,
)
from .models import (  # noqa: E402
    AvoidObservationSummary,
    ExcludedCandidateEntry,
    ExcludedCandidateLog,
    ItemSemanticConcept,
    ItemSemanticRecord,
    ItemValidationRecord,
    PostHardFilterResult,
    ValidatedRetrievalCandidate,
    ValidatedRetrievalCandidateItem,
)
from .ports import ItemRepositoryPort  # noqa: E402

__all__ = [
    "AVOID_CONFIDENCE_THRESHOLD",
    "AvoidObservationSummary",
    "ExcludedCandidateEntry",
    "ExcludedCandidateLog",
    "INPUT_INTENT_AVOID",
    "INPUT_INTENT_NG_CANDIDATE",
    "InMemoryItemRecord",
    "InMemoryItemRepository",
    "ItemRepositoryPort",
    "ItemSemanticConcept",
    "ItemSemanticRecord",
    "ItemValidationRecord",
    "MODULE_ERROR_MODULE_ID",
    "MODULE_ID",
    "NG_CONFIDENCE_THRESHOLD",
    "PHASE_NAME",
    "PostHardFilterError",
    "PostHardFilterExecutor",
    "PostHardFilterResult",
    "REASON_DISPLAY_VALIDATION",
    "REASON_DUPLICATE",
    "REASON_INCONSISTENCY",
    "REASON_SEMANTIC_NG",
    "SURFACE_ERROR_CODE",
    "VALIDATION_STATUS_PASSED",
    "ValidatedRetrievalCandidate",
    "ValidatedRetrievalCandidateItem",
    "build_default_in_memory_item_repository",
    "build_default_post_hard_filter_executor",
    "build_scaffold_post_hard_filter_executor",
    "run_post_hard_filter",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
