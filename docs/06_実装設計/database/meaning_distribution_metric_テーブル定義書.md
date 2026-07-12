# Meaning Distribution Metric テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                       |
| -------------- | ------------------------------------------ |
| ドキュメントID | `DB-TBL-MVP-meaning_distribution_metric`   |
| ドキュメント名 | Meaning Distribution Metric テーブル定義書   |
| 対象システム   | Gift Recommendation Service MVP            |
| MVP対象        | `yes`                                      |
| 作成日         | 2026-06-15                                 |
| 更新日         | 2026-06-15（Human Review #557 全項目決定・物理ER §17.4 反映） |

---

## 2. 概要

`meaning_distribution_metric` は、**Gift Meaning 座標**（Social / Symbolic / λ_ctx）の分布統計量（mean / stddev / 分位点・異常率等）を保持する Log / Observability 系 **Metric** テーブルである。

BATCH-016（分布メトリクス集計 Batch）が `item_meaning` / `user_meaning` から集計して INSERT し、Social / Symbolic 射影の妥当性・Context 重み分布を監視する。個別 Meaning 値の正本は `item_meaning` / `user_meaning` に保持し、本テーブルは **集計スナップショット** のみを担う。

Public API では返却しない（内部監視・品質分析データ）。

---

## 3. 目的

- `entity_type`（item / user）× `value_layer`（social / symbolic / lambda_ctx）ごとの分布統計量を `semantic_config_version` 単位で保存する
- `batch_run_log` / `item_meaning` / `user_meaning` との関係（LOGICAL FK・集計入力・責務境界）を物理 DDL 粒度まで確定する
- IF-DB-BATCH-016（分布メトリクス保存）・`phase_log.feature_distribution_metric_recorded` フェーズとの trace 境界を明記する
- `feature_distribution_metric`（#556）との対称設計を踏襲し、後続 DDL Task が migration を作成できる粒度まで設計を確定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `meaning_distribution_metric` |
| 論理テーブル名 | Meaning Distribution Metric |
| 分類 | Log / Observability系 / Metric |
| 正本区分 | Metric |
| 主な更新主体 | batch（BATCH-016 / IF-DB-BATCH-016）。テーブル一覧上は batch / reco だが **MVP 書き込みは batch のみ** |
| 主な参照主体 | batch（品質監視・再集計）、reco（分布異常検知の参照。MVP は読み取りのみ） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §5.1（論理 schema `metric`）・§8–§11 |

> **schema 分割**: MVP 物理 DDL は **`public` 単一 schema**（物理ER §17 No.8・`feature_distribution_metric_テーブル定義書` §4）。`metric` は論理分類のみ。

---

## 5. 用途・責務

- **Meaning 座標の分布統計量スナップショット**（テーブル一覧 §11 No.60・ログ・Observability設計書 §12.10–§12.12）
- BATCH-016 が `item_meaning` / `user_meaning` 集合から `entity_type` × `value_layer` 単位で集計し、本テーブルへ **INSERT / UPSERT** する
- `batch_run_id` で Batch 実行単位の品質確認（ログ・Observability設計書 §12.9 batch_run 単位）に利用する
- `semantic_config_version_id` で意味体系 version 変更前後の Social / Symbolic 分布比較に利用する
- **追記型 Metric**。同一集計スナップショットキーでの再実行は **UPSERT 上書き**、新規 Batch Run / 日次集計は **新規 INSERT**

### 5.1 対象外

