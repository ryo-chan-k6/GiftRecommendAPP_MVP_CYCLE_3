# Reco Score Distribution Metric テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                          |
| -------------- | --------------------------------------------- |
| ドキュメントID | `DB-TBL-MVP-reco_score_distribution_metric`   |
| ドキュメント名 | Reco Score Distribution Metric テーブル定義書 |
| 対象システム   | Gift Recommendation Service MVP               |
| MVP対象        | `partial`                                     |
| 作成日         | 2026-06-16                                    |
| 更新日         | 2026-06-16（Issue #564 初版） / 2026-06-16（Human Review #564 決定反映） |

---

## 2. 概要

`reco_score_distribution_metric` は、**Online 推薦実行 1 回分**（Recommendation Run / Result）における Matching / Ranking スコアの分布統計量（mean / stddev / 分位点・異常率等）を保持する Log / Observability 系 **Metric** テーブルである。

reco が Ranking 完了・`recommendation_result_item` 保存後に `recommendation_result_item` 集合から集計して INSERT し、Run 単位のスコア偏り・Ranking 差の有無を監視する。個別スコアの正本は `recommendation_result_item` に保持し、本テーブルは **集計スナップショット** のみを担う。

Public API では返却しない（内部監視・品質分析データ）。

---

## 3. 目的

- `score_type`（`context_score` / `final_score` 等）ごとの Run 単位分布統計量を `semantic_config_version` / `ranking_config` スナップショットとともに保存する
- `batch_run_log` / `recommendation_result` / `recommendation_result_item` との関係（LOGICAL FK・集計入力・trace 境界）を物理 DDL 粒度まで確定する
- IF-OBS-005（Metric 記録）・IF-DB-RECO-007 保存フロー・`phase_log` Reco 品質 Metric 記録境界を明記する
- `feature_distribution_metric` / `meaning_distribution_metric`（#556 / #557）の Metric 系列設計を参考に、後続 DDL Task が migration を作成できる粒度まで設計を確定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `reco_score_distribution_metric` |
| 論理テーブル名 | Reco Score Distribution Metric |
| 分類 | Log / Observability系 / Metric |
| 正本区分 | Metric |
| 主な更新主体 | **reco**（Online 推薦実行時。IF-DB-RECO-007 保存フロー内） |
| 主な参照主体 | reco（品質チェック・異常検知）、batch（将来の日次再集計・監視ジョブ。MVP partial では読み取りのみ） |
| MVP対象 | `partial`（テーブル一覧 §11 No.62・物理ER §8） |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §5.1（論理 schema `metric`）・§8–§11 |

> **schema 分割**: MVP 物理 DDL は **`public` 単一 schema**（物理ER §17 No.8・Metric 系列先例）。`metric` は論理分類のみ。

> **Issue 本文との差分**: Issue #564 §5 は「Batch 集計」と記載があるが、テーブル一覧 §11 No.62・ログ・Observability設計書 §22.3 では **reco 主更新** を正とする。本定義書は後者に整合する。

---

## 5. 用途・責務

- **Reco スコア分布の Run 単位スナップショット**（テーブル一覧 §11 No.62・ログ・Observability設計書 §11.2 / §12.9 / §22.3）
- reco が `recommendation_result_item` 集合から `score_type` 単位で集計し、本テーブルへ **INSERT / UPSERT** する（MVP partial）
- `recommendation_run_id` / `recommendation_result_id` で Online 推薦 trace に紐づける
- `semantic_config_version_id` / `ranking_config_id` で Config 変更前後のスコア分布比較に利用する
- **追記型 Metric**。同一 Run × `score_type` の再集計は **UPSERT 上書き**

### 5.1 対象外

