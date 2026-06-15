# Normalization Distribution Metric テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                              |
| -------------- | ------------------------------------------------- |
| ドキュメントID | `DB-TBL-MVP-normalization_distribution_metric`    |
| ドキュメント名 | Normalization Distribution Metric テーブル定義書  |
| 対象システム   | Gift Recommendation Service MVP                   |
| MVP対象        | `yes`                                             |
| 作成日         | 2026-06-16                                        |
| 更新日         | 2026-06-16（#556 / #557 先例踏襲・Human Review 論点整理） |

---

## 2. 概要

`normalization_distribution_metric` は、**Feature 正規化パイプライン**（raw → sigmoid）各段階の分布統計量（mean / stddev / 分位点・張り付き率等）を保持する Log / Observability 系 **Metric** テーブルである。

BATCH-016（分布メトリクス集計 Batch）が `item_feature` から `feature_code` × `value_layer` 単位で集計して INSERT / UPSERT し、sigmoid 正規化の正常性・値の潰れを監視する。個別 Feature 値の正本は `item_feature` に保持し、本テーブルは **集計スナップショット** のみを担う。

Public API では返却しない（内部監視・品質分析データ）。

---

## 3. 目的

- MVP 8 軸 `feature_code` ごとの **正規化前後分布統計量**を `semantic_config_version` / `value_layer`（raw / sigmoid）/ `feature_normalization_version_id` 単位で保存する
- `batch_run_log` / `feature_normalization_version` / `item_feature` との関係（LOGICAL FK・正規化 version 再現性・集計入力）を物理 DDL 粒度まで確定する
- IF-DB-BATCH-016（分布メトリクス保存）・`phase_log.feature_distribution_metric_recorded` フェーズとの trace 境界を明記する
- `feature_distribution_metric`（#556）/ `meaning_distribution_metric`（#557）との対称設計を踏襲し、後続 DDL Task が migration を作成できる粒度まで設計を確定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `normalization_distribution_metric` |
| 論理テーブル名 | Normalization Distribution Metric |
| 分類 | Log / Observability系 / Metric |
| 正本区分 | Metric |
| 主な更新主体 | batch（BATCH-016 / IF-DB-BATCH-016）。テーブル一覧上は batch のみ |
| 主な参照主体 | batch（品質監視・再集計）、reco（正規化異常検知の参照。MVP は読み取りのみ） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §5.1（論理 schema `metric`）・§8–§11 |

> **schema 分割**: MVP 物理 DDL は **`public` 単一 schema**（物理ER §17 No.8・`feature_distribution_metric_テーブル定義書` §4）。`metric` は論理分類のみ。

---

## 5. 用途・責務

- **正規化前後分布統計量スナップショット**（テーブル一覧 §11 No.61・ログ・Observability設計書 §12.6–§12.12）
- BATCH-016 が `item_feature` 集合から `feature_code` × `value_layer` × `feature_normalization_version_id` 単位で集計し、本テーブルへ **INSERT / UPSERT** する
- `batch_run_id` で Batch 実行単位の品質確認（ログ・Observability設計書 §12.9 batch_run 単位）に利用する
- `feature_normalization_version_id` で正規化パラメータ変更前後の sigmoid 分布比較に利用する
- **追記型 Metric**。同一集計スナップショットキーでの再実行は **UPSERT 上書き**、新規 Batch Run / 日次集計は **新規 INSERT**

### 5.1 対象外

- Item Feature **個別値**（`item_feature` の責務。#514 merge 済み）
- Feature 軸の汎用分布（`feature_distribution_metric` の責務。#556 merge 済み。`value_layer=raw/normalized`）
- Meaning 座標分布（`meaning_distribution_metric` の責務。#557 merge 済み）
- Matching / Ranking スコア分布（`reco_score_distribution_metric` の責務。partial）
- 正規化パラメータ正本（`feature_normalization_version` の責務。#458 merge 済み）
- 正規化アルゴリズム詳細（BATCH-013 バッチ仕様書の責務）
- Public API 公開（#469 委譲）
- DDL / migration 本体（DDL Task へ委譲）
- enum `batch_run_phase_name` への `normalization_distribution_metric_recorded` 追加（§17.1 No.5 **決定済み**：追加しない）

