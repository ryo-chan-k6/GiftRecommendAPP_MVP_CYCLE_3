# User Meaning テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                         |
| -------------- | ---------------------------- |
| ドキュメントID | `DB-TBL-MVP-user_meaning`    |
| ドキュメント名 | User Meaning テーブル定義書  |
| 対象システム   | Gift Recommendation Service MVP |
| MVP対象        | `yes`                        |
| 作成日         | 2026-06-15                   |
| 更新日         | 2026-06-15                   |

---

## 2. 概要

`user_meaning` は、**正規化済み User Feature** を Gift Meaning Space 上の **Social / Symbolic 座標**（`user_social` / `user_symbolic`）へ射影し、**Context Score 算出用の `lambda_ctx`** を保持する、User 側 Meaning の正本テーブルである。

Online 推薦（`reco`）実行中に **1 `recommendation_run` あたり最大 1 行** 生成され、Matching / Context Score 算出で参照する。Item Meaning（`item_meaning`）と同一の射影ルール・値域（0.0〜1.0）で比較可能な表現を提供する。

---

## 3. 目的

- User Feature 正規化後の 8 次元ベクトルから **Social / Symbolic スカラー** を算出し、Matching 入力として保存する
- **`lambda_ctx`**（贈答リスク許容度 / Social・Symbolic 統合重み）を Run 単位で保持し、Context Score 再現性を担保する
- `user_feature` との **生成関係**（Online / MOD-RECO-008 / IF-DB-RECO-003）と **冪等キー** を物理 DDL 粒度まで確定する
- `recommendation_run` 経由の **`semantic_config_version` 再現性** 方針を明記する
- 後続 DDL Task が migration を作成できる粒度まで設計を確定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `user_meaning` |
| 論理テーブル名 | User Meaning |
| 分類 | User意味推定系 |
| 正本区分 | 派生 / 実行時生成 |
| 主な更新主体 | reco（Online 推薦パイプライン） |
| 主な参照主体 | reco（Matching / Context Score / Observability） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §4.1 User意味推定系・§9–§11 |

---

## 5. 用途・責務

- **Meaning 射影の正本**（テーブル一覧 §4 No.9・正本定義表 `user_social` / `user_symbolic`）
- MOD-RECO-008（User Meaning Projector）において、同一 `recommendation_run_id` の **8 軸正規化済み `user_feature`** 集合から `user_social` / `user_symbolic` を算出して INSERT する
- MOD-RECO-009（User Context Builder）が算出した **`lambda_ctx`** を本行に保持し、MOD-RECO-016（Context Scorer）の入力とする
- Item Meaning（`item_meaning.item_social` / `item_symbolic`）と **同一 Gift Meaning Space** 上で距離・一致度計算（Matching）に利用する
- **Run 単位で不変**（同一 Run 内で再射影しない。再推薦は新 Run）

### 5.1 対象外

- 8 次元 Feature 値本体（`user_feature` の責務。#554 / Batch R07 No.2）
- User Semantic（`user_semantic` の責務。#553 / Batch R07 No.1）
- Item Meaning / Item Feature（`item_meaning` / `item_feature` の責務。参照のみ）
- 分布統計量（mean / std 等の **集計メトリクス** — `meaning_distribution_metric` の責務）
- 射影重み（`w_formality` 等）の **スナップショット列**（正本は `semantic_config_version` 内設定。MVP では行に denormalize しない）
- `semantic_config_version_id` の **行 denormalize**（正本は `recommendation_run.semantic_config_version_id`。§5.4 参照）
- Public API への直接公開（内部 Matching 用。OpenAPI 変更は #469 へ委譲）
- DDL / migration 本体（DDL Task へ委譲）

### 5.2 `user_feature` からの生成関係

| 観点 | 方針 |
| ---- | ---- |
| 生成モジュール | **MOD-RECO-008** User Meaning Projector（`機能×モジュール対応表` §7 No.8） |
| Context 重み | **MOD-RECO-009** User Context Builder が `lambda_ctx` を算出し、**同一 IF 保存バッチ**で本行に含める |
| 保存 I/F | **IF-DB-RECO-003**（`user_semantic` / `user_feature` / `user_meaning` を INSERT） |
| 入力正本 | 同一 `recommendation_run_id` の **`user_feature` 8 行**（MVP 8 軸すべて正規化済み値が非 NULL） |
| 入力列 | `user_feature.feature_code` + 正規化済み Feature 値（0.0〜1.0。論理ER §10.2 は `feature_value`、#554 merge 後は `user_feature_テーブル定義書` の物理列名に従う） |
| 出力列 | 本テーブル `user_social` / `user_symbolic` / `lambda_ctx` |
| カーディナリティ | `user_feature` **8 行 : `user_meaning` 1 行**（Run 単位） |
| 再生成 | **新 Run のみ**（同一 `recommendation_run_id` への再 INSERT は禁止。§12.1） |
| 生成元正本 | `user_feature_テーブル定義書`（#554 merge 済み時）または論理ER §10.2 / 物理ER §11 |

