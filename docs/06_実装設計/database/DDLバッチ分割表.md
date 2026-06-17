# DDLバッチ分割表（Phase2 ④）

## 1. ドキュメント情報

| 項目 | 内容 |
| ---- | ---- |
| ドキュメントID | `DB-DDL-BATCH-MVP-001` |
| 親 Epic | #435 `docs/epic-435-db-physical-design` |
| 正本関係 | 運用規約は [マイグレーション方針書.md](./マイグレーション方針書.md)。本書は **④ DDL Task 起票・進捗管理の正本** |
| 更新日 | 2026-06-17（D01〜D13 merge 完了反映） |

---

## 2. 運用ルール

| ルール | 内容 |
| ------ | ---- |
| 粒度 | **1 バッチ（Dnn）= 1 論理変更 = 1 Issue = 1 Branch = 1 PR** → Epic Branch |
| 成果物 | `db/ddl/{change_id}.sql`（設計参照用。適用正本は `supabase/migrations/`） |
| 起票順 | D01 完了後に D02 → … → D13。Issue は **5 件前後の wave** で起票 |
| MVP△ | `evaluation_*` / `external_attribute` / `staging_attribute` / `reco_score_distribution_metric` は DDL に含める（Task scope で go/no-go 再確認可） |
| D10/D11 | マイグレーション方針書 §8.1 の「Log / Observability 7 件」を **Log 3 + Metric 4** に分割して Issue 化 |

---

## 3. 適用順序（FK 依存）

```text
D01（extension / enum）
  → D02（Semantic / Feature 定義）
  → D03（Master / Config）
  → D04（Item）
  → D05（外部商品データ連携）
  → D06（Item 派生）
  → D07（Online 推薦）
  → D08（User 意味推定）
  → D09（Evaluation）
  → D10（Log）
  → D11（Metric）
  → D12（遅延 FK / 索引）
  → D13（横断整合ゲート）
```

物理 ER §15・マイグレーション方針書 §8.1 と整合。

---

## 4. バッチ一覧

| Batch | change_id | テーブル数 | Issue 起票 | 備考 |
| ----- | --------- | ---------: | ---------- | ---- |
| D01 | `d01_extensions_and_enums` | — | ✅ 完了 | pgvector + enum 型 26 件 |
| D02 | `d02_semantic_feature_definitions` | 12 | ✅ 完了 | Semantic / Feature 定義系 |
| D03 | `d03_master_config` | 7 | ✅ 完了 | Master / Config |
| D04 | `d04_item` | 7 | ✅ 完了 | Item 系 |
| D05 | `d05_external_product_integration` | 10 | ✅ 完了 | 外部商品データ連携 |
| D06 | `d06_item_derived` | 5 | ✅ 完了 | Item 派生 |
| D07 | `d07_online_recommendation` | 6 | ✅ 完了 | Online 推薦 |
| D08 | `d08_user_meaning` | 3 | ✅ 完了 | User 意味推定 |
| D09 | `d09_evaluation` | 5 | ✅ 完了 | Evaluation（MVP△） |
| D10 | `d10_log_observability` | 3 | ✅ 完了 | Log 3 件 |
| D11 | `d11_metric` | 4 | ✅ 完了 | Metric 4 件（MVP△ 1） |
| D12 | `d12_deferred_fk_indexes` | — | ✅ 完了 | 循環参照回避・後追い索引 |
| D13 | `d13_ddl_cross_check` | — | ✅ 完了 | DDL 横断整合ゲート（#582 型） |

---

## 5. D01 — 拡張・enum 型（Issue #611）

| 項目 | 内容 |
| ---- | ---- |
| 出力 | `db/ddl/d01_extensions_and_enums.sql` |
| extension | `CREATE EXTENSION IF NOT EXISTS vector;` |
| enum 型 | `enum定義書.md` §5 の論理 ID 26 件を `CREATE TYPE`（§4.1: 論理 ID を型名に使用） |

