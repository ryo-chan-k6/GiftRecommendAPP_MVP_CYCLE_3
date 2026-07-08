-- D01: extensions and enum types
-- change_id: d01_extensions_and_enums
-- Issue: #611
-- 正本: docs/06_実装設計/database/enum定義書.md §4.1 / §5 / §6
-- 適用順: D01（全テーブル DDL より先）

CREATE EXTENSION IF NOT EXISTS vector;

-- 6.1 recommendation_run_status
CREATE TYPE recommendation_run_status AS ENUM (
  'accepted',
  'running',
  'succeeded',
  'failed',
  'canceled'
);

-- 6.2 recommendation_result_status
CREATE TYPE recommendation_result_status AS ENUM (
  'generated',
  'empty',
  'failed'
);

-- 6.3 recommendation_feedback_status
CREATE TYPE recommendation_feedback_status AS ENUM (
  'submitted',
  'invalid',
  'ignored'
);

-- 6.4 phase_status
CREATE TYPE phase_status AS ENUM (
  'started',
  'succeeded',
  'failed',
  'skipped'
);

-- 6.5 batch_run_status
CREATE TYPE batch_run_status AS ENUM (
  'queued',
  'running',
  'succeeded',
  'partially_succeeded',
  'failed',
  'canceled'
);

-- 6.6 api_call_status
CREATE TYPE api_call_status AS ENUM (
  'requested',
  'succeeded',
  'failed',
  'rate_limited',
  'skipped'
);

-- 6.7 raw_import_status
CREATE TYPE raw_import_status AS ENUM (
  'raw_saved',
  'staged',
  'imported',
  'skipped',
  'failed'
);

-- 6.8 fetch_cursor_status
CREATE TYPE fetch_cursor_status AS ENUM (
  'active',
  'paused',
  'exhausted',
  'failed'
);

-- 6.9 product_diff_status
CREATE TYPE product_diff_status AS ENUM (
  'new',
  'updated',
  'unchanged',
  'unavailable'
);

-- 6.10 item_active_status
CREATE TYPE item_active_status AS ENUM (
  'active',
  'inactive',
  'unavailable',
  'excluded'
);

-- 6.11 item_generation_queue_status
CREATE TYPE item_generation_queue_status AS ENUM (
  'queued',
  'processing',
  'succeeded',
  'failed',
  'skipped'
);

-- 6.12 evaluation_run_status
CREATE TYPE evaluation_run_status AS ENUM (
  'queued',
  'running',
  'succeeded',
  'failed',
  'canceled'
);

-- 6.13 request_mode
CREATE TYPE request_mode AS ENUM (
  'ui',
  'evaluation',
  'batch'
);

-- 6.14 feedback_target_type
CREATE TYPE feedback_target_type AS ENUM (
  'result',
  'item',
  'reason'
);

-- 6.15 owner_type
CREATE TYPE owner_type AS ENUM (
  'recommendation_request',
  'recommendation_run',
  'recommendation_result',
  'recommendation_feedback',
  'batch_run',
  'api_call',
  'raw_product_metadata',
  'item_generation_queue',
  'evaluation_run',
  'system'
);

-- 6.16 feature_code
CREATE TYPE feature_code AS ENUM (
  'formality',
  'safety',
  'brand_appropriateness',
  'emotion',
  'novelty',
  'intimacy',
  'symbolic_identity',
  'story_richness'
);

-- 6.17 item_generation_type
CREATE TYPE item_generation_type AS ENUM (
  'semantic',
  'feature',
  'embedding'
);

-- 6.18 recommendation_run_phase_name
CREATE TYPE recommendation_run_phase_name AS ENUM (
  'request_received',
  'config_resolved',
  'semantic_extracted',
  'user_feature_generated',
  'user_meaning_projected',
  'query_embedding_generated',
  'pre_hard_filter_completed',
  'retrieval_completed',
  'post_hard_filter_completed',
  'matching_completed',
  'ranking_completed',
  'result_generated',
  'reason_generated',
  'response_built'
);

-- 6.19 batch_run_phase_name
CREATE TYPE batch_run_phase_name AS ENUM (
  'batch_started',
  'cursor_loaded',
  'external_api_called',
  'raw_saved',
  'raw_metadata_saved',
  'staging_transformed',
  'diff_judged',
  'item_imported',
  'item_image_imported',
  'popularity_signal_imported',
  'item_feature_generated',
  'item_embedding_generated',
  'feature_distribution_metric_recorded',
  'summary_created',
  'batch_completed'
);

-- 6.20 input_type
CREATE TYPE input_type AS ENUM (
  'relationship',
  'occasion',
  'preferred_condition',
  'non_preferred_condition',
  'ng_condition',
  'budget_condition',
  'free_text'
);

-- 6.21 application_method
CREATE TYPE application_method AS ENUM (
  'relationship_rule',
  'occasion_rule',
  'concept_feature_delta_add',
  'concept_feature_delta_invert',
  'hard_filter_excluded',
  'semantic_extraction_then_apply'
);

-- 6.22 polarity
CREATE TYPE polarity AS ENUM (
  'positive',
  'negative',
  'mixed'
);

-- 6.23 fetch_cursor_type
CREATE TYPE fetch_cursor_type AS ENUM (
  'genre',
  'keyword',
  'update_sort',
  'ranking_supplement',
  'recheck'
);

-- 6.24 source_api
CREATE TYPE source_api AS ENUM (
  'item_search',
  'item_ranking',
  'genre_search',
  'attribute_search'
);

-- 6.25 batch_type
CREATE TYPE batch_type AS ENUM (
  'external_fetch',
  'staging',
  'import',
  'feature_generation',
  'summary',
  'maintenance'
);

-- 6.26 feedback_type
CREATE TYPE feedback_type AS ENUM (
  'item_good',
  'item_bad',
  'item_not_match',
  'item_ng_violation',
  'item_avoid_match',
  'reason_good',
  'reason_bad',
  'result_good',
  'result_bad',
  'comment'
);