### 5.2 `item_feature` との集計入力責務境界

| 観点 | `item_feature` | 本テーブル |
| ---- | -------------- | ---------- |
| 粒度 | **商品 × version × 軸 × 冪等キー組** の個別値 | **軸 × version × value_layer × 集計スコープ** の統計量 1 行 |
| 保持列 | `raw_feature_value` / `normalized_feature_value` | `mean` / `stddev` / 分位点 / 張り付き率等 |
| 更新 Batch | BATCH-012 / BATCH-013 | BATCH-016 |
| 用途 | Matching / Ranking 入力 | Observability・sigmoid 正規化正常性監視 |
| mean / std | **持たない** | **保持する** |

#### 5.2.1 集計入力ルール（MVP）

| `value_layer` | 入力列 | 対象行の選定 |
| ------------- | ------ | ------------ |
| `raw` | `item_feature.raw_feature_value` | 同一 `semantic_config_version_id` + `feature_code` + `feature_normalization_version_id` で **`raw_feature_value IS NOT NULL`** の行 |
| `sigmoid` | `item_feature.normalized_feature_value` | 同一 `semantic_config_version_id` + `feature_code` + `feature_normalization_version_id` で **`normalized_feature_value IS NOT NULL`** の行 |

> 入力行の世代選定（最新 `generated_at` の冪等キー組 8 行等）は `item_feature_テーブル定義書` §17.1 と BATCH-016 実装の責務。本テーブルは **集計結果の保存正本** のみ定義する。

> **`feature_normalization_version_id` 混在**: 同一集計スコープ内に複数 version が存在する場合は **version ごとに行を分割**する（§5.8・§17.1 No.2）。1 行へ混在集約しない。

#### 5.2.2 `feature_distribution_metric` との value_layer 境界

| 観点 | `feature_distribution_metric`（#556） | 本テーブル |
| ---- | --------------------------------------- | ---------- |
| 目的 | Feature 値分布の汎用 Observability | **正規化パイプライン段階**の監視 |
| `value_layer` | `raw` / `normalized` | `raw` / `sigmoid` |
| sigmoid 監視 | `normalized` 層で間接的にカバー | **`sigmoid` 層で明示**（Observability §12.6） |
| 張り付き率列 | sigmoid 相当は `normalized` 行 | **`sigmoid` 行で必須意味**（§6） |
| 入力 | 同一 `item_feature` | 同一 `item_feature` |
| 重複 | 両テーブルに統計が存在しうる | **責務分離**。本テーブルは正規化正常性検証に特化 |

### 5.3 `feature_normalization_version` との関係

| 観点 | 方針 |
| ---- | ---- |
| 正本 | 正規化パラメータ（`center_feature` / `k_feature` 等）は **`feature_normalization_version.parameter_json`** が正本（`feature_normalization_version_テーブル定義書` §5.1） |
| 参照列 | 本テーブルは **`feature_normalization_version_id`** を保持し、集計入力 `item_feature` が用いた version を記録する |
| FK | **LOGICAL**（物理 FK なし。`feature_normalization_version_テーブル定義書` §8.2・§17.1 No.4 決定済み） |
| 必須性 | MVP は **全行 NOT NULL**（§10 CHECK）。version 混在時は行分割（§5.8） |
| 再現性 | 同一 `feature_normalization_version_id` の Metric 行と `item_feature` 行を突合し、正規化パラメータ変更の影響を追跡する |

### 5.4 `batch_run_log` との関係

