-- D05: External product integration tables
-- change_id: d05_external_product_integration
-- Issue: #602
-- 正本: docs/06_実装設計/database/*_テーブル定義書.md（D05 対象 10 件）
-- 適用順: D01〜D04 適用後。fetch_cursor → api_call_log → raw_product_metadata → Staging 系 → product_diff_result → item_import_summary
-- MVP△: staging_attribute（DDL 参照用に含む。DDLバッチ分割表 §3）
-- LOGICAL 参照: Staging / Log 系は物理 FK なし（batch_run_log / item / external_genre / external_attribute 含む）

-- =============================================================================
-- 1. fetch_cursor
-- =============================================================================
CREATE TABLE fetch_cursor (
  fetch_cursor_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source text NOT NULL DEFAULT 'rakuten',
  source_api varchar(32) NOT NULL DEFAULT 'item_search',
  target_external_genre_id bigint,
  cursor_type varchar(32) NOT NULL,
  cursor_value jsonb NOT NULL DEFAULT '{}',
  last_fetched_at timestamptz,
  cursor_status varchar(32) NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  cursor_scope_fingerprint text GENERATED ALWAYS AS (
    md5(
      coalesce(target_external_genre_id::text, '')
      || cursor_type
      || coalesce((cursor_value -> 'scope')::text, '')
    )
  ) STORED,
  CONSTRAINT uq_fetch_cursor_scope
    UNIQUE (
      source,
      source_api,
      cursor_type,
      target_external_genre_id,
      cursor_scope_fingerprint
    ),
  CONSTRAINT chk_fetch_cursor_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_fetch_cursor_source_api_mvp CHECK (source_api = 'item_search'),
  CONSTRAINT chk_fetch_cursor_type CHECK (
    cursor_type IN (
      'genre',
      'keyword',
      'update_sort',
      'ranking_supplement',
      'recheck'
    )
  ),
  CONSTRAINT chk_fetch_cursor_status CHECK (
    cursor_status IN ('active', 'paused', 'exhausted', 'failed')
  ),
  CONSTRAINT chk_fetch_cursor_genre_requires_target CHECK (
    cursor_type <> 'genre' OR target_external_genre_id IS NOT NULL
  )
);

CREATE INDEX idx_fetch_cursor_status
  ON fetch_cursor (cursor_status, updated_at);

CREATE INDEX idx_fetch_cursor_genre
  ON fetch_cursor (target_external_genre_id);

CREATE INDEX idx_fetch_cursor_source_api
  ON fetch_cursor (source, source_api, cursor_type);

-- =============================================================================
-- 2. api_call_log
-- =============================================================================
CREATE TABLE api_call_log (
  api_call_log_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_run_id uuid NOT NULL,
  fetch_cursor_id uuid,
  trace_id text,
  source text NOT NULL DEFAULT 'rakuten',
  source_api varchar(32) NOT NULL,
  request_params_hash text NOT NULL,
  request_params_json jsonb NOT NULL DEFAULT '{}',
  api_version varchar(32),
  response_status integer,
  call_status varchar(32) NOT NULL DEFAULT 'requested',
  item_count integer NOT NULL DEFAULT 0,
  requested_at timestamptz NOT NULL,
  completed_at timestamptz,
  duration_ms integer,
  error_code varchar(64),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT chk_api_call_log_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_api_call_log_source_api CHECK (
    source_api IN (
      'item_search',
      'item_ranking',
      'genre_search',
      'attribute_search'
    )
  ),
  CONSTRAINT chk_api_call_log_status CHECK (
    call_status IN (
      'requested',
      'succeeded',
      'failed',
      'rate_limited',
      'skipped'
    )
  ),
  CONSTRAINT chk_api_call_log_item_count_nonneg CHECK (item_count >= 0),
  CONSTRAINT chk_api_call_log_duration_nonneg CHECK (
    duration_ms IS NULL OR duration_ms >= 0
  ),
  CONSTRAINT chk_api_call_log_terminal_completed CHECK (
    call_status = 'requested' OR completed_at IS NOT NULL
  )
);

CREATE INDEX idx_api_call_log_batch
  ON api_call_log (batch_run_id, requested_at);

CREATE INDEX idx_api_call_log_fetch_cursor
  ON api_call_log (fetch_cursor_id, requested_at);

CREATE INDEX idx_api_call_log_status
  ON api_call_log (call_status, requested_at);

CREATE INDEX idx_api_call_log_source_api
  ON api_call_log (source_api, requested_at);

CREATE INDEX idx_api_call_log_trace
  ON api_call_log (trace_id);

-- =============================================================================
-- 3. raw_product_metadata
-- =============================================================================
CREATE TABLE raw_product_metadata (
  raw_metadata_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  api_call_log_id uuid,
  object_key text NOT NULL,
  source text NOT NULL DEFAULT 'rakuten',
  source_api varchar(32) NOT NULL,
  content_hash text NOT NULL,
  item_count integer NOT NULL DEFAULT 0,
  import_status varchar(32) NOT NULL DEFAULT 'raw_saved',
  fetched_at timestamptz NOT NULL,
  staged_at timestamptz,
  imported_at timestamptz,
  error_code varchar(64),
  error_message text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_raw_product_metadata_object_key UNIQUE (object_key),
  CONSTRAINT chk_raw_metadata_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_raw_metadata_source_api CHECK (
    source_api IN (
      'item_search',
      'item_ranking',
      'genre_search',
      'attribute_search'
    )
  ),
  CONSTRAINT chk_raw_metadata_import_status CHECK (
    import_status IN (
      'raw_saved',
      'staged',
      'imported',
      'skipped',
      'failed'
    )
  ),
  CONSTRAINT chk_raw_metadata_item_count CHECK (item_count >= 0),
  CONSTRAINT chk_raw_metadata_staged_at CHECK (
    import_status NOT IN ('staged', 'imported') OR staged_at IS NOT NULL
  ),
  CONSTRAINT chk_raw_metadata_imported_at CHECK (
    import_status NOT IN ('imported', 'skipped') OR imported_at IS NOT NULL
  ),
  CONSTRAINT chk_raw_metadata_failed_error CHECK (
    import_status <> 'failed' OR error_message IS NOT NULL
  )
);

CREATE INDEX idx_raw_metadata_status
  ON raw_product_metadata (import_status, fetched_at);

CREATE INDEX idx_raw_metadata_api_call_log
  ON raw_product_metadata (api_call_log_id);

CREATE INDEX idx_raw_metadata_source_api
  ON raw_product_metadata (source, source_api, fetched_at DESC);

-- =============================================================================
-- 4. staging_item
-- =============================================================================
CREATE TABLE staging_item (
  staging_item_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_metadata_id uuid NOT NULL,
  source text NOT NULL DEFAULT 'rakuten',
  external_item_code text NOT NULL,
  item_name varchar(255) NOT NULL,
  item_caption text,
  catchcopy varchar(500),
  price integer NOT NULL,
  item_url text NOT NULL,
  external_genre_id bigint,
  shop_code text,
  availability smallint,
  review_average numeric(3, 2),
  review_count integer,
  normalized_hash varchar(64) NOT NULL,
  diff_status varchar(32),
  staged_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_staging_item_raw_metadata_code
    UNIQUE (raw_metadata_id, external_item_code),
  CONSTRAINT chk_staging_item_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_staging_item_price_non_negative CHECK (price >= 0),
  CONSTRAINT chk_staging_item_review_count CHECK (
    review_count IS NULL OR review_count >= 0
  ),
  CONSTRAINT chk_staging_item_diff_status CHECK (
    diff_status IS NULL
    OR diff_status IN ('new', 'updated', 'unchanged', 'unavailable')
  ),
  CONSTRAINT chk_staging_item_availability CHECK (
    availability IS NULL OR availability IN (0, 1)
  )
);

CREATE INDEX idx_staging_item_raw_metadata
  ON staging_item (raw_metadata_id);

CREATE INDEX idx_staging_item_source_code
  ON staging_item (source, external_item_code);

CREATE INDEX idx_staging_item_diff_status
  ON staging_item (diff_status);

-- =============================================================================
-- 5. staging_item_image
-- =============================================================================
CREATE TABLE staging_item_image (
  staging_item_image_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_metadata_id uuid NOT NULL,
  external_item_code text NOT NULL,
  image_url text NOT NULL,
  image_size_type text NOT NULL,
  display_order integer NOT NULL DEFAULT 0,
  is_primary_candidate boolean NOT NULL DEFAULT false,
  staged_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_staging_item_image_raw_code_url
    UNIQUE (raw_metadata_id, external_item_code, image_url),
  CONSTRAINT chk_staging_item_image_size_type CHECK (
    image_size_type IN ('small', 'medium')
  ),
  CONSTRAINT chk_staging_item_image_display_order CHECK (display_order >= 0),
  CONSTRAINT chk_staging_item_image_url_not_empty CHECK (
    char_length(trim(image_url)) > 0
  )
);

CREATE UNIQUE INDEX uq_staging_item_image_primary_candidate
  ON staging_item_image (raw_metadata_id, external_item_code)
  WHERE is_primary_candidate = true;

CREATE INDEX idx_staging_item_image_raw_metadata
  ON staging_item_image (raw_metadata_id);

CREATE INDEX idx_staging_item_image_raw_code
  ON staging_item_image (raw_metadata_id, external_item_code);

-- =============================================================================
-- 6. staging_ranking_signal
-- =============================================================================
CREATE TABLE staging_ranking_signal (
  staging_ranking_signal_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_metadata_id uuid NOT NULL,
  external_item_code text NOT NULL,
  external_genre_id bigint NOT NULL,
  rank integer NOT NULL,
  period varchar(32) NOT NULL,
  last_build_date timestamptz NOT NULL,
  staged_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_staging_ranking_signal_raw_metadata_rank
    UNIQUE (raw_metadata_id, rank),
  CONSTRAINT chk_staging_ranking_signal_rank_positive CHECK (rank >= 1),
  CONSTRAINT chk_staging_ranking_signal_period_length CHECK (
    char_length(period) BETWEEN 1 AND 32
  ),
  CONSTRAINT chk_staging_ranking_signal_genre_non_negative CHECK (
    external_genre_id >= 0
  )
);

CREATE INDEX idx_staging_ranking_signal_raw_metadata
  ON staging_ranking_signal (raw_metadata_id);

CREATE INDEX idx_staging_ranking_signal_item_code
  ON staging_ranking_signal (external_item_code);

CREATE INDEX idx_staging_ranking_signal_observation
  ON staging_ranking_signal (external_genre_id, period, last_build_date);

-- =============================================================================
-- 7. staging_genre
-- =============================================================================
CREATE TABLE staging_genre (
  staging_genre_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_metadata_id uuid NOT NULL,
  source text NOT NULL DEFAULT 'rakuten',
  external_genre_id bigint NOT NULL,
  genre_name varchar(255) NOT NULL,
  parent_external_genre_id bigint,
  genre_level smallint NOT NULL,
  is_leaf boolean NOT NULL DEFAULT false,
  staged_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_staging_genre_raw_metadata_genre
    UNIQUE (raw_metadata_id, external_genre_id),
  CONSTRAINT chk_staging_genre_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_staging_genre_level_range CHECK (
    genre_level >= 0 AND genre_level <= 5
  ),
  CONSTRAINT chk_staging_genre_name_length CHECK (
    char_length(genre_name) BETWEEN 1 AND 255
  ),
  CONSTRAINT chk_staging_genre_parent_not_self CHECK (
    parent_external_genre_id IS NULL
    OR parent_external_genre_id <> external_genre_id
  )
);

CREATE INDEX idx_staging_genre_raw_metadata
  ON staging_genre (raw_metadata_id);

CREATE INDEX idx_staging_genre_source_id
  ON staging_genre (source, external_genre_id);

-- =============================================================================
-- 8. staging_attribute（MVP△）
-- =============================================================================
CREATE TABLE staging_attribute (
  staging_attribute_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_metadata_id uuid NOT NULL,
  source text NOT NULL DEFAULT 'rakuten',
  external_genre_id bigint NOT NULL,
  external_attribute_id bigint NOT NULL,
  attribute_name varchar(255) NOT NULL,
  attribute_group_name varchar(255),
  staged_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_staging_attribute_raw_metadata_attr
    UNIQUE (raw_metadata_id, external_genre_id, external_attribute_id),
  CONSTRAINT chk_staging_attribute_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_staging_attribute_name_length CHECK (
    char_length(attribute_name) BETWEEN 1 AND 255
  ),
  CONSTRAINT chk_staging_attribute_group_length CHECK (
    attribute_group_name IS NULL
    OR char_length(attribute_group_name) BETWEEN 1 AND 255
  ),
  CONSTRAINT chk_staging_attribute_id_positive CHECK (external_attribute_id > 0)
);

CREATE INDEX idx_staging_attribute_raw_metadata
  ON staging_attribute (raw_metadata_id);

CREATE INDEX idx_staging_attribute_source_genre_attr
  ON staging_attribute (source, external_genre_id, external_attribute_id);

-- =============================================================================
-- 9. product_diff_result
-- =============================================================================
CREATE TABLE product_diff_result (
  product_diff_result_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_run_id uuid NOT NULL,
  staging_item_id uuid NOT NULL,
  external_item_code text NOT NULL,
  old_hash varchar(64),
  new_hash varchar(64) NOT NULL,
  diff_status varchar(32) NOT NULL,
  judged_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_product_diff_batch_code
    UNIQUE (batch_run_id, external_item_code),
  CONSTRAINT chk_product_diff_status CHECK (
    diff_status IN ('new', 'updated', 'unchanged', 'unavailable')
  ),
  CONSTRAINT chk_product_diff_new_hash CHECK (length(new_hash) = 64),
  CONSTRAINT chk_product_diff_old_hash_len CHECK (
    old_hash IS NULL OR length(old_hash) = 64
  ),
  CONSTRAINT chk_product_diff_new_old_consistency CHECK (
    diff_status <> 'new' OR old_hash IS NULL
  ),
  CONSTRAINT chk_product_diff_updated_old CHECK (
    diff_status NOT IN ('updated', 'unchanged') OR old_hash IS NOT NULL
  )
);

CREATE INDEX idx_product_diff_staging_item
  ON product_diff_result (staging_item_id);

CREATE INDEX idx_product_diff_status
  ON product_diff_result (batch_run_id, diff_status);

-- =============================================================================
-- 10. item_import_summary
-- =============================================================================
CREATE TABLE item_import_summary (
  item_import_summary_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_run_id uuid NOT NULL,
  source text NOT NULL DEFAULT 'rakuten',
  source_api varchar(32) NOT NULL,
  fetched_count integer NOT NULL DEFAULT 0,
  new_count integer NOT NULL DEFAULT 0,
  updated_count integer NOT NULL DEFAULT 0,
  unchanged_count integer NOT NULL DEFAULT 0,
  unavailable_count integer NOT NULL DEFAULT 0,
  skipped_count integer NOT NULL DEFAULT 0,
  failed_count integer NOT NULL DEFAULT 0,
  feature_generated_count integer NOT NULL DEFAULT 0,
  embedding_generated_count integer NOT NULL DEFAULT 0,
  summarized_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_item_import_summary_run_api
    UNIQUE (batch_run_id, source_api),
  CONSTRAINT chk_item_import_summary_source CHECK (source = 'rakuten'),
  CONSTRAINT chk_item_import_summary_source_api CHECK (
    source_api IN (
      'item_search',
      'item_ranking',
      'genre_search',
      'attribute_search'
    )
  ),
  CONSTRAINT chk_item_import_summary_counts_nonneg CHECK (
    fetched_count >= 0
    AND new_count >= 0
    AND updated_count >= 0
    AND unchanged_count >= 0
    AND unavailable_count >= 0
    AND skipped_count >= 0
    AND failed_count >= 0
    AND feature_generated_count >= 0
    AND embedding_generated_count >= 0
  )
);

CREATE INDEX idx_item_import_summary_run
  ON item_import_summary (batch_run_id, summarized_at DESC);

CREATE INDEX idx_item_import_summary_source_api
  ON item_import_summary (source_api, summarized_at DESC);
