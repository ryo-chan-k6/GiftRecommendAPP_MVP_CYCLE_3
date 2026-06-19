-- Master seed: semantic_config / semantic_config_version
-- Fixed IDs: semantic_config=a1111111-1111-4111-8111-111111111101, version=a1111111-1111-4111-8111-111111111102

BEGIN;

INSERT INTO semantic_config (semantic_config_id, config_name, config_description, is_active, created_at)
VALUES ('a1111111-1111-4111-8111-111111111101', 'mvp_semantic_config', 'MVP default semantic / feature configuration lineage', true, timestamptz '2026-06-17 12:00:00+00')
ON CONFLICT (config_name) DO UPDATE SET config_description = EXCLUDED.config_description, is_active = EXCLUDED.is_active;

INSERT INTO semantic_config_version (semantic_config_version_id, semantic_config_id, version_label, is_current, valid_from, valid_to, created_at)
VALUES ('a1111111-1111-4111-8111-111111111102', 'a1111111-1111-4111-8111-111111111101', 'v1.0.0', true, timestamptz '2026-06-17 12:00:00+00', timestamptz '9999-12-31 23:59:59+00', timestamptz '2026-06-17 12:00:00+00')
ON CONFLICT (semantic_config_id, version_label) DO UPDATE SET is_current = EXCLUDED.is_current, valid_from = EXCLUDED.valid_from, valid_to = EXCLUDED.valid_to;

COMMIT;
