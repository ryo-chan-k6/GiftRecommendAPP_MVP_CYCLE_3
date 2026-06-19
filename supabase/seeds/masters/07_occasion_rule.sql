-- Master seed: occasion_rule (15 x 8)
-- semantic_config_version_id = a1111111-1111-4111-8111-111111111102

BEGIN;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'birthday', 'formality', 0.400, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'birthday', 'safety', 0.550, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'birthday', 'brand_appropriateness', 0.500, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'birthday', 'emotion', 0.750, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'birthday', 'novelty', 0.650, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'birthday', 'intimacy', 0.650, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'birthday', 'symbolic_identity', 0.650, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'birthday', 'story_richness', 0.600, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'anniversary', 'formality', 0.450, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'anniversary', 'safety', 0.500, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'anniversary', 'brand_appropriateness', 0.600, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'anniversary', 'emotion', 0.850, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'anniversary', 'novelty', 0.700, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'anniversary', 'intimacy', 0.850, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'anniversary', 'symbolic_identity', 0.800, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'anniversary', 'story_richness', 0.850, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'thanks', 'formality', 0.550, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'thanks', 'safety', 0.750, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'thanks', 'brand_appropriateness', 0.650, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'thanks', 'emotion', 0.700, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'thanks', 'novelty', 0.350, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'thanks', 'intimacy', 0.450, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'thanks', 'symbolic_identity', 0.500, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'thanks', 'story_richness', 0.450, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'apology', 'formality', 0.750, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'apology', 'safety', 0.900, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'apology', 'brand_appropriateness', 0.750, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'apology', 'emotion', 0.550, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'apology', 'novelty', 0.200, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'apology', 'intimacy', 0.250, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'apology', 'symbolic_identity', 0.350, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'apology', 'story_richness', 0.300, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'celebration_general', 'formality', 0.650, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'celebration_general', 'safety', 0.700, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'celebration_general', 'brand_appropriateness', 0.700, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'celebration_general', 'emotion', 0.650, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'celebration_general', 'novelty', 0.500, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'celebration_general', 'intimacy', 0.450, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'celebration_general', 'symbolic_identity', 0.550, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'celebration_general', 'story_richness', 0.500, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'wedding_gift', 'formality', 0.850, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'wedding_gift', 'safety', 0.850, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'wedding_gift', 'brand_appropriateness', 0.800, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'wedding_gift', 'emotion', 0.750, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'wedding_gift', 'novelty', 0.450, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'wedding_gift', 'intimacy', 0.400, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'wedding_gift', 'symbolic_identity', 0.650, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'wedding_gift', 'story_richness', 0.650, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'baby_gift', 'formality', 0.650, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'baby_gift', 'safety', 0.750, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'baby_gift', 'brand_appropriateness', 0.650, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'baby_gift', 'emotion', 0.750, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'baby_gift', 'novelty', 0.550, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'baby_gift', 'intimacy', 0.550, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'baby_gift', 'symbolic_identity', 0.600, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'baby_gift', 'story_richness', 0.550, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'housewarming', 'formality', 0.650, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'housewarming', 'safety', 0.750, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'housewarming', 'brand_appropriateness', 0.700, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'housewarming', 'emotion', 0.550, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'housewarming', 'novelty', 0.350, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'housewarming', 'intimacy', 0.350, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'housewarming', 'symbolic_identity', 0.450, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'housewarming', 'story_richness', 0.450, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'farewell', 'formality', 0.650, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'farewell', 'safety', 0.800, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'farewell', 'brand_appropriateness', 0.700, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'farewell', 'emotion', 0.650, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'farewell', 'novelty', 0.350, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'farewell', 'intimacy', 0.400, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'farewell', 'symbolic_identity', 0.550, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'farewell', 'story_richness', 0.550, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'get_well', 'formality', 0.650, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'get_well', 'safety', 0.850, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'get_well', 'brand_appropriateness', 0.650, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'get_well', 'emotion', 0.700, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'get_well', 'novelty', 0.200, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'get_well', 'intimacy', 0.350, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'get_well', 'symbolic_identity', 0.450, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'get_well', 'story_richness', 0.400, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'seasonal_event', 'formality', 0.550, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'seasonal_event', 'safety', 0.700, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'seasonal_event', 'brand_appropriateness', 0.600, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'seasonal_event', 'emotion', 0.550, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'seasonal_event', 'novelty', 0.400, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'seasonal_event', 'intimacy', 0.350, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'seasonal_event', 'symbolic_identity', 0.450, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'seasonal_event', 'story_richness', 0.400, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'souvenir', 'formality', 0.550, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'souvenir', 'safety', 0.750, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'souvenir', 'brand_appropriateness', 0.600, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'souvenir', 'emotion', 0.450, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'souvenir', 'novelty', 0.350, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'souvenir', 'intimacy', 0.250, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'souvenir', 'symbolic_identity', 0.400, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'souvenir', 'story_richness', 0.350, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'return_gift', 'formality', 0.750, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'return_gift', 'safety', 0.850, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'return_gift', 'brand_appropriateness', 0.750, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'return_gift', 'emotion', 0.450, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'return_gift', 'novelty', 0.250, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'return_gift', 'intimacy', 0.250, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'return_gift', 'symbolic_identity', 0.350, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'return_gift', 'story_richness', 0.350, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'no_specific_occasion', 'formality', 0.250, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'no_specific_occasion', 'safety', 0.550, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'no_specific_occasion', 'brand_appropriateness', 0.350, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'no_specific_occasion', 'emotion', 0.450, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'no_specific_occasion', 'novelty', 0.450, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'no_specific_occasion', 'intimacy', 0.500, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'no_specific_occasion', 'symbolic_identity', 0.450, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'no_specific_occasion', 'story_richness', 0.350, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'other', 'formality', 0.500, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'other', 'safety', 0.600, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'other', 'brand_appropriateness', 0.500, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'other', 'emotion', 0.500, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'other', 'novelty', 0.400, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'other', 'intimacy', 0.400, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'other', 'symbolic_identity', 0.400, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO occasion_rule (semantic_config_version_id, occasion_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'other', 'story_richness', 0.400, true)
ON CONFLICT (semantic_config_version_id, occasion_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

COMMIT;
