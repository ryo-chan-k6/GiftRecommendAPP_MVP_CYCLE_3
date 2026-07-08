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
