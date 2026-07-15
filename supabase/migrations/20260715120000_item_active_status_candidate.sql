-- D16: item_active_status_candidate (active_status 候補テーブル)
-- change_id: d16_item_active_status_candidate
-- Issue: #1230
-- 正本: db/ddl/d16_item_active_status_candidate.sql
-- テーブル定義: docs/06_実装設計/database/item_active_status_candidate_テーブル定義書.md
-- 制約: BATCH-004 §18.1 No.7 / §18.1.1

-- =============================================================================
-- item_active_status_candidate
-- =============================================================================
CREATE TABLE item_active_status_candidate (
  item_active_status_candidate_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_run_id uuid NOT NULL,
  source text NOT NULL DEFAULT 'rakuten',
  external_item_code text NOT NULL,
  item_id uuid,
  candidate_active_status varchar(32) NOT NULL,
  reason_code varchar(64) NOT NULL,
  detection_basis varchar(32) NOT NULL,
  candidate_status varchar(32) NOT NULL DEFAULT 'detected',
  detected_at timestamptz NOT NULL,
  applied_at timestamptz,
  raw_metadata_id uuid,
  api_call_log_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_item_active_status_candidate_run_code
    UNIQUE (batch_run_id, source, external_item_code),
  CONSTRAINT chk_item_active_status_candidate_source_mvp CHECK (
    source = 'rakuten'
  ),
  CONSTRAINT chk_item_active_status_candidate_active_status CHECK (
    candidate_active_status IN ('active', 'inactive', 'unavailable', 'excluded')
  ),
  CONSTRAINT chk_item_active_status_candidate_status CHECK (
    candidate_status IN ('detected', 'applied', 'superseded', 'discarded')
  ),
  CONSTRAINT chk_item_active_status_candidate_applied_at CHECK (
    candidate_status <> 'applied' OR applied_at IS NOT NULL
  )
);

CREATE INDEX idx_item_active_status_candidate_status
  ON item_active_status_candidate (candidate_status, detected_at);

CREATE INDEX idx_item_active_status_candidate_item
  ON item_active_status_candidate (item_id)
  WHERE item_id IS NOT NULL;

CREATE INDEX idx_item_active_status_candidate_code
  ON item_active_status_candidate (source, external_item_code, detected_at DESC);