- Item Meaning **個別座標**（`item_meaning` の責務。#515 merge 済み）
- User Meaning **個別座標**（`user_meaning` の責務。#555 merge 済み）
- Feature 軸分布（`feature_distribution_metric` の責務。#556 merge 済み）
- 正規化前後 z-score / sigmoid 変換分布（`normalization_distribution_metric` の責務。別 Task）
- Matching / Ranking スコア分布（`reco_score_distribution_metric` の責務。partial）
- `feature_code` 列（Meaning 軸では不使用。Feature 系は別テーブル）
- 分布集計アルゴリズム詳細（BATCH-016 バッチ仕様書の責務）
- Public API 公開（#469 委譲）
- DDL / migration 本体（DDL Task へ委譲）
- enum `batch_run_phase_name` への `meaning_distribution_metric_recorded` 追加（§17.1 No.5 **決定済み**：追加しない）

### 5.2 `item_meaning` との集計入力責務境界

| 観点 | `item_meaning` | 本テーブル |
| ---- | -------------- | ---------- |
| 粒度 | **商品 × semantic_config_version 1 行** | **entity_type=item × value_layer × 集計スコープ** の統計量 1 行 |
| 保持列 | `item_social` / `item_symbolic` | `mean` / `stddev` / 分位点 / 異常率等 |
| 更新 Batch | BATCH-013 | BATCH-016 |
| 用途 | Matching 入力 | Observability・Gift Meaning 空間品質監視 |
| mean / std | **持たない**（§5.5） | **保持する** |

#### 5.2.1 集計入力ルール（`entity_type = item`）

| `value_layer` | 入力列 | 対象行の選定 |
| ------------- | ------ | ------------ |
| `social` | `item_meaning.item_social` | 同一 `semantic_config_version_id` で **`item_social IS NOT NULL`** の行 |
| `symbolic` | `item_meaning.item_symbolic` | 同一 `semantic_config_version_id` で **`item_symbolic IS NOT NULL`** の行 |

> 入力行の世代選定（最新 `generated_at` の商品集合等）は `item_meaning_テーブル定義書` §12.1 と BATCH-016 実装の責務。本テーブルは **集計結果の保存正本** のみ定義する。

> **`feature_normalization_version_id` 混在**: 同一集計スコープ内に複数 version が存在する場合は **version ごとに行を分割**する（§5.8・§17.1 No.2）。1 行へ混在集約しない。

### 5.3 `user_meaning` との集計入力責務境界

| 観点 | `user_meaning` | 本テーブル |
| ---- | -------------- | ---------- |
| 粒度 | **Run 1 行**（`recommendation_run_id`） | **entity_type=user × value_layer × 集計スコープ** の統計量 1 行 |
| 保持列 | `user_social` / `user_symbolic` / `lambda_ctx` | 分布統計量 |
| 更新主体 | reco（Online 生成） | batch（BATCH-016 集計） |
| 用途 | Matching / Context Score | Observability・Reco 品質監視 |
| mean / std | **持たない**（§5.6） | **保持する** |

#### 5.3.1 集計入力ルール（`entity_type = user`）

| `value_layer` | 入力列 | 対象行の選定 |
| ------------- | ------ | ------------ |
| `social` | `user_meaning.user_social` | §5.3.2 の選定条件を満たす `user_meaning` 行（`user_social IS NOT NULL`） |
| `symbolic` | `user_meaning.user_symbolic` | 同上（`user_symbolic IS NOT NULL`） |
| `lambda_ctx` | `user_meaning.lambda_ctx` | 同上（`lambda_ctx IS NOT NULL`）。**User 専用**（item 側には存在しない） |

> `user_meaning` は行に `semantic_config_version_id` を持たない（`recommendation_run` 経由）。BATCH-016 は **集計スコープ内の Run を `recommendation_run.semantic_config_version_id` でフィルタ**し、本テーブルの `semantic_config_version_id` に記録する。

#### 5.3.2 `aggregation_scope` と user 集計ウィンドウ

