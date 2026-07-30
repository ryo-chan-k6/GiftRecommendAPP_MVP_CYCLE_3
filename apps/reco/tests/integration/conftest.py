"""Shared fixtures for reco integration tests (Postgres E2E)."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

from reco.composition.bootstrap import ensure_composition_application_packages
from reco.infrastructure.db.application_bootstrap import ensure_observability_application_packages

ensure_observability_application_packages()
ensure_composition_application_packages()

_INTEGRATION_ROOT = Path(__file__).resolve().parent
_UNIT_APPLICATION = _INTEGRATION_ROOT.parent / "unit" / "application"
_APPLICATION_ROOT = Path(__file__).resolve().parents[2] / "src/reco/application"
for path in (_INTEGRATION_ROOT, _UNIT_APPLICATION):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _load_package(import_root: str, package_dir: str) -> None:
    init_path = _APPLICATION_ROOT / package_dir / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        import_root,
        init_path,
        submodule_search_locations=[str(init_path.parent)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load package: {import_root}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[import_root] = module
    spec.loader.exec_module(module)


_load_package(
    "reco.application.config_version_resolver",
    "config-version-resolver",
)


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "postgres_integration: requires DATABASE_URL, applied DDL, and observability bootstrap",
    )


@pytest.fixture
def database_url() -> str | None:
    url = os.environ.get("DATABASE_URL")
    if url in (None, "", "scaffold://database"):
        return None
    return url


@pytest.fixture
def postgres_session(database_url: str | None):
    if database_url is None:
        pytest.skip(
            "DATABASE_URL is unset; §14 No.10 Postgres integration tests skipped",
        )

    from reco.infrastructure.db.session import PostgresDatabaseSession

    session = PostgresDatabaseSession(database_url=database_url)
    session.open()
    health = session.health_check()
    if not health.is_available:
        session.close()
        pytest.skip(
            "DATABASE_URL is set but PostgreSQL is unreachable; "
            "§14 No.10 Postgres integration tests skipped",
        )

    from helpers.postgres_bootstrap import ensure_observability_ddl

    if not ensure_observability_ddl(session):
        session.close()
        pytest.skip(
            "observability DDL (metric_log / phase_log / error_log) is missing; "
            "apply supabase migrations before running integration tests",
        )

    try:
        yield session
    finally:
        session.close()
