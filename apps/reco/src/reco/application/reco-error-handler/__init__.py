"""MOD-RECO-024 Reco Error Handler package.

Physical path uses kebab-case per module spec. Import as
``reco.application.reco_error_handler``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.reco_error_handler"
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
    MODULE_SURFACE_ERROR_CODES,
    SERVICE_NAME,
    SURFACE_ERROR_CODE_CONFIG,
    SURFACE_ERROR_CODE_RETRIEVAL,
    SURFACE_ERROR_CODE_RUN_CONFLICT,
    SURFACE_ERROR_CODE_TIMEOUT,
    SURFACE_ERROR_CODE_UNKNOWN,
)
from .executor import (  # noqa: E402
    NoOpErrorLogWriter,
    RecoErrorHandler,
    build_default_reco_error_handler,
)
from .factory import build_scaffold_reco_error_handler  # noqa: E402
from .models import ErrorLogWriteRequest  # noqa: E402
from .ports import ErrorLogWriterPort  # noqa: E402

__all__ = [
    "ErrorLogWriteRequest",
    "ErrorLogWriterPort",
    "MODULE_ID",
    "MODULE_SURFACE_ERROR_CODES",
    "NoOpErrorLogWriter",
    "RecoErrorHandler",
    "SERVICE_NAME",
    "SURFACE_ERROR_CODE_CONFIG",
    "SURFACE_ERROR_CODE_RETRIEVAL",
    "SURFACE_ERROR_CODE_RUN_CONFLICT",
    "SURFACE_ERROR_CODE_TIMEOUT",
    "SURFACE_ERROR_CODE_UNKNOWN",
    "build_default_reco_error_handler",
    "build_scaffold_reco_error_handler",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
