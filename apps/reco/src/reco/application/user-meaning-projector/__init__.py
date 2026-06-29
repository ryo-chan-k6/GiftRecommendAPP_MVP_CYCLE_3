"""MOD-RECO-008 User Meaning Projector package.

Physical path uses kebab-case per module spec. Import as
``reco.application.user_meaning_projector``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.user_meaning_projector"
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
    EXPECTED_USER_FEATURE_ROW_COUNT,
    GUARD_CLIP_MAX,
    GUARD_CLIP_MIN,
    MODULE_ID,
    PHASE_NAME,
    PROJECTION_VALUE_DECIMAL_PLACES,
    SURFACE_ERROR_CODE,
)
from .errors import UserMeaningProjectionError  # noqa: E402
from .factory import (  # noqa: E402
    build_scaffold_user_meaning_projector,
)
from .in_memory_repository import (  # noqa: E402
    InMemoryMeaningProjectionConfigRepository,
    InMemoryRunValidation,
    InMemoryUserFeatureReadRepository,
    build_default_in_memory_repositories,
    build_default_projection_weights,
)
from .models import (  # noqa: E402
    MeaningProjectionWeights,
    UserFeatureRow,
    UserMeaningProjection,
)
from .projection_engine import (  # noqa: E402
    ProjectionStats,
    ensure_complete_normalized_features,
    guard_clip,
    project_user_meaning_coordinates,
    round_to_scale,
)
from .projector import (  # noqa: E402
    UserMeaningProjector,
    build_default_user_meaning_projector,
)

__all__ = [
    "EXPECTED_USER_FEATURE_ROW_COUNT",
    "GUARD_CLIP_MAX",
    "GUARD_CLIP_MIN",
    "InMemoryMeaningProjectionConfigRepository",
    "InMemoryRunValidation",
    "InMemoryUserFeatureReadRepository",
    "MODULE_ID",
    "MeaningProjectionWeights",
    "PHASE_NAME",
    "PROJECTION_VALUE_DECIMAL_PLACES",
    "ProjectionStats",
    "SURFACE_ERROR_CODE",
    "UserFeatureRow",
    "UserMeaningProjection",
    "UserMeaningProjectionError",
    "UserMeaningProjector",
    "build_default_in_memory_repositories",
    "build_default_projection_weights",
    "build_default_user_meaning_projector",
    "build_scaffold_user_meaning_projector",
    "ensure_complete_normalized_features",
    "guard_clip",
    "project_user_meaning_coordinates",
    "round_to_scale",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
