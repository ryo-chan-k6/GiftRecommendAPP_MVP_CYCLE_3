-- Master seed: pair_rule (14 pairs x 8 features)
-- semantic_config_version_id = a1111111-1111-4111-8111-111111111102

BEGIN;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'formality', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'lover' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'safety', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'lover' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'brand_appropriateness', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'lover' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'emotion', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'lover' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'novelty', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'lover' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'intimacy', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'lover' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'symbolic_identity', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'lover' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'story_richness', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'lover' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'formality', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'lover' AND pm.occasion_code = 'anniversary'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'safety', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'lover' AND pm.occasion_code = 'anniversary'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'brand_appropriateness', 0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'lover' AND pm.occasion_code = 'anniversary'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'emotion', 0.150, true
FROM pair_master pm
WHERE pm.relationship_code = 'lover' AND pm.occasion_code = 'anniversary'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'novelty', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'lover' AND pm.occasion_code = 'anniversary'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'intimacy', 0.150, true
FROM pair_master pm
WHERE pm.relationship_code = 'lover' AND pm.occasion_code = 'anniversary'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'symbolic_identity', 0.150, true
FROM pair_master pm
WHERE pm.relationship_code = 'lover' AND pm.occasion_code = 'anniversary'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'story_richness', 0.150, true
FROM pair_master pm
WHERE pm.relationship_code = 'lover' AND pm.occasion_code = 'anniversary'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'formality', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'spouse' AND pm.occasion_code = 'anniversary'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'safety', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'spouse' AND pm.occasion_code = 'anniversary'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'brand_appropriateness', 0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'spouse' AND pm.occasion_code = 'anniversary'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'emotion', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'spouse' AND pm.occasion_code = 'anniversary'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'novelty', 0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'spouse' AND pm.occasion_code = 'anniversary'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'intimacy', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'spouse' AND pm.occasion_code = 'anniversary'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'symbolic_identity', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'spouse' AND pm.occasion_code = 'anniversary'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'story_richness', 0.150, true
FROM pair_master pm
WHERE pm.relationship_code = 'spouse' AND pm.occasion_code = 'anniversary'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'formality', 0.150, true
FROM pair_master pm
WHERE pm.relationship_code = 'boss' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'safety', 0.150, true
FROM pair_master pm
WHERE pm.relationship_code = 'boss' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'brand_appropriateness', 0.150, true
FROM pair_master pm
WHERE pm.relationship_code = 'boss' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'emotion', -0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'boss' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'novelty', -0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'boss' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'intimacy', -0.150, true
FROM pair_master pm
WHERE pm.relationship_code = 'boss' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'symbolic_identity', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'boss' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'story_richness', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'boss' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'formality', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'boss' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'safety', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'boss' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'brand_appropriateness', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'boss' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'emotion', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'boss' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'novelty', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'boss' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'intimacy', -0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'boss' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'symbolic_identity', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'boss' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'story_richness', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'boss' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'formality', 0.150, true
FROM pair_master pm
WHERE pm.relationship_code = 'business_partner' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'safety', 0.150, true
FROM pair_master pm
WHERE pm.relationship_code = 'business_partner' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'brand_appropriateness', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'business_partner' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'emotion', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'business_partner' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'novelty', -0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'business_partner' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'intimacy', -0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'business_partner' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'symbolic_identity', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'business_partner' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'story_richness', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'business_partner' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'formality', 0.200, true
FROM pair_master pm
WHERE pm.relationship_code = 'business_partner' AND pm.occasion_code = 'apology'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'safety', 0.200, true
FROM pair_master pm
WHERE pm.relationship_code = 'business_partner' AND pm.occasion_code = 'apology'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'brand_appropriateness', 0.150, true
FROM pair_master pm
WHERE pm.relationship_code = 'business_partner' AND pm.occasion_code = 'apology'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'emotion', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'business_partner' AND pm.occasion_code = 'apology'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'novelty', -0.200, true
FROM pair_master pm
WHERE pm.relationship_code = 'business_partner' AND pm.occasion_code = 'apology'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'intimacy', -0.150, true
FROM pair_master pm
WHERE pm.relationship_code = 'business_partner' AND pm.occasion_code = 'apology'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'symbolic_identity', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'business_partner' AND pm.occasion_code = 'apology'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'story_richness', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'business_partner' AND pm.occasion_code = 'apology'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'formality', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_close' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'safety', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_close' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'brand_appropriateness', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_close' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'emotion', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_close' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'novelty', 0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_close' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'intimacy', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_close' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'symbolic_identity', 0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_close' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'story_richness', 0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_close' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'formality', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_close' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'safety', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_close' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'brand_appropriateness', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_close' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'emotion', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_close' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'novelty', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_close' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'intimacy', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_close' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'symbolic_identity', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_close' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'story_richness', 0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_close' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'formality', 0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_casual' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'safety', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_casual' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'brand_appropriateness', 0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_casual' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'emotion', 0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_casual' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'novelty', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_casual' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'intimacy', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_casual' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'symbolic_identity', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_casual' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'story_richness', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'friend_casual' AND pm.occasion_code = 'thanks'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'formality', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'colleague' AND pm.occasion_code = 'farewell'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'safety', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'colleague' AND pm.occasion_code = 'farewell'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'brand_appropriateness', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'colleague' AND pm.occasion_code = 'farewell'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'emotion', 0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'colleague' AND pm.occasion_code = 'farewell'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'novelty', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'colleague' AND pm.occasion_code = 'farewell'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'intimacy', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'colleague' AND pm.occasion_code = 'farewell'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'symbolic_identity', 0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'colleague' AND pm.occasion_code = 'farewell'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'story_richness', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'colleague' AND pm.occasion_code = 'farewell'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'formality', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'family_parent' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'safety', 0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'family_parent' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'brand_appropriateness', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'family_parent' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'emotion', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'family_parent' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'novelty', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'family_parent' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'intimacy', 0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'family_parent' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'symbolic_identity', 0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'family_parent' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'story_richness', 0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'family_parent' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'formality', -0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'family_child' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'safety', -0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'family_child' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'brand_appropriateness', -0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'family_child' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'emotion', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'family_child' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'novelty', 0.150, true
FROM pair_master pm
WHERE pm.relationship_code = 'family_child' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'intimacy', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'family_child' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'symbolic_identity', 0.100, true
FROM pair_master pm
WHERE pm.relationship_code = 'family_child' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'story_richness', 0.050, true
FROM pair_master pm
WHERE pm.relationship_code = 'family_child' AND pm.occasion_code = 'birthday'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'formality', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'other' AND pm.occasion_code = 'other'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'safety', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'other' AND pm.occasion_code = 'other'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'brand_appropriateness', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'other' AND pm.occasion_code = 'other'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'emotion', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'other' AND pm.occasion_code = 'other'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'novelty', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'other' AND pm.occasion_code = 'other'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'intimacy', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'other' AND pm.occasion_code = 'other'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'symbolic_identity', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'other' AND pm.occasion_code = 'other'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

INSERT INTO pair_rule (semantic_config_version_id, pair_id, feature_code, feature_delta, is_active)
SELECT 'a1111111-1111-4111-8111-111111111102', pm.pair_id, 'story_richness', 0.000, true
FROM pair_master pm
WHERE pm.relationship_code = 'other' AND pm.occasion_code = 'other'
ON CONFLICT (semantic_config_version_id, pair_id, feature_code) DO UPDATE SET feature_delta = EXCLUDED.feature_delta, is_active = EXCLUDED.is_active;

COMMIT;