| `aggregation_scope` | user 集計の意味 |
| ------------------- | --------------- |
| `batch_run` | 対象 `semantic_config_version_id` に属し、**完了 Run**（`recommendation_run.run_status IN ('succeeded', 'partially_succeeded')`）に紐づく `user_meaning` を、BATCH-016 **実行時点で DB に存在する全行**から集計する（**日次フィルタはかけない**。§17.1 No.9 **決定済み**） |
| `daily` | 当日 UTC に `user_meaning.generated_at` を持つ行（完了 Run に限定するかは BATCH-016 仕様書で明示。推奨は完了 Run のみ） |
| `semantic_config_version` | 同一 `semantic_config_version_id`（Run 経由）かつ完了 Run に紐づく `user_meaning` 行集合 |

**`batch_run` スコープの選定 SQL イメージ**（BATCH-016 実装参考）:

```sql
SELECT um.*
FROM user_meaning um
JOIN recommendation_run rr ON rr.recommendation_run_id = um.recommendation_run_id
WHERE rr.semantic_config_version_id = :semantic_config_version_id
  AND rr.run_status IN ('succeeded', 'partially_succeeded')
  AND um.<value_layer列> IS NOT NULL
```

> **`aggregation_scope = run`（単一 Recommendation Run 単位）は MVP 対象外**（§5.7・§17.1 No.3）。Run あたり 1 行の `user_meaning` に対する「分布」は本テーブルではなく **個別値正本** の責務である。

### 5.4 `batch_run_log` との関係

| 観点 | 方針 |
| ---- | ---- |
| 関係 | BATCH-016 実行時の **`batch_run_log` 1 件 : 本テーブル N 行**（entity_type × value_layer） |
| FK | `batch_run_id` → `batch_run_log.batch_run_id` は **LOGICAL**（物理 FK なし） |
| 必須性 | `aggregation_scope = 'batch_run'` のとき **`batch_run_id` は NOT NULL**（§10 CHECK） |
| trace | `phase_log` に `phase_name = feature_distribution_metric_recorded` を記録（Feature / Meaning / Normalization 各 Metric 記録完了を **1 フェーズで代表**。§5.6） |
| Retention 差分 | `batch_run_log` は **90 日**削除だが、本テーブルは **365 日以上**保持（§13）。`batch_run_id` dangling を許容 |

### 5.5 `feature_distribution_metric` との責務分離

| 観点 | `feature_distribution_metric`（#556） | 本テーブル |
| ---- | --------------------------------------- | ---------- |
| 対象 | **Feature 軸**（8 `feature_code`） | **Meaning 座標**（social / symbolic / lambda_ctx） |
| 識別列 | `feature_code` + `value_layer`（raw / normalized） | `entity_type` + `value_layer`（social / symbolic / lambda_ctx） |
| 入力 | `item_feature`（MVP） | `item_meaning` / `user_meaning` |
| `entity_type` MVP | `item` 固定 | `item` / `user` |
| BATCH | BATCH-016（Feature Distribution Aggregator） | BATCH-016（Meaning Distribution Aggregator） |

### 5.6 BATCH-016 / IF-DB-BATCH-016

| 観点 | 方針 |
| ---- | ---- |
| 実行 Batch | **BATCH-016**（分布メトリクス集計 Batch） |
| 保存 I/F | **IF-DB-BATCH-016**（分布メトリクス保存・**INSERT / UPSERT**） |
| モジュール | `MOD-BATCH-038` Normalization Statistics Manager / Meaning Distribution Aggregator（機能×モジュール対応表） |
| 出力 | `feature_distribution_metric` + **本テーブル** + `normalization_distribution_metric`（正規化系は別 Task） |
| ログ | `batch_run_log` / `phase_log` / `error_log`（バッチ処理一覧） |
| phase_log | **`feature_distribution_metric_recorded` 1 フェーズ**で Feature / Meaning / Normalization 各 Metric 記録完了を代表（専用 enum 追加なし。§17.1 No.5 **決定済み**） |

```text
item_meaning / user_meaning（個別座標正本）
  ↓ BATCH-016 集計
meaning_distribution_metric（本テーブル）
  ↓ phase_log（BATCH-016 終端）
feature_distribution_metric_recorded
```

