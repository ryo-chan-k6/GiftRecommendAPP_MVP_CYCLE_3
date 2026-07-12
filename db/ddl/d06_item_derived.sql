-- D06: Item derived data tables
-- change_id: d06_item_derived
-- Issue: #603
-- 正本: docs/06_実装設計/database/*_テーブル定義書.md（D06 対象 5 件）
-- 適用順: D01〜D05 適用後。item_generation_queue → item_semantic → item_feature → item_meaning → item_embedding
-- LOGICAL 参照: feature_code / feature_normalization_version_id（物理 FK なし）
-- LOGICAL 参照: item_generation_queue と派生テーブル間（物理 FK なし）

-- =============================================================================
-- 1. item_generation_queue
-- =============================================================================
CREATE TABLE item_generation_queue (
  item_generation_queue_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id uuid NOT NULL,
  generation_type text NOT NULL DEFAULT 'semantic',
  queue_status text NOT NULL DEFAULT 'queued',
  retry_count integer NOT NULL DEFAULT 0,
  queued_at timestamptz NOT NULL,
  started_at timestamptz,
  completed_at timestamptz,
  error_message text,
  CONSTRAINT fk_item_generation_queue_item_id
    FOREIGN KEY (item_id)
    REFERENCES item (item_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_item_gen_queue_status CHECK (
    queue_status IN (
      'queued', 'processing', 'succeeded', 'failed', 'skipped'
    )
  ),
  CONSTRAINT chk_item_gen_generation_type CHECK (
    generation_type IN ('semantic', 'feature', 'embedding')
  ),
  CONSTRAINT chk_item_gen_retry_count_nonneg CHECK (retry_count >= 0),
  CONSTRAINT chk_item_gen_retry_count_max CHECK (retry_count <= 5),
  CONSTRAINT chk_item_gen_started_when_processing CHECK (
    queue_status NOT IN ('processing', 'succeeded', 'failed', 'skipped')
    OR started_at IS NOT NULL
  ),
  CONSTRAINT chk_item_gen_completed_when_terminal CHECK (
    queue_status IN ('queued', 'processing')
    OR completed_at IS NOT NULL
  )
);

CREATE INDEX idx_item_gen_queue_status
  ON item_generation_queue (queue_status, queued_at);

CREATE INDEX idx_item_generation_queue_item_id
  ON item_generation_queue (item_id);

CREATE UNIQUE INDEX uq_item_gen_queue_active_per_type
  ON item_generation_queue (item_id, generation_type)
  WHERE queue_status IN ('queued', 'processing');

-- =============================================================================
-- 2. item_semantic
-- =============================================================================
CREATE TABLE item_semantic (
  item_semantic_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id uuid NOT NULL,
  semantic_config_version_id uuid NOT NULL,
  semantic_json jsonb NOT NULL,
  generated_at timestamptz NOT NULL,
  CONSTRAINT uq_item_semantic_item_version
    UNIQUE (item_id, semantic_config_version_id),
  CONSTRAINT fk_item_semantic_item_id
    FOREIGN KEY (item_id)
    REFERENCES item (item_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_item_semantic_semantic_config_version_id
    FOREIGN KEY (semantic_config_version_id)
    REFERENCES semantic_config_version (semantic_config_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_semantic_json_object CHECK (
    jsonb_typeof(semantic_json) = 'object'
  ),
  CONSTRAINT chk_semantic_json_concepts_array CHECK (
    jsonb_typeof(semantic_json -> 'concepts') = 'array'
  )
);

CREATE INDEX idx_item_semantic_item_id
  ON item_semantic (item_id);

CREATE INDEX idx_item_semantic_version_id
  ON item_semantic (semantic_config_version_id);

CREATE INDEX idx_item_semantic_generated_at
  ON item_semantic (generated_at DESC);

-- =============================================================================
-- 3. item_feature
-- =============================================================================
CREATE TABLE item_feature (
  item_feature_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id uuid NOT NULL,
  semantic_config_version_id uuid NOT NULL,
  feature_code text NOT NULL,
  feature_input_hash varchar(64) NOT NULL,
  feature_normalization_version_id uuid NOT NULL,
  raw_feature_value numeric(8, 6) NOT NULL,
  normalized_feature_value numeric(8, 6),
  generated_at timestamptz NOT NULL,
  CONSTRAINT uq_item_feature_idempotent
    UNIQUE (
      item_id,
      semantic_config_version_id,
      feature_code,
      feature_input_hash,
      feature_normalization_version_id
    ),
  CONSTRAINT fk_item_feature_item_id
    FOREIGN KEY (item_id)
    REFERENCES item (item_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_item_feature_semantic_config_version_id
    FOREIGN KEY (semantic_config_version_id)
    REFERENCES semantic_config_version (semantic_config_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_item_feature_code_mvp CHECK (
    feature_code IN (
      'formality', 'safety', 'brand_appropriateness',
      'emotion', 'novelty', 'intimacy', 'symbolic_identity', 'story_richness'
    )
  ),
  CONSTRAINT chk_item_feature_input_hash_format CHECK (
    char_length(feature_input_hash) = 64
    AND feature_input_hash ~ '^[0-9a-f]{64}$'
  ),
  CONSTRAINT chk_item_feature_normalized_range CHECK (
    normalized_feature_value IS NULL
    OR (
      normalized_feature_value >= 0.0
      AND normalized_feature_value <= 1.0
    )
  ),
  CONSTRAINT chk_item_feature_raw_range CHECK (
    raw_feature_value >= 0.0 AND raw_feature_value <= 1.0
  )
);

CREATE INDEX idx_item_feature_lookup
  ON item_feature (item_id, semantic_config_version_id, feature_code);

CREATE INDEX idx_item_feature_item_id
  ON item_feature (item_id);

CREATE INDEX idx_item_feature_norm_version
  ON item_feature (feature_normalization_version_id);

-- =============================================================================
-- 4. item_meaning
-- =============================================================================
CREATE TABLE item_meaning (
  item_meaning_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id uuid NOT NULL,
  semantic_config_version_id uuid NOT NULL,
  feature_normalization_version_id uuid NOT NULL,
  item_social numeric(6, 4) NOT NULL,
  item_symbolic numeric(6, 4) NOT NULL,
  generated_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_item_meaning_item_scv
    UNIQUE (item_id, semantic_config_version_id),
  CONSTRAINT fk_item_meaning_item_id
    FOREIGN KEY (item_id)
    REFERENCES item (item_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_item_meaning_semantic_config_version_id
    FOREIGN KEY (semantic_config_version_id)
    REFERENCES semantic_config_version (semantic_config_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_item_meaning_social_range CHECK (
    item_social >= 0.0 AND item_social <= 1.0
  ),
  CONSTRAINT chk_item_meaning_symbolic_range CHECK (
    item_symbolic >= 0.0 AND item_symbolic <= 1.0
  )
);

CREATE INDEX idx_item_meaning_lookup
  ON item_meaning (item_id, semantic_config_version_id);

CREATE INDEX idx_item_meaning_scv
  ON item_meaning (semantic_config_version_id);

CREATE INDEX idx_item_meaning_norm_version
  ON item_meaning (feature_normalization_version_id);

-- =============================================================================
-- 5. item_embedding
-- =============================================================================
CREATE TABLE item_embedding (
  item_embedding_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id uuid NOT NULL,
  model_version_id uuid NOT NULL,
  embedding_source_type text NOT NULL,
  embedding_input_hash varchar(64) NOT NULL,
  embedding_vector vector(1536) NOT NULL,
  generated_at timestamptz NOT NULL,
  CONSTRAINT uq_item_embedding_idempotent
    UNIQUE (item_id, model_version_id, embedding_input_hash),
  CONSTRAINT fk_item_embedding_item_id
    FOREIGN KEY (item_id)
    REFERENCES item (item_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_item_embedding_model_version_id
    FOREIGN KEY (model_version_id)
    REFERENCES model_version (model_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_item_embedding_source_type CHECK (
    embedding_source_type = 'item_text_context'
  ),
  CONSTRAINT chk_item_embedding_input_hash_format CHECK (
    char_length(embedding_input_hash) = 64
    AND embedding_input_hash ~ '^[0-9a-f]{64}$'
  ),
  CONSTRAINT chk_item_embedding_vector_dims CHECK (
    vector_dims(embedding_vector) = 1536
  )
);

CREATE INDEX idx_item_embedding_item_model
  ON item_embedding (item_id, model_version_id);

CREATE INDEX idx_item_embedding_item_id
  ON item_embedding (item_id);

CREATE INDEX idx_item_embedding_vector
  ON item_embedding
  USING hnsw (embedding_vector vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