- Result Item **個別スコア**（`recommendation_result_item` の `context_score` / `final_score` / `score_breakdown_json` 正本。#545 merge 済み）
- 候補全件スコアの永続化（Observability §12.10。上位 K 件のみ Result Item 正本）
- Feature / Meaning / 正規化分布（各 `*_distribution_metric` テーブルの責務。#556 / #557 / #563）
- BATCH-016 分布メトリクス集計（Feature / Meaning / Normalization 系。本テーブルは **BATCH-016 対象外**）
- `phase_log.phase_name` への `reco_quality_metric_recorded` 追加（`phase_log_テーブル定義書` §5.7。enum 更新は別 Task）
- 分布集計アルゴリズム詳細（reco Ranking / Matching モジュール実装の責務）
- Public API 公開（#469 委譲）
- DDL / migration 本体（DDL Task へ委譲）

### 5.2 `recommendation_result_item` との集計入力責務境界

| 観点 | `recommendation_result_item` | 本テーブル |
| ---- | ---------------------------- | ---------- |
| 粒度 | **商品 × Result 1 行**（rank / 個別スコア） | **Run × score_type × 集計スコープ** の統計量 1 行 |
| 保持列 | `context_score` / `final_score` / `score_breakdown_json` | `mean` / `stddev` / 分位点 / 異常率等 |
| 更新主体 | reco（IF-DB-RECO-007） | reco（同一フロー内・Item 保存後） |
| 用途 | 結果表示・評価再現 | Observability・Reco 品質監視 |
| mean / std | **持たない**（個別値のみ） | **保持する** |

#### 5.2.1 集計入力ルール（MVP partial）

| `score_type` | 入力元 | 抽出方法 |
| ------------ | ------ | -------- |
| `context_score` | `recommendation_result_item.context_score` | 同一 `recommendation_result_id` の全 Item 行 |
| `final_score` | `recommendation_result_item.final_score` | 同上 |

> **`score_breakdown_json` 内訳**（`social_match` / `symbolic_match` / `feature_match` 等）は MVP partial では **物理列化しない**（§17.1 No.2 決定済み）。将来拡張時は JSON キー抽出または列追加を検討する。

> **0 件 Result**（`result_status = empty`）: Item 行が 0 件のため **Metric 行は INSERT しない**（`sample_count >= 1` を要求。§17.1 No.3 決定済み）。

#### 5.2.2 集計対象 Result の選定

| 条件 | 方針 |
| ---- | ---- |
| `recommendation_run.run_status` | **`succeeded` / `partially_succeeded` のみ**集計対象 |
| `recommendation_result.result_status` | **`generated` のみ**（`empty` / `failed` は対象外） |
| 失敗 Run | Metric **INSERT しない** |

### 5.3 `recommendation_result` との関係

| 観点 | 方針 |
| ---- | ---- |
| 関係 | **1 `recommendation_result` : 本テーブル N 行**（`score_type` 数。MVP partial では 2 行） |
| FK | `recommendation_result_id` → `recommendation_result.recommendation_result_id` は **LOGICAL**（物理 FK なし。MVP partial） |
| 必須性 | `aggregation_scope = run` のとき **`recommendation_result_id` は NOT NULL**（§10 CHECK） |
| trace | Observability の `recommendation_result_id` trace キーと整合（`recommendation_result_テーブル定義書` §2） |
| 1 Run : 0..1 Result | Run に Result が無い場合は集計しない（§5.2.2） |

### 5.4 `recommendation_run` との関係

| 観点 | 方針 |
| ---- | ---- |
| 関係 | **1 `recommendation_run` : 本テーブル N 行**（成功 Result がある場合） |
| FK | `recommendation_run_id` → `recommendation_run.recommendation_run_id` は **LOGICAL**（物理 FK なし。MVP partial） |
| 必須性 | `aggregation_scope = run` のとき **`recommendation_run_id` は NOT NULL**（§10 CHECK） |
| version スナップショット | `semantic_config_version_id` / `ranking_config_id` は **Run 正本列をコピー**して保持（`recommendation_run_テーブル定義書` §5.7 と同型） |
| 再現性 | Config 変更後も Metric 行は **生成時点の version 列を不変保持** |

### 5.5 `batch_run_log` との関係

