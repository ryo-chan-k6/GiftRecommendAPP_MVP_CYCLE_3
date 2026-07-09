"""Test bootstrap for API layer (hyphenated application imports)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]


def _load_package(import_root: str, init_relative: str) -> None:
    init_path = _ROOT / init_relative
    spec = importlib.util.spec_from_file_location(
        import_root,
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load package: {import_root}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_load_package(
    "reco.application.recommendation_orchestrator",
    "src/reco/application/recommendation-orchestrator/__init__.py",
)
