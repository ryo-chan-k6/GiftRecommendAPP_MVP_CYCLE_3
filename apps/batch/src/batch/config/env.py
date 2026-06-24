"""Environment identifier for batch settings."""

from __future__ import annotations

from enum import StrEnum


class AppEnv(StrEnum):
    """Execution environment identifier (環境設計書 §19.2)."""

    DEV = "dev"
    STG = "stg"
    PROD = "prod"


def parse_app_env(raw: str | None) -> AppEnv:
    """Parse APP_ENV. Phase4a defaults to dev when unset for local scaffold."""

    if raw is None or raw.strip() == "":
        return AppEnv.DEV

    normalized = raw.strip().lower()
    try:
        return AppEnv(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported APP_ENV value: {raw!r}") from exc
