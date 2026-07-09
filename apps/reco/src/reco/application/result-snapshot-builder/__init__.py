"""MOD-RECO-022 Result Snapshot Builder package.

Physical path uses kebab-case per module spec. Import as
``reco.application.result_snapshot_builder``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.result_snapshot_builder"
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
    ITEM_INFO_ERROR_CODE,
    MODULE_ID,
    PHASE_NAME,
    RESULT_ITEM_SAVE_ERROR_CODE,
    SNAPSHOT_BUILD_ERROR_CODE,
    SURFACE_ERROR_CODE,
)
from .errors import (  # noqa: E402
    MODULE_ERROR_MODULE_ID,
    ResultSnapshotBuilderError,
)
from .executor import (  # noqa: E402
    ResultSnapshotBuilder,
    build_default_result_snapshot_builder,
)
from .factory import build_scaffold_result_snapshot_builder  # noqa: E402
from .in_memory_repository import (  # noqa: E402
    InMemoryItemSnapshotReadRepository,
    InMemoryItemSnapshotSource,
    InMemoryRecommendationResultItemRepository,
    build_default_in_memory_item_snapshot_read_repository,
)
from .input_parser import encode_builder_items, parse_snapshot_builder_input  # noqa: E402
from .models import (  # noqa: E402
    ItemPrimaryImageRecord,
    ItemReviewSnapshotRecord,
    ItemSnapshot,
    ItemSourceRecord,
    RecommendationResultItemInsertRow,
    SnapshotBuilderInput,
    SnapshotBuilderInputItem,
    SnapshotBuilderRunMetrics,
)
from .snapshot_engine import build_result_snapshots  # noqa: E402

__all__ = [
    "BUILDER_ITEMS_VERSION_INFO_KEY",
    "InMemoryItemSnapshotReadRepository",
    "InMemoryItemSnapshotSource",
    "InMemoryRecommendationResultItemRepository",
    "ITEM_INFO_ERROR_CODE",
    "ItemPrimaryImageRecord",
    "ItemReviewSnapshotRecord",
    "ItemSnapshot",
    "ItemSourceRecord",
    "MODULE_ERROR_MODULE_ID",
    "MODULE_ID",
    "PHASE_NAME",
    "RESULT_ITEM_SAVE_ERROR_CODE",
    "RecommendationResultItemInsertRow",
    "ResultSnapshotBuilder",
    "ResultSnapshotBuilderError",
    "SNAPSHOT_BUILD_ERROR_CODE",
    "SURFACE_ERROR_CODE",
    "SnapshotBuilderInput",
    "SnapshotBuilderInputItem",
    "SnapshotBuilderRunMetrics",
    "build_default_in_memory_item_snapshot_read_repository",
    "build_default_result_snapshot_builder",
    "build_result_snapshots",
    "build_scaffold_result_snapshot_builder",
    "encode_builder_items",
    "parse_snapshot_builder_input",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
