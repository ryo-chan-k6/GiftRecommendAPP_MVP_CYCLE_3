# Feature Distribution Metric テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                      |
| -------------- | ----------------------------------------- |
| ドキュメントID | `DB-TBL-MVP-feature_distribution_metric`  |
| ドキュメント名 | Feature Distribution Metric テーブル定義書 |
| 対象システム   | Gift Recommendation Service MVP           |
| MVP対象        | `yes`                                     |
| 作成日         | 2026-06-15                                |
| 更新日         | 2026-06-15（#554 user_feature / #555 user_meaning merge 後突合） |

---

## 2. 概要

`feature_distribution_metric` は、**Item Feature 値の分布統計量**（mean / stddev / 分位点・異常率等）を保持する Log / Observability 系 **Metric** テーブルである。

BATCH-016（分布メトリクス集計 Batch）が `item_feature` から軸ごとに集計して INSERT し、Reco 品質・特徴量変換の正常性を監視する。個別 Feature 値の正本は `item_feature` に保持し、本テーブルは **集計スナップショット** のみを担う。

Public API では返却しない（内部監視・品質分析データ）。

---

## 3. 目的

- MVP 8 軸 `feature_code` ごとの分布統計量を `semantic_config_version` / `value_layer`（raw / normalized）単位で保存する
- `batch_run_log` / `feature_definition` / `item_feature` との関係（LOGICAL FK・集計入力・軸参照）を物理 DDL 粒度まで確定する
- IF-DB-BATCH-016（分布メトリクス保存）・`phase_log.feature_distribution_metric_recorded` フェーズとの trace 境界を明記する
- 後続 DDL Task が migration を作成できる粒度まで設計を確定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `feature_distribution_metric` |
| 論理テーブル名 | Feature Distribution Metric |
| 分類 | Log / Observability系 / Metric |
| 正本区分 | Metric |
| 主な更新主体 | batch（BATCH-016 / IF-DB-BATCH-016）。テーブル一覧上は batch / reco だが **MVP 書き込みは batch のみ** |
| 主な参照主体 | batch（品質監視・再集計）、reco（分布異常検知の参照。MVP は読み取りのみ） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §5.1（論理 schema `metric`）・§8–§11 |

> **schema 分割**: MVP 物理 DDL は **`public` 単一 schema**（物理ER §17 No.8）。`metric` は論理分類のみ。本定義書では列・制約を確定し、schema 名の物理分割は本番前 migration で検討する。

---

## 5. 用途・責務

- **Feature 軸ごとの分布統計量スナップショット**（テーブル一覧 §11 No.59・ログ・Observability設計書 §12.10–§12.12）
- BATCH-016 が `item_feature` 集合から `feature_code` × `value_layer` 単位で集計し、本テーブルへ **INSERT / UPSERT** する
- `batch_run_id` で Batch 実行単位の品質確認（ログ・Observability設計書 §12.9 batch_run 単位）に利用する
- `semantic_config_version_id` で意味体系 version 変更前後の分布比較に利用する
- **追記型 Metric**。同一集計スナップショットキーでの再実行は **UPSERT 上書き**、新規 Batch Run / 日次集計は **新規 INSERT**

### 5.1 対象外

- Item Feature **個別値**（`item_feature` の責務。#514 merge 済み）
- User Feature **個別値**（`user_feature` の責務。#554 merge 済み。MVP 集計入力外・§5.8）
- User Meaning **個別座標**（`user_meaning` の責務。#555 merge 済み。`meaning_distribution_metric` 側・§5.5）
- Feature 軸定義正本（`feature_definition` の責務。#470 merge 済み）
- Social / Symbolic / λ_ctx 等 Meaning 系分布（`meaning_distribution_metric` の責務。#557 別 Task）
- 正規化前後 z-score / sigmoid 変換分布（`normalization_distribution_metric` の責務。別 Task）
- Matching / Ranking スコア分布（`reco_score_distribution_metric` の責務。partial）
- 分布集計アルゴリズム詳細（BATCH-016 バッチ仕様書の責務）
- Public API 公開（#469 委譲）
- DDL / migration 本体（DDL Task へ委譲）

### 5.2 `item_feature` との集計入力責務境界

