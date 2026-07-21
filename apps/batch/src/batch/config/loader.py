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


def _read_optional_bool(source: Mapping[str, str], key: str) -> bool | None:
    raw = _read_optional_str(source, key)
    if raw is None:
        return None
    lowered = raw.lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{key} must be a boolean, got {raw!r}")


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
        rakuten_access_key=_read_optional_str(source, "RAKUTEN_ACCESS_KEY"),
        object_storage_bucket=_read_optional_str(source, "OBJECT_STORAGE_BUCKET"),
        object_storage_endpoint=_read_optional_str(source, "OBJECT_STORAGE_ENDPOINT"),
        object_storage_access_key=_read_optional_str(source, "OBJECT_STORAGE_ACCESS_KEY"),
        object_storage_secret_key=_read_optional_str(source, "OBJECT_STORAGE_SECRET_KEY"),
        batch_internal_token=_read_optional_str(source, "BATCH_INTERNAL_TOKEN"),
        batch_chunk_size=_read_positive_int(source, "BATCH_CHUNK_SIZE"),
        batch_max_retry=_read_positive_int(source, "BATCH_MAX_RETRY"),
        batch_raw_staging_max_raw=_read_positive_int(source, "BATCH_RAW_STAGING_MAX_RAW"),
        batch_raw_staging_source_api=_read_optional_str(source, "BATCH_RAW_STAGING_SOURCE_API"),
        batch_product_diff_max_items=_read_positive_int(source, "BATCH_PRODUCT_DIFF_MAX_ITEMS"),
        batch_product_diff_source=_read_optional_str(source, "BATCH_PRODUCT_DIFF_SOURCE"),
        batch_product_diff_sync_staging=_read_optional_bool(
            source, "BATCH_PRODUCT_DIFF_SYNC_STAGING"
        ),
        batch_item_apply_max_items=_read_positive_int(source, "BATCH_ITEM_APPLY_MAX_ITEMS"),
        batch_item_apply_source=_read_optional_str(source, "BATCH_ITEM_APPLY_SOURCE"),
        batch_item_apply_diff_batch_run_id=_read_optional_str(
            source, "BATCH_ITEM_APPLY_DIFF_BATCH_RUN_ID"
        ),
        batch_item_active_status_max_items=_read_positive_int(
            source, "BATCH_ITEM_ACTIVE_STATUS_MAX_ITEMS"
        ),
        batch_item_active_status_source=_read_optional_str(
            source, "BATCH_ITEM_ACTIVE_STATUS_SOURCE"
        ),
        batch_item_active_status_batch_run_id=_read_optional_str(
            source, "BATCH_ITEM_ACTIVE_STATUS_BATCH_RUN_ID"
        ),
        batch_item_generation_queue_max_items=_read_positive_int(
            source, "BATCH_ITEM_GENERATION_QUEUE_MAX_ITEMS"
        ),
        batch_item_generation_queue_source=_read_optional_str(
            source, "BATCH_ITEM_GENERATION_QUEUE_SOURCE"
        ),
        batch_item_generation_queue_diff_batch_run_id=_read_optional_str(
            source, "BATCH_ITEM_GENERATION_QUEUE_DIFF_BATCH_RUN_ID"
        ),
        batch_item_semantic_max_items=_read_positive_int(
            source, "BATCH_ITEM_SEMANTIC_MAX_ITEMS"
        ),
        batch_item_semantic_source=_read_optional_str(source, "BATCH_ITEM_SEMANTIC_SOURCE"),
        batch_item_semantic_queue_batch_size=_read_positive_int(
            source, "BATCH_ITEM_SEMANTIC_QUEUE_BATCH_SIZE"
        ),
        batch_feature_input_hash_max_items=_read_positive_int(
            source, "BATCH_FEATURE_INPUT_HASH_MAX_ITEMS"
        ),
        batch_feature_input_hash_source=_read_optional_str(
            source, "BATCH_FEATURE_INPUT_HASH_SOURCE"
        ),
        batch_feature_input_hash_queue_batch_size=_read_positive_int(
            source, "BATCH_FEATURE_INPUT_HASH_QUEUE_BATCH_SIZE"
        ),
        batch_item_feature_max_items=_read_positive_int(
            source, "BATCH_ITEM_FEATURE_MAX_ITEMS"
        ),
        batch_item_feature_source=_read_optional_str(source, "BATCH_ITEM_FEATURE_SOURCE"),
        batch_item_feature_queue_batch_size=_read_positive_int(
            source, "BATCH_ITEM_FEATURE_QUEUE_BATCH_SIZE"
        ),
        batch_feature_normalization_max_items=_read_positive_int(
            source, "BATCH_FEATURE_NORMALIZATION_MAX_ITEMS"
        ),
        batch_feature_normalization_source=_read_optional_str(
            source, "BATCH_FEATURE_NORMALIZATION_SOURCE"
        ),
        batch_feature_normalization_queue_batch_size=_read_positive_int(
            source, "BATCH_FEATURE_NORMALIZATION_QUEUE_BATCH_SIZE"
        ),
        batch_embedding_input_hash_max_items=_read_positive_int(
            source, "BATCH_EMBEDDING_INPUT_HASH_MAX_ITEMS"
        ),
        batch_embedding_input_hash_source=_read_optional_str(
            source, "BATCH_EMBEDDING_INPUT_HASH_SOURCE"
        ),
        batch_embedding_input_hash_queue_batch_size=_read_positive_int(
            source, "BATCH_EMBEDDING_INPUT_HASH_QUEUE_BATCH_SIZE"
        ),
        batch_item_embedding_max_items=_read_positive_int(
            source, "BATCH_ITEM_EMBEDDING_MAX_ITEMS"
        ),
        batch_item_embedding_source=_read_optional_str(source, "BATCH_ITEM_EMBEDDING_SOURCE"),
        batch_item_embedding_queue_batch_size=_read_positive_int(
            source, "BATCH_ITEM_EMBEDDING_QUEUE_BATCH_SIZE"
        ),
        batch_distribution_metrics_aggregation_scope=_read_optional_str(
            source, "BATCH_DISTRIBUTION_METRICS_AGGREGATION_SCOPE"
        ),
        batch_distribution_metrics_semantic_config_version_id=_read_optional_str(
            source, "BATCH_DISTRIBUTION_METRICS_SEMANTIC_CONFIG_VERSION_ID"
        ),
        batch_distribution_metrics_include_item_embedding=_read_optional_bool(
            source, "BATCH_DISTRIBUTION_METRICS_INCLUDE_ITEM_EMBEDDING"
        ),
        batch_distribution_metrics_include_user_meaning=_read_optional_bool(
            source, "BATCH_DISTRIBUTION_METRICS_INCLUDE_USER_MEANING"
        ),
        batch_import_summary_source_api=_read_optional_str(
            source, "BATCH_IMPORT_SUMMARY_SOURCE_API"
        ),
        batch_import_summary_batch_run_id=_read_optional_str(
            source, "BATCH_IMPORT_SUMMARY_BATCH_RUN_ID"
        ),
        batch_offline_evaluation_dataset_id=_read_optional_str(
            source, "BATCH_OFFLINE_EVALUATION_DATASET_ID"
        ),
        batch_offline_evaluation_dataset_name=_read_optional_str(
            source, "BATCH_OFFLINE_EVALUATION_DATASET_NAME"
        ),
        batch_offline_evaluation_dataset_version=_read_optional_str(
            source, "BATCH_OFFLINE_EVALUATION_DATASET_VERSION"
        ),
        batch_offline_evaluation_max_cases=_read_positive_int(
            source, "BATCH_OFFLINE_EVALUATION_MAX_CASES"
        ),
        batch_offline_evaluation_dry_run=_read_optional_bool(
            source, "BATCH_OFFLINE_EVALUATION_DRY_RUN"
        ),
        batch_feedback_analysis_period_start=_read_optional_str(
            source, "BATCH_FEEDBACK_ANALYSIS_PERIOD_START"
        ),
        batch_feedback_analysis_period_end=_read_optional_str(
            source, "BATCH_FEEDBACK_ANALYSIS_PERIOD_END"
        ),
        batch_feedback_analysis_aggregation_scope=_read_optional_str(
            source, "BATCH_FEEDBACK_ANALYSIS_AGGREGATION_SCOPE"
        ),
        batch_feedback_analysis_feedback_types=_read_optional_str(
            source, "BATCH_FEEDBACK_ANALYSIS_FEEDBACK_TYPES"
        ),
        batch_feedback_analysis_semantic_config_version_id=_read_optional_str(
            source, "BATCH_FEEDBACK_ANALYSIS_SEMANTIC_CONFIG_VERSION_ID"
        ),
        batch_feedback_analysis_max_feedback_rows=_read_positive_int(
            source, "BATCH_FEEDBACK_ANALYSIS_MAX_FEEDBACK_ROWS"
        ),
        batch_feedback_analysis_dry_run=_read_optional_bool(
            source, "BATCH_FEEDBACK_ANALYSIS_DRY_RUN"
        ),
        batch_feedback_analysis_negative_rating_threshold=_read_positive_int(
            source, "BATCH_FEEDBACK_ANALYSIS_NEGATIVE_RATING_THRESHOLD"
        ),
        supabase_url=_read_optional_str(source, "SUPABASE_URL"),
        supabase_service_role_key=_read_optional_str(source, "SUPABASE_SERVICE_ROLE_KEY"),
    )