#### 5.2.1 生成パイプライン（Online / Batch R07）

処理構成定義書・機能×モジュール対応表に従う。

```text
recommendation_request
  ↓
recommendation_run（MOD-RECO-002）
  ↓
user_semantic（MOD-RECO-004）
  ↓
user_feature（MOD-RECO-007）— 8 行 / Run
  ↓
user_meaning（MOD-RECO-008）+ lambda_ctx（MOD-RECO-009）← IF-DB-RECO-003
  ↓
Matching / Context Score（MOD-RECO-014〜016）
```

`user_meaning_projected` Phase 完了時に `phase_log` を記録する（状態遷移設計書・enum定義書 §6.18）。

### 5.3 Social / Symbolic 射影ルール

GiftMeaningSpace定義書 §5–§7 を正本とする。`item_meaning_テーブル定義書` §5.3 と **同一ルール**（Human Review #515 決定を User 側へ対称適用）。

| 座標 | 入力 Feature（正規化済み値） | MVP 集約 |
| ---- | ----------------------------- | -------- |
| `user_social` | `formality`, `safety`, `brand_appropriateness` | **`semantic_config_version` 内の加重平均**。重み未設定時は **単純平均** |
| `user_symbolic` | `emotion`, `novelty`, `intimacy`, `symbolic_identity`, `story_richness` | 同上 |

```text
user_social =
  w_formality * formality
+ w_safety * safety
+ w_brand * brand_appropriateness

user_symbolic =
  w_emotion * emotion
+ w_novelty * novelty
+ w_intimacy * intimacy
+ w_symbolic_identity * symbolic_identity
+ w_story_richness * story_richness
```

| 観点 | 方針 |
| ---- | ---- |
| 値域 | **0.0〜1.0**（Feature 正規化後と同値域。Matching 比較可能） |
| 射影タイミング | **Feature 正規化後**（GiftMeaningSpace §7.2 `user_meaning_projection`） |
| 重み正本 | `recommendation_run.semantic_config_version_id` が指す `semantic_config_version`。**行に重み JSON を保持しない** |
| 欠損 Feature | 8 軸のいずれかで正規化済み値が NULL の場合、**行を INSERT しない**（エラーまたは phase 失敗として `error_log` へ） |

### 5.4 `lambda_ctx` の保持方針

Matching定義書 §4.5 / §9 を正本とする。

| 観点 | 方針 |
| ---- | ---- |
| 意味 | Social Match と Symbolic Match の **統合重み**（贈答リスク許容度） |
| 値域 | **0.0〜1.0**（`0.0` = Social 重視、`1.0` = Symbolic 重視） |
| 算出主体 | **MOD-RECO-009** User Context Builder（relationship / occasion / user_feature 等を入力） |
| 保存先 | **本テーブル `lambda_ctx` 列**（論理ER §10.2 属性と一致） |
| 欠損時 | Matching 実行時は **0.5** を使用（Matching定義書 §4.5）。DB 行は非 NULL を推奨し、算出不能時のみアプリ層デフォルト |
| Context Score | `context_score = (1 - lambda_ctx) * social_match + lambda_ctx * symbolic_match`（Matching定義書 §9.2） |

### 5.5 `item_meaning` との対称性

論理ER §10.2・`item_meaning_テーブル定義書` §5.4 を参照。

| 観点 | `user_meaning`（本テーブル） | `item_meaning` |
| ---- | ---------------------------- | -------------- |
| 単位 | `recommendation_run_id`（Run 単位） | `item_id`（商品単位） |
| Social 列 | `user_social` | `item_social` |
| Symbolic 列 | `user_symbolic` | `item_symbolic` |
| Context 列 | **`lambda_ctx`（User 専用）** | **持たない** |
| version 参照 | **`recommendation_run.semantic_config_version_id` 経由**（行に denormalize しない） | **`semantic_config_version_id` 列で直接保持** |
| 正規化 version | `feature_normalization_version_id`（LOGICAL・再現性） | 同上（列あり） |
| 更新主体 | reco（Online 生成） | batch（BATCH-013 事前生成） |
| 参照主体 | reco（Matching） | batch / reco（Matching） |
| 冪等性 | **Run あたり 1 行（UNIQUE `recommendation_run_id`）** | 商品 × version で UPSERT |

