"""MOD-RECO-029 Error Log Writer package.

Physical path uses kebab-case per module spec. Import as
``reco.application.error_log_writer``.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.error_log_writer"
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


def _ensure_reco_error_handler_loaded() -> None:
    reco_handler_root = "reco.application.reco_error_handler"
    if reco_handler_root in sys.modules:
        return

    handler_dir = _PKG_DIR.parent / "reco-error-handler"
    init_path = handler_dir / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        reco_handler_root,
        init_path,
        submodule_search_locations=[str(handler_dir)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load reco.application.reco_error_handler")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_ensure_reco_error_handler_loaded()

from .constants import MODULE_ID  # noqa: E402
from .factory import (  # noqa: E402
    build_default_error_log_writer,
    build_scaffold_error_log_writer,
)
from .models import ErrorLogRecord  # noqa: E402
from .ports import ErrorLogRepository  # noqa: E402
from .repository import InMemoryErrorLogRepository  # noqa: E402
from .validation import ErrorLogValidationError  # noqa: E402
from .writer import ErrorLogWriter  # noqa: E402

__all__ = [
    "ErrorLogRecord",
    "ErrorLogRepository",
    "ErrorLogValidationError",
    "ErrorLogWriter",
    "InMemoryErrorLogRepository",
    "MODULE_ID",
    "build_default_error_log_writer",
    "build_scaffold_error_log_writer",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
