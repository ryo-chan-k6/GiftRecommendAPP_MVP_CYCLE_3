"""MOD-RECO-009 User Context Builder package.

Physical path uses kebab-case per module spec. Import as
``reco.application.user_context_builder``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.user_context_builder"
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

from .builder import (  # noqa: E402
    UserContextBuilder,
    build_default_user_context_builder,
)
from .constants import (  # noqa: E402
    EMBEDDING_QUERY_TEXT_MAX_LENGTH,
    EXPECTED_USER_FEATURE_ROW_COUNT,
    FREE_TEXT_TRUNCATE_LENGTH,
    GUARD_CLIP_MAX,
    GUARD_CLIP_MIN,
    LAMBDA_CTX_DECIMAL_PLACES,
    LAMBDA_CTX_FALLBACK,
    MODULE_ID,
    PHASE_NAME,
    SEMANTIC_QUERY_TOP_K,
    SURFACE_ERROR_CODE,
)
from .context_engine import (  # noqa: E402
    assemble_user_context,
    build_avoid_query_text,
    build_context_query,
    build_embedding_query_text,
    build_free_text_query,
    build_preferred_query,
    build_semantic_query,
    normalize_query_text,
)
from .errors import UserContextBuildError  # noqa: E402
from .factory import build_scaffold_user_context_builder  # noqa: E402
from .in_memory_repository import (  # noqa: E402
    InMemoryLambdaContextRuleRepository,
    InMemoryRunValidation,
    InMemoryUserFeatureReadRepository,
    InMemoryUserMeaningRepository,
    build_default_in_memory_repositories,
)
from .lambda_ctx_engine import (  # noqa: E402
    finalize_lambda_ctx,
    guard_clip,
    resolve_lambda_ctx,
    round_to_scale,
)
from .models import (  # noqa: E402
    CompletedUserMeaning,
    NonPreferredContext,
    PreferredContext,
    UserContext,
    UserFeatureRow,
    UserMeaningInsertRow,
)

__all__ = [
    "CompletedUserMeaning",
    "EMBEDDING_QUERY_TEXT_MAX_LENGTH",
    "EXPECTED_USER_FEATURE_ROW_COUNT",
    "FREE_TEXT_TRUNCATE_LENGTH",
    "GUARD_CLIP_MAX",
    "GUARD_CLIP_MIN",
    "InMemoryLambdaContextRuleRepository",
    "InMemoryRunValidation",
    "InMemoryUserFeatureReadRepository",
    "InMemoryUserMeaningRepository",
    "LAMBDA_CTX_DECIMAL_PLACES",
    "LAMBDA_CTX_FALLBACK",
    "MODULE_ID",
    "NonPreferredContext",
    "PHASE_NAME",
    "PreferredContext",
    "SEMANTIC_QUERY_TOP_K",
    "SURFACE_ERROR_CODE",
    "UserContext",
    "UserContextBuildError",
    "UserContextBuilder",
    "UserFeatureRow",
    "UserMeaningInsertRow",
    "assemble_user_context",
    "build_avoid_query_text",
    "build_context_query",
    "build_default_in_memory_repositories",
    "build_default_user_context_builder",
    "build_embedding_query_text",
    "build_free_text_query",
    "build_preferred_query",
    "build_scaffold_user_context_builder",
    "build_semantic_query",
    "finalize_lambda_ctx",
    "guard_clip",
    "normalize_query_text",
    "resolve_lambda_ctx",
    "round_to_scale",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
