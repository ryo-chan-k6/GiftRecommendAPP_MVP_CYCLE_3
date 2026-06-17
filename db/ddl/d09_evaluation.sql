-- D09: Evaluation tables (MVP partial)
-- change_id: d09_evaluation
-- Issue: #606
-- 正本: docs/06_実装設計/database/*_テーブル定義書.md（D09 対象 5 件）
-- 適用順: D01〜D08 適用後。
--   evaluation_dataset → evaluation_case → evaluation_run
--   → evaluation_result → evaluation_metric
-- LOGICAL 参照: recommendation_request_id / recommendation_result_id /
--   batch_run_id / semantic_config_version_id / model_version_id / ranking_config_id

-- =============================================================================
-- 1. evaluation_dataset
-- =============================================================================
CREATE TABLE evaluation_dataset (
  evaluation_dataset_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_name text NOT NULL,
  dataset_description text,
  dataset_version varchar(50) NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_evaluation_dataset_name_version
    UNIQUE (dataset_name, dataset_version),
  CONSTRAINT chk_dataset_name_format CHECK (
    dataset_name ~ '^[a-z][a-z0-9_]*$'
  ),
  CONSTRAINT chk_dataset_version_format CHECK (
    dataset_version ~ '^v[0-9]+\.[0-9]+\.[0-9]+$'
  ),
  CONSTRAINT chk_dataset_description_length CHECK (
    dataset_description IS NULL
    OR char_length(dataset_description) <= 500
  )
);

CREATE INDEX idx_evaluation_dataset_active_name
  ON evaluation_dataset (is_active, dataset_name);

CREATE INDEX idx_evaluation_dataset_created_at
  ON evaluation_dataset (created_at DESC);

-- =============================================================================
-- 2. evaluation_case
-- =============================================================================
CREATE TABLE evaluation_case (
  evaluation_case_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evaluation_dataset_id uuid NOT NULL,
  case_label varchar(100) NOT NULL,
  input_condition_json jsonb NOT NULL,
  expected_result_json jsonb,
  recommendation_request_id uuid,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_evaluation_case_dataset_label
    UNIQUE (evaluation_dataset_id, case_label),
  CONSTRAINT fk_evaluation_case_dataset
    FOREIGN KEY (evaluation_dataset_id)
    REFERENCES evaluation_dataset (evaluation_dataset_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_case_label_format CHECK (
    case_label ~ '^[a-z][a-z0-9_]*$'
  ),
  CONSTRAINT chk_input_condition_not_empty CHECK (
    input_condition_json <> '{}'::jsonb
  )
);

CREATE INDEX idx_evaluation_case_dataset_id
  ON evaluation_case (evaluation_dataset_id);

CREATE INDEX idx_evaluation_case_dataset_active
  ON evaluation_case (evaluation_dataset_id)
  WHERE is_active = true;

CREATE INDEX idx_evaluation_case_request_id
  ON evaluation_case (recommendation_request_id);

CREATE INDEX idx_evaluation_case_created_at
  ON evaluation_case (created_at DESC);

-- =============================================================================
-- 3. evaluation_run
-- =============================================================================
CREATE TABLE evaluation_run (
  evaluation_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evaluation_dataset_id uuid NOT NULL,
  batch_run_id uuid,
  semantic_config_version_id uuid NOT NULL,
  model_version_id uuid NOT NULL,
  ranking_config_id uuid NOT NULL,
  evaluation_status varchar(32) NOT NULL DEFAULT 'queued',
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT fk_evaluation_run_dataset
    FOREIGN KEY (evaluation_dataset_id)
    REFERENCES evaluation_dataset (evaluation_dataset_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_evaluation_status CHECK (
    evaluation_status IN (
      'queued', 'running', 'succeeded', 'failed', 'canceled'
    )
  ),
  CONSTRAINT chk_eval_started_before_completed CHECK (
    completed_at IS NULL
    OR started_at IS NULL
    OR started_at <= completed_at
  ),
  CONSTRAINT chk_eval_completed_terminal CHECK (
    evaluation_status NOT IN ('succeeded', 'failed', 'canceled')
    OR completed_at IS NOT NULL
  ),
  CONSTRAINT chk_eval_nonterminal_no_completed CHECK (
    evaluation_status NOT IN ('queued', 'running')
    OR completed_at IS NULL
  )
);

CREATE INDEX idx_evaluation_run_dataset_id
  ON evaluation_run (evaluation_dataset_id);

CREATE INDEX idx_evaluation_run_status
  ON evaluation_run (evaluation_status, started_at);

CREATE INDEX idx_evaluation_run_batch_run_id
  ON evaluation_run (batch_run_id);

CREATE INDEX idx_evaluation_run_semantic_config_version
  ON evaluation_run (semantic_config_version_id);

CREATE INDEX idx_evaluation_run_model_version
  ON evaluation_run (model_version_id);

CREATE INDEX idx_evaluation_run_ranking_config
  ON evaluation_run (ranking_config_id);

CREATE INDEX idx_evaluation_run_created
  ON evaluation_run (created_at DESC);

-- =============================================================================
-- 4. evaluation_result
-- =============================================================================
CREATE TABLE evaluation_result (
  evaluation_result_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evaluation_run_id uuid NOT NULL,
  evaluation_case_id uuid NOT NULL,
  evaluation_dataset_id uuid NOT NULL,
  recommendation_result_id uuid,
  executed_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_evaluation_result_run_case
    UNIQUE (evaluation_run_id, evaluation_case_id),
  CONSTRAINT fk_evaluation_result_run
    FOREIGN KEY (evaluation_run_id)
    REFERENCES evaluation_run (evaluation_run_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_evaluation_result_case
    FOREIGN KEY (evaluation_case_id)
    REFERENCES evaluation_case (evaluation_case_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_evaluation_result_dataset
    FOREIGN KEY (evaluation_dataset_id)
    REFERENCES evaluation_dataset (evaluation_dataset_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_executed_at_not_future CHECK (
    executed_at <= now() + interval '5 minutes'
  )
);

CREATE INDEX idx_evaluation_result_run_id
  ON evaluation_result (evaluation_run_id);

CREATE INDEX idx_evaluation_result_case_id
  ON evaluation_result (evaluation_case_id);

CREATE INDEX idx_evaluation_result_dataset_id
  ON evaluation_result (evaluation_dataset_id);

CREATE INDEX idx_evaluation_result_recommendation_result_id
  ON evaluation_result (recommendation_result_id);

CREATE INDEX idx_evaluation_result_executed_at
  ON evaluation_result (executed_at DESC);

CREATE INDEX idx_evaluation_result_created_at
  ON evaluation_result (created_at DESC);

-- =============================================================================
-- 5. evaluation_metric
-- =============================================================================
CREATE TABLE evaluation_metric (
  evaluation_metric_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  evaluation_result_id uuid NOT NULL,
  metric_name varchar(64) NOT NULL,
  metric_value numeric(12, 6) NOT NULL,
  metric_detail_json jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_evaluation_metric_result_name
    UNIQUE (evaluation_result_id, metric_name),
  CONSTRAINT fk_evaluation_metric_result
    FOREIGN KEY (evaluation_result_id)
    REFERENCES evaluation_result (evaluation_result_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_metric_name_not_empty CHECK (
    length(trim(metric_name)) > 0
  )
);

CREATE INDEX idx_evaluation_metric_result_id
  ON evaluation_metric (evaluation_result_id);

CREATE INDEX idx_evaluation_metric_name
  ON evaluation_metric (metric_name);

CREATE INDEX idx_evaluation_metric_created_at
  ON evaluation_metric (created_at DESC);
