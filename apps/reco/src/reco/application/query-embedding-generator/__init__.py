"""MOD-RECO-010 Query Embedding Generator package.

Physical path uses kebab-case per module spec. Import as
``reco.application.query_embedding_generator``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.query_embedding_generator"
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
    DETAIL_ERROR_GENERATION_FAILED,
    DETAIL_ERROR_RATE_LIMIT,
    DETAIL_ERROR_TIMEOUT,
    EMBEDDING_DIMENSIONS,
    EMBEDDING_PURPOSE,
    MODULE_ID,
    PHASE_NAME,
    SURFACE_ERROR_CODE,
)
from .embedding_validation import validate_embedding_vector  # noqa: E402
from .errors import QueryEmbeddingGenerationError  # noqa: E402
from .factory import (  # noqa: E402
    build_scaffold_query_embedding_generator,
)
from .generator import (  # noqa: E402
    QueryEmbeddingGenerator,
    build_default_query_embedding_generator,
)
from .in_memory_client import (  # noqa: E402
    InMemoryEmbeddingApiClient,
    build_default_in_memory_embedding_client,
)
from .in_memory_repository import (  # noqa: E402
    InMemoryRunValidation,
    build_default_in_memory_run_validation,
)
from .models import PreferredEmbedding, QueryEmbedding  # noqa: E402
from .ports import (  # noqa: E402
    EmbeddingApiClientPort,
    EmbeddingGenerationResult,
    RunValidationPort,
)

__all__ = [
    "DETAIL_ERROR_GENERATION_FAILED",
    "DETAIL_ERROR_RATE_LIMIT",
    "DETAIL_ERROR_TIMEOUT",
    "EMBEDDING_DIMENSIONS",
    "EMBEDDING_PURPOSE",
    "EmbeddingApiClientPort",
    "EmbeddingGenerationResult",
    "InMemoryEmbeddingApiClient",
    "InMemoryRunValidation",
    "MODULE_ID",
    "PHASE_NAME",
    "PreferredEmbedding",
    "QueryEmbedding",
    "QueryEmbeddingGenerationError",
    "QueryEmbeddingGenerator",
    "RunValidationPort",
    "SURFACE_ERROR_CODE",
    "build_default_in_memory_embedding_client",
    "build_default_in_memory_run_validation",
    "build_default_query_embedding_generator",
    "build_scaffold_query_embedding_generator",
    "validate_embedding_vector",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
