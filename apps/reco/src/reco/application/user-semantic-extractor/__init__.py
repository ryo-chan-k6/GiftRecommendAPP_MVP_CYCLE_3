"""MOD-RECO-004 User Semantic Extractor package.

Physical path uses kebab-case per module spec. Import as
``reco.application.user_semantic_extractor``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.user_semantic_extractor"
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
    PHASE_NAME,
    SURFACE_ERROR_CODE,
)
from .errors import SemanticExtractError  # noqa: E402
from .extractor import UserSemanticExtractor, build_default_user_semantic_extractor  # noqa: E402
from .factory import build_scaffold_user_semantic_extractor  # noqa: E402
from .in_memory_repository import (  # noqa: E402
    DEFAULT_FORMAL_REFINED_CODE,
    DEFAULT_TOO_CASUAL_CODE,
    DEFAULT_WARM_HEARTFELT_CODE,
    InMemoryRunValidation,
    InMemorySemanticCatalog,
    InMemoryUserSemanticRepository,
    build_default_in_memory_repositories,
    build_default_semantic_catalog,
)

__all__ = [
    "CONFIDENCE_ADOPTION_THRESHOLD",
    "DEFAULT_FORMAL_REFINED_CODE",
    "DEFAULT_TOO_CASUAL_CODE",
    "DEFAULT_WARM_HEARTFELT_CODE",
    "InMemoryRunValidation",
    "InMemorySemanticCatalog",
    "InMemoryUserSemanticRepository",
    "MODULE_ID",
    "PHASE_NAME",
    "SURFACE_ERROR_CODE",
    "SemanticExtractError",
    "UserSemanticExtractor",
    "build_default_in_memory_repositories",
    "build_default_semantic_catalog",
    "build_default_user_semantic_extractor",
    "build_scaffold_user_semantic_extractor",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
