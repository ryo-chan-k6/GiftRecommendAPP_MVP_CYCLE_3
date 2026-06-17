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
