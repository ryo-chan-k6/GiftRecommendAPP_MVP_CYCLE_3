-- Master seed: feature_definition (8 axes)
-- semantic_config_version_id = a1111111-1111-4111-8111-111111111102

BEGIN;

INSERT INTO feature_definition (semantic_config_version_id, feature_code, feature_label, feature_group, display_order, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'formality', '格式', 'social', 1, true)
ON CONFLICT (semantic_config_version_id, feature_code) DO UPDATE SET feature_label = EXCLUDED.feature_label, feature_group = EXCLUDED.feature_group, display_order = EXCLUDED.display_order, is_active = EXCLUDED.is_active;

INSERT INTO feature_definition (semantic_config_version_id, feature_code, feature_label, feature_group, display_order, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'safety', '安心感', 'social', 2, true)
ON CONFLICT (semantic_config_version_id, feature_code) DO UPDATE SET feature_label = EXCLUDED.feature_label, feature_group = EXCLUDED.feature_group, display_order = EXCLUDED.display_order, is_active = EXCLUDED.is_active;

INSERT INTO feature_definition (semantic_config_version_id, feature_code, feature_label, feature_group, display_order, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'brand_appropriateness', 'ブランド適合', 'social', 3, true)
ON CONFLICT (semantic_config_version_id, feature_code) DO UPDATE SET feature_label = EXCLUDED.feature_label, feature_group = EXCLUDED.feature_group, display_order = EXCLUDED.display_order, is_active = EXCLUDED.is_active;

INSERT INTO feature_definition (semantic_config_version_id, feature_code, feature_label, feature_group, display_order, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'emotion', '感情', 'symbolic', 4, true)
ON CONFLICT (semantic_config_version_id, feature_code) DO UPDATE SET feature_label = EXCLUDED.feature_label, feature_group = EXCLUDED.feature_group, display_order = EXCLUDED.display_order, is_active = EXCLUDED.is_active;

INSERT INTO feature_definition (semantic_config_version_id, feature_code, feature_label, feature_group, display_order, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'novelty', '新しさ', 'symbolic', 5, true)
ON CONFLICT (semantic_config_version_id, feature_code) DO UPDATE SET feature_label = EXCLUDED.feature_label, feature_group = EXCLUDED.feature_group, display_order = EXCLUDED.display_order, is_active = EXCLUDED.is_active;

INSERT INTO feature_definition (semantic_config_version_id, feature_code, feature_label, feature_group, display_order, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'intimacy', '親密さ', 'symbolic', 6, true)
ON CONFLICT (semantic_config_version_id, feature_code) DO UPDATE SET feature_label = EXCLUDED.feature_label, feature_group = EXCLUDED.feature_group, display_order = EXCLUDED.display_order, is_active = EXCLUDED.is_active;

INSERT INTO feature_definition (semantic_config_version_id, feature_code, feature_label, feature_group, display_order, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'symbolic_identity', '象徴性', 'symbolic', 7, true)
ON CONFLICT (semantic_config_version_id, feature_code) DO UPDATE SET feature_label = EXCLUDED.feature_label, feature_group = EXCLUDED.feature_group, display_order = EXCLUDED.display_order, is_active = EXCLUDED.is_active;

INSERT INTO feature_definition (semantic_config_version_id, feature_code, feature_label, feature_group, display_order, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'story_richness', 'ストーリー性', 'symbolic', 8, true)
ON CONFLICT (semantic_config_version_id, feature_code) DO UPDATE SET feature_label = EXCLUDED.feature_label, feature_group = EXCLUDED.feature_group, display_order = EXCLUDED.display_order, is_active = EXCLUDED.is_active;

COMMIT;
