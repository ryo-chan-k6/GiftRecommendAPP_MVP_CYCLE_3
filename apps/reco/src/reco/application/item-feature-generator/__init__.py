"""MOD-RECO-027 Item Feature Generator package.

Physical path uses kebab-case per module spec. Import as
``reco.application.item_feature_generator``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.item_feature_generator"
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
    MODULE_ID,
    NEUTRAL_BASE,
    SURFACE_ERROR_CODE,
)
from .errors import ItemFeatureGeneratorError  # noqa: E402
from .factory import build_scaffold_item_feature_generator  # noqa: E402
from .generator import ItemFeatureGenerator, build_default_item_feature_generator  # noqa: E402
from .in_memory_repository import (  # noqa: E402
    InMemoryConceptFeatureRuleRepository,
    InMemoryFeatureDefinitionRepository,
    InMemoryItemFeatureRepository,
    InMemoryItemValidation,
    InMemoryNormalizationRuleRepository,
    build_default_in_memory_repositories,
)
from .models import (  # noqa: E402
    GenerationStatus,
    ItemFeatureGenerationContext,
    ItemFeatureGenerationResult,
    ItemSemanticInput,
)
from .ports import ItemFeatureGeneratorPort  # noqa: E402

__all__ = [
    "GenerationStatus",
    "InMemoryConceptFeatureRuleRepository",
    "InMemoryFeatureDefinitionRepository",
    "InMemoryItemFeatureRepository",
    "InMemoryItemValidation",
    "InMemoryNormalizationRuleRepository",
    "ItemFeatureGenerationContext",
    "ItemFeatureGenerationResult",
    "ItemFeatureGenerator",
    "ItemFeatureGeneratorError",
    "ItemFeatureGeneratorPort",
    "ItemSemanticInput",
    "MODULE_ID",
    "NEUTRAL_BASE",
    "SURFACE_ERROR_CODE",
    "build_default_in_memory_repositories",
    "build_default_item_feature_generator",
    "build_scaffold_item_feature_generator",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