| 観点 | 方針 |
| ---- | ---- |
| 関係 | BATCH-016 実行時の **`batch_run_log` 1 件 : 本テーブル N 行**（feature_code × value_layer × feature_normalization_version_id） |
| FK | `batch_run_id` → `batch_run_log.batch_run_id` は **LOGICAL**（物理 FK なし） |
| 必須性 | `aggregation_scope = 'batch_run'` のとき **`batch_run_id` は NOT NULL**（§10 CHECK） |
| trace | `phase_log` に `phase_name = feature_distribution_metric_recorded` を記録（Feature / Meaning / Normalization 各 Metric 記録完了を **1 フェーズで代表**。§5.7） |
| Retention 差分 | `batch_run_log` は **90 日**削除だが、本テーブルは **365 日以上**保持（§13）。`batch_run_id` dangling を許容 |

### 5.5 他 Metric テーブルとの責務分離

| 観点 | 本テーブル | 他テーブル |
| ---- | ---------- | ---------- |
| 対象 | **正規化前後**（raw / sigmoid）分布 | Feature 汎用分布 → `feature_distribution_metric` |
| | | Meaning 座標分布 → `meaning_distribution_metric` |
| | | Reco スコア分布 → `reco_score_distribution_metric` |
| `feature_code` | **必須**（8 軸） | Meaning 系は非使用 |
| BATCH | BATCH-016（Normalization Distribution Aggregator） | 同一 BATCH-016 内の別 Aggregator |

### 5.6 BATCH-013 / BATCH-016 / IF-DB-BATCH-016

| 観点 | 方針 |
| ---- | ---- |
| BATCH-013 | Feature 正規化 Batch。**`item_feature.normalized_feature_value` を更新**する。本テーブルへの **直接 INSERT は MVP では行わない**（§17.1 No.6 **決定済み**） |
| BATCH-016 | 分布メトリクス集計 Batch。**本テーブルへの保存正本**（IF-DB-BATCH-016） |
| 保存 I/F | **IF-DB-BATCH-016**（分布メトリクス保存・**INSERT / UPSERT**） |
| モジュール | `MOD-BATCH-038` Normalization Statistics Manager / Normalization Distribution Aggregator（機能×モジュール対応表） |
| 出力 | `feature_distribution_metric` + `meaning_distribution_metric` + **本テーブル** |
| ログ | `batch_run_log` / `phase_log` / `error_log`（バッチ処理一覧） |
| phase_log | **`feature_distribution_metric_recorded` 1 フェーズ**で全 Metric 記録完了を代表（専用 enum 追加なし。§17.1 No.5 **決定済み**） |

```text
item_feature（raw / normalized 個別値正本）
  ↓ BATCH-013 正規化（normalized_feature_value 更新）
  ↓ BATCH-016 集計
normalization_distribution_metric（本テーブル）
  ↓ phase_log（BATCH-016 終端）
feature_distribution_metric_recorded
```

### 5.7 MVP で採用する `aggregation_scope`

| 値 | 意味 | `batch_run_id` | `aggregation_key` 例 |
| -- | ---- | -------------- | ---------------------- |
| `batch_run` | 1 回の BATCH-016 実行単位 | **必須** | `NULL` |
| `daily` | 日次スナップショット（schedule 実行） | 実行 Run の ID を設定可 | `YYYY-MM-DD`（UTC 日付） |
| `semantic_config_version` | version 単位の再集計スナップショット | 任意 | `NULL` または version ラベル |

> `run`（Recommendation Run 単位）・`relationship` / `genre` 単位は Observability §12.9 にあるが、**本テーブル MVP では対象外**（§17.1 No.3）。

### 5.8 `feature_normalization_version_id` 混在時の集計分割