### 5.6 分布メトリクスとの責務境界

ログ・Observability設計書の `user_social_mean` / `user_symbolic_mean` 等は **集計メトリクス名** であり、本テーブルの列名ではない。

| 観点 | 本テーブル | `meaning_distribution_metric`（別 Task） |
| ---- | ---------- | ---------------------------------------- |
| 粒度 | **Run 1 行** | 分布統計（mean / std / 分位点等） |
| 用途 | Matching / Context Score 入力 | Reco 品質監視・Observability |
| 更新主体 | reco（Online） | batch / reco（集計） |
| mean / std 列 | **持たない** | **保持する**（Metric 系 Task で定義） |

### 5.7 `recommendation_run` との version 再現性

| 観点 | 方針 |
| ---- | ---- |
| `semantic_config_version_id` | **`recommendation_run` 行に保持**（LOGICAL FK。`recommendation_run_テーブル定義書` §6 No.4） |
| 本テーブル | **行に `semantic_config_version_id` を持たない**（Join またはアプリ層キャッシュで解決） |
| 射影重み | Run 生成時点の `semantic_config_version_id` が指す設定を使用 |
| `feature_normalization_version_id` | 本テーブルに **LOGICAL 列で保持**（入力 `user_feature` 8 行の共通正規化 version。再現性） |
| 再現性 | Run 完了後は **不変**。推薦結果再現は `recommendation_run_id` + 子派生データで担保 |

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `user_meaning_id` | User Meaning ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | Meaning 行 ID |
| 2 | `recommendation_run_id` | Recommendation Run ID | `uuid` | `yes` | — | `ON` | `yes` | — | 対象 Run。`recommendation_run.recommendation_run_id` 参照 |
| 3 | `feature_normalization_version_id` | Feature Normalization Version ID | `uuid` | `yes` | — | `LOGICAL` | — | — | 入力 `user_feature` 集合が使用した正規化 version（再現性） |
| 4 | `user_social` | User Social | `numeric(6,4)` | `yes` | — | — | — | — | Social 座標（0.0〜1.0） |
| 5 | `user_symbolic` | User Symbolic | `numeric(6,4)` | `yes` | — | — | — | — | Symbolic 座標（0.0〜1.0） |
| 6 | `lambda_ctx` | Lambda Context | `numeric(6,4)` | `yes` | — | — | — | — | Social / Symbolic 統合重み（0.0〜1.0） |
| 7 | `generated_at` | Generated At | `timestamptz` | `yes` | — | — | — | — | Meaning 射影完了日時（UTC） |
| 8 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | 行作成日時 |
| 9 | `updated_at` | Updated At | `timestamptz` | `yes` | — | — | — | `now()` | 行更新日時（MVP では INSERT 後原則不変） |

> **`user_social` / `user_symbolic` の型**: MVP では **`numeric(6,4)` スカラー** を採用（`item_meaning` 対称・JSONB ベクトルは不採用。Human Review #515 §17.1 No.1 と整合）。

> **`semantic_config_version_id` 非保持**: 論理ER §10.2 属性に合わせ、version は `recommendation_run` 経由で参照する（§5.7）。

> **`updated_at`**: MVP では Run 内再射影を行わないため、INSERT 時に `created_at` と同値を設定し、以降 UPDATE しない。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `user_meaning_id` | サロゲート UUID | — |
| UNIQUE | `recommendation_run_id` | Run あたり最大 1 行 | 物理ER §9 generates 1:0..1・冪等キー（§12.1） |

---

## 8. 外部キー・参照関係

### 8.1 参照先（本テーブルから）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `recommendation_run_id` | `recommendation_run.recommendation_run_id` | `ON` | `ON DELETE RESTRICT` | 物理ER §9・`recommendation_run_テーブル定義書` §8.2 |
| `feature_normalization_version_id` | `feature_normalization_version.feature_normalization_version_id` | `LOGICAL` | Index 推奨 | `user_feature` / `feature_normalization_version_テーブル定義書` §8.2 |

