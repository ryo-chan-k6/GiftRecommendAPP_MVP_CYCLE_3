"""Batch component settings scaffold."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from batch.config.env import AppEnv

BATCH_ENV_KEYS: Final[tuple[str, ...]] = (
    "APP_ENV",
    "LOG_LEVEL",
    "DATABASE_URL",
    "OPENAI_API_KEY",
    "RAKUTEN_APPLICATION_ID",
    "RAKUTEN_ACCESS_KEY",
    "OBJECT_STORAGE_BUCKET",
    "OBJECT_STORAGE_ENDPOINT",
    "OBJECT_STORAGE_ACCESS_KEY",
    "OBJECT_STORAGE_SECRET_KEY",
    "BATCH_INTERNAL_TOKEN",
    "BATCH_CHUNK_SIZE",
    "BATCH_MAX_RETRY",
    "BATCH_RAW_STAGING_MAX_RAW",
    "BATCH_RAW_STAGING_SOURCE_API",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
)

BATCH_REQUIRED_SECRET_KEYS: Final[tuple[str, ...]] = (
    "DATABASE_URL",
    "OPENAI_API_KEY",
    "RAKUTEN_APPLICATION_ID",
    "OBJECT_STORAGE_ACCESS_KEY",
    "OBJECT_STORAGE_SECRET_KEY",
)

BATCH_REQUIRED_CONFIG_KEYS: Final[tuple[str, ...]] = (
    "OBJECT_STORAGE_BUCKET",
)

_SECRET_FIELD_BY_ENV_KEY: Final[dict[str, str]] = {
    "DATABASE_URL": "database_url",
    "OPENAI_API_KEY": "openai_api_key",
    "RAKUTEN_APPLICATION_ID": "rakuten_application_id",
    "OBJECT_STORAGE_ACCESS_KEY": "object_storage_access_key",
    "OBJECT_STORAGE_SECRET_KEY": "object_storage_secret_key",
}

_CONFIG_FIELD_BY_ENV_KEY: Final[dict[str, str]] = {
    "OBJECT_STORAGE_BUCKET": "object_storage_bucket",
}


@dataclass(frozen=True)
class BatchSettings:
    """Typed batch configuration loaded from environment variables."""

    app_env: AppEnv
    log_level: str
    database_url: str | None
    openai_api_key: str | None
    rakuten_application_id: str | None
    rakuten_access_key: str | None
    object_storage_bucket: str | None
    object_storage_endpoint: str | None
    object_storage_access_key: str | None
    object_storage_secret_key: str | None
    batch_internal_token: str | None
    batch_chunk_size: int | None
    batch_max_retry: int | None
    batch_raw_staging_max_raw: int | None
    batch_raw_staging_source_api: str | None
    supabase_url: str | None
    supabase_service_role_key: str | None

    def missing_required_secrets(self) -> tuple[str, ...]:
        """Return MVP-required secret env keys that are unset."""

        missing: list[str] = []
        for env_key in BATCH_REQUIRED_SECRET_KEYS:
            field_name = _SECRET_FIELD_BY_ENV_KEY[env_key]
            if getattr(self, field_name) in (None, ""):
                missing.append(env_key)
        return tuple(missing)

    def missing_required_config(self) -> tuple[str, ...]:
        """Return MVP-required config env keys that are unset."""

        missing: list[str] = []
        for env_key in BATCH_REQUIRED_CONFIG_KEYS:
            field_name = _CONFIG_FIELD_BY_ENV_KEY[env_key]
            if getattr(self, field_name) in (None, ""):
                missing.append(env_key)
        return tuple(missing)

    def has_required_secrets(self) -> bool:
        return not self.missing_required_secrets()

    def has_required_config(self) -> bool:
        return not self.missing_required_config()

    def has_required_settings(self) -> bool:
        return self.has_required_secrets() and self.has_required_config()

    def __repr__(self) -> str:
        return (
            "BatchSettings("
            f"app_env={self.app_env!r}, "
            f"log_level={self.log_level!r}, "
            f"object_storage_bucket={self.object_storage_bucket!r}, "
            f"object_storage_endpoint={self.object_storage_endpoint!r}, "
            f"batch_chunk_size={self.batch_chunk_size!r}, "
            f"batch_max_retry={self.batch_max_retry!r}, "
            f"batch_raw_staging_max_raw={self.batch_raw_staging_max_raw!r}, "
            f"batch_raw_staging_source_api={self.batch_raw_staging_source_api!r}, "
            f"supabase_url={self.supabase_url!r}, "
            "database_url='***', "
            "openai_api_key='***', "
            "rakuten_application_id='***', "
            "rakuten_access_key='***', "
            "object_storage_access_key='***', "
            "object_storage_secret_key='***', "
            "batch_internal_token='***', "
            "supabase_service_role_key='***'"
            ")"
        )
