-- D17: item_feature_input / item_embedding_input
-- change_id: d17_item_feature_embedding_input
-- Issue: #1568
-- Epic: #1561
-- 適用正本: 本 migration（supabase/migrations）
-- 設計正本:
--   docs/06_実装設計/database/item_feature_input_テーブル定義書.md
--   docs/06_実装設計/database/item_embedding_input_テーブル定義書.md
-- 分割参照: db/ddl/d17_item_feature_embedding_input.sql
-- 制約: E2 Human 確定（IF-DB-BATCH-012 / 015 永続化）。加算 CREATE のみ。DROP なし。019 不含。

-- =============================================================================
-- item_feature_input（IF-DB-BATCH-012 / BATCH-011 書込・BATCH-012 読取）
-- =============================================================================
CREATE TABLE item_feature_input (
  item_feature_input_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id uuid NOT NULL,
  semantic_config_version_id uuid NOT NULL,
  feature_input_hash varchar(64) NOT NULL,
  feature_input_payload jsonb NOT NULL,
  batch_run_id uuid,
  item_generation_queue_id uuid,
  computed_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_item_feature_input_idempotent
    UNIQUE (item_id, semantic_config_version_id, feature_input_hash),
  CONSTRAINT fk_item_feature_input_item_id
    FOREIGN KEY (item_id)
    REFERENCES item (item_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_item_feature_input_semantic_config_version_id
    FOREIGN KEY (semantic_config_version_id)
    REFERENCES semantic_config_version (semantic_config_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_item_feature_input_hash_format CHECK (
    char_length(feature_input_hash) = 64
    AND feature_input_hash ~ '^[0-9a-f]{64}$'
  ),
  CONSTRAINT chk_item_feature_input_payload_object CHECK (
    jsonb_typeof(feature_input_payload) = 'object'
  )
);

CREATE INDEX idx_item_feature_input_lookup
  ON item_feature_input (item_id, semantic_config_version_id, computed_at DESC);

CREATE INDEX idx_item_feature_input_hash
  ON item_feature_input (feature_input_hash);

CREATE INDEX idx_item_feature_input_batch_run
  ON item_feature_input (batch_run_id)
  WHERE batch_run_id IS NOT NULL;

CREATE INDEX idx_item_feature_input_queue
  ON item_feature_input (item_generation_queue_id)
  WHERE item_generation_queue_id IS NOT NULL;

-- =============================================================================
-- item_embedding_input（IF-DB-BATCH-015 / BATCH-014 書込・BATCH-015 読取）
-- =============================================================================
CREATE TABLE item_embedding_input (
  item_embedding_input_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id uuid NOT NULL,
  model_version_id uuid NOT NULL,
  embedding_source_type text NOT NULL DEFAULT 'item_text_context',
  embedding_input_hash varchar(64) NOT NULL,
  item_text_context text NOT NULL,
  batch_run_id uuid,
  item_generation_queue_id uuid,
  computed_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_item_embedding_input_idempotent
    UNIQUE (item_id, model_version_id, embedding_input_hash),
  CONSTRAINT fk_item_embedding_input_item_id
    FOREIGN KEY (item_id)
    REFERENCES item (item_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_item_embedding_input_model_version_id
    FOREIGN KEY (model_version_id)
    REFERENCES model_version (model_version_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_item_embedding_input_source_type CHECK (
    embedding_source_type = 'item_text_context'
  ),
  CONSTRAINT chk_item_embedding_input_hash_format CHECK (
    char_length(embedding_input_hash) = 64
    AND embedding_input_hash ~ '^[0-9a-f]{64}$'
  ),
  CONSTRAINT chk_item_embedding_input_context_nonempty CHECK (
    char_length(btrim(item_text_context)) > 0
  )
);

CREATE INDEX idx_item_embedding_input_lookup
  ON item_embedding_input (item_id, model_version_id, computed_at DESC);

CREATE INDEX idx_item_embedding_input_hash
  ON item_embedding_input (embedding_input_hash);

CREATE INDEX idx_item_embedding_input_batch_run
  ON item_embedding_input (batch_run_id)
  WHERE batch_run_id IS NOT NULL;

CREATE INDEX idx_item_embedding_input_queue
  ON item_embedding_input (item_generation_queue_id)
  WHERE item_generation_queue_id IS NOT NULL;
