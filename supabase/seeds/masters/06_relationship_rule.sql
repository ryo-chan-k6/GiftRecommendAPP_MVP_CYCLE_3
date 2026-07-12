-- Master seed: relationship_rule (12 x 8)
-- semantic_config_version_id = a1111111-1111-4111-8111-111111111102

BEGIN;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'lover', 'formality', 0.350, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'lover', 'safety', 0.450, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'lover', 'brand_appropriateness', 0.550, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'lover', 'emotion', 0.850, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'lover', 'novelty', 0.650, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'lover', 'intimacy', 0.950, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'lover', 'symbolic_identity', 0.850, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'lover', 'story_richness', 0.750, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'spouse', 'formality', 0.400, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'spouse', 'safety', 0.550, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'spouse', 'brand_appropriateness', 0.550, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'spouse', 'emotion', 0.800, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'spouse', 'novelty', 0.550, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'spouse', 'intimacy', 0.950, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'spouse', 'symbolic_identity', 0.850, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'spouse', 'story_richness', 0.850, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_parent', 'formality', 0.450, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_parent', 'safety', 0.650, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_parent', 'brand_appropriateness', 0.550, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_parent', 'emotion', 0.750, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_parent', 'novelty', 0.450, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_parent', 'intimacy', 0.800, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_parent', 'symbolic_identity', 0.700, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_parent', 'story_richness', 0.650, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_child', 'formality', 0.250, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_child', 'safety', 0.550, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_child', 'brand_appropriateness', 0.350, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_child', 'emotion', 0.800, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_child', 'novelty', 0.650, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_child', 'intimacy', 0.850, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_child', 'symbolic_identity', 0.750, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_child', 'story_richness', 0.700, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_sibling', 'formality', 0.250, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_sibling', 'safety', 0.550, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_sibling', 'brand_appropriateness', 0.350, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_sibling', 'emotion', 0.600, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_sibling', 'novelty', 0.550, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_sibling', 'intimacy', 0.750, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_sibling', 'symbolic_identity', 0.650, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'family_sibling', 'story_richness', 0.550, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'friend_close', 'formality', 0.250, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'friend_close', 'safety', 0.550, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'friend_close', 'brand_appropriateness', 0.350, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'friend_close', 'emotion', 0.650, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'friend_close', 'novelty', 0.600, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'friend_close', 'intimacy', 0.750, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'friend_close', 'symbolic_identity', 0.650, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'friend_close', 'story_richness', 0.550, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'friend_casual', 'formality', 0.350, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'friend_casual', 'safety', 0.700, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'friend_casual', 'brand_appropriateness', 0.450, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'friend_casual', 'emotion', 0.450, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'friend_casual', 'novelty', 0.450, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'friend_casual', 'intimacy', 0.450, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'friend_casual', 'symbolic_identity', 0.450, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'friend_casual', 'story_richness', 0.350, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'colleague', 'formality', 0.600, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'colleague', 'safety', 0.750, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'colleague', 'brand_appropriateness', 0.650, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'colleague', 'emotion', 0.350, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'colleague', 'novelty', 0.350, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'colleague', 'intimacy', 0.300, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'colleague', 'symbolic_identity', 0.350, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'colleague', 'story_richness', 0.300, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'boss', 'formality', 0.850, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'boss', 'safety', 0.850, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'boss', 'brand_appropriateness', 0.850, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'boss', 'emotion', 0.350, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'boss', 'novelty', 0.250, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'boss', 'intimacy', 0.200, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'boss', 'symbolic_identity', 0.350, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'boss', 'story_richness', 0.350, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'subordinate', 'formality', 0.550, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'subordinate', 'safety', 0.750, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'subordinate', 'brand_appropriateness', 0.600, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'subordinate', 'emotion', 0.500, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'subordinate', 'novelty', 0.400, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'subordinate', 'intimacy', 0.350, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'subordinate', 'symbolic_identity', 0.400, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'subordinate', 'story_richness', 0.350, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'business_partner', 'formality', 0.900, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'business_partner', 'safety', 0.900, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'business_partner', 'brand_appropriateness', 0.850, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'business_partner', 'emotion', 0.250, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'business_partner', 'novelty', 0.200, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'business_partner', 'intimacy', 0.150, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'business_partner', 'symbolic_identity', 0.350, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'business_partner', 'story_richness', 0.350, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'other', 'formality', 0.500, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'other', 'safety', 0.600, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'other', 'brand_appropriateness', 0.500, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'other', 'emotion', 0.400, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'other', 'novelty', 0.400, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'other', 'intimacy', 0.400, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'other', 'symbolic_identity', 0.400, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

INSERT INTO relationship_rule (semantic_config_version_id, relationship_code, feature_code, feature_base_value, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'other', 'story_richness', 0.400, true)
ON CONFLICT (semantic_config_version_id, relationship_code, feature_code) DO UPDATE SET feature_base_value = EXCLUDED.feature_base_value, is_active = EXCLUDED.is_active;

COMMIT;