| 観点 | 方針 |
| ---- | ---- |
| 原則 | 入力 `item_feature` 行の `feature_normalization_version_id` **ごとに別 Metric 行**を生成する |
| 冪等キー | §7 UNIQUE に `feature_normalization_version_id` を含む |
| 混在集約 | **禁止**（多数決・最新 version のみ・NULL 許容による集約は行わない） |
| GROUP BY | `semantic_config_version_id`, `feature_code`, `value_layer`, `feature_normalization_version_id` |
| `sample_count < 2` | 当該 version 分割行の `stddev` は **NULL 許容**（§6） |
| 根拠 | `item_feature_テーブル定義書` §5.3・`feature_distribution_metric_テーブル定義書` §17.1 No.2・`meaning_distribution_metric_テーブル定義書` §5.8 と整合 |

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `normalization_distribution_metric_id` | Normalization Distribution Metric ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | Metric 行 ID |
| 2 | `batch_run_id` | Batch Run ID | `uuid` | `no` | — | `LOGICAL` | — | `NULL` | 集計を実行した Batch Run。`aggregation_scope=batch_run` 時は必須 |
| 3 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `ON` | — | — | 集計対象の意味体系 version |
| 4 | `feature_normalization_version_id` | Feature Normalization Version ID | `uuid` | `yes` | — | `LOGICAL` | — | — | 入力 `item_feature` が用いた正規化 version（再現性） |
| 5 | `feature_code` | Feature Code | `text` | `yes` | — | — | — | — | MVP 8 軸コード。enum定義書 §6.16 正本 |
| 6 | `value_layer` | Value Layer | `varchar(16)` | `yes` | — | — | — | — | `raw` / `sigmoid`（§5.2.2） |
| 7 | `aggregation_scope` | Aggregation Scope | `varchar(32)` | `yes` | — | — | — | `'batch_run'` | 集計単位（§5.7） |
| 8 | `aggregation_key` | Aggregation Key | `varchar(128)` | `no` | — | — | — | `NULL` | scope 補助キー（日次 `YYYY-MM-DD` 等） |
| 9 | `entity_type` | Entity Type | `varchar(16)` | `yes` | — | — | — | `'item'` | 集計対象エンティティ種別。MVP は **item 固定** |
| 10 | `sample_count` | Sample Count | `integer` | `yes` | — | — | — | — | 集計に用いた件数 |
| 11 | `mean` | Mean | `numeric(8,6)` | `yes` | — | — | — | — | 平均 |
| 12 | `stddev` | Standard Deviation | `numeric(8,6)` | `no` | — | — | — | `NULL` | 標準偏差。`sample_count < 2` 時は NULL 許容 |
| 13 | `min_value` | Minimum | `numeric(8,6)` | `no` | — | — | — | `NULL` | 最小値 |
| 14 | `max_value` | Maximum | `numeric(8,6)` | `no` | — | — | — | `NULL` | 最大値 |
| 15 | `p10` | 10th Percentile | `numeric(8,6)` | `no` | — | — | — | `NULL` | 10 パーセンタイル |
| 16 | `p50` | Median | `numeric(8,6)` | `no` | — | — | — | `NULL` | 中央値 |
| 17 | `p90` | 90th Percentile | `numeric(8,6)` | `no` | — | — | — | `NULL` | 90 パーセンタイル |
| 18 | `near_zero_rate` | Near Zero Rate | `numeric(6,4)` | `no` | — | — | — | `NULL` | 0 付近張り付き率（Observability §12.7。主に `sigmoid` 層） |
| 19 | `near_one_rate` | Near One Rate | `numeric(6,4)` | `no` | — | — | — | `NULL` | 1 付近張り付き率 |
| 20 | `mid_concentration_rate` | Mid Concentration Rate | `numeric(6,4)` | `no` | — | — | — | `NULL` | 0.5 付近集中率 |
| 21 | `nan_count` | NaN Count | `integer` | `yes` | — | — | — | `0` | NaN 件数（Observability §12.6 `normalization_nan_count`） |
| 22 | `sigma_zero_count` | Sigma Zero Count | `integer` | `yes` | — | — | — | `0` | σ=0 または極小件数（Observability §12.6–§12.7） |
| 23 | `out_of_range_count` | Out Of Range Count | `integer` | `yes` | — | — | — | `0` | 期待レンジ外件数（sigmoid: 0.0〜1.0 外） |
| 24 | `calculated_at` | Calculated At | `timestamptz` | `yes` | — | — | — | — | 集計完了日時（UTC） |
| 25 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | 行作成日時 |
| 26 | `updated_at` | Updated At | `timestamptz` | `yes` | — | — | — | `now()` | 行更新日時（UPSERT 時） |

