-- Initial schema migration (MVP)
-- Issue: #628 | Epic: #435
-- Source: db/ddl/d01..d12 (D13 is validation-only, excluded)
-- Policy: docs/06_実装設計/database/マイグレーション方針書.md §8.2


-- >>> BEGIN d01_extensions_and_enums.sql
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
-- <<< END d01_extensions_and_enums.sql

-- >>> BEGIN d02_semantic_feature_definitions.sql
-- D02: Semantic / Feature definition tables
-- change_id: d02_semantic_feature_definitions
-- Issue: #599
-- 正本: docs/06_実装設計/database/*_テーブル定義書.md（D02 対象 12 件）
-- 適用順: D01 適用後。semantic_config → semantic_config_version → 子テーブル
-- 延期 FK: pair_rule.pair_id → pair_master（D03）、normalization_rule.feature_normalization_version_id → feature_normalization_version（D03 / D12 後追い）

-- =============================================================================
-- 1. semantic_config
-- =============================================================================
CREATE TABLE semantic_config (
  semantic_config_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  config_name text NOT NULL,
  config_description text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_semantic_config_config_name UNIQUE (config_name),
  CONSTRAINT chk_config_name_format CHECK (config_name ~ '^[a-z][a-z0-9_]*$'),
  CONSTRAINT chk_config_description_length CHECK (
    config_description IS NULL OR char_length(config_description) <= 500
  )
);

CREATE INDEX idx_semantic_config_active_name
  ON semantic_config (is_active, config_name);

CREATE INDEX idx_semantic_config_created_at
  ON semantic_config (created_at DESC);

-- =============================================================================
-- 2. semantic_config_version
-- =============================================================================
CREATE TABLE semantic_config_version (
  semantic_config_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  semantic_config_id uuid NOT NULL,
  version_label varchar(50) NOT NULL,
  is_current boolean NOT NULL DEFAULT false,
  valid_from timestamptz,
  valid_to timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_semantic_config_version_config_label
    UNIQUE (semantic_config_id, version_label),
  CONSTRAINT fk_semantic_config_version_semantic_config
    FOREIGN KEY (semantic_config_id)
    REFERENCES semantic_config (semantic_config_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_version_label_length
    CHECK (char_length(version_label) BETWEEN 1 AND 50),
  CONSTRAINT chk_version_label_format
    CHECK (version_label ~ '^v[0-9]+\.[0-9]+\.[0-9]+$'),
  CONSTRAINT chk_valid_period CHECK (
    valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from
  )
);

CREATE UNIQUE INDEX uq_semantic_config_version_current_per_config
  ON semantic_config_version (semantic_config_id)
  WHERE is_current = true;

CREATE INDEX idx_semantic_config_version_config_created
  ON semantic_config_version (semantic_config_id, created_at DESC);

CREATE INDEX idx_semantic_config_version_valid_period
  ON semantic_config_version (valid_from, valid_to);

-- =============================================================================
-- 3. feature_definition
-- =============================================================================
CREATE TABLE feature_definition (
  feature_definition_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  semantic_config_version_id uuid NOT NULL,
  feature_code text NOT NULL,
  feature_label varchar(100) NOT NULL,
  feature_group text NOT NULL,
  display_order integer NOT NULL DEFAULT 1,
  is_active boolean NOT NULL DEFAULT true,
  CONSTRAINT uq_feature_definition_version_code
    UNIQUE (semantic_config_version_id, feature_code),
  CONSTRAINT fk_feature_definition_semantic_config_version
    FOREIGN KEY (semantic_config_version_id)
    REFERENCES semantic_config_version (semantic_config_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_feature_definition_feature_code_mvp CHECK (
    feature_code IN (
      'formality', 'safety', 'brand_appropriateness',
      'emotion', 'novelty', 'intimacy', 'symbolic_identity', 'story_richness'
    )
  ),
  CONSTRAINT chk_feature_group_mvp CHECK (feature_group IN ('social', 'symbolic')),
  CONSTRAINT chk_feature_group_code_consistency CHECK (
    (feature_group = 'social' AND feature_code IN ('formality', 'safety', 'brand_appropriateness'))
    OR (feature_group = 'symbolic' AND feature_code IN (
      'emotion', 'novelty', 'intimacy', 'symbolic_identity', 'story_richness'
    ))
  ),
  CONSTRAINT chk_display_order_positive CHECK (display_order >= 1),
  CONSTRAINT chk_feature_label_length CHECK (char_length(feature_label) BETWEEN 1 AND 100)
);

CREATE INDEX idx_feature_definition_version_active_order
  ON feature_definition (semantic_config_version_id, is_active, display_order, feature_code);

-- =============================================================================
-- 4. semantic_concept
-- =============================================================================
CREATE TABLE semantic_concept (
  semantic_concept_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  semantic_config_version_id uuid NOT NULL,
  concept_code text NOT NULL,
  concept_label varchar(100) NOT NULL,
  concept_description varchar(500),
  is_active boolean NOT NULL DEFAULT true,
  CONSTRAINT uq_semantic_concept_version_code
    UNIQUE (semantic_config_version_id, concept_code),
  CONSTRAINT fk_semantic_concept_semantic_config_version
    FOREIGN KEY (semantic_config_version_id)
    REFERENCES semantic_config_version (semantic_config_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_concept_code_format CHECK (concept_code ~ '^[a-z][a-z0-9_]*$'),
  CONSTRAINT chk_concept_code_length CHECK (char_length(concept_code) BETWEEN 1 AND 64),
  CONSTRAINT chk_concept_label_length CHECK (char_length(concept_label) BETWEEN 1 AND 100),
  CONSTRAINT chk_concept_description_length CHECK (
    concept_description IS NULL OR char_length(concept_description) <= 500
  )
);

CREATE INDEX idx_semantic_concept_version_active_code
  ON semantic_concept (semantic_config_version_id, is_active, concept_code);

-- =============================================================================
-- 5. semantic_rule
-- =============================================================================
CREATE TABLE semantic_rule (
  semantic_rule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  semantic_config_version_id uuid NOT NULL,
  rule_type text NOT NULL,
  source_text_pattern text NOT NULL,
  semantic_concept_id uuid NOT NULL,
  weight numeric(5, 4) NOT NULL DEFAULT 1.0000,
  is_active boolean NOT NULL DEFAULT true,
  CONSTRAINT uq_semantic_rule_version_type_pattern_concept
    UNIQUE (semantic_config_version_id, rule_type, source_text_pattern, semantic_concept_id),
  CONSTRAINT fk_semantic_rule_semantic_config_version
    FOREIGN KEY (semantic_config_version_id)
    REFERENCES semantic_config_version (semantic_config_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_semantic_rule_semantic_concept
    FOREIGN KEY (semantic_concept_id)
    REFERENCES semantic_concept (semantic_concept_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_rule_type_mvp CHECK (rule_type IN ('keyword', 'phrase', 'pattern', 'llm')),
  CONSTRAINT chk_source_text_pattern_length CHECK (char_length(source_text_pattern) BETWEEN 1 AND 2000),
  CONSTRAINT chk_semantic_rule_weight_range CHECK (weight >= 0.0000 AND weight <= 1.0000)
);

CREATE INDEX idx_semantic_rule_version_active
  ON semantic_rule (semantic_config_version_id, is_active);

CREATE INDEX idx_semantic_rule_concept_id
  ON semantic_rule (semantic_concept_id);

-- =============================================================================
-- 6. relationship_rule
-- =============================================================================
CREATE TABLE relationship_rule (
  relationship_rule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  semantic_config_version_id uuid NOT NULL,
  relationship_code text NOT NULL,
  feature_code text NOT NULL,
  feature_base_value numeric(4, 3) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  CONSTRAINT uq_relationship_rule_version_relationship_feature
    UNIQUE (semantic_config_version_id, relationship_code, feature_code),
  CONSTRAINT fk_relationship_rule_semantic_config_version
    FOREIGN KEY (semantic_config_version_id)
    REFERENCES semantic_config_version (semantic_config_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_relationship_code_format CHECK (relationship_code ~ '^[a-z][a-z0-9_]*$'),
  CONSTRAINT chk_relationship_rule_relationship_code_mvp CHECK (
    relationship_code IN (
      'lover', 'spouse', 'family_parent', 'family_child', 'family_sibling',
      'friend_close', 'friend_casual', 'colleague', 'boss', 'subordinate',
      'business_partner', 'other'
    )
  ),
  CONSTRAINT chk_relationship_rule_feature_code_mvp CHECK (
    feature_code IN (
      'formality', 'safety', 'brand_appropriateness',
      'emotion', 'novelty', 'intimacy', 'symbolic_identity', 'story_richness'
    )
  ),
  CONSTRAINT chk_relationship_rule_feature_base_value_range CHECK (
    feature_base_value >= 0.0 AND feature_base_value <= 1.0
  )
);

CREATE INDEX idx_relationship_rule_version_active_lookup
  ON relationship_rule (semantic_config_version_id, is_active, relationship_code, feature_code);

-- =============================================================================
-- 7. occasion_rule
-- =============================================================================
CREATE TABLE occasion_rule (
  occasion_rule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  semantic_config_version_id uuid NOT NULL,
  occasion_code text NOT NULL,
  feature_code text NOT NULL,
  feature_base_value numeric(4, 3) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  CONSTRAINT uq_occasion_rule_version_occasion_feature
    UNIQUE (semantic_config_version_id, occasion_code, feature_code),
  CONSTRAINT fk_occasion_rule_semantic_config_version
    FOREIGN KEY (semantic_config_version_id)
    REFERENCES semantic_config_version (semantic_config_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_occasion_code_format CHECK (occasion_code ~ '^[a-z][a-z0-9_]*$'),
  CONSTRAINT chk_occasion_rule_occasion_code_mvp CHECK (
    occasion_code IN (
      'birthday', 'anniversary', 'thanks', 'apology', 'celebration_general',
      'wedding_gift', 'baby_gift', 'housewarming', 'farewell', 'get_well',
      'seasonal_event', 'souvenir', 'return_gift', 'no_specific_occasion', 'other'
    )
  ),
  CONSTRAINT chk_occasion_rule_feature_code_mvp CHECK (
    feature_code IN (
      'formality', 'safety', 'brand_appropriateness',
      'emotion', 'novelty', 'intimacy', 'symbolic_identity', 'story_richness'
    )
  ),
  CONSTRAINT chk_occasion_rule_feature_base_value_range CHECK (
    feature_base_value >= 0.0 AND feature_base_value <= 1.0
  )
);

CREATE INDEX idx_occasion_rule_version_active_lookup
  ON occasion_rule (semantic_config_version_id, is_active, occasion_code, feature_code);

-- =============================================================================
-- 8. pair_rule
-- pair_id → pair_master 物理 FK は D03 後追い（D12）
-- =============================================================================
CREATE TABLE pair_rule (
  pair_rule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  semantic_config_version_id uuid NOT NULL,
  pair_id uuid NOT NULL,
  feature_code text NOT NULL,
  feature_delta numeric(4, 3) NOT NULL DEFAULT 0.000,
  is_active boolean NOT NULL DEFAULT true,
  CONSTRAINT uq_pair_rule_version_pair_feature
    UNIQUE (semantic_config_version_id, pair_id, feature_code),
  CONSTRAINT fk_pair_rule_semantic_config_version
    FOREIGN KEY (semantic_config_version_id)
    REFERENCES semantic_config_version (semantic_config_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_pair_rule_feature_code_mvp CHECK (
    feature_code IN (
      'formality', 'safety', 'brand_appropriateness',
      'emotion', 'novelty', 'intimacy', 'symbolic_identity', 'story_richness'
    )
  ),
  CONSTRAINT chk_pair_rule_feature_delta_range CHECK (
    feature_delta >= -1.0 AND feature_delta <= 1.0
  )
);

CREATE INDEX idx_pair_rule_version_pair_active_lookup
  ON pair_rule (semantic_config_version_id, pair_id, is_active, feature_code);

CREATE INDEX idx_pair_rule_pair_id
  ON pair_rule (pair_id);

-- =============================================================================
-- 9. concept_feature_rule
-- =============================================================================
CREATE TABLE concept_feature_rule (
  concept_feature_rule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  semantic_config_version_id uuid NOT NULL,
  semantic_concept_id uuid NOT NULL,
  feature_code text NOT NULL,
  feature_delta numeric(4, 3) NOT NULL DEFAULT 0.000,
  polarity text NOT NULL DEFAULT 'positive',
  is_active boolean NOT NULL DEFAULT true,
  CONSTRAINT uq_concept_feature_rule_version_concept_feature
    UNIQUE (semantic_config_version_id, semantic_concept_id, feature_code),
  CONSTRAINT fk_concept_feature_rule_semantic_config_version
    FOREIGN KEY (semantic_config_version_id)
    REFERENCES semantic_config_version (semantic_config_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_concept_feature_rule_semantic_concept
    FOREIGN KEY (semantic_concept_id)
    REFERENCES semantic_concept (semantic_concept_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_concept_feature_rule_feature_code_mvp CHECK (
    feature_code IN (
      'formality', 'safety', 'brand_appropriateness',
      'emotion', 'novelty', 'intimacy', 'symbolic_identity', 'story_richness'
    )
  ),
  CONSTRAINT chk_concept_feature_rule_feature_delta_range CHECK (
    feature_delta >= 0.0 AND feature_delta <= 1.0
  ),
  CONSTRAINT chk_polarity_mvp CHECK (polarity IN ('positive', 'negative', 'mixed'))
);

CREATE INDEX idx_concept_feature_rule_version_active_lookup
  ON concept_feature_rule (semantic_config_version_id, is_active, semantic_concept_id, feature_code);

CREATE INDEX idx_concept_feature_rule_semantic_concept_id
  ON concept_feature_rule (semantic_concept_id);

-- =============================================================================
-- 10. input_type_rule
-- =============================================================================
CREATE TABLE input_type_rule (
  input_type_rule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  semantic_config_version_id uuid NOT NULL,
  input_type text NOT NULL,
  application_method text NOT NULL,
  invert_delta boolean NOT NULL DEFAULT false,
  participates_in_feature_integration boolean NOT NULL DEFAULT true,
  display_order integer NOT NULL DEFAULT 1,
  is_active boolean NOT NULL DEFAULT true,
  CONSTRAINT uq_input_type_rule_version_input_type
    UNIQUE (semantic_config_version_id, input_type),
  CONSTRAINT fk_input_type_rule_semantic_config_version
    FOREIGN KEY (semantic_config_version_id)
    REFERENCES semantic_config_version (semantic_config_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_input_type_mvp CHECK (
    input_type IN (
      'relationship', 'occasion', 'preferred_condition', 'non_preferred_condition',
      'ng_condition', 'budget_condition', 'free_text'
    )
  ),
  CONSTRAINT chk_application_method_mvp CHECK (
    application_method IN (
      'relationship_rule', 'occasion_rule', 'concept_feature_delta_add',
      'concept_feature_delta_invert', 'hard_filter_excluded', 'semantic_extraction_then_apply'
    )
  ),
  CONSTRAINT chk_invert_delta_application_method CHECK (
    invert_delta = (application_method = 'concept_feature_delta_invert')
  ),
  CONSTRAINT chk_input_type_dispatch_consistency CHECK (
    (input_type = 'relationship'
      AND application_method = 'relationship_rule'
      AND invert_delta = false
      AND participates_in_feature_integration = true)
    OR (input_type = 'occasion'
      AND application_method = 'occasion_rule'
      AND invert_delta = false
      AND participates_in_feature_integration = true)
    OR (input_type = 'preferred_condition'
      AND application_method = 'concept_feature_delta_add'
      AND invert_delta = false
      AND participates_in_feature_integration = true)
    OR (input_type = 'non_preferred_condition'
      AND application_method = 'concept_feature_delta_invert'
      AND invert_delta = true
      AND participates_in_feature_integration = true)
    OR (input_type = 'free_text'
      AND application_method = 'semantic_extraction_then_apply'
      AND invert_delta = false
      AND participates_in_feature_integration = true)
    OR (input_type = 'ng_condition'
      AND application_method = 'hard_filter_excluded'
      AND invert_delta = false
      AND participates_in_feature_integration = false)
    OR (input_type = 'budget_condition'
      AND application_method = 'hard_filter_excluded'
      AND invert_delta = false
      AND participates_in_feature_integration = false)
  )
);

CREATE INDEX idx_input_type_rule_version_active_lookup
  ON input_type_rule (semantic_config_version_id, is_active, display_order);

-- =============================================================================
-- 11. feature_integration_rule
-- =============================================================================
CREATE TABLE feature_integration_rule (
  feature_integration_rule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  semantic_config_version_id uuid NOT NULL,
  feature_code text NOT NULL,
  input_source text NOT NULL,
  weight numeric(4, 3) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  CONSTRAINT uq_feature_integration_rule_version_feature_source
    UNIQUE (semantic_config_version_id, feature_code, input_source),
  CONSTRAINT fk_feature_integration_rule_semantic_config_version
    FOREIGN KEY (semantic_config_version_id)
    REFERENCES semantic_config_version (semantic_config_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_feature_integration_rule_feature_code_mvp CHECK (
    feature_code IN (
      'formality', 'safety', 'brand_appropriateness',
      'emotion', 'novelty', 'intimacy', 'symbolic_identity', 'story_richness'
    )
  ),
  CONSTRAINT chk_input_source_mvp CHECK (
    input_source IN (
      'relationship_feature', 'occasion_feature', 'pair_delta',
      'preferred_delta', 'avoid_delta', 'free_text_delta'
    )
  ),
  CONSTRAINT chk_feature_integration_rule_weight_range CHECK (
    weight >= 0.0 AND weight <= 2.0
  )
);

CREATE INDEX idx_feature_integration_rule_version_feature_active_lookup
  ON feature_integration_rule (semantic_config_version_id, feature_code, is_active, input_source);

-- =============================================================================
-- 12. normalization_rule
-- feature_normalization_version_id → feature_normalization_version 物理 FK は D03 後追い（D12）
-- =============================================================================
CREATE TABLE normalization_rule (
  normalization_rule_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  semantic_config_version_id uuid NOT NULL,
  normalization_method text NOT NULL,
  feature_normalization_version_id uuid NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  CONSTRAINT uq_normalization_rule_version UNIQUE (semantic_config_version_id),
  CONSTRAINT fk_normalization_rule_semantic_config_version
    FOREIGN KEY (semantic_config_version_id)
    REFERENCES semantic_config_version (semantic_config_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_normalization_method_mvp CHECK (normalization_method IN ('sigmoid')),
  CONSTRAINT chk_feature_norm_version_id_not_null CHECK (feature_normalization_version_id IS NOT NULL)
);

CREATE INDEX idx_normalization_rule_version_active_lookup
  ON normalization_rule (semantic_config_version_id, is_active);
-- <<< END d02_semantic_feature_definitions.sql

-- >>> BEGIN d03_master_config.sql
-- D03: Master / Config tables
-- change_id: d03_master_config
-- Issue: #600
-- 正本: docs/06_実装設計/database/*_テーブル定義書.md（D03 対象 7 件）
-- 適用順: D01 / D02 適用後。relationship / occasion / pair → config 群 → reason_template
-- 延期 FK: pair_rule.pair_id → pair_master（本ファイル末尾）
-- 延期 FK（D12）: normalization_rule.feature_normalization_version_id → feature_normalization_version

-- =============================================================================
-- 1. relationship_master
-- =============================================================================
CREATE TABLE relationship_master (
  relationship_code text PRIMARY KEY,
  relationship_label varchar(50) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  display_order integer NOT NULL DEFAULT 0,
  CONSTRAINT chk_relationship_code_format CHECK (
    relationship_code ~ '^[a-z][a-z0-9_]*$'
  ),
  CONSTRAINT chk_relationship_label_length CHECK (
    char_length(relationship_label) BETWEEN 1 AND 50
  ),
  CONSTRAINT chk_display_order_non_negative CHECK (display_order >= 0)
);

CREATE INDEX idx_relationship_master_active_order
  ON relationship_master (is_active, display_order, relationship_code);

-- =============================================================================
-- 2. occasion_master
-- =============================================================================
CREATE TABLE occasion_master (
  occasion_code text PRIMARY KEY,
  occasion_label varchar(50) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  display_order integer NOT NULL DEFAULT 0,
  CONSTRAINT chk_occasion_code_format CHECK (
    occasion_code ~ '^[a-z][a-z0-9_]*$'
  ),
  CONSTRAINT chk_occasion_label_length CHECK (
    char_length(occasion_label) BETWEEN 1 AND 50
  ),
  CONSTRAINT chk_display_order_non_negative CHECK (display_order >= 0)
);

CREATE INDEX idx_occasion_master_active_order
  ON occasion_master (is_active, display_order, occasion_code);

-- =============================================================================
-- 3. pair_master
-- =============================================================================
CREATE TABLE pair_master (
  pair_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  relationship_code text NOT NULL,
  occasion_code text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  CONSTRAINT uq_pair_relationship_occasion
    UNIQUE (relationship_code, occasion_code),
  CONSTRAINT fk_pair_master_relationship
    FOREIGN KEY (relationship_code)
    REFERENCES relationship_master (relationship_code)
    ON DELETE RESTRICT,
  CONSTRAINT fk_pair_master_occasion
    FOREIGN KEY (occasion_code)
    REFERENCES occasion_master (occasion_code)
    ON DELETE RESTRICT,
  CONSTRAINT chk_pair_master_relationship_code_format CHECK (
    relationship_code ~ '^[a-z][a-z0-9_]*$'
  ),
  CONSTRAINT chk_pair_master_occasion_code_format CHECK (
    occasion_code ~ '^[a-z][a-z0-9_]*$'
  )
);

CREATE INDEX idx_pair_master_resolve
  ON pair_master (relationship_code, occasion_code, is_active);

-- =============================================================================
-- 4. model_version
-- =============================================================================
CREATE TABLE model_version (
  model_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  provider varchar(50) NOT NULL,
  model_name varchar(100) NOT NULL,
  model_type text NOT NULL,
  version_label varchar(50) NOT NULL,
  is_current boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_model_version_identity
    UNIQUE (provider, model_name, model_type, version_label),
  CONSTRAINT chk_model_type_mvp CHECK (
    model_type IN ('embedding', 'llm', 'ranking')
  ),
  CONSTRAINT chk_provider_format CHECK (
    provider ~ '^[a-z][a-z0-9_]*$'
  ),
  CONSTRAINT chk_version_label_length CHECK (
    char_length(version_label) BETWEEN 1 AND 50
  ),
  CONSTRAINT chk_model_name_length CHECK (
    char_length(model_name) BETWEEN 1 AND 100
  )
);

CREATE UNIQUE INDEX uq_model_version_current_per_type
  ON model_version (model_type)
  WHERE is_current = true;

CREATE INDEX idx_model_version_type_current
  ON model_version (model_type, is_current);

-- =============================================================================
-- 5. ranking_config
-- =============================================================================
CREATE TABLE ranking_config (
  ranking_config_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  config_name text NOT NULL,
  config_version text NOT NULL,
  parameter_json jsonb NOT NULL,
  is_current boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_ranking_config_name_version
    UNIQUE (config_name, config_version),
  CONSTRAINT chk_ranking_config_name_format CHECK (
    config_name ~ '^[a-z][a-z0-9_]*$'
  ),
  CONSTRAINT chk_ranking_config_version_format CHECK (
    config_version ~ '^v[0-9]{3,}$'
  ),
  CONSTRAINT chk_ranking_config_parameter_json_object CHECK (
    jsonb_typeof(parameter_json) = 'object'
  ),
  CONSTRAINT chk_ranking_weights_sum CHECK (
    abs(
      (parameter_json->'ranking_weights'->>'context')::numeric
      + (parameter_json->'ranking_weights'->>'popularity')::numeric
      + (parameter_json->'ranking_weights'->>'risk')::numeric
      - 1.0
    ) <= 0.001
  )
);

CREATE UNIQUE INDEX uq_ranking_config_current_per_name
  ON ranking_config (config_name)
  WHERE is_current = true;

CREATE INDEX idx_ranking_config_name_created
  ON ranking_config (config_name, created_at DESC);

-- =============================================================================
-- 6. feature_normalization_version
-- =============================================================================
CREATE TABLE feature_normalization_version (
  feature_normalization_version_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  normalization_method text NOT NULL,
  parameter_json jsonb NOT NULL,
  is_current boolean NOT NULL DEFAULT false,
  generated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chk_normalization_method_mvp CHECK (
    normalization_method IN ('sigmoid')
  ),
  CONSTRAINT chk_feature_norm_parameter_json_object CHECK (
    jsonb_typeof(parameter_json) = 'object'
  ),
  CONSTRAINT chk_parameter_json_keys_mvp CHECK (
    parameter_json ? 'center_feature' AND parameter_json ? 'k_feature'
  ),
  CONSTRAINT chk_parameter_json_center_feature CHECK (
    (parameter_json->>'center_feature')::numeric BETWEEN 0.0 AND 1.0
  ),
  CONSTRAINT chk_parameter_json_k_feature CHECK (
    (parameter_json->>'k_feature')::numeric > 0
  )
);

CREATE UNIQUE INDEX uq_feature_norm_version_current_per_method
  ON feature_normalization_version (normalization_method)
  WHERE is_current = true;

CREATE INDEX idx_feature_norm_version_method_generated
  ON feature_normalization_version (normalization_method, generated_at DESC);

-- =============================================================================
-- 7. reason_template
-- =============================================================================
CREATE TABLE reason_template (
  reason_template_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  template_name text NOT NULL,
  template_version integer NOT NULL DEFAULT 1,
  template_type text NOT NULL,
  template_body text NOT NULL,
  relationship_code text,
  occasion_code text,
  feature_code text,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_reason_template_name_version
    UNIQUE (template_name, template_version),
  CONSTRAINT chk_template_name_format CHECK (
    template_name ~ '^[a-z][a-z0-9_]*$'
  ),
  CONSTRAINT chk_template_version CHECK (template_version >= 1),
  CONSTRAINT chk_template_type CHECK (
    template_type IN ('summary', 'detail', 'point', 'caution')
  ),
  CONSTRAINT chk_template_body_length CHECK (
    char_length(template_body) BETWEEN 1 AND 2000
  ),
  CONSTRAINT chk_reason_template_relationship_code_format CHECK (
    relationship_code IS NULL OR relationship_code ~ '^[a-z][a-z0-9_]*$'
  ),
  CONSTRAINT chk_reason_template_occasion_code_format CHECK (
    occasion_code IS NULL OR occasion_code ~ '^[a-z][a-z0-9_]*$'
  ),
  CONSTRAINT chk_feature_code CHECK (
    feature_code IS NULL OR feature_code IN (
      'formality', 'safety', 'brand_appropriateness',
      'emotion', 'novelty', 'intimacy', 'symbolic_identity', 'story_richness'
    )
  )
);

CREATE INDEX idx_reason_template_resolve
  ON reason_template (
    template_type,
    relationship_code,
    occasion_code,
    feature_code,
    is_active
  );

CREATE INDEX idx_reason_template_name_active
  ON reason_template (template_name, is_active);

-- =============================================================================
-- D02 延期 FK: pair_rule → pair_master
-- =============================================================================
ALTER TABLE pair_rule
  ADD CONSTRAINT fk_pair_rule_pair_master
  FOREIGN KEY (pair_id)
  REFERENCES pair_master (pair_id)
  ON DELETE RESTRICT;
-- <<< END d03_master_config.sql

-- >>> BEGIN d04_item.sql
-- D04: Item tables
-- change_id: d04_item
-- Issue: #601
-- 正本: docs/06_実装設計/database/*_テーブル定義書.md（D04 対象 7 件）
-- 適用順: D01 / D02 / D03 適用後。external_genre → item → 子テーブル → ranking_snapshot → item_popularity_signal
-- MVP△: external_attribute（DDL 参照用に含む。DDLバッチ分割表 §3）
-- LOGICAL 参照: item / ranking_snapshot / item_popularity_signal → external_genre（物理 FK なし）
-- LOGICAL 参照: item_popularity_signal.item_id → item（nullable・物理 FK なし）

-- =============================================================================
-- 1. external_genre
-- =============================================================================
CREATE TABLE external_genre (
  external_genre_id bigint PRIMARY KEY,
  source text NOT NULL DEFAULT 'rakuten',
  genre_name varchar(255) NOT NULL,
  parent_external_genre_id bigint,
  genre_level smallint NOT NULL,
  is_leaf boolean NOT NULL DEFAULT false,
  fetched_at timestamptz NOT NULL,
  CONSTRAINT uq_external_genre_source_id
    UNIQUE (source, external_genre_id),
  CONSTRAINT fk_external_genre_parent
    FOREIGN KEY (parent_external_genre_id)
    REFERENCES external_genre (external_genre_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_external_genre_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_external_genre_level_range CHECK (
    genre_level >= 0 AND genre_level <= 5
  ),
  CONSTRAINT chk_external_genre_name_length CHECK (
    char_length(genre_name) BETWEEN 1 AND 255
  ),
  CONSTRAINT chk_external_genre_parent_not_self CHECK (
    parent_external_genre_id IS NULL
    OR parent_external_genre_id <> external_genre_id
  )
);

CREATE INDEX idx_external_genre_parent
  ON external_genre (parent_external_genre_id);

CREATE INDEX idx_external_genre_level_leaf
  ON external_genre (genre_level, is_leaf);

-- =============================================================================
-- 2. item
-- =============================================================================
CREATE TABLE item (
  item_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source text NOT NULL DEFAULT 'rakuten',
  external_item_code text NOT NULL,
  item_name varchar(255) NOT NULL,
  item_caption text,
  catchcopy varchar(500),
  price integer NOT NULL,
  item_url text NOT NULL,
  external_genre_id bigint,
  shop_code text,
  normalized_hash varchar(64) NOT NULL,
  active_status text NOT NULL DEFAULT 'active',
  is_active boolean NOT NULL DEFAULT true,
  first_fetched_at timestamptz NOT NULL,
  last_checked_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_item_source_external_code
    UNIQUE (source, external_item_code),
  CONSTRAINT chk_item_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_item_price_non_negative CHECK (price >= 0),
  CONSTRAINT chk_item_active_status CHECK (
    active_status IN ('active', 'inactive', 'unavailable', 'excluded')
  ),
  CONSTRAINT chk_item_active_status_is_active CHECK (
    is_active = (active_status = 'active')
  )
);

CREATE INDEX idx_item_active_status
  ON item (active_status, is_active);

-- =============================================================================
-- 3. item_image
-- =============================================================================
CREATE TABLE item_image (
  item_image_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id uuid NOT NULL,
  image_url text NOT NULL,
  image_size_type text NOT NULL,
  display_order integer NOT NULL DEFAULT 0,
  is_primary boolean NOT NULL DEFAULT false,
  fetched_at timestamptz NOT NULL,
  CONSTRAINT uq_item_image_item_url
    UNIQUE (item_id, image_url),
  CONSTRAINT fk_item_image_item_id
    FOREIGN KEY (item_id)
    REFERENCES item (item_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_item_image_size_type CHECK (
    image_size_type IN ('small', 'medium')
  ),
  CONSTRAINT chk_item_image_display_order CHECK (display_order >= 0),
  CONSTRAINT chk_item_image_url_not_empty CHECK (
    char_length(trim(image_url)) > 0
  )
);

CREATE UNIQUE INDEX uq_item_image_primary_per_item
  ON item_image (item_id)
  WHERE is_primary = true;

CREATE INDEX idx_item_image_item_id
  ON item_image (item_id);

-- =============================================================================
-- 4. item_review_summary
-- =============================================================================
CREATE TABLE item_review_summary (
  item_review_summary_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id uuid NOT NULL,
  review_average numeric(3, 1),
  review_count integer NOT NULL,
  fetched_at timestamptz NOT NULL,
  CONSTRAINT uq_item_review_summary_item_id
    UNIQUE (item_id),
  CONSTRAINT fk_item_review_summary_item_id
    FOREIGN KEY (item_id)
    REFERENCES item (item_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_item_review_summary_count_nonneg CHECK (review_count >= 0),
  CONSTRAINT chk_item_review_summary_average_range CHECK (
    review_average IS NULL
    OR (review_average >= 0 AND review_average <= 5)
  ),
  CONSTRAINT chk_item_review_summary_average_when_count CHECK (
    review_count = 0 OR review_average IS NOT NULL
  )
);

CREATE INDEX idx_item_review_summary_item_id
  ON item_review_summary (item_id);

-- =============================================================================
-- 5. external_attribute（MVP△）
-- =============================================================================
CREATE TABLE external_attribute (
  source text NOT NULL DEFAULT 'rakuten',
  external_genre_id bigint NOT NULL,
  external_attribute_id bigint NOT NULL,
  attribute_name varchar(255) NOT NULL,
  attribute_group_name varchar(255),
  fetched_at timestamptz NOT NULL,
  PRIMARY KEY (source, external_genre_id, external_attribute_id),
  CONSTRAINT chk_external_attribute_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_external_attribute_name_length CHECK (
    char_length(attribute_name) BETWEEN 1 AND 255
  ),
  CONSTRAINT chk_external_attribute_group_length CHECK (
    attribute_group_name IS NULL
    OR char_length(attribute_group_name) BETWEEN 1 AND 255
  ),
  CONSTRAINT chk_external_attribute_id_positive CHECK (
    external_attribute_id > 0
  )
);

CREATE INDEX idx_external_attribute_genre
  ON external_attribute (external_genre_id);

CREATE INDEX idx_external_attribute_name
  ON external_attribute (attribute_name);

-- =============================================================================
-- 6. ranking_snapshot
-- =============================================================================
CREATE TABLE ranking_snapshot (
  ranking_snapshot_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source text NOT NULL DEFAULT 'rakuten',
  external_genre_id bigint NOT NULL,
  period varchar(32) NOT NULL,
  last_build_date timestamptz NOT NULL,
  fetched_at timestamptz NOT NULL,
  batch_run_id uuid,
  api_call_log_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_ranking_snapshot_observation_key
    UNIQUE (source, external_genre_id, period, last_build_date),
  CONSTRAINT chk_ranking_snapshot_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_ranking_snapshot_period_length CHECK (
    char_length(period) BETWEEN 1 AND 32
  ),
  CONSTRAINT chk_ranking_snapshot_genre_positive CHECK (external_genre_id >= 0)
);

CREATE INDEX idx_ranking_snapshot_genre_fetched
  ON ranking_snapshot (external_genre_id, fetched_at DESC);

CREATE INDEX idx_ranking_snapshot_batch_run
  ON ranking_snapshot (batch_run_id);

-- =============================================================================
-- 7. item_popularity_signal
-- =============================================================================
CREATE TABLE item_popularity_signal (
  item_popularity_signal_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ranking_snapshot_id uuid NOT NULL,
  item_id uuid,
  external_item_code text NOT NULL,
  external_genre_id bigint NOT NULL,
  rank integer NOT NULL,
  period varchar(32) NOT NULL,
  last_build_date timestamptz NOT NULL,
  fetched_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_ips_snapshot_rank
    UNIQUE (ranking_snapshot_id, rank),
  CONSTRAINT fk_ips_ranking_snapshot_id
    FOREIGN KEY (ranking_snapshot_id)
    REFERENCES ranking_snapshot (ranking_snapshot_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_ips_rank_positive CHECK (rank >= 1),
  CONSTRAINT chk_ips_period_length CHECK (
    char_length(period) BETWEEN 1 AND 32
  ),
  CONSTRAINT chk_ips_external_item_code_not_empty CHECK (
    char_length(trim(external_item_code)) > 0
  ),
  CONSTRAINT chk_ips_genre_positive CHECK (external_genre_id >= 0),
  CONSTRAINT chk_ips_item_or_code CHECK (
    item_id IS NOT NULL
    OR char_length(trim(external_item_code)) > 0
  )
);

CREATE INDEX idx_ips_ranking_snapshot_id
  ON item_popularity_signal (ranking_snapshot_id);

CREATE INDEX idx_ips_item_id
  ON item_popularity_signal (item_id);

CREATE INDEX idx_ips_external_item_code
  ON item_popularity_signal (external_item_code);

CREATE INDEX idx_ips_genre_period
  ON item_popularity_signal (external_genre_id, period);
-- <<< END d04_item.sql

-- >>> BEGIN d05_external_product_integration.sql
-- D05: External product integration tables
-- change_id: d05_external_product_integration
-- Issue: #602
-- 正本: docs/06_実装設計/database/*_テーブル定義書.md（D05 対象 10 件）
-- 適用順: D01〜D04 適用後。fetch_cursor → api_call_log → raw_product_metadata → Staging 系 → product_diff_result → item_import_summary
-- MVP△: staging_attribute（DDL 参照用に含む。DDLバッチ分割表 §3）
-- LOGICAL 参照: Staging / Log 系は物理 FK なし（batch_run_log / item / external_genre / external_attribute 含む）

-- =============================================================================
-- 1. fetch_cursor
-- =============================================================================
CREATE TABLE fetch_cursor (
  fetch_cursor_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source text NOT NULL DEFAULT 'rakuten',
  source_api varchar(32) NOT NULL DEFAULT 'item_search',
  target_external_genre_id bigint,
  cursor_type varchar(32) NOT NULL,
  cursor_value jsonb NOT NULL DEFAULT '{}',
  last_fetched_at timestamptz,
  cursor_status varchar(32) NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  cursor_scope_fingerprint text GENERATED ALWAYS AS (
    md5(
      coalesce(target_external_genre_id::text, '')
      || cursor_type
      || coalesce((cursor_value -> 'scope')::text, '')
    )
  ) STORED,
  CONSTRAINT uq_fetch_cursor_scope
    UNIQUE (
      source,
      source_api,
      cursor_type,
      target_external_genre_id,
      cursor_scope_fingerprint
    ),
  CONSTRAINT chk_fetch_cursor_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_fetch_cursor_source_api_mvp CHECK (source_api = 'item_search'),
  CONSTRAINT chk_fetch_cursor_type CHECK (
    cursor_type IN (
      'genre',
      'keyword',
      'update_sort',
      'ranking_supplement',
      'recheck'
    )
  ),
  CONSTRAINT chk_fetch_cursor_status CHECK (
    cursor_status IN ('active', 'paused', 'exhausted', 'failed')
  ),
  CONSTRAINT chk_fetch_cursor_genre_requires_target CHECK (
    cursor_type <> 'genre' OR target_external_genre_id IS NOT NULL
  )
);

CREATE INDEX idx_fetch_cursor_status
  ON fetch_cursor (cursor_status, updated_at);

CREATE INDEX idx_fetch_cursor_genre
  ON fetch_cursor (target_external_genre_id);

CREATE INDEX idx_fetch_cursor_source_api
  ON fetch_cursor (source, source_api, cursor_type);

-- =============================================================================
-- 2. api_call_log
-- =============================================================================
CREATE TABLE api_call_log (
  api_call_log_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_run_id uuid NOT NULL,
  fetch_cursor_id uuid,
  trace_id text,
  source text NOT NULL DEFAULT 'rakuten',
  source_api varchar(32) NOT NULL,
  request_params_hash text NOT NULL,
  request_params_json jsonb NOT NULL DEFAULT '{}',
  api_version varchar(32),
  response_status integer,
  call_status varchar(32) NOT NULL DEFAULT 'requested',
  item_count integer NOT NULL DEFAULT 0,
  requested_at timestamptz NOT NULL,
  completed_at timestamptz,
  duration_ms integer,
  error_code varchar(64),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chk_api_call_log_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_api_call_log_source_api CHECK (
    source_api IN (
      'item_search',
      'item_ranking',
      'genre_search',
      'attribute_search'
    )
  ),
  CONSTRAINT chk_api_call_log_status CHECK (
    call_status IN (
      'requested',
      'succeeded',
      'failed',
      'rate_limited',
      'skipped'
    )
  ),
  CONSTRAINT chk_api_call_log_item_count_nonneg CHECK (item_count >= 0),
  CONSTRAINT chk_api_call_log_duration_nonneg CHECK (
    duration_ms IS NULL OR duration_ms >= 0
  ),
  CONSTRAINT chk_api_call_log_terminal_completed CHECK (
    call_status = 'requested' OR completed_at IS NOT NULL
  )
);

CREATE INDEX idx_api_call_log_batch
  ON api_call_log (batch_run_id, requested_at);

CREATE INDEX idx_api_call_log_fetch_cursor
  ON api_call_log (fetch_cursor_id, requested_at);

CREATE INDEX idx_api_call_log_status
  ON api_call_log (call_status, requested_at);

CREATE INDEX idx_api_call_log_source_api
  ON api_call_log (source_api, requested_at);

CREATE INDEX idx_api_call_log_trace
  ON api_call_log (trace_id);

-- =============================================================================
-- 3. raw_product_metadata
-- =============================================================================
CREATE TABLE raw_product_metadata (
  raw_metadata_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  api_call_log_id uuid,
  object_key text NOT NULL,
  source text NOT NULL DEFAULT 'rakuten',
  source_api varchar(32) NOT NULL,
  content_hash text NOT NULL,
  item_count integer NOT NULL DEFAULT 0,
  import_status varchar(32) NOT NULL DEFAULT 'raw_saved',
  fetched_at timestamptz NOT NULL,
  staged_at timestamptz,
  imported_at timestamptz,
  error_code varchar(64),
  error_message text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_raw_product_metadata_object_key UNIQUE (object_key),
  CONSTRAINT chk_raw_metadata_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_raw_metadata_source_api CHECK (
    source_api IN (
      'item_search',
      'item_ranking',
      'genre_search',
      'attribute_search'
    )
  ),
  CONSTRAINT chk_raw_metadata_import_status CHECK (
    import_status IN (
      'raw_saved',
      'staged',
      'imported',
      'skipped',
      'failed'
    )
  ),
  CONSTRAINT chk_raw_metadata_item_count CHECK (item_count >= 0),
  CONSTRAINT chk_raw_metadata_staged_at CHECK (
    import_status NOT IN ('staged', 'imported') OR staged_at IS NOT NULL
  ),
  CONSTRAINT chk_raw_metadata_imported_at CHECK (
    import_status NOT IN ('imported', 'skipped') OR imported_at IS NOT NULL
  ),
  CONSTRAINT chk_raw_metadata_failed_error CHECK (
    import_status <> 'failed' OR error_message IS NOT NULL
  )
);

CREATE INDEX idx_raw_metadata_status
  ON raw_product_metadata (import_status, fetched_at);

CREATE INDEX idx_raw_metadata_api_call_log
  ON raw_product_metadata (api_call_log_id);

CREATE INDEX idx_raw_metadata_source_api
  ON raw_product_metadata (source, source_api, fetched_at DESC);

-- =============================================================================
-- 4. staging_item
-- =============================================================================
CREATE TABLE staging_item (
  staging_item_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_metadata_id uuid NOT NULL,
  source text NOT NULL DEFAULT 'rakuten',
  external_item_code text NOT NULL,
  item_name varchar(255) NOT NULL,
  item_caption text,
  catchcopy varchar(500),
  price integer NOT NULL,
  item_url text NOT NULL,
  external_genre_id bigint,
  shop_code text,
  availability smallint,
  review_average numeric(3, 2),
  review_count integer,
  normalized_hash varchar(64) NOT NULL,
  diff_status varchar(32),
  staged_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_staging_item_raw_metadata_code
    UNIQUE (raw_metadata_id, external_item_code),
  CONSTRAINT chk_staging_item_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_staging_item_price_non_negative CHECK (price >= 0),
  CONSTRAINT chk_staging_item_review_count CHECK (
    review_count IS NULL OR review_count >= 0
  ),
  CONSTRAINT chk_staging_item_diff_status CHECK (
    diff_status IS NULL
    OR diff_status IN ('new', 'updated', 'unchanged', 'unavailable')
  ),
  CONSTRAINT chk_staging_item_availability CHECK (
    availability IS NULL OR availability IN (0, 1)
  )
);

CREATE INDEX idx_staging_item_raw_metadata
  ON staging_item (raw_metadata_id);

CREATE INDEX idx_staging_item_source_code
  ON staging_item (source, external_item_code);

CREATE INDEX idx_staging_item_diff_status
  ON staging_item (diff_status);

-- =============================================================================
-- 5. staging_item_image
-- =============================================================================
CREATE TABLE staging_item_image (
  staging_item_image_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_metadata_id uuid NOT NULL,
  external_item_code text NOT NULL,
  image_url text NOT NULL,
  image_size_type text NOT NULL,
  display_order integer NOT NULL DEFAULT 0,
  is_primary_candidate boolean NOT NULL DEFAULT false,
  staged_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_staging_item_image_raw_code_url
    UNIQUE (raw_metadata_id, external_item_code, image_url),
  CONSTRAINT chk_staging_item_image_size_type CHECK (
    image_size_type IN ('small', 'medium')
  ),
  CONSTRAINT chk_staging_item_image_display_order CHECK (display_order >= 0),
  CONSTRAINT chk_staging_item_image_url_not_empty CHECK (
    char_length(trim(image_url)) > 0
  )
);

CREATE UNIQUE INDEX uq_staging_item_image_primary_candidate
  ON staging_item_image (raw_metadata_id, external_item_code)
  WHERE is_primary_candidate = true;

CREATE INDEX idx_staging_item_image_raw_metadata
  ON staging_item_image (raw_metadata_id);

CREATE INDEX idx_staging_item_image_raw_code
  ON staging_item_image (raw_metadata_id, external_item_code);

-- =============================================================================
-- 6. staging_ranking_signal
-- =============================================================================
CREATE TABLE staging_ranking_signal (
  staging_ranking_signal_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_metadata_id uuid NOT NULL,
  external_item_code text NOT NULL,
  external_genre_id bigint NOT NULL,
  rank integer NOT NULL,
  period varchar(32) NOT NULL,
  last_build_date timestamptz NOT NULL,
  staged_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_staging_ranking_signal_raw_metadata_rank
    UNIQUE (raw_metadata_id, rank),
  CONSTRAINT chk_staging_ranking_signal_rank_positive CHECK (rank >= 1),
  CONSTRAINT chk_staging_ranking_signal_period_length CHECK (
    char_length(period) BETWEEN 1 AND 32
  ),
  CONSTRAINT chk_staging_ranking_signal_genre_non_negative CHECK (
    external_genre_id >= 0
  )
);

CREATE INDEX idx_staging_ranking_signal_raw_metadata
  ON staging_ranking_signal (raw_metadata_id);

CREATE INDEX idx_staging_ranking_signal_item_code
  ON staging_ranking_signal (external_item_code);

CREATE INDEX idx_staging_ranking_signal_observation
  ON staging_ranking_signal (external_genre_id, period, last_build_date);

-- =============================================================================
-- 7. staging_genre
-- =============================================================================
CREATE TABLE staging_genre (
  staging_genre_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_metadata_id uuid NOT NULL,
  source text NOT NULL DEFAULT 'rakuten',
  external_genre_id bigint NOT NULL,
  genre_name varchar(255) NOT NULL,
  parent_external_genre_id bigint,
  genre_level smallint NOT NULL,
  is_leaf boolean NOT NULL DEFAULT false,
  staged_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_staging_genre_raw_metadata_genre
    UNIQUE (raw_metadata_id, external_genre_id),
  CONSTRAINT chk_staging_genre_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_staging_genre_level_range CHECK (
    genre_level >= 0 AND genre_level <= 5
  ),
  CONSTRAINT chk_staging_genre_name_length CHECK (
    char_length(genre_name) BETWEEN 1 AND 255
  ),
  CONSTRAINT chk_staging_genre_parent_not_self CHECK (
    parent_external_genre_id IS NULL
    OR parent_external_genre_id <> external_genre_id
  )
);

CREATE INDEX idx_staging_genre_raw_metadata
  ON staging_genre (raw_metadata_id);

CREATE INDEX idx_staging_genre_source_id
  ON staging_genre (source, external_genre_id);

-- =============================================================================
-- 8. staging_attribute（MVP△）
-- =============================================================================
CREATE TABLE staging_attribute (
  staging_attribute_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_metadata_id uuid NOT NULL,
  source text NOT NULL DEFAULT 'rakuten',
  external_genre_id bigint NOT NULL,
  external_attribute_id bigint NOT NULL,
  attribute_name varchar(255) NOT NULL,
  attribute_group_name varchar(255),
  staged_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_staging_attribute_raw_metadata_attr
    UNIQUE (raw_metadata_id, external_genre_id, external_attribute_id),
  CONSTRAINT chk_staging_attribute_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_staging_attribute_name_length CHECK (
    char_length(attribute_name) BETWEEN 1 AND 255
  ),
  CONSTRAINT chk_staging_attribute_group_length CHECK (
    attribute_group_name IS NULL
    OR char_length(attribute_group_name) BETWEEN 1 AND 255
  ),
  CONSTRAINT chk_staging_attribute_id_positive CHECK (external_attribute_id > 0)
);

CREATE INDEX idx_staging_attribute_raw_metadata
  ON staging_attribute (raw_metadata_id);

CREATE INDEX idx_staging_attribute_source_genre_attr
  ON staging_attribute (source, external_genre_id, external_attribute_id);

-- =============================================================================
-- 9. product_diff_result
-- =============================================================================
CREATE TABLE product_diff_result (
  product_diff_result_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_run_id uuid NOT NULL,
  staging_item_id uuid NOT NULL,
  external_item_code text NOT NULL,
  old_hash varchar(64),
  new_hash varchar(64) NOT NULL,
  diff_status varchar(32) NOT NULL,
  judged_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_product_diff_batch_code
    UNIQUE (batch_run_id, external_item_code),
  CONSTRAINT chk_product_diff_status CHECK (
    diff_status IN ('new', 'updated', 'unchanged', 'unavailable')
  ),
  CONSTRAINT chk_product_diff_new_hash CHECK (length(new_hash) = 64),
  CONSTRAINT chk_product_diff_old_hash_len CHECK (
    old_hash IS NULL OR length(old_hash) = 64
  ),
  CONSTRAINT chk_product_diff_new_old_consistency CHECK (
    diff_status <> 'new' OR old_hash IS NULL
  ),
  CONSTRAINT chk_product_diff_updated_old CHECK (
    diff_status NOT IN ('updated', 'unchanged') OR old_hash IS NOT NULL
  )
);

CREATE INDEX idx_product_diff_staging_item
  ON product_diff_result (staging_item_id);

CREATE INDEX idx_product_diff_status
  ON product_diff_result (batch_run_id, diff_status);

-- =============================================================================
-- 10. item_import_summary
-- =============================================================================
CREATE TABLE item_import_summary (
  item_import_summary_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_run_id uuid NOT NULL,
  source text NOT NULL DEFAULT 'rakuten',
  source_api varchar(32) NOT NULL,
  fetched_count integer NOT NULL DEFAULT 0,
  new_count integer NOT NULL DEFAULT 0,
  updated_count integer NOT NULL DEFAULT 0,
  unchanged_count integer NOT NULL DEFAULT 0,
  unavailable_count integer NOT NULL DEFAULT 0,
  skipped_count integer NOT NULL DEFAULT 0,
  failed_count integer NOT NULL DEFAULT 0,
  feature_generated_count integer NOT NULL DEFAULT 0,
  embedding_generated_count integer NOT NULL DEFAULT 0,
  summarized_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_item_import_summary_run_api
    UNIQUE (batch_run_id, source_api),
  CONSTRAINT chk_item_import_summary_source CHECK (source = 'rakuten'),
  CONSTRAINT chk_item_import_summary_source_api CHECK (
    source_api IN (
      'item_search',
      'item_ranking',
      'genre_search',
      'attribute_search'
    )
  ),
  CONSTRAINT chk_item_import_summary_counts_nonneg CHECK (
    fetched_count >= 0
    AND new_count >= 0
    AND updated_count >= 0
    AND unchanged_count >= 0
    AND unavailable_count >= 0
    AND skipped_count >= 0
    AND failed_count >= 0
    AND feature_generated_count >= 0
    AND embedding_generated_count >= 0
  )
);

CREATE INDEX idx_item_import_summary_run
  ON item_import_summary (batch_run_id, summarized_at DESC);

CREATE INDEX idx_item_import_summary_source_api
  ON item_import_summary (source_api, summarized_at DESC);
-- <<< END d05_external_product_integration.sql

-- >>> BEGIN d06_item_derived.sql
-- D06: Item derived data tables
-- change_id: d06_item_derived
-- Issue: #603
-- 正本: docs/06_実装設計/database/*_テーブル定義書.md（D06 対象 5 件）
-- 適用順: D01〜D05 適用後。item_generation_queue → item_semantic → item_feature → item_meaning → item_embedding
-- LOGICAL 参照: feature_code / feature_normalization_version_id（物理 FK なし）
-- LOGICAL 参照: item_generation_queue と派生テーブル間（物理 FK なし）

-- =============================================================================
-- 1. item_generation_queue
-- =============================================================================
CREATE TABLE item_generation_queue (
  item_generation_queue_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id uuid NOT NULL,
  generation_type text NOT NULL DEFAULT 'semantic',
  queue_status text NOT NULL DEFAULT 'queued',
  retry_count integer NOT NULL DEFAULT 0,
  queued_at timestamptz NOT NULL,
  started_at timestamptz,
  completed_at timestamptz,
  error_message text,
  CONSTRAINT fk_item_generation_queue_item_id
    FOREIGN KEY (item_id)
    REFERENCES item (item_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_item_gen_queue_status CHECK (
    queue_status IN (
      'queued', 'processing', 'succeeded', 'failed', 'skipped'
    )
  ),
  CONSTRAINT chk_item_gen_generation_type CHECK (
    generation_type IN ('semantic', 'feature', 'embedding')
  ),
  CONSTRAINT chk_item_gen_retry_count_nonneg CHECK (retry_count >= 0),
  CONSTRAINT chk_item_gen_retry_count_max CHECK (retry_count <= 5),
  CONSTRAINT chk_item_gen_started_when_processing CHECK (
    queue_status NOT IN ('processing', 'succeeded', 'failed', 'skipped')
    OR started_at IS NOT NULL
  ),
  CONSTRAINT chk_item_gen_completed_when_terminal CHECK (
    queue_status IN ('queued', 'processing')
    OR completed_at IS NOT NULL
  )
);

CREATE INDEX idx_item_gen_queue_status
  ON item_generation_queue (queue_status, queued_at);

CREATE INDEX idx_item_generation_queue_item_id
  ON item_generation_queue (item_id);

CREATE UNIQUE INDEX uq_item_gen_queue_active_per_type
  ON item_generation_queue (item_id, generation_type)
  WHERE queue_status IN ('queued', 'processing');

-- =============================================================================
-- 2. item_semantic
-- =============================================================================
CREATE TABLE item_semantic (
  item_semantic_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id uuid NOT NULL,
  semantic_config_version_id uuid NOT NULL,
  semantic_json jsonb NOT NULL,
  generated_at timestamptz NOT NULL,
  CONSTRAINT uq_item_semantic_item_version
    UNIQUE (item_id, semantic_config_version_id),
  CONSTRAINT fk_item_semantic_item_id
    FOREIGN KEY (item_id)
    REFERENCES item (item_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_item_semantic_semantic_config_version_id
    FOREIGN KEY (semantic_config_version_id)
    REFERENCES semantic_config_version (semantic_config_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_semantic_json_object CHECK (
    jsonb_typeof(semantic_json) = 'object'
  ),
  CONSTRAINT chk_semantic_json_concepts_array CHECK (
    jsonb_typeof(semantic_json -> 'concepts') = 'array'
  )
);

CREATE INDEX idx_item_semantic_item_id
  ON item_semantic (item_id);

CREATE INDEX idx_item_semantic_version_id
  ON item_semantic (semantic_config_version_id);

CREATE INDEX idx_item_semantic_generated_at
  ON item_semantic (generated_at DESC);

-- =============================================================================
-- 3. item_feature
-- =============================================================================
CREATE TABLE item_feature (
  item_feature_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id uuid NOT NULL,
  semantic_config_version_id uuid NOT NULL,
  feature_code text NOT NULL,
  feature_input_hash varchar(64) NOT NULL,
  feature_normalization_version_id uuid NOT NULL,
  raw_feature_value numeric(8, 6) NOT NULL,
  normalized_feature_value numeric(8, 6),
  generated_at timestamptz NOT NULL,
  CONSTRAINT uq_item_feature_idempotent
    UNIQUE (
      item_id,
      semantic_config_version_id,
      feature_code,
      feature_input_hash,
      feature_normalization_version_id
    ),
  CONSTRAINT fk_item_feature_item_id
    FOREIGN KEY (item_id)
    REFERENCES item (item_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_item_feature_semantic_config_version_id
    FOREIGN KEY (semantic_config_version_id)
    REFERENCES semantic_config_version (semantic_config_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_item_feature_code_mvp CHECK (
    feature_code IN (
      'formality', 'safety', 'brand_appropriateness',
      'emotion', 'novelty', 'intimacy', 'symbolic_identity', 'story_richness'
    )
  ),
  CONSTRAINT chk_item_feature_input_hash_format CHECK (
    char_length(feature_input_hash) = 64
    AND feature_input_hash ~ '^[0-9a-f]{64}$'
  ),
  CONSTRAINT chk_item_feature_normalized_range CHECK (
    normalized_feature_value IS NULL
    OR (
      normalized_feature_value >= 0.0
      AND normalized_feature_value <= 1.0
    )
  ),
  CONSTRAINT chk_item_feature_raw_range CHECK (
    raw_feature_value >= 0.0 AND raw_feature_value <= 1.0
  )
);

CREATE INDEX idx_item_feature_lookup
  ON item_feature (item_id, semantic_config_version_id, feature_code);

CREATE INDEX idx_item_feature_item_id
  ON item_feature (item_id);

CREATE INDEX idx_item_feature_norm_version
  ON item_feature (feature_normalization_version_id);

-- =============================================================================
-- 4. item_meaning
-- =============================================================================
CREATE TABLE item_meaning (
  item_meaning_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id uuid NOT NULL,
  semantic_config_version_id uuid NOT NULL,
  feature_normalization_version_id uuid NOT NULL,
  item_social numeric(6, 4) NOT NULL,
  item_symbolic numeric(6, 4) NOT NULL,
  generated_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_item_meaning_item_scv
    UNIQUE (item_id, semantic_config_version_id),
  CONSTRAINT fk_item_meaning_item_id
    FOREIGN KEY (item_id)
    REFERENCES item (item_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_item_meaning_semantic_config_version_id
    FOREIGN KEY (semantic_config_version_id)
    REFERENCES semantic_config_version (semantic_config_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_item_meaning_social_range CHECK (
    item_social >= 0.0 AND item_social <= 1.0
  ),
  CONSTRAINT chk_item_meaning_symbolic_range CHECK (
    item_symbolic >= 0.0 AND item_symbolic <= 1.0
  )
);

CREATE INDEX idx_item_meaning_lookup
  ON item_meaning (item_id, semantic_config_version_id);

CREATE INDEX idx_item_meaning_scv
  ON item_meaning (semantic_config_version_id);

CREATE INDEX idx_item_meaning_norm_version
  ON item_meaning (feature_normalization_version_id);

-- =============================================================================
-- 5. item_embedding
-- =============================================================================
CREATE TABLE item_embedding (
  item_embedding_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id uuid NOT NULL,
  model_version_id uuid NOT NULL,
  embedding_source_type text NOT NULL,
  embedding_input_hash varchar(64) NOT NULL,
  embedding_vector vector(1536) NOT NULL,
  generated_at timestamptz NOT NULL,
  CONSTRAINT uq_item_embedding_idempotent
    UNIQUE (item_id, model_version_id, embedding_input_hash),
  CONSTRAINT fk_item_embedding_item_id
    FOREIGN KEY (item_id)
    REFERENCES item (item_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_item_embedding_model_version_id
    FOREIGN KEY (model_version_id)
    REFERENCES model_version (model_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_item_embedding_source_type CHECK (
    embedding_source_type = 'item_text_context'
  ),
  CONSTRAINT chk_item_embedding_input_hash_format CHECK (
    char_length(embedding_input_hash) = 64
    AND embedding_input_hash ~ '^[0-9a-f]{64}$'
  ),
  CONSTRAINT chk_item_embedding_vector_dims CHECK (
    vector_dims(embedding_vector) = 1536
  )
);

CREATE INDEX idx_item_embedding_item_model
  ON item_embedding (item_id, model_version_id);

CREATE INDEX idx_item_embedding_item_id
  ON item_embedding (item_id);

CREATE INDEX idx_item_embedding_vector
  ON item_embedding
  USING hnsw (embedding_vector vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
-- <<< END d06_item_derived.sql

-- >>> BEGIN d07_online_recommendation.sql
-- D07: Online recommendation tables
-- change_id: d07_online_recommendation
-- Issue: #604
-- 正本: docs/06_実装設計/database/*_テーブル定義書.md（D07 対象 6 件）
-- 適用順: D01〜D06 適用後。
--   recommendation_request → recommendation_run → recommendation_result
--   → recommendation_result_item → recommendation_reason → recommendation_feedback
-- LOGICAL 参照: relationship_master / occasion_master / Config version 列 / trace 列 / template_id
-- D08 から Run への後追い物理 FK は本バッチでは付与しない

-- =============================================================================
-- 1. recommendation_request
-- =============================================================================
CREATE TABLE recommendation_request (
  recommendation_request_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  request_mode varchar(32) NOT NULL,
  relationship_code text NOT NULL,
  occasion_code text NOT NULL,
  budget_min integer,
  budget_max integer,
  currency varchar(3) NOT NULL DEFAULT 'JPY',
  tax_included boolean,
  preferred_text text,
  non_preferred_text text,
  ng_text text,
  free_text text,
  top_k integer,
  candidate_limit integer,
  include_reason boolean,
  include_debug_info boolean,
  request_payload jsonb NOT NULL,
  validated_payload jsonb NOT NULL,
  trace_id text,
  created_at timestamptz NOT NULL DEFAULT now(),
  validated_at timestamptz NOT NULL,
  CONSTRAINT chk_request_mode CHECK (
    request_mode IN ('ui', 'evaluation', 'batch')
  ),
  CONSTRAINT chk_budget_min_non_negative CHECK (
    budget_min IS NULL OR budget_min >= 0
  ),
  CONSTRAINT chk_budget_max_non_negative CHECK (
    budget_max IS NULL OR budget_max >= 0
  ),
  CONSTRAINT chk_budget_range CHECK (
    budget_min IS NULL
    OR budget_max IS NULL
    OR budget_min <= budget_max
  ),
  CONSTRAINT chk_top_k_range CHECK (
    top_k IS NULL OR (top_k >= 1 AND top_k <= 50)
  ),
  CONSTRAINT chk_candidate_limit_range CHECK (
    candidate_limit IS NULL OR candidate_limit >= 1
  ),
  CONSTRAINT chk_candidate_limit_gte_top_k CHECK (
    top_k IS NULL
    OR candidate_limit IS NULL
    OR candidate_limit >= top_k
  ),
  CONSTRAINT chk_preferred_text_length CHECK (
    preferred_text IS NULL OR char_length(preferred_text) <= 500
  ),
  CONSTRAINT chk_non_preferred_text_length CHECK (
    non_preferred_text IS NULL OR char_length(non_preferred_text) <= 500
  ),
  CONSTRAINT chk_ng_text_length CHECK (
    ng_text IS NULL OR char_length(ng_text) <= 300
  ),
  CONSTRAINT chk_free_text_length CHECK (
    free_text IS NULL OR char_length(free_text) <= 800
  ),
  CONSTRAINT chk_currency_mvp CHECK (currency = 'JPY')
);

CREATE INDEX idx_recommendation_request_created
  ON recommendation_request (created_at DESC);

CREATE INDEX idx_recommendation_request_mode_created
  ON recommendation_request (request_mode, created_at DESC);

CREATE INDEX idx_recommendation_request_relationship
  ON recommendation_request (relationship_code, created_at DESC);

CREATE INDEX idx_recommendation_request_occasion
  ON recommendation_request (occasion_code, created_at DESC);

CREATE INDEX idx_recommendation_request_trace
  ON recommendation_request (trace_id);

-- =============================================================================
-- 2. recommendation_run
-- =============================================================================
CREATE TABLE recommendation_run (
  recommendation_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_request_id uuid NOT NULL,
  pair_id uuid NOT NULL,
  semantic_config_version_id uuid NOT NULL,
  model_version_id uuid NOT NULL,
  ranking_config_id uuid NOT NULL,
  run_status varchar(32) NOT NULL DEFAULT 'accepted',
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT fk_recommendation_run_request
    FOREIGN KEY (recommendation_request_id)
    REFERENCES recommendation_request (recommendation_request_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_recommendation_run_pair
    FOREIGN KEY (pair_id)
    REFERENCES pair_master (pair_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_run_status CHECK (
    run_status IN (
      'accepted', 'running', 'succeeded', 'failed', 'canceled'
    )
  ),
  CONSTRAINT chk_run_started_before_completed CHECK (
    completed_at IS NULL
    OR started_at IS NULL
    OR started_at <= completed_at
  ),
  CONSTRAINT chk_run_completed_terminal CHECK (
    run_status NOT IN ('succeeded', 'failed', 'canceled')
    OR completed_at IS NOT NULL
  ),
  CONSTRAINT chk_run_nonterminal_no_completed CHECK (
    run_status NOT IN ('accepted', 'running')
    OR completed_at IS NULL
  )
);

CREATE INDEX idx_recommendation_run_request_id
  ON recommendation_run (recommendation_request_id);

CREATE INDEX idx_recommendation_run_status
  ON recommendation_run (run_status, started_at);

CREATE INDEX idx_recommendation_run_pair_id
  ON recommendation_run (pair_id);

CREATE INDEX idx_recommendation_run_semantic_config_version
  ON recommendation_run (semantic_config_version_id);

CREATE INDEX idx_recommendation_run_model_version
  ON recommendation_run (model_version_id);

CREATE INDEX idx_recommendation_run_ranking_config
  ON recommendation_run (ranking_config_id);

CREATE INDEX idx_recommendation_run_created
  ON recommendation_run (created_at DESC);

-- =============================================================================
-- 3. recommendation_result
-- =============================================================================
CREATE TABLE recommendation_result (
  recommendation_result_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_request_id uuid NOT NULL,
  recommendation_run_id uuid NOT NULL,
  request_mode varchar(32) NOT NULL,
  result_status varchar(32) NOT NULL,
  top_k integer NOT NULL,
  result_item_count integer NOT NULL DEFAULT 0,
  candidate_count integer,
  fallback_used boolean NOT NULL DEFAULT false,
  display_message text,
  caution_message text,
  semantic_config_version_id uuid NOT NULL,
  model_version_id uuid NOT NULL,
  ranking_config_id uuid NOT NULL,
  reason_template_version_id uuid,
  result_payload jsonb,
  debug_payload jsonb,
  trace_id text,
  generated_at timestamptz NOT NULL DEFAULT now(),
  displayed_at timestamptz,
  expired_at timestamptz,
  CONSTRAINT uq_result_per_run
    UNIQUE (recommendation_run_id),
  CONSTRAINT fk_result_request
    FOREIGN KEY (recommendation_request_id)
    REFERENCES recommendation_request (recommendation_request_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_result_run
    FOREIGN KEY (recommendation_run_id)
    REFERENCES recommendation_run (recommendation_run_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_result_status CHECK (
    result_status IN ('generated', 'empty', 'failed')
  ),
  CONSTRAINT chk_result_request_mode CHECK (
    request_mode IN ('ui', 'evaluation', 'batch')
  ),
  CONSTRAINT chk_top_k_range_result CHECK (
    top_k >= 1 AND top_k <= 50
  ),
  CONSTRAINT chk_result_item_count_non_negative CHECK (
    result_item_count >= 0
  ),
  CONSTRAINT chk_result_item_count_lte_top_k CHECK (
    result_item_count <= top_k
  ),
  CONSTRAINT chk_empty_status_consistency CHECK (
    result_status <> 'empty' OR result_item_count = 0
  ),
  CONSTRAINT chk_generated_status_consistency CHECK (
    result_status <> 'generated' OR result_item_count >= 1
  )
);

CREATE INDEX idx_recommendation_result_run_id
  ON recommendation_result (recommendation_run_id);

CREATE INDEX idx_recommendation_result_request_id
  ON recommendation_result (recommendation_request_id);

CREATE INDEX idx_recommendation_result_generated
  ON recommendation_result (generated_at DESC);

CREATE INDEX idx_recommendation_result_status
  ON recommendation_result (result_status, generated_at DESC);

CREATE INDEX idx_recommendation_result_trace
  ON recommendation_result (trace_id);

-- =============================================================================
-- 4. recommendation_result_item
-- =============================================================================
CREATE TABLE recommendation_result_item (
  recommendation_result_item_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_result_id uuid NOT NULL,
  item_id uuid NOT NULL,
  rank integer NOT NULL,
  final_score numeric(8, 6) NOT NULL,
  context_score numeric(8, 6) NOT NULL,
  score_breakdown_json jsonb,
  item_name_snapshot varchar(255) NOT NULL,
  item_catchcopy_snapshot varchar(500),
  item_price_snapshot integer NOT NULL,
  item_url_snapshot text NOT NULL,
  item_image_url_snapshot text,
  review_average_snapshot numeric(3, 2),
  review_count_snapshot integer,
  shop_name_snapshot text,
  is_displayed boolean NOT NULL DEFAULT true,
  is_fallback boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_result_item_result_rank
    UNIQUE (recommendation_result_id, rank),
  CONSTRAINT uq_result_item_result_item
    UNIQUE (recommendation_result_id, item_id),
  CONSTRAINT fk_result_item_result
    FOREIGN KEY (recommendation_result_id)
    REFERENCES recommendation_result (recommendation_result_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_result_item_item
    FOREIGN KEY (item_id)
    REFERENCES item (item_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_result_item_rank_positive CHECK (rank >= 1),
  CONSTRAINT chk_result_item_final_score_range CHECK (
    final_score >= 0 AND final_score <= 1
  ),
  CONSTRAINT chk_result_item_context_score_range CHECK (
    context_score >= 0 AND context_score <= 1
  ),
  CONSTRAINT chk_result_item_price_non_negative CHECK (
    item_price_snapshot >= 0
  ),
  CONSTRAINT chk_result_item_review_count CHECK (
    review_count_snapshot IS NULL OR review_count_snapshot >= 0
  ),
  CONSTRAINT chk_result_item_review_average CHECK (
    review_average_snapshot IS NULL
    OR (
      review_average_snapshot >= 0
      AND review_average_snapshot <= 5
    )
  )
);

CREATE INDEX idx_result_item_item_id
  ON recommendation_result_item (item_id);

-- =============================================================================
-- 5. recommendation_reason
-- =============================================================================
CREATE TABLE recommendation_reason (
  recommendation_reason_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_result_item_id uuid NOT NULL,
  template_id uuid NOT NULL,
  reason_summary text NOT NULL,
  reason_detail text,
  reason_points_json jsonb,
  reason_badges_json jsonb,
  caution_note text,
  reason_basis_json jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT fk_recommendation_reason_result_item
    FOREIGN KEY (recommendation_result_item_id)
    REFERENCES recommendation_result_item (recommendation_result_item_id)
    ON DELETE RESTRICT,
  CONSTRAINT uq_recommendation_reason_result_item
    UNIQUE (recommendation_result_item_id),
  CONSTRAINT chk_reason_summary_not_empty CHECK (
    length(trim(reason_summary)) > 0
  ),
  CONSTRAINT chk_reason_basis_json_object CHECK (
    jsonb_typeof(reason_basis_json) = 'object'
  )
);

CREATE INDEX idx_recommendation_reason_template_id
  ON recommendation_reason (template_id);

-- =============================================================================
-- 6. recommendation_feedback
-- =============================================================================
CREATE TABLE recommendation_feedback (
  recommendation_feedback_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_result_id uuid NOT NULL,
  recommendation_result_item_id uuid,
  recommendation_reason_id uuid,
  recommendation_request_id uuid,
  recommendation_run_id uuid,
  feedback_target_type varchar(32) NOT NULL,
  feedback_type varchar(64) NOT NULL,
  feedback_value_type varchar(32) NOT NULL,
  feedback_value jsonb,
  feedback_choice_code varchar(64),
  feedback_text text,
  feedback_reason_category varchar(64),
  feedback_rating integer NOT NULL,
  is_positive boolean,
  is_negative boolean,
  rank_at_feedback integer,
  item_id uuid,
  session_id text,
  anonymous_user_id text,
  source_page varchar(64),
  user_agent text,
  feedback_status varchar(32) NOT NULL DEFAULT 'submitted',
  submitted_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz,
  CONSTRAINT fk_feedback_result
    FOREIGN KEY (recommendation_result_id)
    REFERENCES recommendation_result (recommendation_result_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_feedback_status CHECK (
    feedback_status IN ('submitted', 'invalid', 'ignored')
  ),
  CONSTRAINT chk_feedback_target_type CHECK (
    feedback_target_type IN ('result', 'item', 'reason')
  ),
  CONSTRAINT chk_feedback_value_type CHECK (
    feedback_value_type IN ('boolean', 'rating', 'choice', 'text', 'event')
  ),
  CONSTRAINT chk_feedback_type_mvp CHECK (
    feedback_type IN (
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
    )
  ),
  CONSTRAINT chk_feedback_rating_range CHECK (
    feedback_rating BETWEEN 1 AND 5
  ),
  CONSTRAINT chk_feedback_text_length CHECK (
    feedback_text IS NULL OR char_length(feedback_text) <= 500
  ),
  CONSTRAINT chk_feedback_user_agent_length CHECK (
    user_agent IS NULL OR char_length(user_agent) <= 500
  ),
  CONSTRAINT chk_feedback_target_result CHECK (
    feedback_target_type <> 'result'
    OR (
      recommendation_result_item_id IS NULL
      AND recommendation_reason_id IS NULL
    )
  ),
  CONSTRAINT chk_feedback_target_item CHECK (
    feedback_target_type <> 'item'
    OR recommendation_result_item_id IS NOT NULL
  ),
  CONSTRAINT chk_feedback_target_reason CHECK (
    feedback_target_type <> 'reason'
    OR recommendation_reason_id IS NOT NULL
  ),
  CONSTRAINT chk_feedback_type_target_item CHECK (
    (
      feedback_type IN (
        'item_good',
        'item_bad',
        'item_not_match',
        'item_ng_violation',
        'item_avoid_match'
      )
      AND feedback_target_type = 'item'
    )
    OR (
      feedback_type IN ('reason_good', 'reason_bad')
      AND feedback_target_type = 'reason'
    )
    OR (
      feedback_type IN ('result_good', 'result_bad')
      AND feedback_target_type = 'result'
    )
    OR (
      feedback_type = 'comment'
      AND feedback_target_type IN ('result', 'item', 'reason')
    )
  )
);

CREATE UNIQUE INDEX uq_feedback_session_result_type
  ON recommendation_feedback (session_id, recommendation_result_id, feedback_type)
  WHERE feedback_target_type = 'result' AND session_id IS NOT NULL;

CREATE UNIQUE INDEX uq_feedback_session_item_type
  ON recommendation_feedback (
    session_id,
    recommendation_result_item_id,
    feedback_type
  )
  WHERE feedback_target_type = 'item' AND session_id IS NOT NULL;

CREATE UNIQUE INDEX uq_feedback_session_reason_type
  ON recommendation_feedback (session_id, recommendation_reason_id, feedback_type)
  WHERE feedback_target_type = 'reason' AND session_id IS NOT NULL;

CREATE INDEX idx_recommendation_feedback_result_id
  ON recommendation_feedback (recommendation_result_id);

CREATE INDEX idx_recommendation_feedback_result_item_id
  ON recommendation_feedback (recommendation_result_item_id);

CREATE INDEX idx_recommendation_feedback_reason_id
  ON recommendation_feedback (recommendation_reason_id);

CREATE INDEX idx_recommendation_feedback_run_id
  ON recommendation_feedback (recommendation_run_id);

CREATE INDEX idx_recommendation_feedback_request_id
  ON recommendation_feedback (recommendation_request_id);

CREATE INDEX idx_recommendation_feedback_submitted
  ON recommendation_feedback (submitted_at DESC);

CREATE INDEX idx_recommendation_feedback_type_submitted
  ON recommendation_feedback (feedback_type, submitted_at DESC);

CREATE INDEX idx_recommendation_feedback_target_submitted
  ON recommendation_feedback (feedback_target_type, submitted_at DESC);

CREATE INDEX idx_recommendation_feedback_item_id
  ON recommendation_feedback (item_id);
-- <<< END d07_online_recommendation.sql

-- >>> BEGIN d08_user_meaning.sql
-- D08: User meaning estimation tables
-- change_id: d08_user_meaning
-- Issue: #605
-- 正本: docs/06_実装設計/database/*_テーブル定義書.md（D08 対象 3 件）
-- 適用順: D01〜D07 適用後。user_semantic → user_feature → user_meaning
-- LOGICAL 参照: semantic_config_version / feature_definition / feature_normalization_version
-- user_feature → user_semantic の生成順序依存はアプリ層制約（物理 FK なし）

-- =============================================================================
-- 1. user_semantic
-- =============================================================================
CREATE TABLE user_semantic (
  user_semantic_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_run_id uuid NOT NULL,
  semantic_config_version_id uuid NOT NULL,
  extracted_semantic_json jsonb NOT NULL,
  generated_at timestamptz NOT NULL,
  CONSTRAINT uq_user_semantic_recommendation_run_id
    UNIQUE (recommendation_run_id),
  CONSTRAINT fk_user_semantic_recommendation_run_id
    FOREIGN KEY (recommendation_run_id)
    REFERENCES recommendation_run (recommendation_run_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_extracted_semantic_json_object CHECK (
    jsonb_typeof(extracted_semantic_json) = 'object'
  ),
  CONSTRAINT chk_extracted_semantic_json_concepts_array CHECK (
    jsonb_typeof(extracted_semantic_json -> 'concepts') = 'array'
  )
);

CREATE INDEX idx_user_semantic_version_id
  ON user_semantic (semantic_config_version_id);

CREATE INDEX idx_user_semantic_generated_at
  ON user_semantic (generated_at DESC);

-- =============================================================================
-- 2. user_feature
-- =============================================================================
CREATE TABLE user_feature (
  user_feature_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_run_id uuid NOT NULL,
  feature_code text NOT NULL,
  feature_normalization_version_id uuid NOT NULL,
  feature_value numeric(8, 6) NOT NULL,
  source_type text NOT NULL DEFAULT 'aggregated',
  generated_at timestamptz NOT NULL,
  CONSTRAINT uq_user_feature_per_run_axis
    UNIQUE (recommendation_run_id, feature_code),
  CONSTRAINT fk_user_feature_recommendation_run_id
    FOREIGN KEY (recommendation_run_id)
    REFERENCES recommendation_run (recommendation_run_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_user_feature_code_mvp CHECK (
    feature_code IN (
      'formality', 'safety', 'brand_appropriateness',
      'emotion', 'novelty', 'intimacy', 'symbolic_identity', 'story_richness'
    )
  ),
  CONSTRAINT chk_user_feature_value_range CHECK (
    feature_value >= 0.0 AND feature_value <= 1.0
  ),
  CONSTRAINT chk_user_feature_source_type_mvp CHECK (
    source_type = 'aggregated'
  )
);

CREATE INDEX idx_user_feature_lookup
  ON user_feature (recommendation_run_id, feature_code);

CREATE INDEX idx_user_feature_run_id
  ON user_feature (recommendation_run_id);

-- =============================================================================
-- 3. user_meaning
-- =============================================================================
CREATE TABLE user_meaning (
  user_meaning_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_run_id uuid NOT NULL,
  feature_normalization_version_id uuid NOT NULL,
  user_social numeric(6, 4) NOT NULL,
  user_symbolic numeric(6, 4) NOT NULL,
  lambda_ctx numeric(6, 4) NOT NULL,
  generated_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_user_meaning_recommendation_run
    UNIQUE (recommendation_run_id),
  CONSTRAINT fk_user_meaning_recommendation_run_id
    FOREIGN KEY (recommendation_run_id)
    REFERENCES recommendation_run (recommendation_run_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_user_meaning_social_range CHECK (
    user_social >= 0.0 AND user_social <= 1.0
  ),
  CONSTRAINT chk_user_meaning_symbolic_range CHECK (
    user_symbolic >= 0.0 AND user_symbolic <= 1.0
  ),
  CONSTRAINT chk_user_meaning_lambda_ctx_range CHECK (
    lambda_ctx >= 0.0 AND lambda_ctx <= 1.0
  )
);

CREATE INDEX idx_user_meaning_run
  ON user_meaning (recommendation_run_id);
-- <<< END d08_user_meaning.sql

-- >>> BEGIN d09_evaluation.sql
-- D09: Evaluation tables (MVP partial)
-- change_id: d09_evaluation
-- Issue: #606
-- 正本: docs/06_実装設計/database/*_テーブル定義書.md（D09 対象 5 件）
-- 適用順: D01〜D08 適用後。
--   evaluation_dataset → evaluation_case → evaluation_run
--   → evaluation_result → evaluation_metric
-- LOGICAL 参照: recommendation_request_id / recommendation_result_id /
--   batch_run_id / semantic_config_version_id / model_version_id / ranking_config_id

-- =============================================================================
-- 1. evaluation_dataset
-- =============================================================================
CREATE TABLE evaluation_dataset (
  evaluation_dataset_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_name text NOT NULL,
  dataset_description text,
  dataset_version varchar(50) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_evaluation_dataset_name_version
    UNIQUE (dataset_name, dataset_version),
  CONSTRAINT chk_dataset_name_format CHECK (
    dataset_name ~ '^[a-z][a-z0-9_]*$'
  ),
  CONSTRAINT chk_dataset_version_format CHECK (
    dataset_version ~ '^v[0-9]+\.[0-9]+\.[0-9]+$'
  ),
  CONSTRAINT chk_dataset_description_length CHECK (
    dataset_description IS NULL
    OR char_length(dataset_description) <= 500
  )
);

CREATE INDEX idx_evaluation_dataset_active_name
  ON evaluation_dataset (is_active, dataset_name);

CREATE INDEX idx_evaluation_dataset_created_at
  ON evaluation_dataset (created_at DESC);

-- =============================================================================
-- 2. evaluation_case
-- =============================================================================
CREATE TABLE evaluation_case (
  evaluation_case_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evaluation_dataset_id uuid NOT NULL,
  case_label varchar(100) NOT NULL,
  input_condition_json jsonb NOT NULL,
  expected_result_json jsonb,
  recommendation_request_id uuid,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_evaluation_case_dataset_label
    UNIQUE (evaluation_dataset_id, case_label),
  CONSTRAINT fk_evaluation_case_dataset
    FOREIGN KEY (evaluation_dataset_id)
    REFERENCES evaluation_dataset (evaluation_dataset_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_case_label_format CHECK (
    case_label ~ '^[a-z][a-z0-9_]*$'
  ),
  CONSTRAINT chk_input_condition_not_empty CHECK (
    input_condition_json <> '{}'::jsonb
  )
);

CREATE INDEX idx_evaluation_case_dataset_id
  ON evaluation_case (evaluation_dataset_id);

CREATE INDEX idx_evaluation_case_dataset_active
  ON evaluation_case (evaluation_dataset_id)
  WHERE is_active = true;

CREATE INDEX idx_evaluation_case_request_id
  ON evaluation_case (recommendation_request_id);

CREATE INDEX idx_evaluation_case_created_at
  ON evaluation_case (created_at DESC);

-- =============================================================================
-- 3. evaluation_run
-- =============================================================================
CREATE TABLE evaluation_run (
  evaluation_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evaluation_dataset_id uuid NOT NULL,
  batch_run_id uuid,
  semantic_config_version_id uuid NOT NULL,
  model_version_id uuid NOT NULL,
  ranking_config_id uuid NOT NULL,
  evaluation_status varchar(32) NOT NULL DEFAULT 'queued',
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT fk_evaluation_run_dataset
    FOREIGN KEY (evaluation_dataset_id)
    REFERENCES evaluation_dataset (evaluation_dataset_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_evaluation_status CHECK (
    evaluation_status IN (
      'queued', 'running', 'succeeded', 'failed', 'canceled'
    )
  ),
  CONSTRAINT chk_eval_started_before_completed CHECK (
    completed_at IS NULL
    OR started_at IS NULL
    OR started_at <= completed_at
  ),
  CONSTRAINT chk_eval_completed_terminal CHECK (
    evaluation_status NOT IN ('succeeded', 'failed', 'canceled')
    OR completed_at IS NOT NULL
  ),
  CONSTRAINT chk_eval_nonterminal_no_completed CHECK (
    evaluation_status NOT IN ('queued', 'running')
    OR completed_at IS NULL
  )
);

CREATE INDEX idx_evaluation_run_dataset_id
  ON evaluation_run (evaluation_dataset_id);

CREATE INDEX idx_evaluation_run_status
  ON evaluation_run (evaluation_status, started_at);

CREATE INDEX idx_evaluation_run_batch_run_id
  ON evaluation_run (batch_run_id);

CREATE INDEX idx_evaluation_run_semantic_config_version
  ON evaluation_run (semantic_config_version_id);

CREATE INDEX idx_evaluation_run_model_version
  ON evaluation_run (model_version_id);

CREATE INDEX idx_evaluation_run_ranking_config
  ON evaluation_run (ranking_config_id);

CREATE INDEX idx_evaluation_run_created
  ON evaluation_run (created_at DESC);

-- =============================================================================
-- 4. evaluation_result
-- =============================================================================
CREATE TABLE evaluation_result (
  evaluation_result_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evaluation_run_id uuid NOT NULL,
  evaluation_case_id uuid NOT NULL,
  evaluation_dataset_id uuid NOT NULL,
  recommendation_result_id uuid,
  executed_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_evaluation_result_run_case
    UNIQUE (evaluation_run_id, evaluation_case_id),
  CONSTRAINT fk_evaluation_result_run
    FOREIGN KEY (evaluation_run_id)
    REFERENCES evaluation_run (evaluation_run_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_evaluation_result_case
    FOREIGN KEY (evaluation_case_id)
    REFERENCES evaluation_case (evaluation_case_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_evaluation_result_dataset
    FOREIGN KEY (evaluation_dataset_id)
    REFERENCES evaluation_dataset (evaluation_dataset_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_executed_at_not_future CHECK (
    executed_at <= now() + interval '5 minutes'
  )
);

CREATE INDEX idx_evaluation_result_run_id
  ON evaluation_result (evaluation_run_id);

CREATE INDEX idx_evaluation_result_case_id
  ON evaluation_result (evaluation_case_id);

CREATE INDEX idx_evaluation_result_dataset_id
  ON evaluation_result (evaluation_dataset_id);

CREATE INDEX idx_evaluation_result_recommendation_result_id
  ON evaluation_result (recommendation_result_id);

CREATE INDEX idx_evaluation_result_executed_at
  ON evaluation_result (executed_at DESC);

CREATE INDEX idx_evaluation_result_created_at
  ON evaluation_result (created_at DESC);

-- =============================================================================
-- 5. evaluation_metric
-- =============================================================================
CREATE TABLE evaluation_metric (
  evaluation_metric_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evaluation_result_id uuid NOT NULL,
  metric_name varchar(64) NOT NULL,
  metric_value numeric(12, 6) NOT NULL,
  metric_detail_json jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_evaluation_metric_result_name
    UNIQUE (evaluation_result_id, metric_name),
  CONSTRAINT fk_evaluation_metric_result
    FOREIGN KEY (evaluation_result_id)
    REFERENCES evaluation_result (evaluation_result_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_metric_name_not_empty CHECK (
    length(trim(metric_name)) > 0
  )
);

CREATE INDEX idx_evaluation_metric_result_id
  ON evaluation_metric (evaluation_result_id);

CREATE INDEX idx_evaluation_metric_name
  ON evaluation_metric (metric_name);

CREATE INDEX idx_evaluation_metric_created_at
  ON evaluation_metric (created_at DESC);
-- <<< END d09_evaluation.sql

-- >>> BEGIN d10_log_observability.sql
-- D10: Log / Observability tables
-- change_id: d10_log_observability
-- Issue: #607
-- 正本: docs/06_実装設計/database/*_テーブル定義書.md（D10 対象 3 件）
-- 適用順: D01〜D09 適用後。
--   batch_run_log → phase_log → error_log
-- LOGICAL 参照: polymorphic owner_type / owner_id、下流 batch_run_id 被参照

-- =============================================================================
-- 1. batch_run_log
-- =============================================================================
CREATE TABLE batch_run_log (
  batch_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  trace_id text,
  batch_name text NOT NULL,
  batch_type varchar(32),
  run_status varchar(32) NOT NULL DEFAULT 'queued',
  started_at timestamptz NOT NULL,
  completed_at timestamptz,
  duration_ms integer,
  success_count integer NOT NULL DEFAULT 0,
  failed_count integer NOT NULL DEFAULT 0,
  skipped_count integer NOT NULL DEFAULT 0,
  error_summary text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chk_batch_run_log_status CHECK (
    run_status IN (
      'queued',
      'running',
      'succeeded',
      'partially_succeeded',
      'failed',
      'canceled'
    )
  ),
  CONSTRAINT chk_batch_run_log_counts_nonneg CHECK (
    success_count >= 0
    AND failed_count >= 0
    AND skipped_count >= 0
  ),
  CONSTRAINT chk_batch_run_log_duration_nonneg CHECK (
    duration_ms IS NULL OR duration_ms >= 0
  ),
  CONSTRAINT chk_batch_run_log_completed_terminal CHECK (
    run_status NOT IN (
      'succeeded',
      'partially_succeeded',
      'failed',
      'canceled'
    )
    OR completed_at IS NOT NULL
  ),
  CONSTRAINT chk_batch_run_log_nonterminal_no_completed CHECK (
    run_status NOT IN ('queued', 'running')
    OR completed_at IS NULL
  ),
  CONSTRAINT chk_batch_run_log_batch_type CHECK (
    batch_type IS NULL
    OR batch_type IN (
      'external_fetch',
      'staging',
      'import',
      'feature_generation',
      'summary',
      'maintenance'
    )
  )
);

CREATE INDEX idx_batch_run_log_status
  ON batch_run_log (run_status, started_at DESC);

CREATE INDEX idx_batch_run_log_name
  ON batch_run_log (batch_name, started_at DESC);

CREATE INDEX idx_batch_run_log_trace
  ON batch_run_log (trace_id);

-- =============================================================================
-- 2. phase_log
-- =============================================================================
CREATE TABLE phase_log (
  phase_log_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  trace_id text,
  owner_type varchar(32) NOT NULL,
  owner_id uuid NOT NULL,
  phase_name varchar(64) NOT NULL,
  phase_status varchar(32) NOT NULL DEFAULT 'started',
  started_at timestamptz NOT NULL,
  completed_at timestamptz,
  duration_ms integer,
  error_code varchar(64),
  detail_json jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chk_phase_log_owner_type CHECK (
    owner_type IN (
      'recommendation_run',
      'batch_run',
      'evaluation_run'
    )
  ),
  CONSTRAINT chk_phase_log_status CHECK (
    phase_status IN ('started', 'succeeded', 'failed', 'skipped')
  ),
  CONSTRAINT chk_phase_log_phase_name_run CHECK (
    owner_type <> 'recommendation_run'
    OR phase_name IN (
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
    )
  ),
  CONSTRAINT chk_phase_log_phase_name_batch CHECK (
    owner_type <> 'batch_run'
    OR phase_name IN (
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
    )
  ),
  CONSTRAINT chk_phase_log_duration_nonneg CHECK (
    duration_ms IS NULL OR duration_ms >= 0
  ),
  CONSTRAINT chk_phase_log_completed_terminal CHECK (
    phase_status NOT IN ('succeeded', 'failed', 'skipped')
    OR completed_at IS NOT NULL
  ),
  CONSTRAINT chk_phase_log_nonterminal_no_completed CHECK (
    phase_status <> 'started'
    OR completed_at IS NULL
  )
);

CREATE INDEX idx_phase_log_owner
  ON phase_log (owner_type, owner_id, started_at);

CREATE INDEX idx_phase_log_trace
  ON phase_log (trace_id);

CREATE INDEX idx_phase_log_status
  ON phase_log (phase_status, started_at);

CREATE INDEX idx_phase_log_phase_name
  ON phase_log (owner_type, phase_name, started_at);

CREATE INDEX idx_phase_log_created
  ON phase_log (created_at);

-- =============================================================================
-- 3. error_log
-- =============================================================================
CREATE TABLE error_log (
  error_log_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  trace_id text,
  request_id text,
  owner_type varchar(64) NOT NULL,
  owner_id uuid,
  service varchar(16) NOT NULL,
  error_code varchar(64) NOT NULL,
  error_message text NOT NULL,
  severity varchar(16) NOT NULL DEFAULT 'error',
  retryable boolean NOT NULL DEFAULT false,
  error_detail_json jsonb NOT NULL DEFAULT '{}',
  occurred_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chk_error_log_owner_type CHECK (
    owner_type IN (
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
    )
  ),
  CONSTRAINT chk_error_log_owner_id_system CHECK (
    owner_type <> 'system' OR owner_id IS NULL
  ),
  CONSTRAINT chk_error_log_owner_id_required CHECK (
    owner_type = 'system' OR owner_id IS NOT NULL
  ),
  CONSTRAINT chk_error_log_service CHECK (
    service IN ('api', 'reco', 'batch')
  ),
  CONSTRAINT chk_error_log_severity CHECK (
    severity IN ('warn', 'error', 'critical')
  ),
  CONSTRAINT chk_error_log_error_code_format CHECK (
    error_code ~ '^GRS-[A-Z]{3}-[0-9]{3}$'
  )
);

CREATE INDEX idx_error_log_owner
  ON error_log (owner_type, owner_id, occurred_at);

CREATE INDEX idx_error_log_trace
  ON error_log (trace_id);

CREATE INDEX idx_error_log_code
  ON error_log (error_code, occurred_at);

CREATE INDEX idx_error_log_occurred
  ON error_log (occurred_at);

CREATE INDEX idx_error_log_service
  ON error_log (service, occurred_at);
-- <<< END d10_log_observability.sql

-- >>> BEGIN d11_metric.sql
-- D11: Metric / Distribution tables
-- change_id: d11_metric
-- Issue: #608
-- 正本: docs/06_実装設計/database/*_テーブル定義書.md（D11 対象 4 件）
-- 適用順: D01〜D10 適用後。
--   feature_distribution_metric → meaning_distribution_metric
--   → normalization_distribution_metric → reco_score_distribution_metric
-- LOGICAL 参照: batch_run_log / feature_definition / item_feature / item_meaning /
--   user_meaning / feature_normalization_version / recommendation_run /
--   recommendation_result / ranking_config（物理 FK は D12 委譲）

-- =============================================================================
-- 1. feature_distribution_metric
-- =============================================================================
CREATE TABLE feature_distribution_metric (
  feature_distribution_metric_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_run_id uuid,
  semantic_config_version_id uuid NOT NULL,
  feature_normalization_version_id uuid,
  feature_code text NOT NULL,
  aggregation_scope varchar(32) NOT NULL DEFAULT 'batch_run',
  aggregation_key varchar(128),
  entity_type varchar(16) NOT NULL DEFAULT 'item',
  value_layer varchar(16) NOT NULL,
  sample_count integer NOT NULL,
  mean numeric(8, 6) NOT NULL,
  stddev numeric(8, 6),
  min_value numeric(8, 6),
  max_value numeric(8, 6),
  p10 numeric(8, 6),
  p50 numeric(8, 6),
  p90 numeric(8, 6),
  near_zero_rate numeric(6, 4),
  near_one_rate numeric(6, 4),
  mid_concentration_rate numeric(6, 4),
  nan_count integer NOT NULL DEFAULT 0,
  out_of_range_count integer NOT NULL DEFAULT 0,
  calculated_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_fdm_snapshot_key UNIQUE NULLS NOT DISTINCT (
    batch_run_id,
    semantic_config_version_id,
    feature_code,
    value_layer,
    aggregation_scope,
    aggregation_key
  ),
  CONSTRAINT chk_fdm_feature_code_mvp CHECK (
    feature_code IN (
      'formality',
      'safety',
      'brand_appropriateness',
      'emotion',
      'novelty',
      'intimacy',
      'symbolic_identity',
      'story_richness'
    )
  ),
  CONSTRAINT chk_fdm_value_layer CHECK (
    value_layer IN ('raw', 'normalized')
  ),
  CONSTRAINT chk_fdm_aggregation_scope CHECK (
    aggregation_scope IN ('batch_run', 'daily', 'semantic_config_version')
  ),
  CONSTRAINT chk_fdm_entity_type_item CHECK (
    entity_type = 'item'
  ),
  CONSTRAINT chk_fdm_batch_run_required CHECK (
    aggregation_scope <> 'batch_run'
    OR batch_run_id IS NOT NULL
  ),
  CONSTRAINT chk_fdm_sample_count_non_negative CHECK (
    sample_count >= 0
  ),
  CONSTRAINT chk_fdm_nan_count_non_negative CHECK (
    nan_count >= 0
    AND out_of_range_count >= 0
  ),
  CONSTRAINT chk_fdm_rate_range CHECK (
    (near_zero_rate IS NULL OR (near_zero_rate >= 0.0 AND near_zero_rate <= 1.0))
    AND (near_one_rate IS NULL OR (near_one_rate >= 0.0 AND near_one_rate <= 1.0))
    AND (
      mid_concentration_rate IS NULL
      OR (mid_concentration_rate >= 0.0 AND mid_concentration_rate <= 1.0)
    )
  ),
  CONSTRAINT chk_fdm_normalized_version_when_layer CHECK (
    value_layer = 'raw'
    OR feature_normalization_version_id IS NOT NULL
  )
);

CREATE UNIQUE INDEX uq_fdm_non_batch_snapshot
  ON feature_distribution_metric (
    aggregation_scope,
    aggregation_key,
    semantic_config_version_id,
    feature_code,
    value_layer
  )
  WHERE aggregation_scope <> 'batch_run';

CREATE INDEX idx_fdm_batch_run_id
  ON feature_distribution_metric (batch_run_id);

CREATE INDEX idx_fdm_version_feature
  ON feature_distribution_metric (
    semantic_config_version_id,
    feature_code,
    value_layer
  );

CREATE INDEX idx_fdm_calculated_at
  ON feature_distribution_metric (calculated_at);

CREATE INDEX idx_fdm_scope_key
  ON feature_distribution_metric (aggregation_scope, aggregation_key);

-- =============================================================================
-- 2. meaning_distribution_metric
-- =============================================================================
CREATE TABLE meaning_distribution_metric (
  meaning_distribution_metric_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_run_id uuid,
  semantic_config_version_id uuid NOT NULL,
  feature_normalization_version_id uuid NOT NULL,
  entity_type varchar(16) NOT NULL,
  value_layer varchar(16) NOT NULL,
  aggregation_scope varchar(32) NOT NULL DEFAULT 'batch_run',
  aggregation_key varchar(128),
  sample_count integer NOT NULL,
  mean numeric(8, 6) NOT NULL,
  stddev numeric(8, 6),
  min_value numeric(8, 6),
  max_value numeric(8, 6),
  p10 numeric(8, 6),
  p50 numeric(8, 6),
  p90 numeric(8, 6),
  near_zero_rate numeric(6, 4),
  near_one_rate numeric(6, 4),
  mid_concentration_rate numeric(6, 4),
  nan_count integer NOT NULL DEFAULT 0,
  out_of_range_count integer NOT NULL DEFAULT 0,
  calculated_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_mdm_snapshot_key UNIQUE NULLS NOT DISTINCT (
    batch_run_id,
    semantic_config_version_id,
    entity_type,
    value_layer,
    feature_normalization_version_id,
    aggregation_scope,
    aggregation_key
  ),
  CONSTRAINT chk_mdm_entity_type CHECK (
    entity_type IN ('item', 'user')
  ),
  CONSTRAINT chk_mdm_value_layer CHECK (
    value_layer IN ('social', 'symbolic', 'lambda_ctx')
  ),
  CONSTRAINT chk_mdm_lambda_ctx_user_only CHECK (
    value_layer <> 'lambda_ctx'
    OR entity_type = 'user'
  ),
  CONSTRAINT chk_mdm_item_layers CHECK (
    entity_type <> 'item'
    OR value_layer IN ('social', 'symbolic')
  ),
  CONSTRAINT chk_mdm_aggregation_scope CHECK (
    aggregation_scope IN ('batch_run', 'daily', 'semantic_config_version')
  ),
  CONSTRAINT chk_mdm_batch_run_required CHECK (
    aggregation_scope <> 'batch_run'
    OR batch_run_id IS NOT NULL
  ),
  CONSTRAINT chk_mdm_sample_count_non_negative CHECK (
    sample_count >= 0
  ),
  CONSTRAINT chk_mdm_nan_count_non_negative CHECK (
    nan_count >= 0
    AND out_of_range_count >= 0
  ),
  CONSTRAINT chk_mdm_rate_range CHECK (
    (near_zero_rate IS NULL OR (near_zero_rate >= 0.0 AND near_zero_rate <= 1.0))
    AND (near_one_rate IS NULL OR (near_one_rate >= 0.0 AND near_one_rate <= 1.0))
    AND (
      mid_concentration_rate IS NULL
      OR (mid_concentration_rate >= 0.0 AND mid_concentration_rate <= 1.0)
    )
  ),
  CONSTRAINT chk_mdm_normalization_version_required CHECK (
    feature_normalization_version_id IS NOT NULL
  )
);

CREATE UNIQUE INDEX uq_mdm_non_batch_snapshot
  ON meaning_distribution_metric (
    aggregation_scope,
    aggregation_key,
    semantic_config_version_id,
    entity_type,
    value_layer,
    feature_normalization_version_id
  )
  WHERE aggregation_scope <> 'batch_run';

CREATE INDEX idx_mdm_batch_run_id
  ON meaning_distribution_metric (batch_run_id);

CREATE INDEX idx_mdm_version_entity_layer
  ON meaning_distribution_metric (
    semantic_config_version_id,
    entity_type,
    value_layer
  );

CREATE INDEX idx_mdm_calculated_at
  ON meaning_distribution_metric (calculated_at);

CREATE INDEX idx_mdm_scope_key
  ON meaning_distribution_metric (aggregation_scope, aggregation_key);

-- =============================================================================
-- 3. normalization_distribution_metric
-- =============================================================================
CREATE TABLE normalization_distribution_metric (
  normalization_distribution_metric_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_run_id uuid,
  semantic_config_version_id uuid NOT NULL,
  feature_normalization_version_id uuid NOT NULL,
  feature_code text NOT NULL,
  value_layer varchar(16) NOT NULL,
  aggregation_scope varchar(32) NOT NULL DEFAULT 'batch_run',
  aggregation_key varchar(128),
  entity_type varchar(16) NOT NULL DEFAULT 'item',
  sample_count integer NOT NULL,
  mean numeric(8, 6) NOT NULL,
  stddev numeric(8, 6),
  min_value numeric(8, 6),
  max_value numeric(8, 6),
  p10 numeric(8, 6),
  p50 numeric(8, 6),
  p90 numeric(8, 6),
  near_zero_rate numeric(6, 4),
  near_one_rate numeric(6, 4),
  mid_concentration_rate numeric(6, 4),
  nan_count integer NOT NULL DEFAULT 0,
  sigma_zero_count integer NOT NULL DEFAULT 0,
  out_of_range_count integer NOT NULL DEFAULT 0,
  calculated_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_ndm_snapshot_key UNIQUE NULLS NOT DISTINCT (
    batch_run_id,
    semantic_config_version_id,
    feature_code,
    value_layer,
    feature_normalization_version_id,
    aggregation_scope,
    aggregation_key
  ),
  CONSTRAINT chk_ndm_feature_code_mvp CHECK (
    feature_code IN (
      'formality',
      'safety',
      'brand_appropriateness',
      'emotion',
      'novelty',
      'intimacy',
      'symbolic_identity',
      'story_richness'
    )
  ),
  CONSTRAINT chk_ndm_value_layer CHECK (
    value_layer IN ('raw', 'sigmoid')
  ),
  CONSTRAINT chk_ndm_aggregation_scope CHECK (
    aggregation_scope IN ('batch_run', 'daily', 'semantic_config_version')
  ),
  CONSTRAINT chk_ndm_entity_type_item CHECK (
    entity_type = 'item'
  ),
  CONSTRAINT chk_ndm_batch_run_required CHECK (
    aggregation_scope <> 'batch_run'
    OR batch_run_id IS NOT NULL
  ),
  CONSTRAINT chk_ndm_sample_count_non_negative CHECK (
    sample_count >= 0
  ),
  CONSTRAINT chk_ndm_count_non_negative CHECK (
    nan_count >= 0
    AND sigma_zero_count >= 0
    AND out_of_range_count >= 0
  ),
  CONSTRAINT chk_ndm_rate_range CHECK (
    (near_zero_rate IS NULL OR (near_zero_rate >= 0.0 AND near_zero_rate <= 1.0))
    AND (near_one_rate IS NULL OR (near_one_rate >= 0.0 AND near_one_rate <= 1.0))
    AND (
      mid_concentration_rate IS NULL
      OR (mid_concentration_rate >= 0.0 AND mid_concentration_rate <= 1.0)
    )
  ),
  CONSTRAINT chk_ndm_normalization_version_required CHECK (
    feature_normalization_version_id IS NOT NULL
  )
);

CREATE UNIQUE INDEX uq_ndm_non_batch_snapshot
  ON normalization_distribution_metric (
    aggregation_scope,
    aggregation_key,
    semantic_config_version_id,
    feature_code,
    value_layer,
    feature_normalization_version_id
  )
  WHERE aggregation_scope <> 'batch_run';

CREATE INDEX idx_ndm_batch_run_id
  ON normalization_distribution_metric (batch_run_id);

CREATE INDEX idx_ndm_version_feature_layer
  ON normalization_distribution_metric (
    semantic_config_version_id,
    feature_code,
    value_layer
  );

CREATE INDEX idx_ndm_norm_version
  ON normalization_distribution_metric (
    feature_normalization_version_id,
    calculated_at DESC
  );

CREATE INDEX idx_ndm_calculated_at
  ON normalization_distribution_metric (calculated_at);

CREATE INDEX idx_ndm_scope_key
  ON normalization_distribution_metric (aggregation_scope, aggregation_key);

-- =============================================================================
-- 4. reco_score_distribution_metric
-- =============================================================================
CREATE TABLE reco_score_distribution_metric (
  reco_score_distribution_metric_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_run_id uuid,
  recommendation_result_id uuid,
  batch_run_id uuid,
  semantic_config_version_id uuid NOT NULL,
  ranking_config_id uuid NOT NULL,
  score_type varchar(32) NOT NULL,
  aggregation_scope varchar(32) NOT NULL DEFAULT 'run',
  aggregation_key varchar(128),
  sample_count integer NOT NULL,
  mean numeric(8, 6) NOT NULL,
  stddev numeric(8, 6),
  min_value numeric(8, 6),
  max_value numeric(8, 6),
  p10 numeric(8, 6),
  p50 numeric(8, 6),
  p90 numeric(8, 6),
  near_zero_rate numeric(6, 4),
  near_one_rate numeric(6, 4),
  mid_concentration_rate numeric(6, 4),
  nan_count integer NOT NULL DEFAULT 0,
  out_of_range_count integer NOT NULL DEFAULT 0,
  calculated_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_rsdm_run_snapshot_key UNIQUE NULLS NOT DISTINCT (
    recommendation_run_id,
    recommendation_result_id,
    score_type,
    aggregation_scope,
    aggregation_key
  ),
  CONSTRAINT chk_rsdm_score_type CHECK (
    score_type IN ('context_score', 'final_score')
  ),
  CONSTRAINT chk_rsdm_aggregation_scope CHECK (
    aggregation_scope IN ('run')
  ),
  CONSTRAINT chk_rsdm_run_required CHECK (
    aggregation_scope <> 'run'
    OR recommendation_run_id IS NOT NULL
  ),
  CONSTRAINT chk_rsdm_result_required CHECK (
    aggregation_scope <> 'run'
    OR recommendation_result_id IS NOT NULL
  ),
  CONSTRAINT chk_rsdm_batch_run_null_mvp CHECK (
    batch_run_id IS NULL
  ),
  CONSTRAINT chk_rsdm_sample_count_positive CHECK (
    sample_count >= 1
  ),
  CONSTRAINT chk_rsdm_nan_count_non_negative CHECK (
    nan_count >= 0
    AND out_of_range_count >= 0
  ),
  CONSTRAINT chk_rsdm_rate_range CHECK (
    (near_zero_rate IS NULL OR (near_zero_rate >= 0.0 AND near_zero_rate <= 1.0))
    AND (near_one_rate IS NULL OR (near_one_rate >= 0.0 AND near_one_rate <= 1.0))
    AND (
      mid_concentration_rate IS NULL
      OR (mid_concentration_rate >= 0.0 AND mid_concentration_rate <= 1.0)
    )
  ),
  CONSTRAINT chk_rsdm_score_value_range CHECK (
    mean >= 0.0 AND mean <= 1.0
    AND (min_value IS NULL OR (min_value >= 0.0 AND min_value <= 1.0))
    AND (max_value IS NULL OR (max_value >= 0.0 AND max_value <= 1.0))
    AND (p10 IS NULL OR (p10 >= 0.0 AND p10 <= 1.0))
    AND (p50 IS NULL OR (p50 >= 0.0 AND p50 <= 1.0))
    AND (p90 IS NULL OR (p90 >= 0.0 AND p90 <= 1.0))
    AND (stddev IS NULL OR stddev >= 0.0)
  )
);

CREATE INDEX idx_rsdm_recommendation_run_id
  ON reco_score_distribution_metric (recommendation_run_id);

CREATE INDEX idx_rsdm_recommendation_result_id
  ON reco_score_distribution_metric (recommendation_result_id);

CREATE INDEX idx_rsdm_version_score
  ON reco_score_distribution_metric (
    semantic_config_version_id,
    ranking_config_id,
    score_type
  );

CREATE INDEX idx_rsdm_calculated_at
  ON reco_score_distribution_metric (calculated_at);
-- <<< END d11_metric.sql

-- >>> BEGIN d12_deferred_fk_indexes.sql
-- D12: Deferred foreign keys and follow-up indexes
-- change_id: d12_deferred_fk_indexes
-- Issue: #609
-- 正本: docs/06_実装設計/database/物理ER.md §9・§11、各テーブル定義書 §8〜§10
-- 適用順: D01〜D11 適用後。
-- 延期 FK 棚卸し（D02〜D11 DDL コメント）:
--   normalization_rule.feature_normalization_version_id → feature_normalization_version（D02/D03）
--   Metric 4 テーブル.semantic_config_version_id → semantic_config_version（D11）
-- 索引: item_embedding HNSW（idx_item_embedding_vector）は D06 作成済みのため本ファイルでは追加しない

-- =============================================================================
-- 1. normalization_rule → feature_normalization_version
-- =============================================================================
ALTER TABLE normalization_rule
  ADD CONSTRAINT fk_normalization_rule_feature_normalization_version
  FOREIGN KEY (feature_normalization_version_id)
  REFERENCES feature_normalization_version (feature_normalization_version_id)
  ON DELETE RESTRICT;

-- =============================================================================
-- 2. feature_distribution_metric → semantic_config_version
-- =============================================================================
ALTER TABLE feature_distribution_metric
  ADD CONSTRAINT fk_fdm_semantic_config_version_id
  FOREIGN KEY (semantic_config_version_id)
  REFERENCES semantic_config_version (semantic_config_version_id)
  ON DELETE RESTRICT;

-- =============================================================================
-- 3. meaning_distribution_metric → semantic_config_version
-- =============================================================================
ALTER TABLE meaning_distribution_metric
  ADD CONSTRAINT fk_mdm_semantic_config_version_id
  FOREIGN KEY (semantic_config_version_id)
  REFERENCES semantic_config_version (semantic_config_version_id)
  ON DELETE RESTRICT;

-- =============================================================================
-- 4. normalization_distribution_metric → semantic_config_version
-- =============================================================================
ALTER TABLE normalization_distribution_metric
  ADD CONSTRAINT fk_ndm_semantic_config_version_id
  FOREIGN KEY (semantic_config_version_id)
  REFERENCES semantic_config_version (semantic_config_version_id)
  ON DELETE RESTRICT;

-- =============================================================================
-- 5. reco_score_distribution_metric → semantic_config_version
-- =============================================================================
ALTER TABLE reco_score_distribution_metric
  ADD CONSTRAINT fk_rsdm_semantic_config_version_id
  FOREIGN KEY (semantic_config_version_id)
  REFERENCES semantic_config_version (semantic_config_version_id)
  ON DELETE RESTRICT;
-- <<< END d12_deferred_fk_indexes.sql