| 観点 | `item_feature` | 本テーブル |
| ---- | -------------- | ---------- |
| 粒度 | **商品 × version × 軸 × 冪等キー組** の個別値 | **軸 × version × value_layer × 集計スコープ** の統計量 1 行 |
| 保持列 | `raw_feature_value` / `normalized_feature_value` | `mean` / `stddev` / 分位点 / 異常率等 |
| 更新 Batch | BATCH-012 / BATCH-013 | BATCH-016 |
| 用途 | Matching / Ranking 入力 | Observability・品質監視 |
| 個別値の再保存 | **行単位 Upsert** | **しない**（集計結果のみ） |

#### 5.2.1 集計入力ルール（MVP）

| `value_layer` | 入力列 | 対象行の選定 |
| ------------- | ------ | ------------ |
| `raw` | `item_feature.raw_feature_value` | 同一 `semantic_config_version_id` + `feature_code` で **`normalized_feature_value` の有無に関わらず** raw が非 NULL の行 |
| `normalized` | `item_feature.normalized_feature_value` | 同一 `semantic_config_version_id` + `feature_code` で **`normalized_feature_value IS NOT NULL`** の行のみ |

> 入力行の世代選定（最新 `generated_at` の冪等キー組 8 行等）は `item_feature_テーブル定義書` §17.1 と BATCH-016 実装の責務。本テーブルは **集計結果の保存正本** のみ定義する。

### 5.3 `feature_definition` / `feature_code` との関係

| 観点 | 方針 |
| ---- | ---- |
| 軸参照 | **`feature_code` 列**で MVP 8 軸を識別（`feature_definition_id` 列は持たない。`item_feature_テーブル定義書` §8.4 と同型） |
| 存在整合 | 同一 `semantic_config_version_id` 内に `feature_definition.feature_code` が存在することを **アプリ層で確認**（LOGICAL 参照） |
| CHECK | DB 上は `chk_feature_code_mvp`（enum定義書 §6.16 / `packages/code-definitions/semantic/feature_code.yaml`） |
| 8 軸固定 | MVP は 8 値以外を拒否。version 追加軸は **semantic_config_version 更新 + feature_definition seed** で対応 |

### 5.4 `batch_run_log` との関係

| 観点 | 方針 |
| ---- | ---- |
| 関係 | BATCH-016 実行時の **`batch_run_log` 1 件 : 本テーブル N 行**（軸 × value_layer） |
| FK | `batch_run_id` → `batch_run_log.batch_run_id` は **LOGICAL**（物理 FK なし） |
| 必須性 | `aggregation_scope = 'batch_run'` のとき **`batch_run_id` は NOT NULL**（§10 CHECK） |
| trace | `phase_log` に `phase_name = feature_distribution_metric_recorded` を記録（`phase_log_テーブル定義書` §11.2） |
| Retention 差分 | `batch_run_log` は **90 日**削除（BATCH-RET-001）だが、本テーブルは **365 日以上**保持（§13）。`batch_run_id` は **履歴参照キー**として残し、親 Run 削除後も Metric 行は単独保持する |

### 5.5 `meaning_distribution_metric` との責務分離

| 観点 | 本テーブル | `meaning_distribution_metric` |
| ---- | ---------- | ----------------------------- |
| 対象 | **Feature 軸**（formality 等 8 値） | **Meaning 座標**（user_social / user_symbolic / λ_ctx 等） |
| 入力 | `item_feature`（主）。将来 user_feature 拡張は別論点 | `item_meaning` / `user_meaning` 等 |
| `feature_code` 列 | **必須** | 該当しない場合 NULL（別テーブル定義） |
| BATCH | BATCH-016（Feature Distribution Aggregator） | BATCH-016（Meaning Distribution Aggregator） |

### 5.6 BATCH-016 / IF-DB-BATCH-016

| 観点 | 方針 |
| ---- | ---- |
| 実行 Batch | **BATCH-016**（分布メトリクス集計 Batch） |
| 保存 I/F | **IF-DB-BATCH-016**（分布メトリクス保存・**INSERT / UPSERT**） |
| モジュール | `MOD-BATCH-038` Normalization Statistics Manager / Feature Distribution Aggregator（機能×モジュール対応表） |
| 出力 | 本テーブル + `meaning_distribution_metric` + `normalization_distribution_metric`（後者 2 件は別 Task） |
| ログ | `batch_run_log` / `phase_log` / `error_log`（バッチ処理一覧） |

