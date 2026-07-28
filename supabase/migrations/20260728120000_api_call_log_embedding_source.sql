-- Wave 5 / Issue #1710: api_call_log を BATCH-015 Embedding 呼出監査に対応させる。
-- Human 確定 §8.4 案 B: source=openai / source_api=item_embedding
--
-- 対象: api_call_log の CHECK のみ。
-- 非対象（変更禁止）: raw_product_metadata / item_import_summary / fetch_cursor の CHECK。
--
-- 注: api_call_log.source_api 列は varchar + CHECK（ENUM 型列ではない）。
--     ALTER TYPE source_api ADD VALUE は code-definition / enum 正本との整合用。

-- ---------------------------------------------------------------------------
-- 1) Postgres ENUM source_api に item_embedding を追加（冪等）
--    PG12+ ではトランザクション内 ADD VALUE 可。同一 TX 内で ENUM 列へ即利用は
--    制約があるが、本 migration の CHECK は文字列リテラルのため問題なし。
-- ---------------------------------------------------------------------------
ALTER TYPE source_api ADD VALUE IF NOT EXISTS 'item_embedding';

-- ---------------------------------------------------------------------------
-- 2) chk_api_call_log_source_mvp: rakuten | openai
--    openai は外部 Embedding API 提供者識別。item.source（マーケット）とは別概念。
-- ---------------------------------------------------------------------------
ALTER TABLE api_call_log DROP CONSTRAINT IF EXISTS chk_api_call_log_source_mvp;

ALTER TABLE api_call_log
  ADD CONSTRAINT chk_api_call_log_source_mvp
  CHECK (source IN ('rakuten', 'openai'));

-- ---------------------------------------------------------------------------
-- 3) chk_api_call_log_source_api: 既存 4 値 + item_embedding
-- ---------------------------------------------------------------------------
ALTER TABLE api_call_log DROP CONSTRAINT IF EXISTS chk_api_call_log_source_api;

ALTER TABLE api_call_log
  ADD CONSTRAINT chk_api_call_log_source_api
  CHECK (
    source_api IN (
      'item_search',
      'item_ranking',
      'genre_search',
      'attribute_search',
      'item_embedding'
    )
  );
