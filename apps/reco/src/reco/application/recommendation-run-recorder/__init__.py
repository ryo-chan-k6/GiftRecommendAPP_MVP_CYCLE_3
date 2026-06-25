"""MOD-RECO-002 Recommendation Run Recorder package.

Physical path uses kebab-case per module spec. Import as
``reco.application.recommendation_run_recorder``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.recommendation_run_recorder"
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

from .errors import MODULE_ID, RunRecorderError, RunStateConflictError  # noqa: E402
from .recorder import RecommendationRunRecorder  # noqa: E402

__all__ = [
    "MODULE_ID",
    "RecommendationRunRecorder",
    "RunRecorderError",
    "RunStateConflictError",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