> **Observability §12.6 / §12.12 との差分**: `metric_type`（テーブル名で自明）、`z_score` 段階統計、`skewness` / `kurtosis` / `inf_count` / `model_version_id` は **MVP 物理列に含めない**（§17.1 No.1 / No.4）。`z_score` 段階は将来 `value_layer` 拡張で対応する。

> **`value_layer=raw` と張り付き率**: `near_*_rate` / `mid_concentration_rate` は sigmoid 監視が主目的のため **NULL 許容**。BATCH-016 は raw 行では算出省略可（§17.1 No.7）。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `normalization_distribution_metric_id` | サロゲート UUID | — |
| UNIQUE | `batch_run_id`, `semantic_config_version_id`, `feature_code`, `value_layer`, `feature_normalization_version_id`, `aggregation_scope`, `aggregation_key` | 集計スナップショット冪等キー | Index 名: `uq_ndm_snapshot_key`。`aggregation_scope=batch_run` 時は `aggregation_key` は **NULL 固定**（§12.1） |
| UNIQUE（部分） | `aggregation_scope`, `aggregation_key`, `semantic_config_version_id`, `feature_code`, `value_layer`, `feature_normalization_version_id` | 日次等 batch_run 非依存キー | `WHERE aggregation_scope <> 'batch_run'`。Index 名: `uq_ndm_non_batch_snapshot`（§12.2） |

---

## 8. 外部キー・参照関係

### 8.1 参照先（本テーブルから）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `semantic_config_version_id` | `semantic_config_version.semantic_config_version_id` | `ON` | `ON DELETE RESTRICT` | 集計 version 正本 |
| `batch_run_id` | `batch_run_log.batch_run_id` | `LOGICAL` | アプリ層 | `batch_run_log_テーブル定義書` §5.2 |
| `feature_normalization_version_id` | `feature_normalization_version.feature_normalization_version_id` | `LOGICAL` | アプリ層 | §5.3。正規化 version 再現性 |
| `feature_code` | `feature_definition.feature_code`（同一 `semantic_config_version_id`） | `LOGICAL` | アプリ層 | `feature_definition_テーブル定義書` §8 |

### 8.2 被参照

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| batch（監視ジョブ） | 統計列 | reads | アプリ層 | ダッシュボード・異常検知（将来） |
| reco（品質チェック） | 統計列 | reads | アプリ層 | MVP は参照のみ。書き込み禁止 |

### 8.3 集計入力関係（非 FK）

| 入力 | 関係 | 備考 |
| ---- | ---- | ---- |
| `item_feature` | aggregates from | §5.2。`entity_type=item` 固定 |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `normalization_distribution_metric_pkey` | `normalization_distribution_metric_id` | btree（PK） | 主キー | 自動生成 |
| `uq_ndm_snapshot_key` | §7 UNIQUE 列 | unique btree | batch_run 単位冪等 UPSERT | `aggregation_key` NULLS NOT DISTINCT（PG15+） |
| `uq_ndm_non_batch_snapshot` | §7 部分 UNIQUE 列 | unique btree partial | 日次 / version スコープ冪等 | `WHERE aggregation_scope <> 'batch_run'` |
| `idx_ndm_batch_run_id` | `batch_run_id` | btree | Batch Run 単位一覧 | nullable |
| `idx_ndm_version_feature_layer` | `semantic_config_version_id`, `feature_code`, `value_layer` | btree | version 比較・軸別参照 | |
| `idx_ndm_norm_version` | `feature_normalization_version_id`, `calculated_at` DESC | btree | 正規化 version 別履歴 | §5.3 |
| `idx_ndm_calculated_at` | `calculated_at` | btree | Retention DELETE | §13 |
| `idx_ndm_scope_key` | `aggregation_scope`, `aggregation_key` | btree | 日次 / version スコープ検索 | 補助 |