```text
item_feature（個別値正本）
  ↓ BATCH-016 集計
feature_distribution_metric（本テーブル）
  ↓ phase_log
feature_distribution_metric_recorded
```

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `feature_distribution_metric_id` | Feature Distribution Metric ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | Metric 行 ID |
| 2 | `batch_run_id` | Batch Run ID | `uuid` | `no` | — | `LOGICAL` | — | `NULL` | 集計を実行した Batch Run。`aggregation_scope=batch_run` 時は必須 |
| 3 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `ON` | — | — | 集計対象の意味体系 version |
| 4 | `feature_normalization_version_id` | Feature Normalization Version ID | `uuid` | `no` | — | `LOGICAL` | — | `NULL` | `value_layer=normalized` 時に入力 `item_feature` が用いた正規化 version（再現性） |
| 5 | `feature_code` | Feature Code | `text` | `yes` | — | — | — | — | MVP 8 軸コード。enum定義書 §6.16 正本 |
| 6 | `aggregation_scope` | Aggregation Scope | `varchar(32)` | `yes` | — | — | — | `'batch_run'` | 集計単位（§5.7） |
| 7 | `aggregation_key` | Aggregation Key | `varchar(128)` | `no` | — | — | — | `NULL` | scope 補助キー（例: 日次 `YYYY-MM-DD`、将来 genre 単位 ID） |
| 8 | `entity_type` | Entity Type | `varchar(16)` | `yes` | — | — | — | `'item'` | 集計対象エンティティ種別。MVP は **item 固定** |
| 9 | `value_layer` | Value Layer | `varchar(16)` | `yes` | — | — | — | — | `raw` / `normalized` |
| 10 | `sample_count` | Sample Count | `integer` | `yes` | — | — | — | — | 集計に用いた件数 |
| 11 | `mean` | Mean | `numeric(8,6)` | `yes` | — | — | — | — | 平均 |
| 12 | `stddev` | Standard Deviation | `numeric(8,6)` | `no` | — | — | — | `NULL` | 標準偏差。`sample_count < 2` 時は NULL 許容 |
| 13 | `min_value` | Minimum | `numeric(8,6)` | `no` | — | — | — | `NULL` | 最小値（SQL 予約語回避のため `min_value`） |
| 14 | `max_value` | Maximum | `numeric(8,6)` | `no` | — | — | — | `NULL` | 最大値 |
| 15 | `p10` | 10th Percentile | `numeric(8,6)` | `no` | — | — | — | `NULL` | 10 パーセンタイル |
| 16 | `p50` | Median | `numeric(8,6)` | `no` | — | — | — | `NULL` | 中央値 |
| 17 | `p90` | 90th Percentile | `numeric(8,6)` | `no` | — | — | — | `NULL` | 90 パーセンタイル |
| 18 | `near_zero_rate` | Near Zero Rate | `numeric(6,4)` | `no` | — | — | — | `NULL` | 0 付近張り付き率（Observability §12.7 系） |
| 19 | `near_one_rate` | Near One Rate | `numeric(6,4)` | `no` | — | — | — | `NULL` | 1 付近張り付き率 |
| 20 | `mid_concentration_rate` | Mid Concentration Rate | `numeric(6,4)` | `no` | — | — | — | `NULL` | 0.5 付近集中率 |
| 21 | `nan_count` | NaN Count | `integer` | `yes` | — | — | — | `0` | NaN 件数（入力に含まれた場合） |
| 22 | `out_of_range_count` | Out Of Range Count | `integer` | `yes` | — | — | — | `0` | 期待レンジ外件数（normalized: 0.0〜1.0 外） |
| 23 | `calculated_at` | Calculated At | `timestamptz` | `yes` | — | — | — | — | 集計完了日時（UTC） |
| 24 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | 行作成日時 |
| 25 | `updated_at` | Updated At | `timestamptz` | `yes` | — | — | — | `now()` | 行更新日時（UPSERT 時） |

