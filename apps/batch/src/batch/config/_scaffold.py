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
        batch_raw_staging_max_raw=1000,
        batch_raw_staging_source_api="item_search",
        batch_product_diff_max_items=1000,
        batch_product_diff_source="rakuten",
        batch_product_diff_sync_staging=True,
        batch_item_apply_max_items=1000,
        batch_item_apply_source="rakuten",
        batch_item_apply_diff_batch_run_id=None,
        batch_item_active_status_max_items=1000,
        batch_item_active_status_source="rakuten",
        batch_item_active_status_batch_run_id=None,
        batch_item_generation_queue_max_items=1000,
        batch_item_generation_queue_source="rakuten",
        batch_item_generation_queue_diff_batch_run_id=None,
        batch_item_semantic_max_items=1000,
        batch_item_semantic_source="rakuten",
        batch_item_semantic_queue_batch_size=100,
        batch_feature_input_hash_max_items=1000,
        batch_feature_input_hash_source="rakuten",
        batch_feature_input_hash_queue_batch_size=100,
        batch_item_feature_max_items=1000,
        batch_item_feature_source="rakuten",
        batch_item_feature_queue_batch_size=100,
        supabase_url=None,
        supabase_service_role_key=None,
    )
