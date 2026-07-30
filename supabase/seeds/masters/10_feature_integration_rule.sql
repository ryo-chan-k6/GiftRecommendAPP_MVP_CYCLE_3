-- Master seed: feature_integration_rule (8 axes x 6 input sources = 48 rows)
-- semantic_config_version_id = a1111111-1111-4111-8111-111111111102
-- Weights: Featureルール定義書 §12.3 / feature_integration_ruleテーブル定義書 §11.1

BEGIN;

WITH feature_codes(feature_code) AS (
  VALUES
    ('formality'),
    ('safety'),
    ('brand_appropriateness'),
    ('emotion'),
    ('novelty'),
    ('intimacy'),
    ('symbolic_identity'),
    ('story_richness')
),
input_weights(input_source, weight) AS (
  VALUES
    ('relationship_feature', 0.500::numeric(4, 3)),
    ('occasion_feature', 0.500::numeric(4, 3)),
    ('pair_delta', 1.000::numeric(4, 3)),
    ('preferred_delta', 1.000::numeric(4, 3)),
    ('avoid_delta', 1.000::numeric(4, 3)),
    ('free_text_delta', 0.700::numeric(4, 3))
)
INSERT INTO feature_integration_rule (
  semantic_config_version_id,
  feature_code,
  input_source,
  weight,
  is_active
)
SELECT
  'a1111111-1111-4111-8111-111111111102'::uuid,
  feature_codes.feature_code,
  input_weights.input_source,
  input_weights.weight,
  true
FROM feature_codes
CROSS JOIN input_weights
ON CONFLICT (semantic_config_version_id, feature_code, input_source)
DO UPDATE SET
  weight = EXCLUDED.weight,
  is_active = EXCLUDED.is_active;

COMMIT;