### 8.2 被参照

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| reco（Matching / Context Score） | `recommendation_run_id` | reads | アプリ層 | MOD-RECO-014〜016 |
| Observability | Run 単位集計 | aggregates | アプリ層 | `user_social_mean` 等メトリクス名（§5.6） |

### 8.3 生成元（論理関係・物理 FK なし）

| 生成元 | 関係 | 備考 |
| ------ | ---- | ---- |
| `user_feature`（8 行 / Run） | derives_from | 同一 `recommendation_run_id` + 8 `feature_code` |
| MOD-RECO-008 / MOD-RECO-009 | generates | IF-DB-RECO-003 保存バッチ |
| `recommendation_run` | version_context | `semantic_config_version_id` は親 Run 行を参照 |

### 8.4 `user_feature` との整合（#554 merge 前 / 後）

| 論点 | `user_feature`（論理ER §10.2 / #554 正本） | 本テーブル |
| ---- | ------------------------------------------ | ---------- |
| 射影入力列 | 正規化済み Feature 値（0.0〜1.0） | `user_social` / `user_symbolic` へ集約 |
| 入力行数 | **8 行 / Run** | **1 行 / Run** |
| `recommendation_run_id` FK | 物理 FK **ON**（1:N） | 物理 FK **ON**（1:0..1 UNIQUE） |
| `feature_normalization_version_id` | LOGICAL（行ごと） | LOGICAL（8 行の共通 version を記録） |
| 更新主体 | reco（Online INSERT） | reco（Online INSERT） |

### 8.5 `item_meaning` との整合（#515 正本）

| 論点 | 本テーブル | `item_meaning` |
| ---- | ---------- | -------------- |
| Social / Symbolic 型 | `numeric(6,4)` × 2 | 同型 |
| 射影式 | GiftMeaningSpace §5 加重平均（未設定時単純平均） | 同型 |
| version 列 | Run 経由（非 denormalize） | `semantic_config_version_id` 直接保持 |
| Context | `lambda_ctx` あり | なし |
| 更新操作 | INSERT（Run 単位） | UPSERT（商品 × version） |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `user_meaning_pkey` | `user_meaning_id` | btree（PK） | 主キー | 自動生成 |
| `uq_user_meaning_recommendation_run` | `recommendation_run_id` | unique btree | Run あたり 1 行 | §7 |
| `idx_user_meaning_run` | `recommendation_run_id` | btree | Matching / Run 単位参照 | FK 補助 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `user_meaning_pkey` | PRIMARY KEY | `user_meaning_id` | 主キー | — |
| `fk_user_meaning_recommendation_run_id` | FOREIGN KEY | `recommendation_run_id` | `recommendation_run(recommendation_run_id)` ON DELETE RESTRICT | §8.1 |
| `uq_user_meaning_recommendation_run` | UNIQUE | `recommendation_run_id` | Run あたり 1 行 | §7 |
| `chk_user_meaning_social_range` | CHECK | `user_social` | `user_social >= 0.0 AND user_social <= 1.0` | 物理ER §11 `chk_feature_value_range` と同型 |
| `chk_user_meaning_symbolic_range` | CHECK | `user_symbolic` | `user_symbolic >= 0.0 AND user_symbolic <= 1.0` | 同上 |
| `chk_user_meaning_lambda_ctx_range` | CHECK | `lambda_ctx` | `lambda_ctx >= 0.0 AND lambda_ctx <= 1.0` | Matching定義書 §4.5 |

---

## 11. 状態・enum

本テーブルは **状態カラムを持たない**（論理ER §15 対象外）。Phase 名は `phase_log.phase_name = user_meaning_projected` で記録（enum定義書 §6.18）。

| カラム | enum / code | 定義元 | 備考 |
| ------ | ----------- | ------ | ---- |
| — | `user_meaning_projected` | `enum定義書` §6.18 / `recommendation_run_phase_name` | 本テーブル列ではなく phase_log 側 |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| INSERT | reco（MOD-RECO-008 / 009） | 8 軸 `user_feature` 正規化値が揃っている | 全業務列 | `recommendation_run_id` UNIQUE | IF-DB-RECO-003 |
| SELECT | reco | Matching / Context Score / 監視 | — | — | Run 内参照 |
| UPDATE | reco | — | — | **MVP 禁止** | Run 完了後は不変 |
| DELETE | reco / batch | §13 方針 | 孤児行等 | 定期 | 通常は INSERT のみ |
| INSERT / UPDATE / DELETE | api | — | — | **禁止** | api は直接 DML しない |