| 観点 | 方針 |
| ---- | ---- |
| 関係 | MVP partial では **直接の親子関係なし**（BATCH-016 系 Metric とは異なる） |
| FK | `batch_run_id` → `batch_run_log.batch_run_id` は **LOGICAL**（物理 FK なし） |
| 必須性 | **MVP partial では `batch_run_id` は常に NULL**（reco Online 記録。§10 CHECK） |
| 将来拡張 | 日次再集計 Batch を導入する場合のみ `batch_run_id` を設定可（`aggregation_scope = daily` 等。§5.7 将来） |
| Retention 差分 | `batch_run_log` は **90 日**削除だが、本テーブルは **365 日以上**保持（§13）。非連動 |
| trace 境界 | Batch 実行 trace と Reco Online trace は **別系統**。混同しない |

### 5.6 `feature_distribution_metric` / `meaning_distribution_metric` との責務分離

| 観点 | Feature / Meaning Metric（#556 / #557） | 本テーブル |
| ---- | ----------------------------------------- | ---------- |
| 対象 | Feature 軸 / Meaning 座標の分布 | **Matching / Ranking スコア**分布 |
| 識別列 | `feature_code` + `value_layer` / `entity_type` + `value_layer` | **`score_type`** |
| 入力 | `item_feature` / `item_meaning` / `user_meaning` | **`recommendation_result_item`** |
| 更新主体 | batch（BATCH-016） | **reco**（Online） |
| `aggregation_scope` MVP | `batch_run` / `daily` / `semantic_config_version` | **`run` のみ**（partial） |
| `batch_run_id` | `batch_run` スコープで必須 | **NULL**（MVP partial） |

### 5.7 MVP partial で採用する `aggregation_scope`

| 値 | 意味 | `recommendation_run_id` | `recommendation_result_id` | `batch_run_id` |
| -- | ---- | ----------------------- | -------------------------- | -------------- |
| `run` | 1 回の Online 推薦実行（Result Item 集合） | **必須** | **必須** | **NULL** |

> `daily` / `semantic_config_version` / `batch_run` は Observability §12.9 にあるが、**MVP partial では対象外**（§17.1 No.4 決定済み）。将来 Batch 再集計で拡張する。

### 5.8 IF-OBS-005 / IF-DB-RECO-007 との保存 I/F

| 観点 | 方針 |
| ---- | ---- |
| トリガー | reco が Ranking 完了・`recommendation_result` / `recommendation_result_item` INSERT 後 |
| 保存 I/F | **IF-DB-RECO-007**（Recommendation Result 保存）の **拡張ステップ**として同一トランザクション内で実行を推奨 |
| Metric I/F | **IF-OBS-005**（Metric 記録・△）の Reco スコア分布保存。MVP partial では本テーブルへの INSERT が具体化 |
| モジュール | reco Recommendation Orchestrator / Result Build 後段（機能×モジュール対応表は実装 Task で確定） |
| phase_log | **専用 phase 名は追加しない**（`phase_log_テーブル定義書` §5.7）。Metric 行の存在で品質記録を代替 |

```text
recommendation_run（実行中）
  ↓ reco Ranking / Result Build
recommendation_result + recommendation_result_item（個別スコア正本）
  ↓ reco 集計（同一トランザクション推奨）
reco_score_distribution_metric（本テーブル）
```

### 5.9 `phase_log` との trace 境界

