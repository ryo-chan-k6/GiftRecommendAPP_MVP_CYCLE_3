"""Test bootstrap for hyphenated recommendation-run-recorder package path."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_run_recorder_package() -> None:
    init_path = (
        Path(__file__).resolve().parents[4]
        / "src/reco/application/recommendation-run-recorder/__init__.py"
    )
    spec = importlib.util.spec_from_file_location(
        "reco.application.recommendation_run_recorder",
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load recommendation run recorder package")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_load_run_recorder_package()
