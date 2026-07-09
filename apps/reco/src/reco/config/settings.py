"""Reco component settings scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from reco.config.env import AppEnv

RECO_ENV_KEYS: Final[tuple[str, ...]] = (
    "APP_ENV",
    "LOG_LEVEL",
    "PORT",
    "DATABASE_URL",
    "REDIS_URL",
    "OPENAI_API_KEY",
    "RECO_INTERNAL_API_KEY",
)

RECO_REQUIRED_SECRET_KEYS: Final[tuple[str, ...]] = (
    "DATABASE_URL",
    "REDIS_URL",
    "OPENAI_API_KEY",
    "RECO_INTERNAL_API_KEY",
)

_SECRET_FIELD_BY_ENV_KEY: Final[dict[str, str]] = {
    "DATABASE_URL": "database_url",
    "REDIS_URL": "redis_url",
    "OPENAI_API_KEY": "openai_api_key",
    "RECO_INTERNAL_API_KEY": "reco_internal_api_key",
}


@dataclass(frozen=True)
class RecoSettings:
    """Typed reco configuration loaded from environment variables."""

    app_env: AppEnv
    log_level: str
    port: int | None
    database_url: str | None
    redis_url: str | None
    openai_api_key: str | None
    reco_internal_api_key: str | None

    def missing_required_secrets(self) -> tuple[str, ...]:
        """Return MVP-required secret env keys that are unset."""

        missing: list[str] = []
        for env_key in RECO_REQUIRED_SECRET_KEYS:
            field_name = _SECRET_FIELD_BY_ENV_KEY[env_key]
            if getattr(self, field_name) in (None, ""):
                missing.append(env_key)
        return tuple(missing)

    def has_required_secrets(self) -> bool:
        return not self.missing_required_secrets()

    def __repr__(self) -> str:
        return (
            "RecoSettings("
            f"app_env={self.app_env!r}, "
            f"log_level={self.log_level!r}, "
            f"port={self.port!r}, "
            "database_url='***', "
            "redis_url='***', "
            "openai_api_key='***', "
            "reco_internal_api_key='***'"
            ")"
        )