| 観点 | 方針 |
| ---- | ---- |
| `reco_quality_metric_recorded` | Observability §10.3 候補だが **phase_name には含めない**（§5.7） |
| MVP 代替 | Metric 行の `recommendation_run_id` + `calculated_at` で Run 品質を追跡 |
| Ranking フェーズ | `phase_log` の `ranking_completed` 等は **処理フェーズ**。本テーブルは **品質 Metric** |

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `reco_score_distribution_metric_id` | Reco Score Distribution Metric ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | Metric 行 ID |
| 2 | `recommendation_run_id` | Recommendation Run ID | `uuid` | `no` | — | `LOGICAL` | — | `NULL` | 集計元 Run。`aggregation_scope=run` 時は必須 |
| 3 | `recommendation_result_id` | Recommendation Result ID | `uuid` | `no` | — | `LOGICAL` | — | `NULL` | 集計元 Result。`aggregation_scope=run` 時は必須 |
| 4 | `batch_run_id` | Batch Run ID | `uuid` | `no` | — | `LOGICAL` | — | `NULL` | MVP partial では **常に NULL**（§5.5） |
| 5 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `ON` | — | — | Run 実行時の意味体系 version（スナップショット） |
| 6 | `ranking_config_id` | Ranking Config ID | `uuid` | `yes` | — | `LOGICAL` | — | — | Run 実行時の Ranking Config（スナップショット） |
| 7 | `score_type` | Score Type | `varchar(32)` | `yes` | — | — | — | — | `context_score` / `final_score`（MVP partial。§5.7） |
| 8 | `aggregation_scope` | Aggregation Scope | `varchar(32)` | `yes` | — | — | — | `'run'` | 集計単位（MVP partial は `run` のみ） |
| 9 | `aggregation_key` | Aggregation Key | `varchar(128)` | `no` | — | — | — | `NULL` | scope 補助キー。`run` スコープでは **NULL 固定** |
| 10 | `sample_count` | Sample Count | `integer` | `yes` | — | — | — | — | 集計に用いた Result Item 件数（`>= 1`） |
| 11 | `mean` | Mean | `numeric(8,6)` | `yes` | — | — | — | — | 平均 |
| 12 | `stddev` | Standard Deviation | `numeric(8,6)` | `no` | — | — | — | `NULL` | 標準偏差。`sample_count < 2` 時は NULL 許容 |
| 13 | `min_value` | Minimum | `numeric(8,6)` | `no` | — | — | — | `NULL` | 最小値 |
| 14 | `max_value` | Maximum | `numeric(8,6)` | `no` | — | — | — | `NULL` | 最大値 |
| 15 | `p10` | 10th Percentile | `numeric(8,6)` | `no` | — | — | — | `NULL` | 10 パーセンタイル |
| 16 | `p50` | Median | `numeric(8,6)` | `no` | — | — | — | `NULL` | 中央値 |
| 17 | `p90` | 90th Percentile | `numeric(8,6)` | `no` | — | — | — | `NULL` | 90 パーセンタイル |
| 18 | `near_zero_rate` | Near Zero Rate | `numeric(6,4)` | `no` | — | — | — | `NULL` | 0 付近張り付き率（§12.7 暫定定義） |
| 19 | `near_one_rate` | Near One Rate | `numeric(6,4)` | `no` | — | — | — | `NULL` | 1 付近張り付き率 |
| 20 | `mid_concentration_rate` | Mid Concentration Rate | `numeric(6,4)` | `no` | — | — | — | `NULL` | 0.5 付近集中率 |
| 21 | `nan_count` | NaN Count | `integer` | `yes` | — | — | — | `0` | NaN 件数 |
| 22 | `out_of_range_count` | Out Of Range Count | `integer` | `yes` | — | — | — | `0` | 期待レンジ外件数（0.0〜1.0 外） |
| 23 | `calculated_at` | Calculated At | `timestamptz` | `yes` | — | — | — | — | 集計完了日時（UTC） |
| 24 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | 行作成日時 |
| 25 | `updated_at` | Updated At | `timestamptz` | `yes` | — | — | — | `now()` | 行更新日時（UPSERT 時） |

> **Observability §12.12 との差分**: `metric_type`（テーブル名で自明）、`feature_code` / `entity_type` / `value_layer` / `model_version_id` / `feature_normalization_version_id` は **本テーブルでは不使用**。`skewness` / `kurtosis` / `inf_count` は **MVP partial 物理列に含めない**（#556 / #557 §17.1 No.1 同型）。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `reco_score_distribution_metric_id` | サロゲート UUID | — |
| UNIQUE | `recommendation_run_id`, `recommendation_result_id`, `score_type`, `aggregation_scope`, `aggregation_key` | Run 単位冪等キー | Index 名: `uq_rsdm_run_snapshot_key`。`aggregation_scope=run` 時は `aggregation_key` **NULL 固定** |

---

## 8. 外部キー・参照関係

