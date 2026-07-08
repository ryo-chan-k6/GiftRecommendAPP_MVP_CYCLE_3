-- D12: Deferred foreign keys and follow-up indexes
-- change_id: d12_deferred_fk_indexes
-- Issue: #609
-- 正本: docs/06_実装設計/database/物理ER.md §9・§11、各テーブル定義書 §8〜§10
-- 適用順: D01〜D11 適用後。
-- 延期 FK 棚卸し（D02〜D11 DDL コメント）:
--   normalization_rule.feature_normalization_version_id → feature_normalization_version（D02/D03）
--   Metric 4 テーブル.semantic_config_version_id → semantic_config_version（D11）
-- 索引: item_embedding HNSW（idx_item_embedding_vector）は D06 作成済みのため本ファイルでは追加しない

-- =============================================================================
-- 1. normalization_rule → feature_normalization_version
-- =============================================================================
ALTER TABLE normalization_rule
  ADD CONSTRAINT fk_normalization_rule_feature_normalization_version
  FOREIGN KEY (feature_normalization_version_id)
  REFERENCES feature_normalization_version (feature_normalization_version_id)
  ON DELETE RESTRICT;

-- =============================================================================
-- 2. feature_distribution_metric → semantic_config_version
-- =============================================================================
ALTER TABLE feature_distribution_metric
  ADD CONSTRAINT fk_fdm_semantic_config_version_id
  FOREIGN KEY (semantic_config_version_id)
  REFERENCES semantic_config_version (semantic_config_version_id)
  ON DELETE RESTRICT;

-- =============================================================================
-- 3. meaning_distribution_metric → semantic_config_version
-- =============================================================================
ALTER TABLE meaning_distribution_metric
  ADD CONSTRAINT fk_mdm_semantic_config_version_id
  FOREIGN KEY (semantic_config_version_id)
  REFERENCES semantic_config_version (semantic_config_version_id)
  ON DELETE RESTRICT;

-- =============================================================================
-- 4. normalization_distribution_metric → semantic_config_version
-- =============================================================================
ALTER TABLE normalization_distribution_metric
  ADD CONSTRAINT fk_ndm_semantic_config_version_id
  FOREIGN KEY (semantic_config_version_id)
  REFERENCES semantic_config_version (semantic_config_version_id)
  ON DELETE RESTRICT;

-- =============================================================================
-- 5. reco_score_distribution_metric → semantic_config_version
-- =============================================================================
ALTER TABLE reco_score_distribution_metric
  ADD CONSTRAINT fk_rsdm_semantic_config_version_id
  FOREIGN KEY (semantic_config_version_id)
  REFERENCES semantic_config_version (semantic_config_version_id)
  ON DELETE RESTRICT;
