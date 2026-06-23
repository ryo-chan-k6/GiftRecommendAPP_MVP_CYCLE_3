"""Shared scaffold helpers for config modules."""

from __future__ import annotations

from reco.config.env import AppEnv
from reco.config.settings import RecoSettings


def scaffold_reco_settings(*, app_env: AppEnv = AppEnv.DEV) -> RecoSettings:
    """Build in-memory settings for Phase4a unit tests without real secrets."""

    return RecoSettings(
        app_env=app_env,
        log_level="info",
        port=8000,
        database_url="scaffold://database",
        redis_url="scaffold://redis",
        openai_api_key="scaffold-openai-api-key",
        reco_internal_api_key="scaffold-reco-internal-api-key",
    )
