"""Shared fixtures for infrastructure/db tests."""

from __future__ import annotations

import os

import pytest

from reco.infrastructure.db.application_bootstrap import ensure_observability_application_packages

ensure_observability_application_packages()


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "postgres_integration: requires a reachable DATABASE_URL and applied DDL",
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
        pytest.skip("DATABASE_URL is unset; postgres integration test skipped")

    from reco.infrastructure.db.session import PostgresDatabaseSession

    session = PostgresDatabaseSession(database_url=database_url)
    session.open()
    health = session.health_check()
    if not health.is_available:
        session.close()
        pytest.skip("DATABASE_URL is set but PostgreSQL is unreachable")
    try:
        yield session
    finally:
        session.close()
