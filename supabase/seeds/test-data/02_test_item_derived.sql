-- Test seed: item_feature / item_meaning / item_embedding for fixture items
-- Issue: #674 | Epic C C2
-- Prerequisite: 01_test_items.sql + master seed

BEGIN;

DO $$
DECLARE
  scv_id uuid := 'a1111111-1111-4111-8111-111111111102';
  fnv_id uuid;
  model_id uuid;
  zero_vec vector(1536);
BEGIN
  SELECT feature_normalization_version_id
    INTO fnv_id
    FROM feature_normalization_version
   WHERE normalization_method = 'sigmoid'
     AND is_current = true
   ORDER BY generated_at DESC
   LIMIT 1;

  IF fnv_id IS NULL THEN
    RAISE EXCEPTION 'feature_normalization_version (sigmoid, is_current) not found — apply master seed first';
  END IF;

  SELECT model_version_id
    INTO model_id
    FROM model_version
   WHERE provider = 'openai'
     AND model_name = 'text-embedding-3-small'
     AND model_type = 'embedding'
     AND is_current = true
   LIMIT 1;

  IF model_id IS NULL THEN
    RAISE EXCEPTION 'model_version (text-embedding-3-small) not found — apply master seed first';
  END IF;

  zero_vec := ('[' || repeat('0.001,', 1535) || '0.001]')::vector(1536);

  -- item_001: high formality / safety (boss thanks primary)
  INSERT INTO item_feature (
    item_id, semantic_config_version_id, feature_code, feature_input_hash,
    feature_normalization_version_id, raw_feature_value, normalized_feature_value, generated_at
  )
  VALUES
    ('b1111111-1111-4111-8111-111111111001', scv_id, 'formality', '1111111111111111111111111111111111111111111111111111111111111111', fnv_id, 0.880000, 0.850000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111001', scv_id, 'safety', '1111111111111111111111111111111111111111111111111111111111111112', fnv_id, 0.820000, 0.800000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111001', scv_id, 'brand_appropriateness', '1111111111111111111111111111111111111111111111111111111111111113', fnv_id, 0.780000, 0.760000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111001', scv_id, 'emotion', '1111111111111111111111111111111111111111111111111111111111111114', fnv_id, 0.620000, 0.600000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111001', scv_id, 'novelty', '1111111111111111111111111111111111111111111111111111111111111115', fnv_id, 0.450000, 0.430000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111001', scv_id, 'intimacy', '1111111111111111111111111111111111111111111111111111111111111116', fnv_id, 0.350000, 0.330000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111001', scv_id, 'symbolic_identity', '1111111111111111111111111111111111111111111111111111111111111117', fnv_id, 0.500000, 0.480000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111001', scv_id, 'story_richness', '1111111111111111111111111111111111111111111111111111111111111118', fnv_id, 0.550000, 0.530000, timestamptz '2026-06-17 12:00:00+00')
  ON CONFLICT ON CONSTRAINT uq_item_feature_idempotent DO UPDATE SET
    raw_feature_value = EXCLUDED.raw_feature_value,
    normalized_feature_value = EXCLUDED.normalized_feature_value,
    generated_at = EXCLUDED.generated_at;

  -- item_002: low formality decoy
  INSERT INTO item_feature (
    item_id, semantic_config_version_id, feature_code, feature_input_hash,
    feature_normalization_version_id, raw_feature_value, normalized_feature_value, generated_at
  )
  VALUES
    ('b1111111-1111-4111-8111-111111111002', scv_id, 'formality', '2222222222222222222222222222222222222222222222222222222222222221', fnv_id, 0.280000, 0.250000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111002', scv_id, 'safety', '2222222222222222222222222222222222222222222222222222222222222222', fnv_id, 0.650000, 0.620000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111002', scv_id, 'brand_appropriateness', '2222222222222222222222222222222222222222222222222222222222222223', fnv_id, 0.400000, 0.380000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111002', scv_id, 'emotion', '2222222222222222222222222222222222222222222222222222222222222224', fnv_id, 0.700000, 0.680000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111002', scv_id, 'novelty', '2222222222222222222222222222222222222222222222222222222222222225', fnv_id, 0.720000, 0.700000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111002', scv_id, 'intimacy', '2222222222222222222222222222222222222222222222222222222222222226', fnv_id, 0.680000, 0.660000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111002', scv_id, 'symbolic_identity', '2222222222222222222222222222222222222222222222222222222222222227', fnv_id, 0.450000, 0.430000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111002', scv_id, 'story_richness', '2222222222222222222222222222222222222222222222222222222222222228', fnv_id, 0.420000, 0.400000, timestamptz '2026-06-17 12:00:00+00')
  ON CONFLICT ON CONSTRAINT uq_item_feature_idempotent DO UPDATE SET
    raw_feature_value = EXCLUDED.raw_feature_value,
    normalized_feature_value = EXCLUDED.normalized_feature_value,
    generated_at = EXCLUDED.generated_at;

  -- item_003: alcohol NG case (moderate formality, safety risk for NG keyword)
  INSERT INTO item_feature (
    item_id, semantic_config_version_id, feature_code, feature_input_hash,
    feature_normalization_version_id, raw_feature_value, normalized_feature_value, generated_at
  )
  VALUES
    ('b1111111-1111-4111-8111-111111111003', scv_id, 'formality', '3333333333333333333333333333333333333333333333333333333333333331', fnv_id, 0.750000, 0.720000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111003', scv_id, 'safety', '3333333333333333333333333333333333333333333333333333333333333332', fnv_id, 0.550000, 0.520000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111003', scv_id, 'brand_appropriateness', '3333333333333333333333333333333333333333333333333333333333333333', fnv_id, 0.700000, 0.680000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111003', scv_id, 'emotion', '3333333333333333333333333333333333333333333333333333333333333334', fnv_id, 0.650000, 0.630000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111003', scv_id, 'novelty', '3333333333333333333333333333333333333333333333333333333333333335', fnv_id, 0.580000, 0.560000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111003', scv_id, 'intimacy', '3333333333333333333333333333333333333333333333333333333333333336', fnv_id, 0.480000, 0.460000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111003', scv_id, 'symbolic_identity', '3333333333333333333333333333333333333333333333333333333333333337', fnv_id, 0.620000, 0.600000, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111003', scv_id, 'story_richness', '3333333333333333333333333333333333333333333333333333333333333338', fnv_id, 0.600000, 0.580000, timestamptz '2026-06-17 12:00:00+00')
  ON CONFLICT ON CONSTRAINT uq_item_feature_idempotent DO UPDATE SET
    raw_feature_value = EXCLUDED.raw_feature_value,
    normalized_feature_value = EXCLUDED.normalized_feature_value,
    generated_at = EXCLUDED.generated_at;

  INSERT INTO item_meaning (
    item_id, semantic_config_version_id, feature_normalization_version_id,
    item_social, item_symbolic, generated_at
  )
  VALUES
    ('b1111111-1111-4111-8111-111111111001', scv_id, fnv_id, 0.8033, 0.4880, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111002', scv_id, fnv_id, 0.4167, 0.5975, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111003', scv_id, fnv_id, 0.6400, 0.5675, timestamptz '2026-06-17 12:00:00+00')
  ON CONFLICT ON CONSTRAINT uq_item_meaning_item_scv DO UPDATE SET
    feature_normalization_version_id = EXCLUDED.feature_normalization_version_id,
    item_social = EXCLUDED.item_social,
    item_symbolic = EXCLUDED.item_symbolic,
    generated_at = EXCLUDED.generated_at,
    updated_at = now();

  INSERT INTO item_embedding (
    item_id, model_version_id, embedding_source_type, embedding_input_hash,
    embedding_vector, generated_at
  )
  VALUES
    ('b1111111-1111-4111-8111-111111111001', model_id, 'item_text_context', '4444444444444444444444444444444444444444444444444444444444444441', zero_vec, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111002', model_id, 'item_text_context', '4444444444444444444444444444444444444444444444444444444444444442', zero_vec, timestamptz '2026-06-17 12:00:00+00'),
    ('b1111111-1111-4111-8111-111111111003', model_id, 'item_text_context', '4444444444444444444444444444444444444444444444444444444444444443', zero_vec, timestamptz '2026-06-17 12:00:00+00')
  ON CONFLICT ON CONSTRAINT uq_item_embedding_idempotent DO UPDATE SET
    embedding_vector = EXCLUDED.embedding_vector,
    generated_at = EXCLUDED.generated_at;
END $$;

COMMIT;