| # | PostgreSQL 型名（論理 ID） | 備考 |
| - | -------------------------- | ---- |
| 1 | `recommendation_run_status` | 物理列 `run_status`（Run 専用） |
| 2 | `recommendation_result_status` | |
| 3 | `recommendation_feedback_status` | |
| 4 | `phase_status` | |
| 5 | `batch_run_status` | 物理列 `run_status`（Batch 専用） |
| 6 | `api_call_status` | |
| 7 | `raw_import_status` | |
| 8 | `fetch_cursor_status` | |
| 9 | `fetch_cursor_type` | |
| 10 | `source_api` | |
| 11 | `product_diff_status` | |
| 12 | `item_active_status` | |
| 13 | `item_generation_queue_status` | |
| 14 | `evaluation_run_status` | |
| 15 | `request_mode` | |
| 16 | `feedback_target_type` | |
| 17 | `feedback_type` | |
| 18 | `owner_type` | |
| 19 | `feature_code` | MVP 8 軸 |
| 20 | `item_generation_type` | |
| 21 | `recommendation_run_phase_name` | |
| 22 | `batch_run_phase_name` | |
| 23 | `batch_type` | |
| 24 | `input_type` | |
| 25 | `application_method` | |
| 26 | `polarity` | |

`phase_log.phase_name` は owner 別 CHECK。`evaluation_run_phase_name` は Evaluation DDL Task で別途検討。

---

## 6. D02 — Semantic / Feature 定義系（12）

| # | テーブル | テーブル定義書 |
| - | -------- | -------------- |
| 1 | `semantic_config` | `semantic_config_テーブル定義書.md` |
| 2 | `semantic_config_version` | `semantic_config_version_テーブル定義書.md` |
| 3 | `feature_definition` | `feature_definition_テーブル定義書.md` |
| 4 | `semantic_concept` | `semantic_concept_テーブル定義書.md` |
| 5 | `semantic_rule` | `semantic_rule_テーブル定義書.md` |
| 6 | `relationship_rule` | `relationship_rule_テーブル定義書.md` |
| 7 | `occasion_rule` | `occasion_rule_テーブル定義書.md` |
| 8 | `pair_rule` | `pair_rule_テーブル定義書.md` |
| 9 | `concept_feature_rule` | `concept_feature_rule_テーブル定義書.md` |
| 10 | `input_type_rule` | `input_type_rule_テーブル定義書.md` |
| 11 | `feature_integration_rule` | `feature_integration_rule_テーブル定義書.md` |
| 12 | `normalization_rule` | `normalization_rule_テーブル定義書.md` |

---

## 7. D03 — Master / Config 系（7）

| # | テーブル | MVP |
| - | -------- | --- |
| 1 | `relationship_master` | ○ |
| 2 | `occasion_master` | ○ |
| 3 | `pair_master` | ○ |
| 4 | `model_version` | ○ |
| 5 | `ranking_config` | ○ |
| 6 | `reason_template` | ○ |
| 7 | `feature_normalization_version` | ○ |

---

## 8. D04 — Item 系（7）

| # | テーブル | MVP |
| - | -------- | --- |
| 1 | `external_genre` | ○ |
| 2 | `item` | ○ |
| 3 | `item_image` | ○ |
| 4 | `item_review_summary` | ○ |
| 5 | `external_attribute` | △ |
| 6 | `ranking_snapshot` | ○ |
| 7 | `item_popularity_signal` | ○ |

---

## 9. D05 — 外部商品データ連携系（10）

| # | テーブル | MVP |
| - | -------- | --- |
| 1 | `fetch_cursor` | ○ |
| 2 | `api_call_log` | ○ |
| 3 | `raw_product_metadata` | ○ |
| 4 | `staging_item` | ○ |
| 5 | `staging_item_image` | ○ |
| 6 | `staging_ranking_signal` | ○ |
| 7 | `staging_genre` | ○ |
| 8 | `staging_attribute` | △ |
| 9 | `product_diff_result` | ○ |
| 10 | `item_import_summary` | ○ |

---

## 10. D06 — Item 派生データ系（5）

| # | テーブル |
| - | -------- |
| 1 | `item_generation_queue` |
| 2 | `item_semantic` |
| 3 | `item_feature` |
| 4 | `item_meaning` |
| 5 | `item_embedding` |

