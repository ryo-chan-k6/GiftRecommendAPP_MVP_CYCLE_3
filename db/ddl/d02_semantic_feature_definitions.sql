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