### 8.1 参照先（本テーブルから）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `semantic_config_version_id` | `semantic_config_version.semantic_config_version_id` | `ON` | `ON DELETE RESTRICT` | Run スナップショット |
| `ranking_config_id` | `ranking_config.ranking_config_id` | `LOGICAL` | アプリ層 | Run スナップショット |
| `recommendation_run_id` | `recommendation_run.recommendation_run_id` | `LOGICAL` | アプリ層 | §5.4 |
| `recommendation_result_id` | `recommendation_result.recommendation_result_id` | `LOGICAL` | アプリ層 | §5.3 |
| `batch_run_id` | `batch_run_log.batch_run_id` | `LOGICAL` | アプリ層 | MVP partial では NULL。§5.5 |

### 8.2 被参照

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| reco（品質チェック） | 統計列 | reads | アプリ層 | 同一 Run 内異常検知 |
| batch（将来監視） | 統計列 | reads | アプリ層 | MVP partial では未使用 |

### 8.3 集計入力関係（非 FK）

| 入力 | 関係 | 備考 |
| ---- | ---- | ---- |
| `recommendation_result_item` | aggregates from | §5.2。`recommendation_result_id` 経由 |
| `recommendation_result` | trace header | §5.3 |
| `recommendation_run` | trace + version | §5.4 |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `reco_score_distribution_metric_pkey` | `reco_score_distribution_metric_id` | btree（PK） | 主キー | 自動生成 |
| `uq_rsdm_run_snapshot_key` | §7 UNIQUE 列 | unique btree | Run 単位冪等 UPSERT | `aggregation_key` NULLS NOT DISTINCT（PG15+） |
| `idx_rsdm_recommendation_run_id` | `recommendation_run_id` | btree | Run 単位一覧 | |
| `idx_rsdm_recommendation_result_id` | `recommendation_result_id` | btree | Result 単位参照 | |
| `idx_rsdm_version_score` | `semantic_config_version_id`, `ranking_config_id`, `score_type` | btree | Config 比較・軸別参照 | |
| `idx_rsdm_calculated_at` | `calculated_at` | btree | Retention DELETE | §13 |

> 物理ER §9 / §10 / §11 / §13 / §17.6 に本テーブル関係・Index・CHECK・Retention・Human Review 決定を反映済み（Issue #564）。

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `reco_score_distribution_metric_pkey` | PRIMARY KEY | `reco_score_distribution_metric_id` | 主キー | — |
| `uq_rsdm_run_snapshot_key` | UNIQUE | §7 | Run 系冪等キー | — |
| `fk_rsdm_semantic_config_version_id` | FOREIGN KEY | `semantic_config_version_id` | `semantic_config_version` ON DELETE RESTRICT | §8.1 |
| `chk_rsdm_score_type` | CHECK | `score_type` | `IN ('context_score', 'final_score')` | MVP partial（§17.1 No.2） |
| `chk_rsdm_aggregation_scope` | CHECK | `aggregation_scope` | `IN ('run')` | MVP partial（§5.7） |
| `chk_rsdm_run_required` | CHECK | `recommendation_run_id`, `aggregation_scope` | `aggregation_scope <> 'run' OR recommendation_run_id IS NOT NULL` | §5.4 |
| `chk_rsdm_result_required` | CHECK | `recommendation_result_id`, `aggregation_scope` | `aggregation_scope <> 'run' OR recommendation_result_id IS NOT NULL` | §5.3 |
| `chk_rsdm_batch_run_null_mvp` | CHECK | `batch_run_id` | `batch_run_id IS NULL` | MVP partial。将来 migration で解除（§17.1 No.5） |
| `chk_rsdm_sample_count_positive` | CHECK | `sample_count` | `>= 1` | 0 件 Result は INSERT しない（§5.2.2） |
| `chk_rsdm_nan_count_non_negative` | CHECK | `nan_count`, `out_of_range_count` | `>= 0` | — |
| `chk_rsdm_rate_range` | CHECK | `near_zero_rate`, `near_one_rate`, `mid_concentration_rate` | NULL または `0.0 <= x <= 1.0` | — |
| `chk_rsdm_score_value_range` | CHECK | `mean`, `min_value`, `max_value` 等 | NULL または `0.0 <= x <= 1.0` | スコア正規化レンジ |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `score_type` | （テーブル内 CHECK） | 本定義書 §5.2.1 | `context_score`, `final_score` | MVP partial。Matching / Ranking 主要 2 軸 |
| `aggregation_scope` | （テーブル内 CHECK） | 本定義書 §5.7 | `run` | MVP partial |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| INSERT / UPSERT | reco | §5.2.2 条件を満たす Result Item 保存後 | 統計列 + `calculated_at` | §12.1 | 主経路 |
| INSERT / UPDATE | batch | — | — | **禁止**（MVP partial） | 将来日次再集計で拡張可 |
| SELECT | reco / batch | 監視・異常検知 | — | — | |
| DELETE | Retention Batch（後続） | `calculated_at` 経過 | — | 再実行安全 | §13 |

