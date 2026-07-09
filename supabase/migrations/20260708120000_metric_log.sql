-- D15: metric_log (Tier 1 Run 集約 Metric)
-- change_id: d15_metric_log
-- Issue: #1080
-- 正本: db/ddl/d15_metric_log.sql

CREATE TABLE metric_log (
  metric_log_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  trace_id text,
  recommendation_run_id uuid NOT NULL,
  recommendation_latency_ms integer NOT NULL,
  pre_filter_candidate_count integer,
  retrieval_candidate_count integer,
  post_filter_candidate_count integer,
  final_result_count integer NOT NULL,
  recommendation_empty boolean NOT NULL DEFAULT false,
  reason_fallback_count integer NOT NULL DEFAULT 0,
  retrieval_phase_latency_ms integer,
  matching_latency_ms integer,
  ranking_latency_ms integer,
  reason_generation_latency_ms integer,
  recorded_at timestamptz NOT NULL,
  metric_source varchar(32) NOT NULL DEFAULT 'MOD-RECO-025',
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_metric_log_recommendation_run UNIQUE (recommendation_run_id),
  CONSTRAINT chk_metric_log_latency_nonneg CHECK (
    recommendation_latency_ms >= 0
  ),
  CONSTRAINT chk_metric_log_counts_nonneg CHECK (
    (pre_filter_candidate_count IS NULL OR pre_filter_candidate_count >= 0)
    AND (retrieval_candidate_count IS NULL OR retrieval_candidate_count >= 0)
    AND (post_filter_candidate_count IS NULL OR post_filter_candidate_count >= 0)
    AND final_result_count >= 0
    AND reason_fallback_count >= 0
  ),
  CONSTRAINT chk_metric_log_tier1b_latency_nonneg CHECK (
    (retrieval_phase_latency_ms IS NULL OR retrieval_phase_latency_ms >= 0)
    AND (matching_latency_ms IS NULL OR matching_latency_ms >= 0)
    AND (ranking_latency_ms IS NULL OR ranking_latency_ms >= 0)
    AND (
      reason_generation_latency_ms IS NULL
      OR reason_generation_latency_ms >= 0
    )
  ),
  CONSTRAINT chk_metric_log_metric_source CHECK (
    metric_source = 'MOD-RECO-025'
  )
);

CREATE INDEX idx_metric_log_trace
  ON metric_log (trace_id);

CREATE INDEX idx_metric_log_recorded
  ON metric_log (recorded_at);

CREATE INDEX idx_metric_log_created
  ON metric_log (created_at);