### 5.7 MVP で採用する `aggregation_scope`

| 値 | 意味 | `batch_run_id` | `aggregation_key` 例 |
| -- | ---- | -------------- | ---------------------- |
| `batch_run` | 1 回の BATCH-016 実行単位 | **必須** | `NULL` |
| `daily` | 日次スナップショット（schedule 実行） | 実行 Run の ID を設定可 | `YYYY-MM-DD`（UTC 日付） |
| `semantic_config_version` | version 単位の再集計スナップショット | 任意 | `NULL` または version ラベル |

> `run`（Recommendation Run 単位）・`relationship` / `genre` 単位は Observability §12.9 にあるが、**本テーブル MVP では対象外**（§5.3.2・§17.1 No.3）。

### 5.8 `feature_normalization_version_id` 混在時の集計分割

| 観点 | 方針 |
| ---- | ---- |
| 原則 | 入力 `item_meaning` / `user_meaning` 行の `feature_normalization_version_id` **ごとに別 Metric 行**を生成する |
| 冪等キー | §7 UNIQUE に `feature_normalization_version_id` を含む設計をそのまま活用 |
| 混在集約 | **禁止**（多数決・最新 version のみ・NULL 許容による集約は行わない） |
| GROUP BY | `semantic_config_version_id`, `entity_type`, `value_layer`, `feature_normalization_version_id` |
| `sample_count < 2` | 当該 version 分割行の `stddev` は **NULL 許容**（§6） |
| 根拠 | `item_meaning` / `user_meaning` の行単位 version 正本・#556 normalized 層の version 分離方針と整合（§17.1 No.2 **決定済み**） |

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `meaning_distribution_metric_id` | Meaning Distribution Metric ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | Metric 行 ID |
| 2 | `batch_run_id` | Batch Run ID | `uuid` | `no` | — | `LOGICAL` | — | `NULL` | 集計を実行した Batch Run。`aggregation_scope=batch_run` 時は必須 |
| 3 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `ON` | — | — | 集計対象の意味体系 version |
| 4 | `feature_normalization_version_id` | Feature Normalization Version ID | `uuid` | `yes` | — | `LOGICAL` | — | — | 入力 Meaning 行が用いた正規化 version（再現性。item / user 共通） |
| 5 | `entity_type` | Entity Type | `varchar(16)` | `yes` | — | — | — | — | `item` / `user`（§5.7） |
| 6 | `value_layer` | Value Layer | `varchar(16)` | `yes` | — | — | — | — | `social` / `symbolic` / `lambda_ctx` |
| 7 | `aggregation_scope` | Aggregation Scope | `varchar(32)` | `yes` | — | — | — | `'batch_run'` | 集計単位（§5.7） |
| 8 | `aggregation_key` | Aggregation Key | `varchar(128)` | `no` | — | — | — | `NULL` | scope 補助キー（日次 `YYYY-MM-DD` 等） |
| 9 | `sample_count` | Sample Count | `integer` | `yes` | — | — | — | — | 集計に用いた件数 |
| 10 | `mean` | Mean | `numeric(8,6)` | `yes` | — | — | — | — | 平均 |
| 11 | `stddev` | Standard Deviation | `numeric(8,6)` | `no` | — | — | — | `NULL` | 標準偏差。`sample_count < 2` 時は NULL 許容 |
| 12 | `min_value` | Minimum | `numeric(8,6)` | `no` | — | — | — | `NULL` | 最小値 |
| 13 | `max_value` | Maximum | `numeric(8,6)` | `no` | — | — | — | `NULL` | 最大値 |
| 14 | `p10` | 10th Percentile | `numeric(8,6)` | `no` | — | — | — | `NULL` | 10 パーセンタイル |
| 15 | `p50` | Median | `numeric(8,6)` | `no` | — | — | — | `NULL` | 中央値 |
| 16 | `p90` | 90th Percentile | `numeric(8,6)` | `no` | — | — | — | `NULL` | 90 パーセンタイル |
| 17 | `near_zero_rate` | Near Zero Rate | `numeric(6,4)` | `no` | — | — | — | `NULL` | 0 付近張り付き率 |
| 18 | `near_one_rate` | Near One Rate | `numeric(6,4)` | `no` | — | — | — | `NULL` | 1 付近張り付き率 |
| 19 | `mid_concentration_rate` | Mid Concentration Rate | `numeric(6,4)` | `no` | — | — | — | `NULL` | 0.5 付近集中率 |
| 20 | `nan_count` | NaN Count | `integer` | `yes` | — | — | — | `0` | NaN 件数 |
| 21 | `out_of_range_count` | Out Of Range Count | `integer` | `yes` | — | — | — | `0` | 期待レンジ外件数（0.0〜1.0 外） |
| 22 | `calculated_at` | Calculated At | `timestamptz` | `yes` | — | — | — | — | 集計完了日時（UTC） |
| 23 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | 行作成日時 |
| 24 | `updated_at` | Updated At | `timestamptz` | `yes` | — | — | — | `now()` | 行更新日時（UPSERT 時） |

