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