> 物理ER §10・§11 に本テーブル Index / 制約を反映する（#563）。

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `normalization_distribution_metric_pkey` | PRIMARY KEY | `normalization_distribution_metric_id` | 主キー | — |
| `uq_ndm_snapshot_key` | UNIQUE | §7 | batch_run 系冪等キー | — |
| `fk_ndm_semantic_config_version_id` | FOREIGN KEY | `semantic_config_version_id` | `semantic_config_version` ON DELETE RESTRICT | §8.1 |
| `chk_ndm_feature_code_mvp` | CHECK | `feature_code` | MVP 8 軸のみ | enum Task / `feature_definition` と連携 |
| `chk_ndm_value_layer` | CHECK | `value_layer` | `IN ('raw', 'sigmoid')` | §5.2。`z_score` は §17.1 No.4 |
| `chk_ndm_aggregation_scope` | CHECK | `aggregation_scope` | `IN ('batch_run', 'daily', 'semantic_config_version')` | §5.7 |
| `chk_ndm_entity_type_item` | CHECK | `entity_type` | `= 'item'` | MVP 固定 |
| `chk_ndm_batch_run_required` | CHECK | `batch_run_id`, `aggregation_scope` | `aggregation_scope <> 'batch_run' OR batch_run_id IS NOT NULL` | §5.4 |
| `chk_ndm_sample_count_non_negative` | CHECK | `sample_count` | `>= 0` | — |
| `chk_ndm_count_non_negative` | CHECK | `nan_count`, `sigma_zero_count`, `out_of_range_count` | `>= 0` | — |
| `chk_ndm_rate_range` | CHECK | `near_zero_rate`, `near_one_rate`, `mid_concentration_rate` | NULL または `0.0 <= x <= 1.0` | Observability §12.7 |
| `chk_ndm_normalization_version_required` | CHECK | `feature_normalization_version_id` | `IS NOT NULL` | MVP 必須（§17.1 No.2） |

#### `chk_ndm_feature_code_mvp` 許容値

`formality`, `safety`, `brand_appropriateness`, `emotion`, `novelty`, `intimacy`, `symbolic_identity`, `story_richness`（enum定義書 §6.16 / AGENTS.md）

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `feature_code` | `feature_code` | enum定義書 §6.16 / `packages/code-definitions/semantic/feature_code.yaml` | MVP 8 軸 | §10 CHECK |
| `value_layer` | （テーブル内 CHECK） | 本定義書 §5.2 | `raw`, `sigmoid` | Observability §12.6 の raw / sigmoid 段階 |
| `aggregation_scope` | （テーブル内 CHECK） | 本定義書 §5.7 | `batch_run`, `daily`, `semantic_config_version` | #556 / #557 と同型 |
| `entity_type` | （テーブル内 CHECK） | 本定義書 | `item`（MVP） | item_feature 集計 |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| INSERT / UPSERT | batch（BATCH-016 / IF-DB-BATCH-016） | `item_feature` 集計完了後 | 統計列 + `calculated_at` | §12.1 / §12.2 | 主経路 |
| INSERT / UPDATE | batch（BATCH-013） | — | — | **禁止**（MVP） | §5.6 / §17.1 No.6 |
| INSERT / UPDATE | reco | — | — | **禁止**（MVP） | 読み取りのみ |
| SELECT | batch / reco | 監視・異常検知 | — | — | reco は読み取りのみ |
| DELETE | Retention Batch（後続） | `calculated_at` 経過 | — | 再実行安全 | §13 |

### 12.1 `aggregation_scope = batch_run` の UPSERT

