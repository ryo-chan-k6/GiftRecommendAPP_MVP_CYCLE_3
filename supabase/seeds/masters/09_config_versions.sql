-- Master seed: model_version / ranking_config / matching_config / feature_normalization_version / normalization_rule

BEGIN;

INSERT INTO model_version (provider, model_name, model_type, version_label, is_current, created_at)
VALUES ('openai', 'text-embedding-3-small', 'embedding', 'v001', true, timestamptz '2026-06-17 12:00:00+00')
ON CONFLICT (provider, model_name, model_type, version_label) DO UPDATE SET is_current = EXCLUDED.is_current;

INSERT INTO model_version (provider, model_name, model_type, version_label, is_current, created_at)
VALUES ('openai', 'gpt-4o-mini', 'llm', 'v001', true, timestamptz '2026-06-17 12:00:00+00')
ON CONFLICT (provider, model_name, model_type, version_label) DO UPDATE SET is_current = EXCLUDED.is_current;

INSERT INTO model_version (provider, model_name, model_type, version_label, is_current, created_at)
VALUES ('internal', 'mvp_ranking_v1', 'ranking', 'v001', true, timestamptz '2026-06-17 12:00:00+00')
ON CONFLICT (provider, model_name, model_type, version_label) DO UPDATE SET is_current = EXCLUDED.is_current;

INSERT INTO ranking_config (config_name, config_version, parameter_json, is_current, created_at)
VALUES (
  'mvp_ranking_config',
  'v001',
  '{"ranking_weights": {"context": 0.70, "popularity": 0.20, "risk": 0.10}, "lambda_mmr": 0.75, "mmr_candidate_limit": 50, "top_k_default": 10, "diversity_method": "mmr"}'::jsonb,
  true,
  timestamptz '2026-06-17 12:00:00+00'
)
ON CONFLICT (config_name, config_version) DO UPDATE SET parameter_json = EXCLUDED.parameter_json, is_current = EXCLUDED.is_current;

INSERT INTO matching_config (config_name, config_version, parameter_json, is_current, created_at)
VALUES (
  'mvp_matching_config',
  'v001',
  '{"distance_method": "absolute_distance", "feature_match_method": "one_minus_distance", "social_feature_weights": {"formality": 0.333, "safety": 0.333, "brand_appropriateness": 0.333}, "symbolic_feature_weights": {"emotion": 0.200, "novelty": 0.200, "intimacy": 0.200, "symbolic_identity": 0.200, "story_richness": 0.200}, "context_score_formula": "lambda_ctx_weighted", "avoid_similarity_method": "mvp_default", "threshold_rule": {"strong_match": 0.80, "normal_match": 0.60}}'::jsonb,
  true,
  timestamptz '2026-07-02 12:00:00+00'
)
ON CONFLICT (config_name, config_version) DO UPDATE SET parameter_json = EXCLUDED.parameter_json, is_current = EXCLUDED.is_current;

UPDATE feature_normalization_version
SET is_current = false
WHERE normalization_method = 'sigmoid' AND is_current = true;

INSERT INTO feature_normalization_version (normalization_method, parameter_json, is_current, generated_at)
SELECT 'sigmoid', '{"center_feature": 0.5, "k_feature": 4.0}'::jsonb, true, timestamptz '2026-06-17 12:00:00+00'
WHERE NOT EXISTS (
  SELECT 1 FROM feature_normalization_version
  WHERE normalization_method = 'sigmoid'
    AND is_current = true
    AND parameter_json = '{"center_feature": 0.5, "k_feature": 4.0}'::jsonb
);

-- normalization_rule: current semantic_config_version と current sigmoid feature_normalization_version の binding
-- ID はハードコードせず SELECT で current 行を解決するため、current が更新された再実行でも binding が追随する。
-- uq_normalization_rule_version (semantic_config_version_id) により version あたり 1 行。既存行は DELETE せず再 binding する。
INSERT INTO normalization_rule (
  semantic_config_version_id,
  normalization_method,
  feature_normalization_version_id,
  is_active
)
SELECT
  scv.semantic_config_version_id,
  'sigmoid',
  fnv.feature_normalization_version_id,
  true
FROM semantic_config_version scv
JOIN semantic_config sc
  ON sc.semantic_config_id = scv.semantic_config_id
JOIN feature_normalization_version fnv
  ON fnv.normalization_method = 'sigmoid'
 AND fnv.is_current = true
WHERE sc.config_name = 'mvp_semantic_config'
  AND sc.is_active = true
  AND scv.is_current = true
ON CONFLICT ON CONSTRAINT uq_normalization_rule_version DO UPDATE
SET normalization_method = EXCLUDED.normalization_method,
    feature_normalization_version_id = EXCLUDED.feature_normalization_version_id,
    is_active = EXCLUDED.is_active;

COMMIT;