> **Observability §12.12 との差分**: `metric_type`（テーブル名で自明）、`feature_code`（Meaning 軸では不使用）、`skewness` / `kurtosis` / `inf_count` / `model_version_id` は **MVP 物理列に含めない**（`feature_distribution_metric_テーブル定義書` §17.1 No.1 と同型）。

> **`lambda_ctx` と `value_layer`**: `lambda_ctx` は **`entity_type = user` のときのみ**許可（§10 CHECK）。item 側 Meaning に Context 列は存在しない（`item_meaning_テーブル定義書` §5.4）。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `meaning_distribution_metric_id` | サロゲート UUID | — |
| UNIQUE | `batch_run_id`, `semantic_config_version_id`, `entity_type`, `value_layer`, `feature_normalization_version_id`, `aggregation_scope`, `aggregation_key` | 集計スナップショット冪等キー | Index 名: `uq_mdm_snapshot_key`。`aggregation_scope=batch_run` 時は `aggregation_key` は **NULL 固定**（§12.1） |
| UNIQUE（部分） | `aggregation_scope`, `aggregation_key`, `semantic_config_version_id`, `entity_type`, `value_layer`, `feature_normalization_version_id` | 日次等 batch_run 非依存キー | `WHERE aggregation_scope <> 'batch_run'`。Index 名: `uq_mdm_non_batch_snapshot`（§12.2） |

---

## 8. 外部キー・参照関係

### 8.1 参照先（本テーブルから）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `semantic_config_version_id` | `semantic_config_version.semantic_config_version_id` | `ON` | `ON DELETE RESTRICT` | 集計 version 正本 |
| `batch_run_id` | `batch_run_log.batch_run_id` | `LOGICAL` | アプリ層 | `batch_run_log_テーブル定義書` §5.2 |
| `feature_normalization_version_id` | `feature_normalization_version.feature_normalization_version_id` | `LOGICAL` | アプリ層 | item / user Meaning 入力の再現性 |

### 8.2 被参照

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| batch（監視ジョブ） | 統計列 | reads | アプリ層 | ダッシュボード・異常検知（将来） |
| reco（品質チェック） | 統計列 | reads | アプリ層 | MVP は参照のみ。書き込み禁止 |

### 8.3 集計入力関係（非 FK）