```text
1. BATCH-016 開始前に batch_run_log 行が存在すること
2. item_feature から semantic_config_version_id × feature_code × value_layer ×
   feature_normalization_version_id ごとに統計量を算出（§5.8）
3. 8 軸 × 2 value_layer（raw / sigmoid）× version 分割で N 行 / batch_run
   （sigmoid 対象行が無い軸はスキップ可）
4. UNIQUE (batch_run_id, semantic_config_version_id, feature_code, value_layer,
   feature_normalization_version_id, aggregation_scope, aggregation_key)
   に対し INSERT ... ON CONFLICT DO UPDATE
5. phase_log に feature_distribution_metric_recorded を INSERT（全 Metric 記録完了後）
```

`aggregation_key` は **`batch_run` スコープでは NULL 固定**。

### 12.2 `aggregation_scope <> batch_run` の UPSERT

日次・version スコープは **部分 UNIQUE** `uq_ndm_non_batch_snapshot` で冪等化する。

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
| 保持期間 | **365 日以上**（ログ・Observability設計書 §20.2。正規化方式妥当性検証） |
| 削除方式 | 後続 Retention Batch による **物理 DELETE** 候補 |
| 削除条件 | `calculated_at < now() - interval '365 days'` |
| 論理削除 | 採用しない |
| `batch_run_log` 連動 | **連動削除しない**（90 日パージ対象外。§5.4） |
| partition | MVP **未適用**（物理ER §17 No.5） |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `normalization_distribution_metric` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | **`semantic_config_version` / `feature_definition` / `feature_normalization_version` / `item_feature` / `batch_run_log` 作成後** |
| rollback方針 | forward migration 主体 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | batch / reco（service role 経由） |
| 書き込み権限 | **batch のみ**（BATCH-016） |
| service role利用 | Normalization Distribution Aggregator に限定 |
| 個人情報・機微情報 | **統計量のみ**。個別商品 ID・ユーザー入力は含めない |
| ログ出力制限 | 分布統計を過剰ログ出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / CHECK / UNIQUE | migration |
| 2 | feature_code CHECK | 9 軸目が拒否される | migration |
| 3 | value_layer CHECK | `z_score` が拒否される（MVP） | migration |
| 4 | batch_run 冪等 UPSERT | 同一キー再 INSERT が統計上書きになる | integration |
| 5 | version 混在分割 | 複数 `feature_normalization_version_id` が別行になる | integration |
| 6 | phase_log 連携 | `feature_distribution_metric_recorded` が記録される | integration |
| 7 | item_feature 境界 | 個別値が本テーブルに混入しない | manual |
| 8 | BATCH-013 非書込 | BATCH-013 実行だけでは本テーブル行が増えない | manual |
| 9 | Retention | `calculated_at` 基準 DELETE | manual |
| 10 | Metric 系列対称性 | 冪等キー・Retention・aggregation_scope が #556 / #557 と整合 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | Observability §12.6 / §12.12 追加統計列 | MVP 物理列範囲 | Human Reviewer | PR レビュー時 | §17.1 No.1 参照 |
| 2 | `feature_normalization_version_id` 必須条件 | version 混在分割 | Human Reviewer | PR レビュー時 | §17.1 No.2 参照 |
| 3 | `aggregation_scope` Run 拡張 | MVP 範囲 | Human Reviewer | PR レビュー時 | §17.1 No.3 参照 |
| 4 | `z_score` value_layer 追加タイミング | sigmoid-only MVP とのギャップ | Human Reviewer | PR レビュー時 | §17.1 No.4 参照 |
| 5 | phase_log フェーズ名 | enum 追加要否 | Human Reviewer | PR レビュー時 | §17.1 No.5 参照 |
| 6 | BATCH-013 直接書込 | 候補 vs 本保存境界 | Human Reviewer | PR レビュー時 | §17.1 No.6 参照 |
| 7 | raw 層の張り付き率列 | 算出要否 | Human Reviewer | PR レビュー時 | §17.1 No.7 参照 |

### 17.1 Human Review 論点（#556 / #557 先例踏襲・推奨決定案）