### 12.1 `aggregation_scope = run` の UPSERT

```text
1. recommendation_run が succeeded / partially_succeeded であること
2. recommendation_result が generated であること
3. recommendation_result_item が 1 件以上存在すること
4. recommendation_result_item から score_type ごとに統計量を算出（§5.2.1）
5. UNIQUE (recommendation_run_id, recommendation_result_id, score_type,
   aggregation_scope, aggregation_key) に対し INSERT ... ON CONFLICT DO UPDATE
6. batch_run_id は NULL のまま（§5.5）
```

`aggregation_key` は **`run` スコープでは NULL 固定**。

### 12.2 再集計・再実行

| 観点 | 方針 |
| ---- | ---- |
| 同一 Run の再集計 | **UPSERT 上書き**（Result Item 不変のため通常は初回のみ） |
| Result 再生成 | MVP では Result / Item **UPDATE 禁止**のため発生しない |
| Retention 削除後 | 再集計不可（個別 Item 正本が残っていれば別途 Batch 再集計 Task で検討） |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | **365 日以上**（ログ・Observability設計書 §20.2。Metric 系列先例 #556 / #557 と同型） |
| 削除方式 | 後続 Retention Batch による **物理 DELETE** 候補 |
| 削除条件 | `calculated_at < now() - interval '365 days'` |
| 論理削除 | 採用しない |
| `batch_run_log` 連動 | **連動削除しない**（§5.5） |
| `recommendation_result` 連動 | **連動削除しない**（Online コア Retention は別 Task で一括確定。Result Item 定義書 §13 参考） |
| partition | MVP **未適用** |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `reco_score_distribution_metric` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | **`semantic_config_version` / `ranking_config` / `recommendation_run` / `recommendation_result` / `recommendation_result_item` 作成後** |
| rollback方針 | forward migration 主体 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | reco / batch（service role 経由） |
| 書き込み権限 | **reco のみ**（MVP partial） |
| service role利用 | reco DB アクセス層に限定 |
| 個人情報・機微情報 | **統計量のみ**。個別商品 ID・自由入力・`score_breakdown_json` 全文は含めない |
| ログ出力制限 | 分布統計・`score_breakdown` 全文を過剰ログ出力しない（§22.3） |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / CHECK / UNIQUE | migration |
| 2 | score_type CHECK | MVP 外 score_type が拒否される | migration |
| 3 | Run 冪等 UPSERT | 同一 Run × score_type 再 INSERT が統計上書きになる | integration |
| 4 | Result Item 境界 | 個別スコアが本テーブルに重複保存されない | manual |
| 5 | empty Result | `result_status=empty` で Metric 行が作成されない | integration |
| 6 | batch_run_id NULL | MVP CHECK で非 NULL が拒否される | migration |
| 7 | Retention | `calculated_at` 基準 DELETE | manual |
| 8 | Config スナップショット | Run の version 列が Metric 行にコピーされる | integration |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | `daily` / `batch_run` スコープ拡張 | 日次 Batch 再集計をいつ導入するか | Human | 将来 Task | §17.1 No.4 |
| 2 | `chk_rsdm_batch_run_null_mvp` 解除タイミング | 将来 Batch 再集計時に CHECK 変更が必要 | Human | 将来 Task | §17.1 No.5 |