| 入力 | 関係 | 備考 |
| ---- | ---- | ---- |
| `item_meaning` | aggregates from | §5.2。`entity_type=item` |
| `user_meaning` | aggregates from | §5.3。`entity_type=user`。Run 経由で version 整合 |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `meaning_distribution_metric_pkey` | `meaning_distribution_metric_id` | btree（PK） | 主キー | 自動生成 |
| `uq_mdm_snapshot_key` | §7 UNIQUE 列 | unique btree | batch_run 単位冪等 UPSERT | `aggregation_key` NULLS NOT DISTINCT（PG15+） |
| `uq_mdm_non_batch_snapshot` | §7 部分 UNIQUE 列 | unique btree partial | 日次 / version スコープ冪等 | `WHERE aggregation_scope <> 'batch_run'` |
| `idx_mdm_batch_run_id` | `batch_run_id` | btree | Batch Run 単位一覧 | nullable |
| `idx_mdm_version_entity_layer` | `semantic_config_version_id`, `entity_type`, `value_layer` | btree | version 比較・軸別参照 | |
| `idx_mdm_calculated_at` | `calculated_at` | btree | Retention DELETE | §13 |
| `idx_mdm_scope_key` | `aggregation_scope`, `aggregation_key` | btree | 日次 / version スコープ検索 | 補助 |

> 物理ER §10・§11 に本テーブル Index / 制約を反映する（#557）。

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `meaning_distribution_metric_pkey` | PRIMARY KEY | `meaning_distribution_metric_id` | 主キー | — |
| `uq_mdm_snapshot_key` | UNIQUE | §7 | batch_run 系冪等キー | — |
| `fk_mdm_semantic_config_version_id` | FOREIGN KEY | `semantic_config_version_id` | `semantic_config_version` ON DELETE RESTRICT | §8.1 |
| `chk_mdm_entity_type` | CHECK | `entity_type` | `IN ('item', 'user')` | MVP |
| `chk_mdm_value_layer` | CHECK | `value_layer` | `IN ('social', 'symbolic', 'lambda_ctx')` | Observability §12.12 subset |
| `chk_mdm_lambda_ctx_user_only` | CHECK | `entity_type`, `value_layer` | `value_layer <> 'lambda_ctx' OR entity_type = 'user'` | §6 注記 |
| `chk_mdm_item_layers` | CHECK | `entity_type`, `value_layer` | `entity_type <> 'item' OR value_layer IN ('social', 'symbolic')` | item に lambda_ctx なし |
| `chk_mdm_aggregation_scope` | CHECK | `aggregation_scope` | `IN ('batch_run', 'daily', 'semantic_config_version')` | §5.7 |
| `chk_mdm_batch_run_required` | CHECK | `batch_run_id`, `aggregation_scope` | `aggregation_scope <> 'batch_run' OR batch_run_id IS NOT NULL` | §5.4 |
| `chk_mdm_sample_count_non_negative` | CHECK | `sample_count` | `>= 0` | — |
| `chk_mdm_nan_count_non_negative` | CHECK | `nan_count`, `out_of_range_count` | `>= 0` | — |
| `chk_mdm_rate_range` | CHECK | `near_zero_rate`, `near_one_rate`, `mid_concentration_rate` | NULL または `0.0 <= x <= 1.0` | — |
| `chk_mdm_normalization_version_required` | CHECK | `feature_normalization_version_id` | `IS NOT NULL` | MVP 必須（#556 §17.1 No.2 同型） |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `entity_type` | （テーブル内 CHECK） | 本定義書 §5.2–§5.3 | `item`, `user` | Observability §12.12 subset |
| `value_layer` | （テーブル内 CHECK） | 本定義書 §6 | `social`, `symbolic`, `lambda_ctx` | Meaning 座標軸 |
| `aggregation_scope` | （テーブル内 CHECK） | 本定義書 §5.7 | `batch_run`, `daily`, `semantic_config_version` | #556 と同型 |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| INSERT / UPSERT | batch（BATCH-016 / IF-DB-BATCH-016） | `item_meaning` / `user_meaning` 集計完了後 | 統計列 + `calculated_at` | §12.1 / §12.2 | 主経路 |
| INSERT / UPDATE | reco | — | — | **禁止**（MVP） | テーブル一覧の reco は将来拡張用 |
| SELECT | batch / reco | 監視・異常検知 | — | — | reco は読み取りのみ |
| DELETE | Retention Batch（後続） | `calculated_at` 経過 | — | 再実行安全 | §13 |