---

## 11. D07 — Online 推薦系（6）

| # | テーブル |
| - | -------- |
| 1 | `recommendation_request` |
| 2 | `recommendation_run` |
| 3 | `recommendation_result` |
| 4 | `recommendation_result_item` |
| 5 | `recommendation_reason` |
| 6 | `recommendation_feedback` |

---

## 12. D08 — User 意味推定系（3）

| # | テーブル |
| - | -------- |
| 1 | `user_semantic` |
| 2 | `user_feature` |
| 3 | `user_meaning` |

---

## 13. D09 — Evaluation 系（5・MVP△）

| # | テーブル |
| - | -------- |
| 1 | `evaluation_dataset` |
| 2 | `evaluation_case` |
| 3 | `evaluation_run` |
| 4 | `evaluation_result` |
| 5 | `evaluation_metric` |

---

## 14. D10 — Log 系（3）

| # | テーブル |
| - | -------- |
| 1 | `batch_run_log` |
| 2 | `phase_log` |
| 3 | `error_log` |

retention 詳細は ⑥ データ保持・削除方針書 Task で確定。DDL は列・索引のみ。

---

## 15. D11 — Metric 系（4）

| # | テーブル | MVP |
| - | -------- | --- |
| 1 | `feature_distribution_metric` | ○ |
| 2 | `meaning_distribution_metric` | ○ |
| 3 | `normalization_distribution_metric` | ○ |
| 4 | `reco_score_distribution_metric` | △ |

---

## 16. D12 — 遅延 FK / 索引追加

| 項目 | 内容 |
| ---- | ---- |
| 出力 | `db/ddl/d12_deferred_fk_indexes.sql` |
| 対象 | 物理 ER §17 決定の後追い物理 FK、ivfflat 等の vector 索引、循環参照回避用制約 |
| 入力 | D02〜D11 完了後の棚卸し。`物理ER.md` §9 制約一覧・§10 索引 |

---

## 17. D13 — DDL 横断整合チェック

| 項目 | 内容 |
| ---- | ---- |
| 種別 | ゲート Task（#582 / #469 と同型） |
| 確認 | D01〜D12 成果物、enum・テーブル定義・DDL の横断整合、`db/ddl/` と docs の一致 |
| 成果 | チェックリスト + 必要な修正 PR |

---

## 18. Issue 起票 wave

| Wave | Batch | Issue 数 |
| ---- | ----- | --------: |
| 0 | D01 | 1（#611） |
| 1 | D02〜D06 | 5（#599〜#603） |
| 2 | D07〜D11 | 5（#604〜#608） |
| 3 | D12〜D13 | 2（#609〜#610） |

D01 完了後に Wave 1（D02〜）へ着手する。**④ 全バッチ merge 完了**（Epic HEAD `690dbc6`）。次は ⑤ migration/seed。

---

## 19. Issue 進捗（事実）

**Epic Branch HEAD**: `690dbc6`（2026-06-17）

| Batch | Issue | PR | 状態 |
| ----- | ----- | -- | ---- |
| D01 | #611 | #614 | CLOSED |
| D02 | #599 | #615 | CLOSED |
| D03 | #600 | #616 | CLOSED |
| D04 | #601 | #617 | CLOSED |
| D05 | #602 | #618 | CLOSED |
| D06 | #603 | #619 | CLOSED |
| D07 | #604 | #620 | CLOSED |
| D08 | #605 | #621 | CLOSED |
| D09 | #606 | #622 | CLOSED |
| D10 | #607 | #623 | CLOSED |
| D11 | #608 | #624 | CLOSED |
| D12 | #609 | #625 | CLOSED |
| D13 | #610 | #626 | CLOSED |

---

## 20. 関連資料

| 種別 | パス |
| ---- | ---- |
| マイグレーション方針 | `docs/06_実装設計/database/マイグレーション方針書.md` |
| enum 正本 | `docs/06_実装設計/database/enum定義書.md` |
| 物理 ER | `docs/06_実装設計/database/物理ER.md` |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` |
