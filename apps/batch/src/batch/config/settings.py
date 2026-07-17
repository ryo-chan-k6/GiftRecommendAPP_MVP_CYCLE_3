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
    "BATCH_PRODUCT_DIFF_MAX_ITEMS",
    "BATCH_PRODUCT_DIFF_SOURCE",
    "BATCH_PRODUCT_DIFF_SYNC_STAGING",
    "BATCH_ITEM_APPLY_MAX_ITEMS",
    "BATCH_ITEM_APPLY_SOURCE",
    "BATCH_ITEM_APPLY_DIFF_BATCH_RUN_ID",
    "BATCH_ITEM_ACTIVE_STATUS_MAX_ITEMS",
    "BATCH_ITEM_ACTIVE_STATUS_SOURCE",
    "BATCH_ITEM_ACTIVE_STATUS_BATCH_RUN_ID",
    "BATCH_ITEM_GENERATION_QUEUE_MAX_ITEMS",
    "BATCH_ITEM_GENERATION_QUEUE_SOURCE",
    "BATCH_ITEM_GENERATION_QUEUE_DIFF_BATCH_RUN_ID",
    "BATCH_ITEM_SEMANTIC_MAX_ITEMS",
    "BATCH_ITEM_SEMANTIC_SOURCE",
    "BATCH_ITEM_SEMANTIC_QUEUE_BATCH_SIZE",
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
    batch_product_diff_max_items: int | None
    batch_product_diff_source: str | None
    batch_product_diff_sync_staging: bool | None
    batch_item_apply_max_items: int | None
    batch_item_apply_source: str | None
    batch_item_apply_diff_batch_run_id: str | None
    batch_item_active_status_max_items: int | None
    batch_item_active_status_source: str | None
    batch_item_active_status_batch_run_id: str | None
    batch_item_generation_queue_max_items: int | None
    batch_item_generation_queue_source: str | None
    batch_item_generation_queue_diff_batch_run_id: str | None
    batch_item_semantic_max_items: int | None
    batch_item_semantic_source: str | None
    batch_item_semantic_queue_batch_size: int | None
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
            f"batch_product_diff_max_items={self.batch_product_diff_max_items!r}, "
            f"batch_product_diff_source={self.batch_product_diff_source!r}, "
            f"batch_product_diff_sync_staging={self.batch_product_diff_sync_staging!r}, "
            f"batch_item_apply_max_items={self.batch_item_apply_max_items!r}, "
            f"batch_item_apply_source={self.batch_item_apply_source!r}, "
            f"batch_item_apply_diff_batch_run_id={self.batch_item_apply_diff_batch_run_id!r}, "
            f"batch_item_active_status_max_items={self.batch_item_active_status_max_items!r}, "
            f"batch_item_active_status_source={self.batch_item_active_status_source!r}, "
            f"batch_item_active_status_batch_run_id={self.batch_item_active_status_batch_run_id!r}, "
            f"batch_item_generation_queue_max_items={self.batch_item_generation_queue_max_items!r}, "
            f"batch_item_generation_queue_source={self.batch_item_generation_queue_source!r}, "
            f"batch_item_generation_queue_diff_batch_run_id={self.batch_item_generation_queue_diff_batch_run_id!r}, "
            f"batch_item_semantic_max_items={self.batch_item_semantic_max_items!r}, "
            f"batch_item_semantic_source={self.batch_item_semantic_source!r}, "
            f"batch_item_semantic_queue_batch_size={self.batch_item_semantic_queue_batch_size!r}, "
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