### 12.1 `aggregation_scope = batch_run` の UPSERT

```text
1. BATCH-016 開始前に batch_run_log 行が存在すること
2. item_meaning から entity_type=item × value_layer=social|symbolic ×
   feature_normalization_version_id ごとに統計量を算出（§5.8）
3. user_meaning から entity_type=user × value_layer=social|symbolic|lambda_ctx ×
   feature_normalization_version_id ごとに統計量を算出（§5.3.2 完了 Run フィルタ・§5.8）
4. UNIQUE (batch_run_id, semantic_config_version_id, entity_type, value_layer,
   feature_normalization_version_id, aggregation_scope, aggregation_key)
   に対し INSERT ... ON CONFLICT DO UPDATE
5. phase_log に feature_distribution_metric_recorded を INSERT（全 Metric 記録完了後）
```

`aggregation_key` は **`batch_run` スコープでは NULL 固定**。

### 12.2 `aggregation_scope <> batch_run` の UPSERT

日次・version スコープは **部分 UNIQUE** `uq_mdm_non_batch_snapshot` で冪等化する。

### 12.3 再集計・再実行

| 観点 | 方針 |
| ---- | ---- |
| 同一 `batch_run_id` の再集計 | **UPSERT 上書き** |
| Workflow 再実行（新 Run） | **新 `batch_run_id` で新規 INSERT** |
| 親 Run 削除後 | Metric 行は **残存**（`batch_run_id` dangling 許容） |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | **365 日以上**（ログ・Observability設計書 §20.2。Gift Meaning 空間品質推移） |
| 削除方式 | 後続 Retention Batch による **物理 DELETE** 候補 |
| 削除条件 | `calculated_at < now() - interval '365 days'` |
| 論理削除 | 採用しない |
| `batch_run_log` 連動 | **連動削除しない**（90 日パージ対象外。§5.4） |
| partition | MVP **未適用**（物理ER §17 No.5） |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `meaning_distribution_metric` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | **`semantic_config_version` / `item_meaning` / `user_meaning` / `batch_run_log` 作成後** |
| rollback方針 | forward migration 主体 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | batch / reco（service role 経由） |
| 書き込み権限 | **batch のみ**（BATCH-016） |
| service role利用 | Distribution Metric Collector に限定 |
| 個人情報・機微情報 | **統計量のみ**。個別 Run ID・商品 ID・自由記述は含めない |
| ログ出力制限 | 分布統計を過剰ログ出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / CHECK / UNIQUE | migration |
| 2 | entity_type / value_layer CHECK | `lambda_ctx` + `item` の組み合わせが拒否される | migration |
| 3 | batch_run 冪等 UPSERT | 同一キー再 INSERT が統計上書きになる | integration |
| 4 | item / user 入力境界 | `item_meaning` / `user_meaning` 個別値が混入しない | manual |
| 5 | phase_log 連携 | `feature_distribution_metric_recorded` が記録される | integration |
| 6 | Retention | `calculated_at` 基準 DELETE | manual |
| 7 | feature_distribution_metric 対称性 | 冪等キー・Retention・aggregation_scope が #556 と整合 | manual |
| 8 | user 集計ウィンドウ | `batch_run` 時は完了 Run × 対象 version の全行（日次は `daily`） | manual |
| 9 | version 混在分割 | 複数 `feature_normalization_version_id` が別行になる | integration |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review #557 にて No.1〜9 を決定済み（下記 §17.1） |

### 17.1 Human Review 決定事項（Issue #557 / #556 先例踏襲）

