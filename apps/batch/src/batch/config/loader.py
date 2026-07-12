"""Environment variable loader for batch settings."""

from __future__ import annotations

import os
from collections.abc import Mapping

from batch.config.env import parse_app_env
from batch.config.settings import BatchSettings


def _read_optional_str(source: Mapping[str, str], key: str) -> str | None:
    value = source.get(key)
    if value is None or value.strip() == "":
        return None
    return value.strip()


def _read_positive_int(source: Mapping[str, str], key: str) -> int | None:
    raw = _read_optional_str(source, key)
    if raw is None:
        return None

    try:
        parsed = int(raw)
    except ValueError as exc:
        raise ValueError(f"{key} must be an integer, got {raw!r}") from exc

    if parsed <= 0:
        raise ValueError(f"{key} must be positive, got {parsed}")

    return parsed


def load_batch_settings(*, environ: Mapping[str, str] | None = None) -> BatchSettings:
    """Load batch settings from environment variables.

    Secret values are retained on the returned object but must not be logged.
    """

    source = os.environ if environ is None else environ

    return BatchSettings(
        app_env=parse_app_env(source.get("APP_ENV")),
        log_level=_read_optional_str(source, "LOG_LEVEL") or "info",
        database_url=_read_optional_str(source, "DATABASE_URL"),
        openai_api_key=_read_optional_str(source, "OPENAI_API_KEY"),
        rakuten_application_id=_read_optional_str(source, "RAKUTEN_APPLICATION_ID"),
        object_storage_bucket=_read_optional_str(source, "OBJECT_STORAGE_BUCKET"),
        object_storage_endpoint=_read_optional_str(source, "OBJECT_STORAGE_ENDPOINT"),
        object_storage_access_key=_read_optional_str(source, "OBJECT_STORAGE_ACCESS_KEY"),
        object_storage_secret_key=_read_optional_str(source, "OBJECT_STORAGE_SECRET_KEY"),
        batch_internal_token=_read_optional_str(source, "BATCH_INTERNAL_TOKEN"),
        batch_chunk_size=_read_positive_int(source, "BATCH_CHUNK_SIZE"),
        batch_max_retry=_read_positive_int(source, "BATCH_MAX_RETRY"),
        supabase_url=_read_optional_str(source, "SUPABASE_URL"),
        supabase_service_role_key=_read_optional_str(source, "SUPABASE_SERVICE_ROLE_KEY"),
    )