> **Observability §12.12 との差分**: `metric_type`（テーブル名で自明のため省略）、`skewness` / `kurtosis` / `inf_count` / `model_version_id` は **MVP 物理列に含めない**（§17.1 No.1）。必要時は `detail_json` 拡張または後続 migration で追加する。

### 5.7 MVP で採用する `aggregation_scope`

| 値 | 意味 | `batch_run_id` | `aggregation_key` 例 |
| -- | ---- | -------------- | ---------------------- |
| `batch_run` | 1 回の BATCH-016 実行単位 | **必須** | `NULL` |
| `daily` | 日次スナップショット（schedule 実行） | 実行 Run の ID を設定可 | `YYYY-MM-DD`（UTC 日付） |
| `semantic_config_version` | version 単位の再集計スナップショット | 任意 | `NULL` または version ラベル |

> `run`（Recommendation Run 単位）・`relationship` / `genre` 単位は Observability §12.9 にあるが、**本テーブル MVP では対象外**（§5.8・§17.1 No.3）。Run 単位 **User Feature** 分布の将来拡張先は本テーブル、`user_social` / `user_symbolic` / `λ_ctx` 等 **Meaning** 分布は `meaning_distribution_metric`。

### 5.8 `user_feature` / `user_meaning` との責務境界（#554 / #555 突合）

Epic Branch 最新（`user_feature_テーブル定義書` #554、`user_meaning_テーブル定義書` #555 merge 済み）との整合。

| 観点 | `user_feature`（#554） | `user_meaning`（#555） | 本テーブル |
| ---- | ---------------------- | ---------------------- | ---------- |
| 分類 | User意味推定系 | User意味推定系 | Log / Observability / Metric |
| 親キー | `recommendation_run_id` | `recommendation_run_id` | `batch_run_id`（LOGICAL）+ 集計スコープ |
| 値の正本 | `feature_value`（**正規化後 1 列のみ**。raw 非保持） | `user_social` / `user_symbolic` / `lambda_ctx` | 分布統計量（mean / stddev 等） |
| version 列 | **行に `semantic_config_version_id` なし**（Run 経由） | 同上（Run 経由） | **`semantic_config_version_id` 必須**（item 集計の version 正本） |
| 更新主体 | reco（Online） | reco（Online） | batch（BATCH-016） |
| MVP 集計入力 | **対象外**（`entity_type=item` 固定） | **対象外**（Meaning 系は `meaning_distribution_metric`） | `item_feature` のみ |

#### 5.8.1 将来拡張（MVP 外・§17.1 No.3）

Observability §12.9 の **run 単位** User Feature 分布は、将来 `entity_type=user`・`aggregation_scope=run`・`value_layer=normalized`（`user_feature.feature_value` 入力）で本テーブルへ拡張しうる。`user_meaning` の Social / Symbolic / λ_ctx 分布は **`meaning_distribution_metric`** の責務であり、本テーブルには含めない（`user_meaning_テーブル定義書` §5.6・`item_meaning_テーブル定義書` §5.5 と同型）。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `feature_distribution_metric_id` | サロゲート UUID | — |
| UNIQUE | `batch_run_id`, `semantic_config_version_id`, `feature_code`, `value_layer`, `aggregation_scope`, `aggregation_key` | 集計スナップショット冪等キー | Index 名: `uq_fdm_snapshot_key`。`aggregation_scope=batch_run` 時は `aggregation_key` は **NULL 固定**（§12.1） |
| UNIQUE（部分） | `aggregation_scope`, `aggregation_key`, `semantic_config_version_id`, `feature_code`, `value_layer` | 日次等 batch_run 非依存キー | `WHERE aggregation_scope <> 'batch_run'`。Index 名: `uq_fdm_non_batch_snapshot`（§12.2） |

---

## 8. 外部キー・参照関係