| No | 論点 | 決定内容 | 備考 |
| --: | ---- | -------- | ---- |
| 1 | Observability §12.12 追加統計列 | MVP は **本表の列のみ**（`skewness` 等は物理列化しない） | `feature_distribution_metric_テーブル定義書` §17.1 No.1 同型 |
| 2 | `feature_normalization_version_id` | **NOT NULL 必須**（§10 CHECK）。混在時は **version ごとに行分割**（§5.8）。1 行への混在集約は禁止 | item / user 入力の再現性 |
| 3 | `aggregation_scope` の Run 拡張 | MVP は **`batch_run` / `daily` / `semantic_config_version` のみ** | Run 単位は個別値正本（`user_meaning`）の責務 |
| 4 | `batch_run_id` と Retention | **親 Run 削除後も Metric 保持**。dangling 許容 | #556 §17.1 No.4 同型 |
| 5 | phase_log フェーズ名 | MVP は **`feature_distribution_metric_recorded` に Meaning 記録を包含**。`meaning_distribution_metric_recorded` enum は **追加しない** | enum定義書 §6.19 変更は out_of_scope |
| 6 | reco 書き込み | MVP は **batch のみ INSERT / UPSERT** | #556 §17.1 No.6 同型 |
| 7 | `entity_type` MVP 範囲 | **`item`（item_meaning）と `user`（user_meaning）** | `feature_code` 列は持たない |
| 8 | 物理 schema | MVP は **`public` 単一 schema** | #556 §17.1 No.5 同型 |
| 9 | user 集計ウィンドウ（`batch_run`） | 対象 `semantic_config_version_id` の **完了 Run**（`succeeded` / `partially_succeeded`）に紐づく `user_meaning` を実行時点で **全件集計**。日次フィルタは **`daily` scope に委譲** | §5.3.2 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §5.1 / §8–§11 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §11 No.60 |
| ログ・Observability | `docs/05_アプリケーション設計/アプリ/ログ・Observability設計書.md` | §12.9–§12.12 / §20.2 |
| バッチ処理一覧 | `docs/05_アプリケーション設計/アプリ/batch/バッチ処理一覧.md` | BATCH-016 |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-DB-BATCH-016 |
| batch_run_log | `docs/06_実装設計/database/batch_run_log_テーブル定義書.md` | §5.2 / §13 |
| item_meaning | `docs/06_実装設計/database/item_meaning_テーブル定義書.md` | §5.5 / §8.2 集計入力 |
| user_meaning | `docs/06_実装設計/database/user_meaning_テーブル定義書.md` | §5.6 集計入力 |
| feature_distribution_metric | `docs/06_実装設計/database/feature_distribution_metric_テーブル定義書.md` | §5.5 / §17.1 対称設計正本 |
| phase_log | `docs/06_実装設計/database/phase_log_テーブル定義書.md` | `feature_distribution_metric_recorded` |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | §6.19 batch_run_phase_name |

---

## 19. レビュー観点

- テーブル一覧 §11 No.60・物理ER Log / Observability / Metric 分類と矛盾していない
- `batch_run_log` / `item_meaning` / `user_meaning` との関係が §5 / §8 で明記されている
- BATCH-016 / IF-DB-BATCH-016・`phase_log` trace 境界が整合している
- `feature_distribution_metric` との責務分離・対称設計が §5.5 / §17.1 で明記されている
- user_social / user_symbolic / λ_ctx 分布の扱いが §5.3 / §6 で明記されている
- user 集計ウィンドウ（完了 Run・version フィルタ）と version 混在分割が §5.3.2 / §5.8 / §17.1 で明記されている
- Observability §12.12 候補列との差分が §6 / §17.1 で整理されている
- Retention（365 日以上）と `batch_run_log`（90 日）の非連動が §13 で明記されている
- PK / Unique / Index / CHECK が DDL Task へ展開できる粒度である
- secret や `.env` 実値が含まれていない