### 12.1 Online 射影 INSERT フロー

```text
1. recommendation_run が running 状態で存在すること
2. 同一 recommendation_run_id の user_feature 8 行を取得
3. いずれか正規化済み値が NULL → 本テーブル INSERT スキップ（error_log）
4. GiftMeaningSpace §5 射影式で user_social / user_symbolic を算出
   （重みは recommendation_run.semantic_config_version_id 経由で解決）
5. MOD-RECO-009 で lambda_ctx を算出（算出不能時は 0.5 をアプリ層で使用しつつ DB には記録方針を Human Review）
6. feature_normalization_version_id は 8 行の共通 version を記録
7. INSERT（recommendation_run_id の UNIQUE 違反時はエラー — 再実行は冪等設計で INSERT 前に存在確認）
8. generated_at = now(), created_at = updated_at = now()
9. phase_log に user_meaning_projected を記録（IF-DB-RECO-009）
```

### 12.2 INSERT 疑似 SQL

```sql
INSERT INTO user_meaning (
  recommendation_run_id,
  feature_normalization_version_id,
  user_social,
  user_symbolic,
  lambda_ctx,
  generated_at
) VALUES (
  :recommendation_run_id,
  :feature_normalization_version_id,
  :user_social,
  :user_symbolic,
  :lambda_ctx,
  now()
);
```

### 12.3 再生成・再実行方針

| 要因 | 本テーブル更新 |
| ---- | -------------- |
| 同一 Run 内の再射影 | **×**（設計上禁止。失敗時は Run failed） |
| 新 `recommendation_run`（再推薦） | ○（新 Run 用に新行 INSERT） |
| `semantic_config_version` 変更（新 Run） | ○（新 Run の Run 行 version で射影） |
| `user_feature` 再生成（同一 Run） | ×（パイプライン異常。Run 失敗扱い） |
| Batch による更新 | ×（User 派生は Online 生成のみ） |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | **Run ライフサイクルに追随**（`recommendation_run` と同程度。長期分析用に保持） |
| 削除方式 | 親 `recommendation_run` 削除は **RESTRICT**。Run Retention 方針は Epic 後続 Task |
| 削除条件 | 孤児行整理は運用メンテナンス（低頻度） |
| 論理削除 | 列なし |
| アーカイブ | MVP 対象外 |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `user_meaning` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: **`recommendation_run` 作成後**。`user_feature` 作成後（生成元依存）。`recommendation_result` より **前または並行可** |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | reco（service role 経由） |
| 書き込み権限 | reco のみ（Online パイプライン） |
| service role利用 | reco DML に限定。api から直接 DML 禁止 |
| 個人情報・機微情報 | ユーザー入力から **派生した意味スコア**。生テキストは `user_semantic` 側。ログに secret を含めない |
| ログ出力制限 | secret・API キー・生のユーザー入力全文をログに含めない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / FK / CHECK / UNIQUE が定義どおり | migration |
| 2 | FK 整合 | 存在しない `recommendation_run_id` への INSERT が拒否される | migration |
| 3 | 値域 CHECK | `user_social` / `user_symbolic` / `lambda_ctx` が 0.0〜1.0 外で拒否される | migration |
| 4 | UNIQUE | 同一 `recommendation_run_id` で 2 行目 INSERT が拒否される | integration |
| 5 | 射影整合 | MOD-RECO-008 後、8 軸 Feature から算出した Social / Symbolic と DB 行が一致 | integration |
| 6 | IF 整合 | IF-DB-RECO-003 経路で `user_feature` と本テーブルが同一パイプラインで保存される | integration |
| 7 | lambda_ctx | Context Score 算出が保存済み `lambda_ctx` と一致 | integration |
| 8 | version 再現 | `recommendation_run.semantic_config_version_id` と射影結果が対応 | integration |
| 9 | 権限 | api ロールからの DML が拒否される | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | `lambda_ctx` 算出不能時の DB 保存 | NULL 許容 vs `0.5` 固定 INSERT | Human | Human Review | §5.4 / §12.1 |
| 2 | `feature_normalization_version_id` 8 行不一致時 | 射影拒否 vs 多数決 version | Human | Human Review | §8.4 |
| 3 | #554 merge 後の物理列名突合 | `feature_value` vs `normalized_feature_value` | Human | #554 完了後 | §5.2 / §8.4 |

