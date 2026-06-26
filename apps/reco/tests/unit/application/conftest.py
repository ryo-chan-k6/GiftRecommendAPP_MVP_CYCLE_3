"""Test bootstrap for hyphenated application package paths."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parents[3] / "src/reco/application"


def _load_hyphenated_package(import_root: str, directory_name: str) -> None:
    init_path = _SRC_ROOT / directory_name / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        import_root,
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load package: {import_root}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


_load_hyphenated_package(
    "reco.application.recommendation_orchestrator",
    "recommendation-orchestrator",
)
_load_hyphenated_package(
    "reco.application.recommendation_run_recorder",
    "recommendation-run-recorder",
)
_load_hyphenated_package(
    "reco.application.config_version_resolver",
    "config-version-resolver",
)
