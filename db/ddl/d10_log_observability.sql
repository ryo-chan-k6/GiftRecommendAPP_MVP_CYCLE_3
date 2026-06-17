-- D10: Log / Observability tables
-- change_id: d10_log_observability
-- Issue: #607
-- 正本: docs/06_実装設計/database/*_テーブル定義書.md（D10 対象 3 件）
-- 適用順: D01〜D09 適用後。
--   batch_run_log → phase_log → error_log
-- LOGICAL 参照: polymorphic owner_type / owner_id、下流 batch_run_id 被参照

-- =============================================================================
-- 1. batch_run_log
-- =============================================================================
CREATE TABLE batch_run_log (
  batch_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  trace_id text,
  batch_name text NOT NULL,
  batch_type varchar(32),
  run_status varchar(32) NOT NULL DEFAULT 'queued',
  started_at timestamptz NOT NULL,
  completed_at timestamptz,
  duration_ms integer,
  success_count integer NOT NULL DEFAULT 0,
  failed_count integer NOT NULL DEFAULT 0,
  skipped_count integer NOT NULL DEFAULT 0,
  error_summary text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chk_batch_run_log_status CHECK (
    run_status IN (
      'queued',
      'running',
      'succeeded',
      'partially_succeeded',
      'failed',
      'canceled'
    )
  ),
  CONSTRAINT chk_batch_run_log_counts_nonneg CHECK (
    success_count >= 0
    AND failed_count >= 0
    AND skipped_count >= 0
  ),
  CONSTRAINT chk_batch_run_log_duration_nonneg CHECK (
    duration_ms IS NULL OR duration_ms >= 0
  ),
  CONSTRAINT chk_batch_run_log_completed_terminal CHECK (
    run_status NOT IN (
      'succeeded',
      'partially_succeeded',
      'failed',
      'canceled'
    )
    OR completed_at IS NOT NULL
  ),
  CONSTRAINT chk_batch_run_log_nonterminal_no_completed CHECK (
    run_status NOT IN ('queued', 'running')
    OR completed_at IS NULL
  ),
  CONSTRAINT chk_batch_run_log_batch_type CHECK (
    batch_type IS NULL
    OR batch_type IN (
      'external_fetch',
      'staging',
      'import',
      'feature_generation',
      'summary',
      'maintenance'
    )
  )
);

CREATE INDEX idx_batch_run_log_status
  ON batch_run_log (run_status, started_at DESC);

CREATE INDEX idx_batch_run_log_name
  ON batch_run_log (batch_name, started_at DESC);

CREATE INDEX idx_batch_run_log_trace
  ON batch_run_log (trace_id);

-- =============================================================================
-- 2. phase_log
-- =============================================================================
CREATE TABLE phase_log (
  phase_log_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  trace_id text,
  owner_type varchar(32) NOT NULL,
  owner_id uuid NOT NULL,
  phase_name varchar(64) NOT NULL,
  phase_status varchar(32) NOT NULL DEFAULT 'started',
  started_at timestamptz NOT NULL,
  completed_at timestamptz,
  duration_ms integer,
  error_code varchar(64),
  detail_json jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chk_phase_log_owner_type CHECK (
    owner_type IN (
      'recommendation_run',
      'batch_run',
      'evaluation_run'
    )
  ),
  CONSTRAINT chk_phase_log_status CHECK (
    phase_status IN ('started', 'succeeded', 'failed', 'skipped')
  ),
  CONSTRAINT chk_phase_log_phase_name_run CHECK (
    owner_type <> 'recommendation_run'
    OR phase_name IN (
      'request_received',
      'config_resolved',
      'semantic_extracted',
      'user_feature_generated',
      'user_meaning_projected',
      'query_embedding_generated',
      'pre_hard_filter_completed',
      'retrieval_completed',
      'post_hard_filter_completed',
      'matching_completed',
      'ranking_completed',
      'result_generated',
      'reason_generated',
      'response_built'
    )
  ),
  CONSTRAINT chk_phase_log_phase_name_batch CHECK (
    owner_type <> 'batch_run'
    OR phase_name IN (
      'batch_started',
      'cursor_loaded',
      'external_api_called',
      'raw_saved',
      'raw_metadata_saved',
      'staging_transformed',
      'diff_judged',
      'item_imported',
      'item_image_imported',
      'popularity_signal_imported',
      'item_feature_generated',
      'item_embedding_generated',
      'feature_distribution_metric_recorded',
      'summary_created',
      'batch_completed'
    )
  ),
  CONSTRAINT chk_phase_log_duration_nonneg CHECK (
    duration_ms IS NULL OR duration_ms >= 0
  ),
  CONSTRAINT chk_phase_log_completed_terminal CHECK (
    phase_status NOT IN ('succeeded', 'failed', 'skipped')
    OR completed_at IS NOT NULL
  ),
  CONSTRAINT chk_phase_log_nonterminal_no_completed CHECK (
    phase_status <> 'started'
    OR completed_at IS NULL
  )
);

CREATE INDEX idx_phase_log_owner
  ON phase_log (owner_type, owner_id, started_at);

CREATE INDEX idx_phase_log_trace
  ON phase_log (trace_id);

CREATE INDEX idx_phase_log_status
  ON phase_log (phase_status, started_at);

CREATE INDEX idx_phase_log_phase_name
  ON phase_log (owner_type, phase_name, started_at);

CREATE INDEX idx_phase_log_created
  ON phase_log (created_at);

-- =============================================================================
-- 3. error_log
-- =============================================================================
CREATE TABLE error_log (
  error_log_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  trace_id text,
  request_id text,
  owner_type varchar(64) NOT NULL,
  owner_id uuid,
  service varchar(16) NOT NULL,
  error_code varchar(64) NOT NULL,
  error_message text NOT NULL,
  severity varchar(16) NOT NULL DEFAULT 'error',
  retryable boolean NOT NULL DEFAULT false,
  error_detail_json jsonb NOT NULL DEFAULT '{}',
  occurred_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chk_error_log_owner_type CHECK (
    owner_type IN (
      'recommendation_request',
      'recommendation_run',
      'recommendation_result',
      'recommendation_feedback',
      'batch_run',
      'api_call',
      'raw_product_metadata',
      'item_generation_queue',
      'evaluation_run',
      'system'
    )
  ),
  CONSTRAINT chk_error_log_owner_id_system CHECK (
    owner_type <> 'system' OR owner_id IS NULL
  ),
  CONSTRAINT chk_error_log_owner_id_required CHECK (
    owner_type = 'system' OR owner_id IS NOT NULL
  ),
  CONSTRAINT chk_error_log_service CHECK (
    service IN ('api', 'reco', 'batch')
  ),
  CONSTRAINT chk_error_log_severity CHECK (
    severity IN ('warn', 'error', 'critical')
  ),
  CONSTRAINT chk_error_log_error_code_format CHECK (
    error_code ~ '^GRS-[A-Z]{3}-[0-9]{3}$'
  )
);

CREATE INDEX idx_error_log_owner
  ON error_log (owner_type, owner_id, occurred_at);

CREATE INDEX idx_error_log_trace
  ON error_log (trace_id);

CREATE INDEX idx_error_log_code
  ON error_log (error_code, occurred_at);

CREATE INDEX idx_error_log_occurred
  ON error_log (occurred_at);

CREATE INDEX idx_error_log_service
  ON error_log (service, occurred_at);
