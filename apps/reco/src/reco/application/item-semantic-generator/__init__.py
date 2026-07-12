"""MOD-RECO-026 Item Semantic Generator package.

Physical path uses kebab-case per module spec. Import as
``reco.application.item_semantic_generator``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.item_semantic_generator"
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
    CONFIDENCE_ADOPTION_THRESHOLD,
    MODULE_ID,
    SURFACE_ERROR_CODE,
)
from .errors import ItemSemanticGeneratorError  # noqa: E402
from .factory import build_scaffold_item_semantic_generator  # noqa: E402
from .generator import ItemSemanticGenerator, build_default_item_semantic_generator  # noqa: E402
from .in_memory_repository import (  # noqa: E402
    DEFAULT_FORMAL_REFINED_CODE,
    DEFAULT_PRESTIGIOUS_QUALITY_CODE,
    DEFAULT_SAFE_CLASSIC_CODE,
    InMemoryItemSemanticRepository,
    InMemoryItemValidation,
    InMemorySemanticCatalog,
    InMemorySemanticConfigVersion,
    build_default_in_memory_repositories,
    build_default_semantic_catalog,
)
from .models import (  # noqa: E402
    GenerationStatus,
    ItemSemanticGenerationContext,
    ItemSemanticGenerationResult,
)
from .ports import ItemSemanticGeneratorPort  # noqa: E402

__all__ = [
    "CONFIDENCE_ADOPTION_THRESHOLD",
    "DEFAULT_FORMAL_REFINED_CODE",
    "DEFAULT_PRESTIGIOUS_QUALITY_CODE",
    "DEFAULT_SAFE_CLASSIC_CODE",
    "GenerationStatus",
    "InMemoryItemSemanticRepository",
    "InMemoryItemValidation",
    "InMemorySemanticCatalog",
    "InMemorySemanticConfigVersion",
    "ItemSemanticGenerationContext",
    "ItemSemanticGenerationResult",
    "ItemSemanticGenerator",
    "ItemSemanticGeneratorError",
    "ItemSemanticGeneratorPort",
    "MODULE_ID",
    "SURFACE_ERROR_CODE",
    "build_default_in_memory_repositories",
    "build_default_item_semantic_generator",
    "build_default_semantic_catalog",
    "build_scaffold_item_semantic_generator",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