### 8.1 参照先（本テーブルから）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `semantic_config_version_id` | `semantic_config_version.semantic_config_version_id` | `ON` | `ON DELETE RESTRICT` | 集計 version 正本 |
| `batch_run_id` | `batch_run_log.batch_run_id` | `LOGICAL` | アプリ層 | `batch_run_log_テーブル定義書` §5.2。Retention 後も Metric 行は残る |
| `feature_code` | `feature_definition.feature_code`（同一 `semantic_config_version_id`） | `LOGICAL` | アプリ層 | `feature_definition_テーブル定義書` §8 |
| `feature_normalization_version_id` | `feature_normalization_version.feature_normalization_version_id` | `LOGICAL` | アプリ層 | `value_layer=normalized` 時推奨 |

### 8.2 被参照

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| batch（監視ジョブ） | 統計列 | reads | アプリ層 | ダッシュボード・異常検知（将来） |
| reco（品質チェック） | 統計列 | reads | アプリ層 | MVP は参照のみ。書き込み禁止 |

### 8.3 `item_feature` 集計関係（非 FK）

| 入力 | 関係 | 備考 |
| ---- | ---- | ---- |
| `item_feature` | aggregates from | §5.2。物理 FK なし（集計はアプリ層クエリ） |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `feature_distribution_metric_pkey` | `feature_distribution_metric_id` | btree（PK） | 主キー | 自動生成 |
| `uq_fdm_snapshot_key` | §7 UNIQUE 列 | unique btree | batch_run 単位冪等 UPSERT | `aggregation_key` NULLS NOT DISTINCT（PG15+） |
| `uq_fdm_non_batch_snapshot` | §7 部分 UNIQUE 列 | unique btree partial | 日次 / version スコープ冪等 | `WHERE aggregation_scope <> 'batch_run'` |
| `idx_fdm_batch_run_id` | `batch_run_id` | btree | Batch Run 単位一覧 | nullable |
| `idx_fdm_version_feature` | `semantic_config_version_id`, `feature_code`, `value_layer` | btree | version 比較・軸別参照 | |
| `idx_fdm_calculated_at` | `calculated_at` | btree | Retention DELETE | §13 |
| `idx_fdm_scope_key` | `aggregation_scope`, `aggregation_key` | btree | 日次 / version スコープ検索 | 補助 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `feature_distribution_metric_pkey` | PRIMARY KEY | `feature_distribution_metric_id` | 主キー | — |
| `uq_fdm_snapshot_key` | UNIQUE | §7 | batch_run 系冪等キー | — |
| `fk_fdm_semantic_config_version_id` | FOREIGN KEY | `semantic_config_version_id` | `semantic_config_version` ON DELETE RESTRICT | §8.1 |
| `chk_fdm_feature_code_mvp` | CHECK | `feature_code` | MVP 8 軸のみ（物理ER §11 相当） | enum Task / `feature_definition` と連携 |
| `chk_fdm_value_layer` | CHECK | `value_layer` | `IN ('raw', 'normalized')` | §5.2 |
| `chk_fdm_aggregation_scope` | CHECK | `aggregation_scope` | `IN ('batch_run', 'daily', 'semantic_config_version')` | §5.7 |
| `chk_fdm_entity_type_item` | CHECK | `entity_type` | `= 'item'` | MVP 固定 |
| `chk_fdm_batch_run_required` | CHECK | `batch_run_id`, `aggregation_scope` | `aggregation_scope <> 'batch_run' OR batch_run_id IS NOT NULL` | §5.4 |
| `chk_fdm_sample_count_non_negative` | CHECK | `sample_count` | `>= 0` | — |
| `chk_fdm_nan_count_non_negative` | CHECK | `nan_count`, `out_of_range_count` | `>= 0` | — |
| `chk_fdm_rate_range` | CHECK | `near_zero_rate`, `near_one_rate`, `mid_concentration_rate` | NULL または `0.0 <= x <= 1.0` | Observability §12.7 系 |
| `chk_fdm_normalized_version_when_layer` | CHECK | `value_layer`, `feature_normalization_version_id` | `value_layer = 'raw' OR feature_normalization_version_id IS NOT NULL` | normalized 層の再現性（§17.1 No.2 で緩和可） |

#### `chk_fdm_feature_code_mvp` 許容値

