"""Environment variable loader for reco settings."""

from __future__ import annotations

import os
from collections.abc import Mapping

from reco.config.env import parse_app_env
from reco.config.settings import RecoSettings


def _read_optional_str(source: Mapping[str, str], key: str) -> str | None:
    value = source.get(key)
    if value is None or value.strip() == "":
        return None
    return value.strip()


def _read_port(source: Mapping[str, str]) -> int | None:
    raw = _read_optional_str(source, "PORT")
    if raw is None:
        return None

    try:
        port = int(raw)
    except ValueError as exc:
        raise ValueError(f"PORT must be an integer, got {raw!r}") from exc

    if port <= 0:
        raise ValueError(f"PORT must be positive, got {port}")

    return port


def load_reco_settings(*, environ: Mapping[str, str] | None = None) -> RecoSettings:
    """Load reco settings from environment variables.

    Secret values are retained on the returned object but must not be logged.
    """

    source = os.environ if environ is None else environ

    return RecoSettings(
        app_env=parse_app_env(source.get("APP_ENV")),
        log_level=_read_optional_str(source, "LOG_LEVEL") or "info",
        port=_read_port(source),
        database_url=_read_optional_str(source, "DATABASE_URL"),
        redis_url=_read_optional_str(source, "REDIS_URL"),
        openai_api_key=_read_optional_str(source, "OPENAI_API_KEY"),
        reco_internal_api_key=_read_optional_str(source, "RECO_INTERNAL_API_KEY"),
    )