### 17.1 Human Review 決定事項（Issue #564）

Human Review にて以下を確定した（2026-06-16）。

| No | 論点 | 決定内容 | 備考 |
| --: | ---- | -------- | ---- |
| 1 | Observability §12.12 追加統計列 | MVP partial は **本表の列のみ**（`skewness` 等は物理列化しない） | #556 / #557 §17.1 No.1 同型 |
| 2 | `score_type` MVP 範囲 | **`context_score` / `final_score` の 2 値のみ** | `score_breakdown_json` 内訳は将来拡張 |
| 3 | empty Result | **`sample_count >= 1` を要求し、0 件 Result では INSERT しない** | 空統計行を避ける |
| 4 | `aggregation_scope` | MVP partial は **`run` のみ** | `daily` / `semantic_config_version` は将来 |
| 5 | `batch_run_id` | MVP partial では **常に NULL**（CHECK 固定）。Batch 再集計導入時に CHECK 解除 | BATCH-016 系と責務分離 |
| 6 | reco 書き込み | MVP partial では **reco のみ INSERT / UPSERT** | Feature / Meaning Metric とは逆 |
| 7 | phase_log フェーズ名 | **`reco_quality_metric_recorded` は追加しない** | `phase_log_テーブル定義書` §5.7 |
| 8 | 物理 schema | MVP は **`public` 単一 schema** | Metric 系列先例 |
| 9 | Retention | **365 日以上**。`batch_run_log`（90 日）と**非連動** | #556 / #557 同型 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §5.1 / §8–§11 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §11 No.62 |
| ログ・Observability | `docs/05_アプリケーション設計/アプリ/ログ・Observability設計書.md` | §11.2 / §12.9–§12.12 / §22.3 / §20.2 |
| RecommendationResult | `docs/04_ドメインモデル設計/RecommendationResult定義書.md` | §15.1 スコア項目 |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-OBS-005 / IF-DB-RECO-007 |
| batch_run_log | `docs/06_実装設計/database/batch_run_log_テーブル定義書.md` | §5.2 / §13 |
| recommendation_run | `docs/06_実装設計/database/recommendation_run_テーブル定義書.md` | Run trace・version |
| recommendation_result | `docs/06_実装設計/database/recommendation_result_テーブル定義書.md` | Result trace |
| recommendation_result_item | `docs/06_実装設計/database/recommendation_result_item_テーブル定義書.md` | 集計入力正本 |
| feature_distribution_metric | `docs/06_実装設計/database/feature_distribution_metric_テーブル定義書.md` | Metric 系列参考 |
| meaning_distribution_metric | `docs/06_実装設計/database/meaning_distribution_metric_テーブル定義書.md` | Metric 系列参考 |
| phase_log | `docs/06_実装設計/database/phase_log_テーブル定義書.md` | §5.7 Reco 品質 Metric 境界 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | run_status / result_status 参照 |

---

## 19. レビュー観点

- テーブル一覧 §11 No.62・物理ER Log / Observability / Metric / partial 分類と矛盾していない
- `batch_run_log` / `recommendation_result` / `recommendation_result_item` との関係が §5 / §8 で明記されている
- reco Online 記録方針（§5.8 / §22.3）と IF-OBS-005 / IF-DB-RECO-007 整理が整合している
- `feature_distribution_metric` / `meaning_distribution_metric` との責務分離が §5.6 で明記されている
- `context_score` / `final_score` の MVP partial 採用範囲が §5.2 / §6 / §17.1 で明記されている
- `phase_log` Reco 品質 Metric 記録境界（専用 phase 非追加）が §5.9 で整合している
- Observability §12.12 候補列との差分が §6 / §17.1 で整理されている
- Retention（365 日以上）と `batch_run_log`（90 日）の非連動が §13 で明記されている
- PK / Unique / Index / CHECK が DDL Task へ展開できる粒度である
- secret や `.env` 実値が含まれていない