`formality`, `safety`, `brand_appropriateness`, `emotion`, `novelty`, `intimacy`, `symbolic_identity`, `story_richness`（enum定義書 §6.16 / AGENTS.md）

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `feature_code` | `feature_code` | enum定義書 §6.16 / `packages/code-definitions/semantic/feature_code.yaml` | MVP 8 軸 | §10 CHECK |
| `value_layer` | （テーブル内 CHECK） | 本定義書 §5.2 | `raw`, `normalized` | Observability §12.12 の `raw` / `sigmoid` 等のうち Feature 表現層 |
| `aggregation_scope` | （テーブル内 CHECK） | 本定義書 §5.7 | `batch_run`, `daily`, `semantic_config_version` | Observability §12.9 / §12.12 |
| `entity_type` | （テーブル内 CHECK） | 本定義書 | `item`（MVP） | §12.12 `entity_type` の subset |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| INSERT / UPSERT | batch（BATCH-016 / IF-DB-BATCH-016） | `item_feature` 集計完了後 | 統計列 + `calculated_at` | §12.1 / §12.2 | 主経路 |
| INSERT / UPDATE | reco | — | — | **禁止**（MVP） | テーブル一覧の reco は将来拡張用 |
| SELECT | batch / reco | 監視・異常検知 | — | — | reco は読み取りのみ |
| DELETE | Retention Batch（後続） | `calculated_at` 経過 | — | 再実行安全 | §13 |

### 12.1 `aggregation_scope = batch_run` の UPSERT

```text
1. BATCH-016 開始前に batch_run_log 行が存在すること
2. item_feature から semantic_config_version_id × feature_code × value_layer ごとに統計量を算出
3. 8 軸 × 2 value_layer（raw / normalized）で最大 16 行 / batch_run（normalized 対象行が無い軸はスキップ可）
4. UNIQUE (batch_run_id, semantic_config_version_id, feature_code, value_layer, aggregation_scope, aggregation_key)
   に対し INSERT ... ON CONFLICT DO UPDATE（統計列・calculated_at・updated_at）
5. phase_log に feature_distribution_metric_recorded を INSERT
```

`aggregation_key` は **`batch_run` スコープでは NULL 固定**（UNIQUE の NULLS NOT DISTINCT 前提）。

### 12.2 `aggregation_scope <> batch_run` の UPSERT

日次・version スコープは **部分 UNIQUE** `uq_fdm_non_batch_snapshot` で冪等化する。`batch_run_id` は実行 Run の trace として設定してよいが、冪等キーには含めない。

### 12.3 再集計・再実行

| 観点 | 方針 |
| ---- | ---- |
| 同一 `batch_run_id` の再集計 | **UPSERT 上書き**（統計列・`calculated_at` 更新） |
| Workflow 再実行（新 Run） | **新 `batch_run_id` で新規 INSERT**（`batch_run_log` §12.2 と同型） |
| 親 Run 削除後 | Metric 行は **残存**（`batch_run_id` は dangling 参照になりうる。監査用） |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | **365 日以上**（ログ・Observability設計書 §20.2。Feature 分布は品質推移の重要データ） |
| 削除方式 | 後続 Retention Batch による **物理 DELETE** 候補 |
| 削除条件 | `calculated_at < now() - interval '365 days'`（具体日数は運用で 365〜730 に調整可） |
| 論理削除 | 採用しない |
| `batch_run_log` 連動 | **連動削除しない**（90 日パージ対象外。§5.4） |
| partition | MVP **未適用**。物理ER §17 No.5 に従い本番前に `calculated_at` range partition 検討 |
| アーカイブ | MVP 対象外 |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `feature_distribution_metric` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | **`semantic_config_version` / `feature_definition` / `item_feature` / `batch_run_log` 作成後**（LOGICAL 参照元） |
| rollback方針 | forward migration 主体 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | batch / reco（service role 経由） |
| 書き込み権限 | **batch のみ**（BATCH-016）。api / web からの DML 禁止 |
| service role利用 | Distribution Metric Collector に限定 |
| 個人情報・機微情報 | **統計量のみ**保持。個別ユーザー入力・商品識別子は含めない |
| ログ出力制限 | 分布統計を過剰ログ出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / CHECK / UNIQUE | migration |
| 2 | feature_code CHECK | 9 軸目が拒否される | migration |
| 3 | batch_run 冪等 UPSERT | 同一キー再 INSERT が統計上書きになる | integration |
| 4 | value_layer | raw / normalized で入力列が切り替わる | integration |
| 5 | phase_log 連携 | `feature_distribution_metric_recorded` が記録される | integration |
| 6 | Retention | `calculated_at` 基準 DELETE が動作する | manual |
| 7 | item_feature 境界 | 個別値が本テーブルに混入しない | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review 論点は §17.1 を参照 |

