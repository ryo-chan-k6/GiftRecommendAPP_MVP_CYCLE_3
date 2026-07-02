"""MOD-RECO-015 Meaning Match Aggregator package.

Physical path uses kebab-case per module spec. Import as
``reco.application.meaning_match_aggregator``.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.meaning_match_aggregator"
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

from .aggregation_engine import run_meaning_match_aggregation  # noqa: E402
from .constants import (  # noqa: E402
    AGGREGATION_METHOD_WEIGHTED_AVERAGE,
    MODULE_ID,
    PHASE_NAME,
    SURFACE_ERROR_CODE,
)
from .errors import MODULE_ERROR_MODULE_ID, MeaningMatchAggregatorError  # noqa: E402
from .executor import (  # noqa: E402
    MeaningMatchAggregator,
    build_default_meaning_match_aggregator,
)
from .factory import build_scaffold_meaning_match_aggregator  # noqa: E402
from .models import (  # noqa: E402
    MeaningMatchAggregatorRunMetrics,
    MeaningMatchEntry,
    MeaningMatchResult,
)

__all__ = [
    "AGGREGATION_METHOD_WEIGHTED_AVERAGE",
    "MODULE_ERROR_MODULE_ID",
    "MODULE_ID",
    "MeaningMatchAggregator",
    "MeaningMatchAggregatorError",
    "MeaningMatchAggregatorRunMetrics",
    "MeaningMatchEntry",
    "MeaningMatchResult",
    "PHASE_NAME",
    "SURFACE_ERROR_CODE",
    "build_default_meaning_match_aggregator",
    "build_scaffold_meaning_match_aggregator",
    "run_meaning_match_aggregation",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
