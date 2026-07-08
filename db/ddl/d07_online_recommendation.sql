-- D07: Online recommendation tables
-- change_id: d07_online_recommendation
-- Issue: #604
-- 正本: docs/06_実装設計/database/*_テーブル定義書.md（D07 対象 6 件）
-- 適用順: D01〜D06 適用後。
--   recommendation_request → recommendation_run → recommendation_result
--   → recommendation_result_item → recommendation_reason → recommendation_feedback
-- LOGICAL 参照: relationship_master / occasion_master / Config version 列 / trace 列 / template_id
-- D08 から Run への後追い物理 FK は本バッチでは付与しない

-- =============================================================================
-- 1. recommendation_request
-- =============================================================================
CREATE TABLE recommendation_request (
  recommendation_request_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  request_mode varchar(32) NOT NULL,
  relationship_code text NOT NULL,
  occasion_code text NOT NULL,
  budget_min integer,
  budget_max integer,
  currency varchar(3) NOT NULL DEFAULT 'JPY',
  tax_included boolean,
  preferred_text text,
  non_preferred_text text,
  ng_text text,
  free_text text,
  top_k integer,
  candidate_limit integer,
  include_reason boolean,
  include_debug_info boolean,
  request_payload jsonb NOT NULL,
  validated_payload jsonb NOT NULL,
  trace_id text,
  created_at timestamptz NOT NULL DEFAULT now(),
  validated_at timestamptz NOT NULL,
  CONSTRAINT chk_request_mode CHECK (
    request_mode IN ('ui', 'evaluation', 'batch')
  ),
  CONSTRAINT chk_budget_min_non_negative CHECK (
    budget_min IS NULL OR budget_min >= 0
  ),
  CONSTRAINT chk_budget_max_non_negative CHECK (
    budget_max IS NULL OR budget_max >= 0
  ),
  CONSTRAINT chk_budget_range CHECK (
    budget_min IS NULL
    OR budget_max IS NULL
    OR budget_min <= budget_max
  ),
  CONSTRAINT chk_top_k_range CHECK (
    top_k IS NULL OR (top_k >= 1 AND top_k <= 50)
  ),
  CONSTRAINT chk_candidate_limit_range CHECK (
    candidate_limit IS NULL OR candidate_limit >= 1
  ),
  CONSTRAINT chk_candidate_limit_gte_top_k CHECK (
    top_k IS NULL
    OR candidate_limit IS NULL
    OR candidate_limit >= top_k
  ),
  CONSTRAINT chk_preferred_text_length CHECK (
    preferred_text IS NULL OR char_length(preferred_text) <= 500
  ),
  CONSTRAINT chk_non_preferred_text_length CHECK (
    non_preferred_text IS NULL OR char_length(non_preferred_text) <= 500
  ),
  CONSTRAINT chk_ng_text_length CHECK (
    ng_text IS NULL OR char_length(ng_text) <= 300
  ),
  CONSTRAINT chk_free_text_length CHECK (
    free_text IS NULL OR char_length(free_text) <= 800
  ),
  CONSTRAINT chk_currency_mvp CHECK (currency = 'JPY')
);

CREATE INDEX idx_recommendation_request_created
  ON recommendation_request (created_at DESC);

CREATE INDEX idx_recommendation_request_mode_created
  ON recommendation_request (request_mode, created_at DESC);

CREATE INDEX idx_recommendation_request_relationship
  ON recommendation_request (relationship_code, created_at DESC);

CREATE INDEX idx_recommendation_request_occasion
  ON recommendation_request (occasion_code, created_at DESC);

CREATE INDEX idx_recommendation_request_trace
  ON recommendation_request (trace_id);

-- =============================================================================
-- 2. recommendation_run
-- =============================================================================
CREATE TABLE recommendation_run (
  recommendation_run_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_request_id uuid NOT NULL,
  pair_id uuid NOT NULL,
  semantic_config_version_id uuid NOT NULL,
  model_version_id uuid NOT NULL,
  ranking_config_id uuid NOT NULL,
  run_status varchar(32) NOT NULL DEFAULT 'accepted',
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT fk_recommendation_run_request
    FOREIGN KEY (recommendation_request_id)
    REFERENCES recommendation_request (recommendation_request_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_recommendation_run_pair
    FOREIGN KEY (pair_id)
    REFERENCES pair_master (pair_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_run_status CHECK (
    run_status IN (
      'accepted', 'running', 'succeeded', 'failed', 'canceled'
    )
  ),
  CONSTRAINT chk_run_started_before_completed CHECK (
    completed_at IS NULL
    OR started_at IS NULL
    OR started_at <= completed_at
  ),
  CONSTRAINT chk_run_completed_terminal CHECK (
    run_status NOT IN ('succeeded', 'failed', 'canceled')
    OR completed_at IS NOT NULL
  ),
  CONSTRAINT chk_run_nonterminal_no_completed CHECK (
    run_status NOT IN ('accepted', 'running')
    OR completed_at IS NULL
  )
);

CREATE INDEX idx_recommendation_run_request_id
  ON recommendation_run (recommendation_request_id);

CREATE INDEX idx_recommendation_run_status
  ON recommendation_run (run_status, started_at);

CREATE INDEX idx_recommendation_run_pair_id
  ON recommendation_run (pair_id);

CREATE INDEX idx_recommendation_run_semantic_config_version
  ON recommendation_run (semantic_config_version_id);

CREATE INDEX idx_recommendation_run_model_version
  ON recommendation_run (model_version_id);

CREATE INDEX idx_recommendation_run_ranking_config
  ON recommendation_run (ranking_config_id);

CREATE INDEX idx_recommendation_run_created
  ON recommendation_run (created_at DESC);

-- =============================================================================
-- 3. recommendation_result
-- =============================================================================
CREATE TABLE recommendation_result (
  recommendation_result_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_request_id uuid NOT NULL,
  recommendation_run_id uuid NOT NULL,
  request_mode varchar(32) NOT NULL,
  result_status varchar(32) NOT NULL,
  top_k integer NOT NULL,
  result_item_count integer NOT NULL DEFAULT 0,
  candidate_count integer,
  fallback_used boolean NOT NULL DEFAULT false,
  display_message text,
  caution_message text,
  semantic_config_version_id uuid NOT NULL,
  model_version_id uuid NOT NULL,
  ranking_config_id uuid NOT NULL,
  reason_template_version_id uuid,
  result_payload jsonb,
  debug_payload jsonb,
  trace_id text,
  generated_at timestamptz NOT NULL DEFAULT now(),
  displayed_at timestamptz,
  expired_at timestamptz,
  CONSTRAINT uq_result_per_run
    UNIQUE (recommendation_run_id),
  CONSTRAINT fk_result_request
    FOREIGN KEY (recommendation_request_id)
    REFERENCES recommendation_request (recommendation_request_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_result_run
    FOREIGN KEY (recommendation_run_id)
    REFERENCES recommendation_run (recommendation_run_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_result_status CHECK (
    result_status IN ('generated', 'empty', 'failed')
  ),
  CONSTRAINT chk_result_request_mode CHECK (
    request_mode IN ('ui', 'evaluation', 'batch')
  ),
  CONSTRAINT chk_top_k_range_result CHECK (
    top_k >= 1 AND top_k <= 50
  ),
  CONSTRAINT chk_result_item_count_non_negative CHECK (
    result_item_count >= 0
  ),
  CONSTRAINT chk_result_item_count_lte_top_k CHECK (
    result_item_count <= top_k
  ),
  CONSTRAINT chk_empty_status_consistency CHECK (
    result_status <> 'empty' OR result_item_count = 0
  ),
  CONSTRAINT chk_generated_status_consistency CHECK (
    result_status <> 'generated' OR result_item_count >= 1
  )
);

CREATE INDEX idx_recommendation_result_run_id
  ON recommendation_result (recommendation_run_id);

CREATE INDEX idx_recommendation_result_request_id
  ON recommendation_result (recommendation_request_id);

CREATE INDEX idx_recommendation_result_generated
  ON recommendation_result (generated_at DESC);

CREATE INDEX idx_recommendation_result_status
  ON recommendation_result (result_status, generated_at DESC);

CREATE INDEX idx_recommendation_result_trace
  ON recommendation_result (trace_id);

-- =============================================================================
-- 4. recommendation_result_item
-- =============================================================================
CREATE TABLE recommendation_result_item (
  recommendation_result_item_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_result_id uuid NOT NULL,
  item_id uuid NOT NULL,
  rank integer NOT NULL,
  final_score numeric(8, 6) NOT NULL,
  context_score numeric(8, 6) NOT NULL,
  score_breakdown_json jsonb,
  item_name_snapshot varchar(255) NOT NULL,
  item_catchcopy_snapshot varchar(500),
  item_price_snapshot integer NOT NULL,
  item_url_snapshot text NOT NULL,
  item_image_url_snapshot text,
  review_average_snapshot numeric(3, 2),
  review_count_snapshot integer,
  shop_name_snapshot text,
  is_displayed boolean NOT NULL DEFAULT true,
  is_fallback boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_result_item_result_rank
    UNIQUE (recommendation_result_id, rank),
  CONSTRAINT uq_result_item_result_item
    UNIQUE (recommendation_result_id, item_id),
  CONSTRAINT fk_result_item_result
    FOREIGN KEY (recommendation_result_id)
    REFERENCES recommendation_result (recommendation_result_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_result_item_item
    FOREIGN KEY (item_id)
    REFERENCES item (item_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_result_item_rank_positive CHECK (rank >= 1),
  CONSTRAINT chk_result_item_final_score_range CHECK (
    final_score >= 0 AND final_score <= 1
  ),
  CONSTRAINT chk_result_item_context_score_range CHECK (
    context_score >= 0 AND context_score <= 1
  ),
  CONSTRAINT chk_result_item_price_non_negative CHECK (
    item_price_snapshot >= 0
  ),
  CONSTRAINT chk_result_item_review_count CHECK (
    review_count_snapshot IS NULL OR review_count_snapshot >= 0
  ),
  CONSTRAINT chk_result_item_review_average CHECK (
    review_average_snapshot IS NULL
    OR (
      review_average_snapshot >= 0
      AND review_average_snapshot <= 5
    )
  )
);

CREATE INDEX idx_result_item_item_id
  ON recommendation_result_item (item_id);

-- =============================================================================
-- 5. recommendation_reason
-- =============================================================================
CREATE TABLE recommendation_reason (
  recommendation_reason_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_result_item_id uuid NOT NULL,
  template_id uuid NOT NULL,
  reason_summary text NOT NULL,
  reason_detail text,
  reason_points_json jsonb,
  reason_badges_json jsonb,
  caution_note text,
  reason_basis_json jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT fk_recommendation_reason_result_item
    FOREIGN KEY (recommendation_result_item_id)
    REFERENCES recommendation_result_item (recommendation_result_item_id)
    ON DELETE RESTRICT,
  CONSTRAINT uq_recommendation_reason_result_item
    UNIQUE (recommendation_result_item_id),
  CONSTRAINT chk_reason_summary_not_empty CHECK (
    length(trim(reason_summary)) > 0
  ),
  CONSTRAINT chk_reason_basis_json_object CHECK (
    jsonb_typeof(reason_basis_json) = 'object'
  )
);

CREATE INDEX idx_recommendation_reason_template_id
  ON recommendation_reason (template_id);

-- =============================================================================
-- 6. recommendation_feedback
-- =============================================================================
CREATE TABLE recommendation_feedback (
  recommendation_feedback_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  recommendation_result_id uuid NOT NULL,
  recommendation_result_item_id uuid,
  recommendation_reason_id uuid,
  recommendation_request_id uuid,
  recommendation_run_id uuid,
  feedback_target_type varchar(32) NOT NULL,
  feedback_type varchar(64) NOT NULL,
  feedback_value_type varchar(32) NOT NULL,
  feedback_value jsonb,
  feedback_choice_code varchar(64),
  feedback_text text,
  feedback_reason_category varchar(64),
  feedback_rating integer NOT NULL,
  is_positive boolean,
  is_negative boolean,
  rank_at_feedback integer,
  item_id uuid,
  session_id text,
  anonymous_user_id text,
  source_page varchar(64),
  user_agent text,
  feedback_status varchar(32) NOT NULL DEFAULT 'submitted',
  submitted_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz,
  CONSTRAINT fk_feedback_result
    FOREIGN KEY (recommendation_result_id)
    REFERENCES recommendation_result (recommendation_result_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_feedback_status CHECK (
    feedback_status IN ('submitted', 'invalid', 'ignored')
  ),
  CONSTRAINT chk_feedback_target_type CHECK (
    feedback_target_type IN ('result', 'item', 'reason')
  ),
  CONSTRAINT chk_feedback_value_type CHECK (
    feedback_value_type IN ('boolean', 'rating', 'choice', 'text', 'event')
  ),
  CONSTRAINT chk_feedback_type_mvp CHECK (
    feedback_type IN (
      'item_good',
      'item_bad',
      'item_not_match',
      'item_ng_violation',
      'item_avoid_match',
      'reason_good',
      'reason_bad',
      'result_good',
      'result_bad',
      'comment'
    )
  ),
  CONSTRAINT chk_feedback_rating_range CHECK (
    feedback_rating BETWEEN 1 AND 5
  ),
  CONSTRAINT chk_feedback_text_length CHECK (
    feedback_text IS NULL OR char_length(feedback_text) <= 500
  ),
  CONSTRAINT chk_feedback_user_agent_length CHECK (
    user_agent IS NULL OR char_length(user_agent) <= 500
  ),
  CONSTRAINT chk_feedback_target_result CHECK (
    feedback_target_type <> 'result'
    OR (
      recommendation_result_item_id IS NULL
      AND recommendation_reason_id IS NULL
    )
  ),
  CONSTRAINT chk_feedback_target_item CHECK (
    feedback_target_type <> 'item'
    OR recommendation_result_item_id IS NOT NULL
  ),
  CONSTRAINT chk_feedback_target_reason CHECK (
    feedback_target_type <> 'reason'
    OR recommendation_reason_id IS NOT NULL
  ),
  CONSTRAINT chk_feedback_type_target_item CHECK (
    (
      feedback_type IN (
        'item_good',
        'item_bad',
        'item_not_match',
        'item_ng_violation',
        'item_avoid_match'
      )
      AND feedback_target_type = 'item'
    )
    OR (
      feedback_type IN ('reason_good', 'reason_bad')
      AND feedback_target_type = 'reason'
    )
    OR (
      feedback_type IN ('result_good', 'result_bad')
      AND feedback_target_type = 'result'
    )
    OR (
      feedback_type = 'comment'
      AND feedback_target_type IN ('result', 'item', 'reason')
    )
  )
);

CREATE UNIQUE INDEX uq_feedback_session_result_type
  ON recommendation_feedback (session_id, recommendation_result_id, feedback_type)
  WHERE feedback_target_type = 'result' AND session_id IS NOT NULL;

CREATE UNIQUE INDEX uq_feedback_session_item_type
  ON recommendation_feedback (
    session_id,
    recommendation_result_item_id,
    feedback_type
  )
  WHERE feedback_target_type = 'item' AND session_id IS NOT NULL;

CREATE UNIQUE INDEX uq_feedback_session_reason_type
  ON recommendation_feedback (session_id, recommendation_reason_id, feedback_type)
  WHERE feedback_target_type = 'reason' AND session_id IS NOT NULL;

CREATE INDEX idx_recommendation_feedback_result_id
  ON recommendation_feedback (recommendation_result_id);

CREATE INDEX idx_recommendation_feedback_result_item_id
  ON recommendation_feedback (recommendation_result_item_id);

CREATE INDEX idx_recommendation_feedback_reason_id
  ON recommendation_feedback (recommendation_reason_id);

CREATE INDEX idx_recommendation_feedback_run_id
  ON recommendation_feedback (recommendation_run_id);

CREATE INDEX idx_recommendation_feedback_request_id
  ON recommendation_feedback (recommendation_request_id);

CREATE INDEX idx_recommendation_feedback_submitted
  ON recommendation_feedback (submitted_at DESC);

CREATE INDEX idx_recommendation_feedback_type_submitted
  ON recommendation_feedback (feedback_type, submitted_at DESC);

CREATE INDEX idx_recommendation_feedback_target_submitted
  ON recommendation_feedback (feedback_target_type, submitted_at DESC);

CREATE INDEX idx_recommendation_feedback_item_id
  ON recommendation_feedback (item_id);