### 17.1 Human Review 観点（Issue #556）

| No | 論点 | 推奨案 | 判断者 | 備考 |
| --: | ---- | ------ | ------ | ---- |
| 1 | Observability §12.12 の追加統計列（`skewness` / `kurtosis` / `inf_count`） | MVP は **本表の列のみ**採用。追加は migration または `detail_json` | Human | §6 注記 |
| 2 | `feature_normalization_version_id` 必須 CHECK | normalized 層では **NOT NULL 推奨**（§10）。raw 層は NULL | Human | 複数 normalization version 混在時の集計ルールは BATCH-016 側 |
| 3 | `aggregation_scope` の Run / genre 拡張 | MVP は **batch_run / daily / semantic_config_version のみ** | Human | Run 単位 User Feature は将来 `entity_type=user` で本テーブル拡張。Meaning 系は `meaning_distribution_metric`（§5.8） |
| 4 | `batch_run_id` と Retention 独立性 | **親 Run 削除後も Metric 保持**（§5.4 / §13） | Human | dangling `batch_run_id` を許容 |
| 5 | 物理 schema `metric` 分割タイミング | MVP は **public**。論理分類のみ明記（§4） | Human | 物理ER §17 No.8 |
| 6 | reco 書き込み | MVP は **batch のみ INSERT**。reco は SELECT のみ | Human | テーブル一覧 §11 の reco は将来拡張 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §5.1 / §8–§11 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §11 No.59 |
| ログ・Observability | `docs/05_アプリケーション設計/アプリ/ログ・Observability設計書.md` | §12.9–§12.12 / §20.2 |
| バッチ処理一覧 | `docs/05_アプリケーション設計/アプリ/batch/バッチ処理一覧.md` | BATCH-016 |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-DB-BATCH-016 |
| batch_run_log | `docs/06_実装設計/database/batch_run_log_テーブル定義書.md` | §5.2 / §13 |
| feature_definition | `docs/06_実装設計/database/feature_definition_テーブル定義書.md` | feature_code 正本 |
| item_feature | `docs/06_実装設計/database/item_feature_テーブル定義書.md` | 集計入力（MVP 正本） |
| user_feature | `docs/06_実装設計/database/user_feature_テーブル定義書.md` | #554。MVP 集計入力外・将来 run 拡張参照（§5.8） |
| user_meaning | `docs/06_実装設計/database/user_meaning_テーブル定義書.md` | #555。Meaning 分布は `meaning_distribution_metric`（§5.8） |
| item_meaning | `docs/06_実装設計/database/item_meaning_テーブル定義書.md` | Meaning 分布責務境界参考（§5.5） |
| phase_log | `docs/06_実装設計/database/phase_log_テーブル定義書.md` | `feature_distribution_metric_recorded` |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | §6.16 feature_code |
| feature_code | `packages/code-definitions/semantic/feature_code.yaml` | コード定義正本 |

---

## 19. レビュー観点

- テーブル一覧 §11 No.59・物理ER Log / Observability / Metric 分類と矛盾していない
- `batch_run_log` / `feature_definition` / `item_feature` との関係が §5 / §8 で明記されている
- BATCH-016 / IF-DB-BATCH-016・`phase_log.feature_distribution_metric_recorded` と整合している
- `meaning_distribution_metric` との責務分離が §5.5 で明記されている
- `user_feature` / `user_meaning`（#554 / #555）との MVP 集計境界が §5.8 で明記されている
- Observability §12.12 候補列との差分が §6 / §17.1 で整理されている
- Retention（365 日以上）と `batch_run_log`（90 日）の非連動が §13 で明記されている
- PK / Unique / Index / CHECK が DDL Task へ展開できる粒度である
- secret や `.env` 実値が含まれていない