### 17.1 Human Review 仮決定（Issue #555 作業時点）

`item_meaning`（#515）の決定を対称適用する仮決定。Human Review で確定する。

| No | 論点 | 仮決定内容 | 根拠 |
| --: | ---- | ---------- | ---- |
| 1 | Social / Symbolic 列型 | **`numeric(6,4)` スカラー 2 列** | #515 §17.1 No.1 対称 |
| 2 | 射影重みスナップショット | **行に保持しない**。`recommendation_run` → `semantic_config_version` 参照 | #515 §17.1 No.2 対称 |
| 3 | 加重平均 vs 単純平均 | **`semantic_config_version` 内加重平均**。未設定時 **単純平均** | #515 §17.1 No.3 対称 |
| 4 | `semantic_config_version_id` | **行に denormalize しない**（Run 経由） | 論理ER §10.2・§5.7 |
| 5 | `lambda_ctx` | **本テーブル列に保持**（非 NULL） | 論理ER §10.2・Matching §4.5 |
| 6 | 冪等キー / mean・std | **`UNIQUE (recommendation_run_id)`**。mean / std は **Metric 系のみ** | 物理ER 1:0..1・§5.6 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §9 FK・§11 制約方針 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §10.2 user_meaning 属性・§16 責務境界 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §4 No.9 |
| 正本定義表 | `docs/05_アプリケーション設計/アプリ/database/正本定義表.md` | User Meaning 正本区分 |
| GiftMeaningSpace | `docs/04_ドメインモデル設計/GiftMeaningSpace定義書.md` | §5–§7 射影ルール |
| Matching | `docs/04_ドメインモデル設計/Matching定義書.md` | lambda_ctx・Context Score |
| Feature定義書 | `docs/04_ドメインモデル設計/Feature定義書.md` | 8 軸 Feature |
| 処理構成定義書 | `docs/05_アプリケーション設計/アプリ/処理構成定義書.md` | Online パイプライン |
| 機能×モジュール対応表 | `docs/05_アプリケーション設計/アプリ/機能×モジュール対応表.md` | MOD-RECO-008 / 009 |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-DB-RECO-003 |
| 状態遷移設計書 | `docs/05_アプリケーション設計/アプリ/状態遷移設計書.md` | user_meaning_projected |
| ログ・Observability | `docs/05_アプリケーション設計/アプリ/ログ・Observability設計書.md` | 分布メトリクス名 |
| recommendation_run | `docs/06_実装設計/database/recommendation_run_テーブル定義書.md` | §8.2 被参照・version 列 |
| semantic_config_version | `docs/06_実装設計/database/semantic_config_version_テーブル定義書.md` | 射影重み |
| feature_definition | `docs/06_実装設計/database/feature_definition_テーブル定義書.md` | 8 軸 |
| feature_normalization_version | `docs/06_実装設計/database/feature_normalization_version_テーブル定義書.md` | 正規化 version |
| item_meaning | `docs/06_実装設計/database/item_meaning_テーブル定義書.md` | #515 対称性正本 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | phase_name / feature_code |
| user_feature | `docs/06_実装設計/database/user_feature_テーブル定義書.md` | #554 merge 後・生成元正本 |

---

## 19. レビュー観点

- 物理ER §9（`recommendation_run_id` ON・generates 1:0..1）・テーブル一覧 §4 No.9 と矛盾していない
- GiftMeaningSpace §5–§7 の Social / Symbolic 射影と `user_social` / `user_symbolic` 列が整合している
- `item_meaning_テーブル定義書`（#515）との対称性・差分が §5.5 / §8.5 で整理されている
- IF-DB-RECO-003 / MOD-RECO-008 による `user_feature` → `user_meaning` 生成関係が §5.2 / §12 で明示されている
- `lambda_ctx` の保持・値域・Context Score 利用が §5.4 で明記されている
- `recommendation_run` 経由の `semantic_config_version` 再現性が §5.7 で明記されている
- 冪等キー `recommendation_run_id` UNIQUE が §7 / §12.1 で定義されている
- mean / std 等分布統計が本テーブルに混在せず、Metric 系と責務分離されている（§5.6）
- 論理ER §10.2 属性（`user_social` / `user_symbolic` / `lambda_ctx`）と整合している
- User 派生は Online 生成・Item 派生は Online 更新しない（論理ER §16）責務境界が明記されている
- apps/** / OpenAPI / generated 変更が含まれていない
- secret や `.env` 実値が含まれていない
