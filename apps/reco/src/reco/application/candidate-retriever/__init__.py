"""MOD-RECO-012 Candidate Retriever package.

Physical path uses kebab-case per module spec. Import as
``reco.application.candidate_retriever``.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_IMPORT_ROOT = "reco.application.candidate_retriever"
_PKG_DIR = Path(__file__).resolve().parent


def _ensure_package_shell() -> None:
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


def _register_kebab_subpackage(import_name: str, directory_name: str) -> None:
    sub_root = f"{_IMPORT_ROOT}.{import_name}"
    if sub_root in sys.modules:
        return

    sub_dir = _PKG_DIR / directory_name
    sub_pkg = types.ModuleType(sub_root)
    sub_pkg.__path__ = [str(sub_dir)]  # type: ignore[attr-defined]
    sub_pkg.__package__ = sub_root
    sys.modules[sub_root] = sub_pkg

    for py_file in sorted(sub_dir.glob("*.py")):
        if py_file.name == "__init__.py":
            continue
        module_stem = py_file.stem
        module_qualname = f"{sub_root}.{module_stem}"
        spec = importlib.util.spec_from_file_location(module_qualname, py_file)
        if spec is None or spec.loader is None:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_qualname] = module
        spec.loader.exec_module(module)
        setattr(sub_pkg, module_stem, module)


_ensure_package_shell()

from . import constants, errors, models, ports  # noqa: E402

_register_kebab_subpackage("pre_hard_filter", "pre-hard-filter")
_register_kebab_subpackage("retrieval", "retrieval")

from .constants import (  # noqa: E402
    DEFAULT_CANDIDATE_LIMIT_BATCH,
    DEFAULT_CANDIDATE_LIMIT_UI,
    MATERIALIZED_IDS_TEST_LIMIT,
    MODULE_ID,
    PHASE_NAME,
    PRE_FILTER_PHASE_NAME,
    RETRIEVAL_METHOD_VECTOR,
    SURFACE_ERROR_CODE_PRE_FILTER,
    SURFACE_ERROR_CODE_RETRIEVAL,
)
from .errors import (  # noqa: E402
    MODULE_ERROR_MODULE_ID,
    PreHardFilterError,
    RetrievalError,
)
from .factory import build_scaffold_candidate_retriever  # noqa: E402
from .in_memory_repository import (  # noqa: E402
    InMemoryItemRecord,
    InMemoryItemRepository,
    build_default_in_memory_item_repository,
)
from .models import (  # noqa: E402
    CandidateRetrieverResult,
    FilterPredicate,
    MergedFilterConditions,
    PoolRepresentation,
    PreFilteredItemPool,
    RetrievalCandidate,
    RetrievalCandidateItem,
)
from .ports import ItemRepositoryPort  # noqa: E402
from .retriever import (  # noqa: E402
    CandidateRetriever,
    build_default_candidate_retriever,
)

__all__ = [
    "DEFAULT_CANDIDATE_LIMIT_BATCH",
    "DEFAULT_CANDIDATE_LIMIT_UI",
    "CandidateRetriever",
    "CandidateRetrieverResult",
    "FilterPredicate",
    "InMemoryItemRecord",
    "InMemoryItemRepository",
    "ItemRepositoryPort",
    "MATERIALIZED_IDS_TEST_LIMIT",
    "MODULE_ERROR_MODULE_ID",
    "MODULE_ID",
    "MergedFilterConditions",
    "PHASE_NAME",
    "PRE_FILTER_PHASE_NAME",
    "PoolRepresentation",
    "PreFilteredItemPool",
    "PreHardFilterError",
    "RETRIEVAL_METHOD_VECTOR",
    "RetrievalCandidate",
    "RetrievalCandidateItem",
    "RetrievalError",
    "SURFACE_ERROR_CODE_PRE_FILTER",
    "SURFACE_ERROR_CODE_RETRIEVAL",
    "build_default_candidate_retriever",
    "build_default_in_memory_item_repository",
    "build_scaffold_candidate_retriever",
]

_virtual = sys.modules[_IMPORT_ROOT]
for _name in __all__:
    setattr(_virtual, _name, globals()[_name])
