"""Shared scaffold helpers for config modules."""

from __future__ import annotations

from batch.config.env import AppEnv
from batch.config.settings import BatchSettings


def scaffold_batch_settings(*, app_env: AppEnv = AppEnv.DEV) -> BatchSettings:
    """Build in-memory settings for Phase4a unit tests without real secrets."""

    return BatchSettings(
        app_env=app_env,
        log_level="info",
        database_url="scaffold://database",
        openai_api_key="scaffold-openai-api-key",
        rakuten_application_id="scaffold-rakuten-application-id",
        rakuten_access_key="scaffold-rakuten-access-key",
        object_storage_bucket="scaffold-raw-bucket",
        object_storage_endpoint="https://scaffold-storage.example",
        object_storage_access_key="scaffold-object-storage-access-key",
        object_storage_secret_key="scaffold-object-storage-secret-key",
        batch_internal_token="scaffold-batch-internal-token",
        batch_chunk_size=100,
        batch_max_retry=3,
        supabase_url=None,
        supabase_service_role_key=None,
    )
