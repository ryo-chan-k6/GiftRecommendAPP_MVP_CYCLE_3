-- D14: matching_config + Run reproducibility columns
-- change_id: d14_matching_config
-- Issue: #906
-- 正本: docs/06_実装設計/database/matching_config_テーブル定義書.md
-- 適用順: D01〜D13 適用後の増分 migration

-- =============================================================================
-- 1. matching_config
-- =============================================================================
CREATE TABLE matching_config (
  matching_config_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  config_name text NOT NULL,
  config_version text NOT NULL,
  parameter_json jsonb NOT NULL,
  is_current boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_matching_config_name_version
    UNIQUE (config_name, config_version),
  CONSTRAINT chk_matching_config_name_format CHECK (
    config_name ~ '^[a-z][a-z0-9_]*$'
  ),
  CONSTRAINT chk_matching_config_version_format CHECK (
    config_version ~ '^v[0-9]{3,}$'
  ),
  CONSTRAINT chk_matching_parameter_json_object CHECK (
    jsonb_typeof(parameter_json) = 'object'
  ),
  CONSTRAINT chk_social_feature_weights_sum CHECK (
    abs(
      (parameter_json->'social_feature_weights'->>'formality')::numeric
      + (parameter_json->'social_feature_weights'->>'safety')::numeric
      + (parameter_json->'social_feature_weights'->>'brand_appropriateness')::numeric
      - 1.0
    ) <= 0.001
  ),
  CONSTRAINT chk_symbolic_feature_weights_sum CHECK (
    abs(
      (parameter_json->'symbolic_feature_weights'->>'emotion')::numeric
      + (parameter_json->'symbolic_feature_weights'->>'novelty')::numeric
      + (parameter_json->'symbolic_feature_weights'->>'intimacy')::numeric
      + (parameter_json->'symbolic_feature_weights'->>'symbolic_identity')::numeric
      + (parameter_json->'symbolic_feature_weights'->>'story_richness')::numeric
      - 1.0
    ) <= 0.001
  )
);

CREATE UNIQUE INDEX uq_matching_config_current_per_name
  ON matching_config (config_name)
  WHERE is_current = true;

CREATE INDEX idx_matching_config_name_created
  ON matching_config (config_name, created_at DESC);

-- =============================================================================
-- 2. Run 再現性列: recommendation_run.matching_config_id
-- =============================================================================
INSERT INTO matching_config (config_name, config_version, parameter_json, is_current, created_at)
VALUES (
  'mvp_matching_config',
  'v001',
  '{"distance_method": "absolute_distance", "feature_match_method": "one_minus_distance", "social_feature_weights": {"formality": 0.333, "safety": 0.333, "brand_appropriateness": 0.333}, "symbolic_feature_weights": {"emotion": 0.200, "novelty": 0.200, "intimacy": 0.200, "symbolic_identity": 0.200, "story_richness": 0.200}, "context_score_formula": "lambda_ctx_weighted", "avoid_similarity_method": "mvp_default", "threshold_rule": {"strong_match": 0.80, "normal_match": 0.60}}'::jsonb,
  true,
  timestamptz '2026-07-02 12:00:00+00'
)
ON CONFLICT (config_name, config_version) DO NOTHING;

ALTER TABLE recommendation_run
  ADD COLUMN matching_config_id uuid;

UPDATE recommendation_run
SET matching_config_id = (
  SELECT matching_config_id
  FROM matching_config
  WHERE config_name = 'mvp_matching_config'
    AND config_version = 'v001'
  LIMIT 1
);

ALTER TABLE recommendation_run
  ALTER COLUMN matching_config_id SET NOT NULL;

CREATE INDEX idx_recommendation_run_matching_config
  ON recommendation_run (matching_config_id);

-- =============================================================================
-- 3. Run スナップショット列: recommendation_result.matching_config_id
-- =============================================================================
ALTER TABLE recommendation_result
  ADD COLUMN matching_config_id uuid;

UPDATE recommendation_result
SET matching_config_id = (
  SELECT matching_config_id
  FROM matching_config
  WHERE config_name = 'mvp_matching_config'
    AND config_version = 'v001'
  LIMIT 1
);

ALTER TABLE recommendation_result
  ALTER COLUMN matching_config_id SET NOT NULL;

CREATE INDEX idx_recommendation_result_matching_config
  ON recommendation_result (matching_config_id);

-- =============================================================================
-- 4. Evaluation Run: evaluation_run.matching_config_id
-- =============================================================================
ALTER TABLE evaluation_run
  ADD COLUMN matching_config_id uuid;

UPDATE evaluation_run
SET matching_config_id = (
  SELECT matching_config_id
  FROM matching_config
  WHERE config_name = 'mvp_matching_config'
    AND config_version = 'v001'
  LIMIT 1
);

ALTER TABLE evaluation_run
  ALTER COLUMN matching_config_id SET NOT NULL;

CREATE INDEX idx_evaluation_run_matching_config
  ON evaluation_run (matching_config_id);