| No | 論点 | 推奨決定案 | 備考 |
| --: | ---- | ---------- | ---- |
| 1 | Observability §12.6 / §12.12 追加統計列 | MVP は **本表の列のみ**（`skewness` / `inf_count` 等は物理列化しない）。**`sigma_zero_count` のみ**正規化監視のため本テーブルに採用 | #556 §17.1 No.1 + Observability §12.6 固有項目 |
| 2 | `feature_normalization_version_id` | **NOT NULL 必須**（§10 CHECK）。混在時は **version ごとに行分割**（§5.8） | #557 §17.1 No.2 同型 |
| 3 | `aggregation_scope` Run 拡張 | MVP は **`batch_run` / `daily` / `semantic_config_version` のみ** | #556 §17.1 No.3 同型 |
| 4 | `z_score` value_layer | MVP は **`raw` / `sigmoid` のみ**。`z_score` は **将来 migration で CHECK 拡張**（Featureルール定義書 §14 z-score 拡張時） | feature_normalization_version §6 は sigmoid-only |
| 5 | phase_log フェーズ名 | MVP は **`feature_distribution_metric_recorded` に Normalization 記録を包含**。専用 enum **追加しない** | #557 §17.1 No.5 同型 |
| 6 | BATCH-013 直接書込 | MVP は **BATCH-016 のみ INSERT / UPSERT**。BATCH-013 は `item_feature` 更新のみ | バッチ処理一覧の「候補」表記との整合 |
| 7 | raw 層の張り付き率列 | **`near_*_rate` / `mid_concentration_rate` は NULL 許容**。sigmoid 行での算出を必須としない（BATCH-016 実装で推奨算出） | Observability §12.6 は sigmoid 監視が主 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §5.1 / §8–§11 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §11 No.61 |
| Featureルール定義書 | `docs/04_ドメインモデル設計/Featureルール定義書.md` | §14 sigmoid 正規化 |
| ログ・Observability | `docs/05_アプリケーション設計/アプリ/ログ・Observability設計書.md` | §12.6–§12.12 / §20.2 |
| バッチ処理一覧 | `docs/05_アプリケーション設計/アプリ/batch/バッチ処理一覧.md` | BATCH-013 / BATCH-016 |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-DB-BATCH-016 |
| batch_run_log | `docs/06_実装設計/database/batch_run_log_テーブル定義書.md` | §5.2 / §13 |
| feature_normalization_version | `docs/06_実装設計/database/feature_normalization_version_テーブル定義書.md` | §5.2 / §7.1 / §8.2 |
| item_feature | `docs/06_実装設計/database/item_feature_テーブル定義書.md` | §5.3 集計入力 |
| feature_distribution_metric | `docs/06_実装設計/database/feature_distribution_metric_テーブル定義書.md` | §5.5 / §17.1 対称設計正本 |
| meaning_distribution_metric | `docs/06_実装設計/database/meaning_distribution_metric_テーブル定義書.md` | §5.5 / §17.1 Metric 系列正本 |
| phase_log | `docs/06_実装設計/database/phase_log_テーブル定義書.md` | `feature_distribution_metric_recorded` |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | §6.16 feature_code |

---

## 19. レビュー観点

- テーブル一覧 §11 No.61・物理ER Log / Observability / Metric 分類と矛盾していない
- `batch_run_log` / `feature_normalization_version` / `item_feature` との関係が §5 / §8 で明記されている
- BATCH-013 / BATCH-016 / IF-DB-BATCH-016・`phase_log` trace 境界が整合している
- `feature_distribution_metric` / `meaning_distribution_metric` との責務分離・対称設計が §5.2.2 / §5.5 / §17.1 で明記されている
- raw / sigmoid 変換段階（`value_layer`）の扱いが §5.2 / §6 / §17.1 で明記されている
- Observability §12.6 候補列との差分が §6 / §17.1 で整理されている
- Retention（365 日以上）と `batch_run_log`（90 日）の非連動が §13 で明記されている
- PK / Unique / Index / CHECK が DDL Task へ展開できる粒度である
- secret や `.env` 実値が含まれていない
