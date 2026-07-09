"""MOD-RECO-003 Config Version Resolver package.

Physical path uses kebab-case per module spec. Import as
``reco.application.config_version_resolver``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.config_version_resolver"
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
    DEFAULT_SEMANTIC_CONFIG_NAME,
    MODULE_ID,
    REQUIRED_MODEL_TYPES,
    SURFACE_ERROR_CODE,
)
from .errors import ConfigResolveError  # noqa: E402
from .in_memory_repository import (  # noqa: E402
    DEFAULT_EMBEDDING_MODEL_VERSION_ID,
    DEFAULT_MATCHING_CONFIG_ID,
    DEFAULT_RANKING_CONFIG_ID,
    DEFAULT_SEMANTIC_CONFIG_VERSION_ID,
    InMemoryConfigRepository,
    build_default_in_memory_repository,
)
from .models import (  # noqa: E402
    BatchResolveContext,
    GenerationType,
    ResolvedConfigVersions,
)
from .resolver import ConfigVersionResolver, build_default_config_resolver  # noqa: E402

__all__ = [
    "BatchResolveContext",
    "ConfigResolveError",
    "ConfigVersionResolver",
    "DEFAULT_EMBEDDING_MODEL_VERSION_ID",
    "DEFAULT_MATCHING_CONFIG_ID",
    "DEFAULT_RANKING_CONFIG_ID",
    "DEFAULT_SEMANTIC_CONFIG_NAME",
    "DEFAULT_SEMANTIC_CONFIG_VERSION_ID",
    "GenerationType",
    "InMemoryConfigRepository",
    "MODULE_ID",
    "REQUIRED_MODEL_TYPES",
    "ResolvedConfigVersions",
    "SURFACE_ERROR_CODE",
    "build_default_config_resolver",
    "build_default_in_memory_repository",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
