-- Master seed: semantic_concept (18 concepts)
-- semantic_config_version_id = a1111111-1111-4111-8111-111111111102

BEGIN;

INSERT INTO semantic_concept (semantic_config_version_id, concept_code, concept_label, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'formal_refined', '上品・端正', true)
ON CONFLICT (semantic_config_version_id, concept_code) DO UPDATE SET concept_label = EXCLUDED.concept_label, is_active = EXCLUDED.is_active;

INSERT INTO semantic_concept (semantic_config_version_id, concept_code, concept_label, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'safe_classic', '無難・定番', true)
ON CONFLICT (semantic_config_version_id, concept_code) DO UPDATE SET concept_label = EXCLUDED.concept_label, is_active = EXCLUDED.is_active;

INSERT INTO semantic_concept (semantic_config_version_id, concept_code, concept_label, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'prestigious_quality', '高級・上質', true)
ON CONFLICT (semantic_config_version_id, concept_code) DO UPDATE SET concept_label = EXCLUDED.concept_label, is_active = EXCLUDED.is_active;

INSERT INTO semantic_concept (semantic_config_version_id, concept_code, concept_label, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'practical_useful', '実用・機能', true)
ON CONFLICT (semantic_config_version_id, concept_code) DO UPDATE SET concept_label = EXCLUDED.concept_label, is_active = EXCLUDED.is_active;

INSERT INTO semantic_concept (semantic_config_version_id, concept_code, concept_label, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'emotional_warm', '温かい気持ち', true)
ON CONFLICT (semantic_config_version_id, concept_code) DO UPDATE SET concept_label = EXCLUDED.concept_label, is_active = EXCLUDED.is_active;

INSERT INTO semantic_concept (semantic_config_version_id, concept_code, concept_label, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'special_memorable', '特別・記憶に残る', true)
ON CONFLICT (semantic_config_version_id, concept_code) DO UPDATE SET concept_label = EXCLUDED.concept_label, is_active = EXCLUDED.is_active;

INSERT INTO semantic_concept (semantic_config_version_id, concept_code, concept_label, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'surprising_unique', '意外性・ユニーク', true)
ON CONFLICT (semantic_config_version_id, concept_code) DO UPDATE SET concept_label = EXCLUDED.concept_label, is_active = EXCLUDED.is_active;

INSERT INTO semantic_concept (semantic_config_version_id, concept_code, concept_label, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'romantic_affectionate', '愛情・ロマン', true)
ON CONFLICT (semantic_config_version_id, concept_code) DO UPDATE SET concept_label = EXCLUDED.concept_label, is_active = EXCLUDED.is_active;

INSERT INTO semantic_concept (semantic_config_version_id, concept_code, concept_label, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'close_personal', '親しさ・近さ', true)
ON CONFLICT (semantic_config_version_id, concept_code) DO UPDATE SET concept_label = EXCLUDED.concept_label, is_active = EXCLUDED.is_active;

INSERT INTO semantic_concept (semantic_config_version_id, concept_code, concept_label, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'symbolic_identity_fit', 'その人らしさ', true)
ON CONFLICT (semantic_config_version_id, concept_code) DO UPDATE SET concept_label = EXCLUDED.concept_label, is_active = EXCLUDED.is_active;

INSERT INTO semantic_concept (semantic_config_version_id, concept_code, concept_label, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'story_narrative', 'ストーリー性', true)
ON CONFLICT (semantic_config_version_id, concept_code) DO UPDATE SET concept_label = EXCLUDED.concept_label, is_active = EXCLUDED.is_active;

INSERT INTO semantic_concept (semantic_config_version_id, concept_code, concept_label, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'stylish_aesthetic', 'おしゃれ・美意識', true)
ON CONFLICT (semantic_config_version_id, concept_code) DO UPDATE SET concept_label = EXCLUDED.concept_label, is_active = EXCLUDED.is_active;

INSERT INTO semantic_concept (semantic_config_version_id, concept_code, concept_label, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'cute_soft', 'かわいい・柔らかい', true)
ON CONFLICT (semantic_config_version_id, concept_code) DO UPDATE SET concept_label = EXCLUDED.concept_label, is_active = EXCLUDED.is_active;

INSERT INTO semantic_concept (semantic_config_version_id, concept_code, concept_label, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'casual_light', 'カジュアル・軽さ', true)
ON CONFLICT (semantic_config_version_id, concept_code) DO UPDATE SET concept_label = EXCLUDED.concept_label, is_active = EXCLUDED.is_active;

INSERT INTO semantic_concept (semantic_config_version_id, concept_code, concept_label, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'not_too_much', '重すぎない', true)
ON CONFLICT (semantic_config_version_id, concept_code) DO UPDATE SET concept_label = EXCLUDED.concept_label, is_active = EXCLUDED.is_active;

INSERT INTO semantic_concept (semantic_config_version_id, concept_code, concept_label, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'not_too_safe', '無難すぎない', true)
ON CONFLICT (semantic_config_version_id, concept_code) DO UPDATE SET concept_label = EXCLUDED.concept_label, is_active = EXCLUDED.is_active;

INSERT INTO semantic_concept (semantic_config_version_id, concept_code, concept_label, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'luxurious_rich', '豪華・華やか', true)
ON CONFLICT (semantic_config_version_id, concept_code) DO UPDATE SET concept_label = EXCLUDED.concept_label, is_active = EXCLUDED.is_active;

INSERT INTO semantic_concept (semantic_config_version_id, concept_code, concept_label, is_active)
VALUES ('a1111111-1111-4111-8111-111111111102', 'cheerful_positive', '明るい・前向き', true)
ON CONFLICT (semantic_config_version_id, concept_code) DO UPDATE SET concept_label = EXCLUDED.concept_label, is_active = EXCLUDED.is_active;

COMMIT;
