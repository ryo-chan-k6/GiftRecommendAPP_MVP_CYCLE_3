-- D04: Item tables
-- change_id: d04_item
-- Issue: #601
-- 正本: docs/06_実装設計/database/*_テーブル定義書.md（D04 対象 7 件）
-- 適用順: D01 / D02 / D03 適用後。external_genre → item → 子テーブル → ranking_snapshot → item_popularity_signal
-- MVP△: external_attribute（DDL 参照用に含む。DDLバッチ分割表 §3）
-- LOGICAL 参照: item / ranking_snapshot / item_popularity_signal → external_genre（物理 FK なし）
-- LOGICAL 参照: item_popularity_signal.item_id → item（nullable・物理 FK なし）

-- =============================================================================
-- 1. external_genre
-- =============================================================================
CREATE TABLE external_genre (
  external_genre_id bigint PRIMARY KEY,
  source text NOT NULL DEFAULT 'rakuten',
  genre_name varchar(255) NOT NULL,
  parent_external_genre_id bigint,
  genre_level smallint NOT NULL,
  is_leaf boolean NOT NULL DEFAULT false,
  fetched_at timestamptz NOT NULL,
  CONSTRAINT uq_external_genre_source_id
    UNIQUE (source, external_genre_id),
  CONSTRAINT fk_external_genre_parent
    FOREIGN KEY (parent_external_genre_id)
    REFERENCES external_genre (external_genre_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_external_genre_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_external_genre_level_range CHECK (
    genre_level >= 0 AND genre_level <= 5
  ),
  CONSTRAINT chk_external_genre_name_length CHECK (
    char_length(genre_name) BETWEEN 1 AND 255
  ),
  CONSTRAINT chk_external_genre_parent_not_self CHECK (
    parent_external_genre_id IS NULL
    OR parent_external_genre_id <> external_genre_id
  )
);

CREATE INDEX idx_external_genre_parent
  ON external_genre (parent_external_genre_id);

CREATE INDEX idx_external_genre_level_leaf
  ON external_genre (genre_level, is_leaf);

-- =============================================================================
-- 2. item
-- =============================================================================
CREATE TABLE item (
  item_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source text NOT NULL DEFAULT 'rakuten',
  external_item_code text NOT NULL,
  item_name varchar(255) NOT NULL,
  item_caption text,
  catchcopy varchar(500),
  price integer NOT NULL,
  item_url text NOT NULL,
  external_genre_id bigint,
  shop_code text,
  normalized_hash varchar(64) NOT NULL,
  active_status text NOT NULL DEFAULT 'active',
  is_active boolean NOT NULL DEFAULT true,
  first_fetched_at timestamptz NOT NULL,
  last_checked_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_item_source_external_code
    UNIQUE (source, external_item_code),
  CONSTRAINT chk_item_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_item_price_non_negative CHECK (price >= 0),
  CONSTRAINT chk_item_active_status CHECK (
    active_status IN ('active', 'inactive', 'unavailable', 'excluded')
  ),
  CONSTRAINT chk_item_active_status_is_active CHECK (
    is_active = (active_status = 'active')
  )
);

CREATE INDEX idx_item_active_status
  ON item (active_status, is_active);

-- =============================================================================
-- 3. item_image
-- =============================================================================
CREATE TABLE item_image (
  item_image_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id uuid NOT NULL,
  image_url text NOT NULL,
  image_size_type text NOT NULL,
  display_order integer NOT NULL DEFAULT 0,
  is_primary boolean NOT NULL DEFAULT false,
  fetched_at timestamptz NOT NULL,
  CONSTRAINT uq_item_image_item_url
    UNIQUE (item_id, image_url),
  CONSTRAINT fk_item_image_item_id
    FOREIGN KEY (item_id)
    REFERENCES item (item_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_item_image_size_type CHECK (
    image_size_type IN ('small', 'medium')
  ),
  CONSTRAINT chk_item_image_display_order CHECK (display_order >= 0),
  CONSTRAINT chk_item_image_url_not_empty CHECK (
    char_length(trim(image_url)) > 0
  )
);

CREATE UNIQUE INDEX uq_item_image_primary_per_item
  ON item_image (item_id)
  WHERE is_primary = true;

CREATE INDEX idx_item_image_item_id
  ON item_image (item_id);

-- =============================================================================
-- 4. item_review_summary
-- =============================================================================
CREATE TABLE item_review_summary (
  item_review_summary_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  item_id uuid NOT NULL,
  review_average numeric(3, 1),
  review_count integer NOT NULL,
  fetched_at timestamptz NOT NULL,
  CONSTRAINT uq_item_review_summary_item_id
    UNIQUE (item_id),
  CONSTRAINT fk_item_review_summary_item_id
    FOREIGN KEY (item_id)
    REFERENCES item (item_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_item_review_summary_count_nonneg CHECK (review_count >= 0),
  CONSTRAINT chk_item_review_summary_average_range CHECK (
    review_average IS NULL
    OR (review_average >= 0 AND review_average <= 5)
  ),
  CONSTRAINT chk_item_review_summary_average_when_count CHECK (
    review_count = 0 OR review_average IS NOT NULL
  )
);

CREATE INDEX idx_item_review_summary_item_id
  ON item_review_summary (item_id);

-- =============================================================================
-- 5. external_attribute（MVP△）
-- =============================================================================
CREATE TABLE external_attribute (
  source text NOT NULL DEFAULT 'rakuten',
  external_genre_id bigint NOT NULL,
  external_attribute_id bigint NOT NULL,
  attribute_name varchar(255) NOT NULL,
  attribute_group_name varchar(255),
  fetched_at timestamptz NOT NULL,
  PRIMARY KEY (source, external_genre_id, external_attribute_id),
  CONSTRAINT chk_external_attribute_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_external_attribute_name_length CHECK (
    char_length(attribute_name) BETWEEN 1 AND 255
  ),
  CONSTRAINT chk_external_attribute_group_length CHECK (
    attribute_group_name IS NULL
    OR char_length(attribute_group_name) BETWEEN 1 AND 255
  ),
  CONSTRAINT chk_external_attribute_id_positive CHECK (
    external_attribute_id > 0
  )
);

CREATE INDEX idx_external_attribute_genre
  ON external_attribute (external_genre_id);

CREATE INDEX idx_external_attribute_name
  ON external_attribute (attribute_name);

-- =============================================================================
-- 6. ranking_snapshot
-- =============================================================================
CREATE TABLE ranking_snapshot (
  ranking_snapshot_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source text NOT NULL DEFAULT 'rakuten',
  external_genre_id bigint NOT NULL,
  period varchar(32) NOT NULL,
  last_build_date timestamptz NOT NULL,
  fetched_at timestamptz NOT NULL,
  batch_run_id uuid,
  api_call_log_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_ranking_snapshot_observation_key
    UNIQUE (source, external_genre_id, period, last_build_date),
  CONSTRAINT chk_ranking_snapshot_source_mvp CHECK (source = 'rakuten'),
  CONSTRAINT chk_ranking_snapshot_period_length CHECK (
    char_length(period) BETWEEN 1 AND 32
  ),
  CONSTRAINT chk_ranking_snapshot_genre_positive CHECK (external_genre_id >= 0)
);

CREATE INDEX idx_ranking_snapshot_genre_fetched
  ON ranking_snapshot (external_genre_id, fetched_at DESC);

CREATE INDEX idx_ranking_snapshot_batch_run
  ON ranking_snapshot (batch_run_id);

-- =============================================================================
-- 7. item_popularity_signal
-- =============================================================================
CREATE TABLE item_popularity_signal (
  item_popularity_signal_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ranking_snapshot_id uuid NOT NULL,
  item_id uuid,
  external_item_code text NOT NULL,
  external_genre_id bigint NOT NULL,
  rank integer NOT NULL,
  period varchar(32) NOT NULL,
  last_build_date timestamptz NOT NULL,
  fetched_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_ips_snapshot_rank
    UNIQUE (ranking_snapshot_id, rank),
  CONSTRAINT fk_ips_ranking_snapshot_id
    FOREIGN KEY (ranking_snapshot_id)
    REFERENCES ranking_snapshot (ranking_snapshot_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_ips_rank_positive CHECK (rank >= 1),
  CONSTRAINT chk_ips_period_length CHECK (
    char_length(period) BETWEEN 1 AND 32
  ),
  CONSTRAINT chk_ips_external_item_code_not_empty CHECK (
    char_length(trim(external_item_code)) > 0
  ),
  CONSTRAINT chk_ips_genre_positive CHECK (external_genre_id >= 0),
  CONSTRAINT chk_ips_item_or_code CHECK (
    item_id IS NOT NULL
    OR char_length(trim(external_item_code)) > 0
  )
);

CREATE INDEX idx_ips_ranking_snapshot_id
  ON item_popularity_signal (ranking_snapshot_id);

CREATE INDEX idx_ips_item_id
  ON item_popularity_signal (item_id);

CREATE INDEX idx_ips_external_item_code
  ON item_popularity_signal (external_item_code);

CREATE INDEX idx_ips_genre_period
  ON item_popularity_signal (external_genre_id, period);
