"""Test bootstrap for hyphenated application package paths."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_package(import_root: str, init_relative: str) -> None:
    init_path = Path(__file__).resolve().parents[3] / init_relative
    spec = importlib.util.spec_from_file_location(
        import_root,
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load package: {import_root}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def _load_orchestrator_package() -> None:
    _load_package(
        "reco.application.recommendation_orchestrator",
        "src/reco/application/recommendation-orchestrator/__init__.py",
    )


def _load_run_recorder_package() -> None:
    _load_package(
        "reco.application.recommendation_run_recorder",
        "src/reco/application/recommendation-run-recorder/__init__.py",
    )


def _load_config_version_resolver_package() -> None:
    _load_package(
        "reco.application.config_version_resolver",
        "src/reco/application/config-version-resolver/__init__.py",
    )


_load_run_recorder_package()
_load_orchestrator_package()
_load_config_version_resolver_package()
