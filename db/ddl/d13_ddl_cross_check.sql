-- D13: DDL cross-check validation (Epic #435 gate)
-- change_id: d13_ddl_cross_check
-- Issue: #610
-- 正本: docs/06_実装設計/database/DDLバッチ分割表.md §17
-- 適用順: D01〜D12 適用後。本ファイルはスキーマ追加ではなく横断検証のみ。
-- 実行: psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f db/ddl/d13_ddl_cross_check.sql

-- =============================================================================
-- 0. ヘルパー: 期待値不一致時に例外を送出
-- =============================================================================
CREATE OR REPLACE FUNCTION _d13_assert_eq(p_label text, p_actual bigint, p_expected bigint)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  IF p_actual IS DISTINCT FROM p_expected THEN
    RAISE EXCEPTION '[D13] %: expected %, got %', p_label, p_expected, p_actual;
  END IF;
END;
$$;

CREATE OR REPLACE FUNCTION _d13_assert_missing_objects(p_label text, p_missing text[])
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
  IF array_length(p_missing, 1) IS NOT NULL THEN
    RAISE EXCEPTION '[D13] %: missing %', p_label, array_to_string(p_missing, ', ');
  END IF;
END;
$$;

-- =============================================================================
-- 1. pgvector 拡張
-- =============================================================================
DO $$
DECLARE
  v_count bigint;
BEGIN
  SELECT count(*) INTO v_count
  FROM pg_extension
  WHERE extname = 'vector';

  PERFORM _d13_assert_eq('vector extension', v_count, 1);
END;
$$;

-- =============================================================================
-- 2. enum 型 26 件（enum定義書 §5 / D01）
-- =============================================================================
DO $$
DECLARE
  v_expected constant text[] := ARRAY[
    'recommendation_run_status',
    'recommendation_result_status',
    'recommendation_feedback_status',
    'phase_status',
    'batch_run_status',
    'api_call_status',
    'raw_import_status',
    'fetch_cursor_status',
    'fetch_cursor_type',
    'source_api',
    'product_diff_status',
    'item_active_status',
    'item_generation_queue_status',
    'evaluation_run_status',
    'request_mode',
    'feedback_target_type',
    'feedback_type',
    'owner_type',
    'feature_code',
    'item_generation_type',
    'recommendation_run_phase_name',
    'batch_run_phase_name',
    'batch_type',
    'input_type',
    'application_method',
    'polarity'
  ];
  v_missing text[];
  v_count bigint;
BEGIN
  SELECT count(*) INTO v_count
  FROM pg_type t
  JOIN pg_namespace n ON n.oid = t.typnamespace
  WHERE t.typtype = 'e'
    AND n.nspname = 'public';

  PERFORM _d13_assert_eq('public enum type count', v_count, 26);

  SELECT coalesce(array_agg(e ORDER BY e), ARRAY[]::text[]) INTO v_missing
  FROM unnest(v_expected) AS e
  WHERE NOT EXISTS (
    SELECT 1
    FROM pg_type t
    JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE t.typname = e
      AND t.typtype = 'e'
      AND n.nspname = 'public'
  );

  PERFORM _d13_assert_missing_objects('enum types', v_missing);

  -- out_of_scope: evaluation_run_phase_name は D01 に含めない
  SELECT count(*) INTO v_count
  FROM pg_type t
  JOIN pg_namespace n ON n.oid = t.typnamespace
  WHERE t.typname = 'evaluation_run_phase_name'
    AND t.typtype = 'e'
    AND n.nspname = 'public';

  IF v_count <> 0 THEN
    RAISE EXCEPTION '[D13] evaluation_run_phase_name must not exist (out_of_scope), got %', v_count;
  END IF;
END;
$$;

-- =============================================================================
-- 3. public テーブル 62 件（DDLバッチ分割表 D02〜D11）
-- =============================================================================
DO $$
DECLARE
  v_expected constant text[] := ARRAY[
    -- D02
    'semantic_config', 'semantic_config_version', 'feature_definition', 'semantic_concept',
    'semantic_rule', 'relationship_rule', 'occasion_rule', 'pair_rule',
    'concept_feature_rule', 'input_type_rule', 'feature_integration_rule', 'normalization_rule',
    -- D03
    'relationship_master', 'occasion_master', 'pair_master', 'model_version',
    'ranking_config', 'reason_template', 'feature_normalization_version',
    -- D04
    'external_genre', 'item', 'item_image', 'item_review_summary',
    'external_attribute', 'ranking_snapshot', 'item_popularity_signal',
    -- D05
    'fetch_cursor', 'api_call_log', 'raw_product_metadata', 'staging_item',
    'staging_item_image', 'staging_ranking_signal', 'staging_genre',
    'staging_attribute', 'product_diff_result', 'item_import_summary',
    -- D06
    'item_generation_queue', 'item_semantic', 'item_feature', 'item_meaning', 'item_embedding',
    -- D07
    'recommendation_request', 'recommendation_run', 'recommendation_result',
    'recommendation_result_item', 'recommendation_reason', 'recommendation_feedback',
    -- D08
    'user_semantic', 'user_feature', 'user_meaning',
    -- D09
    'evaluation_dataset', 'evaluation_case', 'evaluation_run', 'evaluation_result', 'evaluation_metric',
    -- D10
    'batch_run_log', 'phase_log', 'error_log',
    -- D11
    'feature_distribution_metric', 'meaning_distribution_metric',
    'normalization_distribution_metric', 'reco_score_distribution_metric'
  ];
  v_missing text[];
  v_count bigint;
BEGIN
  SELECT count(*) INTO v_count
  FROM information_schema.tables
  WHERE table_schema = 'public'
    AND table_type = 'BASE TABLE';

  PERFORM _d13_assert_eq('public table count', v_count, 62);

  SELECT coalesce(array_agg(e ORDER BY e), ARRAY[]::text[]) INTO v_missing
  FROM unnest(v_expected) AS e
  WHERE NOT EXISTS (
    SELECT 1
    FROM information_schema.tables t
    WHERE t.table_schema = 'public'
      AND t.table_name = e
      AND t.table_type = 'BASE TABLE'
  );

  PERFORM _d13_assert_missing_objects('tables', v_missing);
END;
$$;

-- =============================================================================
-- 4. D12 延期物理 FK 5 件
-- =============================================================================
DO $$
DECLARE
  v_expected constant text[] := ARRAY[
    'fk_normalization_rule_feature_normalization_version',
    'fk_fdm_semantic_config_version_id',
    'fk_mdm_semantic_config_version_id',
    'fk_ndm_semantic_config_version_id',
    'fk_rsdm_semantic_config_version_id'
  ];
  v_missing text[];
BEGIN
  SELECT coalesce(array_agg(c ORDER BY c), ARRAY[]::text[]) INTO v_missing
  FROM unnest(v_expected) AS c
  WHERE NOT EXISTS (
    SELECT 1
    FROM pg_constraint con
    JOIN pg_namespace n ON n.oid = con.connamespace
    WHERE con.conname = c
      AND con.contype = 'f'
      AND n.nspname = 'public'
  );

  PERFORM _d13_assert_missing_objects('deferred foreign keys (D12)', v_missing);
END;
$$;

-- =============================================================================
-- 5. D06 HNSW 索引（D12 で重複作成しない方針）
-- =============================================================================
DO $$
DECLARE
  v_count bigint;
BEGIN
  SELECT count(*) INTO v_count
  FROM pg_indexes
  WHERE schemaname = 'public'
    AND tablename = 'item_embedding'
    AND indexname = 'idx_item_embedding_vector';

  PERFORM _d13_assert_eq('item_embedding HNSW index', v_count, 1);
END;
$$;

-- =============================================================================
-- 6. 論理 ID 分離: run_status / phase_name 用 enum
-- =============================================================================
DO $$
DECLARE
  v_count bigint;
BEGIN
  SELECT count(*) INTO v_count
  FROM pg_type t
  JOIN pg_namespace n ON n.oid = t.typnamespace
  WHERE t.typname IN ('recommendation_run_status', 'batch_run_status')
    AND t.typtype = 'e'
    AND n.nspname = 'public';

  PERFORM _d13_assert_eq('run_status logical enum split', v_count, 2);

  SELECT count(*) INTO v_count
  FROM pg_type t
  JOIN pg_namespace n ON n.oid = t.typnamespace
  WHERE t.typname IN ('recommendation_run_phase_name', 'batch_run_phase_name')
    AND t.typtype = 'e'
    AND n.nspname = 'public';

  PERFORM _d13_assert_eq('phase_name logical enum split', v_count, 2);
END;
$$;

-- =============================================================================
-- 7. サマリ出力（成功時）
-- =============================================================================
DO $$
BEGIN
  RAISE NOTICE '[D13] cross-check passed: vector extension, 26 enums, 62 tables, 5 deferred FKs, HNSW index, logical ID separation';
END;
$$;

-- 検証用ヘルパー関数は残さない
DROP FUNCTION IF EXISTS _d13_assert_missing_objects(text, text[]);
DROP FUNCTION IF EXISTS _d13_assert_eq(text, bigint, bigint);
