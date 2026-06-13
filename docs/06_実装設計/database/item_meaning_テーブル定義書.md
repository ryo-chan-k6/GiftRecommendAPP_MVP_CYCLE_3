# Item Meaning テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                         |
| -------------- | ---------------------------- |
| ドキュメントID | `DB-TBL-MVP-item_meaning`    |
| ドキュメント名 | Item Meaning テーブル定義書  |
| 対象システム   | Gift Recommendation Service MVP |
| MVP対象        | `yes`                        |
| 作成日         | 2026-06-14                   |
| 更新日         | 2026-06-14                   |

---

## 2. 概要

`item_meaning` は、**正規化済み Item Feature** を Gift Meaning Space 上の **Social / Symbolic 座標**（`item_social` / `item_symbolic`）へ射影した、商品側 Meaning の正本テーブルである。

Batch 事前生成（BATCH-013 Feature 正規化 Batch）で UPSERT され、Online 推薦（Matching / Retrieval 前処理）では **参照のみ** とする。User Meaning（`user_meaning`）と同一の射影ルール・値域（0.0〜1.0）で比較可能な表現を提供する。

---

## 3. 目的

- Item Feature 正規化後の 8 次元ベクトルから **Social / Symbolic スカラー** を算出し、Matching 入力として保存する
- `item_feature` との **生成関係**（BATCH-013 / IF-DB-BATCH-014）と **冪等キー** を物理 DDL 粒度まで確定する
- `semantic_config_version_id` による意味体系 version 管理と再生成判定方針を明記する
- 後続 DDL Task が migration を作成できる粒度まで設計を確定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `item_meaning` |
| 論理テーブル名 | Item Meaning |
| 分類 | Item派生データ系 |
| 正本区分 | 派生 / 推薦用正本 |
| 主な更新主体 | batch（BATCH-013 / IF-DB-BATCH-014） |
| 主な参照主体 | batch / reco（Matching・分布監視の入力。api は直接参照しない） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §4.1 Item派生データ系・§9–§11 |

---

## 5. 用途・責務

- **Meaning 射影の正本**（テーブル一覧 §7 No.30・正本定義表 `item_social` / `item_symbolic`）
- BATCH-013 において、同一 `item_id` + `semantic_config_version_id` の **8 軸 `item_feature.normalized_value`** 集合から `item_social` / `item_symbolic` を算出して UPSERT する
- User Meaning（`user_meaning.user_social` / `user_symbolic`）と **同一 Gift Meaning Space** 上で距離・一致度計算（Matching）に利用する
- Online 推薦中は **更新しない**（論理ER §16.1・`item_テーブル定義書` §5.2 と同型）

### 5.1 対象外

- 8 次元 Feature 値本体（`item_feature` の責務。#514 / Batch R03 No.2）
- Item Semantic / Item Embedding（別 Task）
- User Meaning（Online / `recommendation_run` 単位。User意味推定系）
- 分布統計量（mean / std 等の **集計メトリクス** — `meaning_distribution_metric` の責務。BATCH-016）
- 射影重み（`w_formality` 等）の **スナップショット列**（正本は `semantic_config_version` 内設定。MVP では行に denormalize しない）
- Public API への直接公開（内部 Matching 用。OpenAPI 変更は #469 へ委譲）
- DDL / migration 本体（DDL Task へ委譲）

### 5.2 `item_feature` からの生成関係

| 観点 | 方針 |
| ---- | ---- |
| 生成 Batch | **BATCH-013**（Feature 正規化 Batch。`item_feature.raw_value` → `normalized_value` と **同一トランザクション** で Meaning 射影） |
| 保存 I/F | **IF-DB-BATCH-014**（`item_feature.normalized_value` / `item_meaning` を UPDATE / UPSERT） |
| 入力正本 | 同一 `item_id` + `semantic_config_version_id` の **`item_feature` 8 行**（MVP 8 軸すべて `normalized_value` が非 NULL） |
| 入力列 | `item_feature.feature_code` + `item_feature.normalized_value`（正規化後 0.0〜1.0） |
| 出力列 | 本テーブル `item_social` / `item_symbolic` |
| カーディナリティ | `item_feature` **8 行 : `item_meaning` 1 行**（version 単位） |
| 再生成トリガー | `item_feature` 集合の再生成（`feature_input_hash` / `feature_normalization_version_id` 変更を含む）に追随して BATCH-013 が再 UPSERT |
| 先行 Task | `item_feature` テーブル定義書（#514）。未 merge 時は論理ER §10.2・物理ER §11 `uq_item_feature_idempotent` を参照 |

#### 5.2.1 生成パイプライン（Batch R03）

バッチ設計方針書 §13・バッチ依存関係図に従う。

```text
item (正本)
  ↓
item_semantic（BATCH-010〜011）
  ↓
item_feature.raw_value（BATCH-012）
  ↓
item_feature.normalized_value + item_meaning（BATCH-013）← IF-DB-BATCH-014
  ↓
Matching / meaning_distribution_metric（BATCH-016）
```

`item_generation_queue`（`generation_type = feature` / `semantic`）消化時、BATCH-011〜013 区間で本テーブルが更新される。

### 5.3 Social / Symbolic 射影ルール

GiftMeaningSpace定義書 §5–§7 を正本とする。

| 座標 | 入力 Feature（`normalized_value`） | MVP 集約 |
| ---- | ----------------------------------- | -------- |
| `item_social` | `formality`, `safety`, `brand_appropriateness` | 加重平均（重みは `semantic_config_version` 内。未設定時は **単純平均**） |
| `item_symbolic` | `emotion`, `novelty`, `intimacy`, `symbolic_identity`, `story_richness` | 同上 |

```text
item_social =
  w_formality * formality
+ w_safety * safety
+ w_brand * brand_appropriateness

item_symbolic =
  w_emotion * emotion
+ w_novelty * novelty
+ w_intimacy * intimacy
+ w_symbolic_identity * symbolic_identity
+ w_story_richness * story_richness
```

| 観点 | 方針 |
| ---- | ---- |
| 値域 | **0.0〜1.0**（Feature 正規化後と同値域。Matching 比較可能） |
| 射影タイミング | **Feature 正規化後**（GiftMeaningSpace §7.2 `item_meaning_projection`） |
| 重み正本 | `semantic_config_version`（§5.4）。本テーブル行には **重み JSON を保持しない** |
| 欠損 Feature | 8 軸のいずれかが欠損・NULL の場合、**行を UPSERT しない**（`item_feature.generation_status` で先行判定。詳細は #514） |

### 5.4 `user_meaning` との対称性

論理ER §10.2・正本定義表を参照。

| 観点 | `user_meaning` | `item_meaning`（本テーブル） |
| ---- | -------------- | ---------------------------- |
| 単位 | `recommendation_run_id`（Run 単位） | `item_id`（商品単位） |
| Social 列 | `user_social` | `item_social` |
| Symbolic 列 | `user_symbolic` | `item_symbolic` |
| Context 列 | `lambda_ctx`（User 専用） | **持たない** |
| version 参照 | `recommendation_run.semantic_config_version_id` 経由 | **`semantic_config_version_id` 列で直接保持** |
| 更新主体 | reco（Online 生成） | batch（事前生成） |
| 参照主体 | reco（Matching） | batch / reco（Matching） |

> **論理ER §10.2 との差分**: 論理ER主要属性表に **`item_meaning` エンティティが未列挙**（`user_meaning` のみ定義）。本定義書は物理ER §9・テーブル一覧 §7 No.30 を正として `item_meaning_id` / `item_id` / `semantic_config_version_id` / `item_social` / `item_symbolic` / `generated_at` を採用する。論理ER への追記は別 docs Task で検討する（§17.1 No.4）。

### 5.5 分布メトリクスとの責務境界

ログ・Observability設計書の `item_social_mean` / `item_symbolic_mean` 等は **集計メトリクス名** であり、本テーブルの列名ではない。

| 観点 | 本テーブル | `meaning_distribution_metric`（BATCH-016） |
| ---- | ---------- | ------------------------------------------- |
| 粒度 | **商品 × semantic_config_version 1 行** | 分布統計（mean / std / 分位点等） |
| 用途 | Matching 入力 | Reco 品質監視・Observability |
| 更新 Batch | BATCH-013 | BATCH-016 |
| mean / std 列 | **持たない** | **保持する**（Metric 系 Task で定義） |

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `item_meaning_id` | Item Meaning ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | Meaning 行 ID |
| 2 | `item_id` | Item ID | `uuid` | `yes` | — | `ON` | — | — | 対象商品。`item.item_id` 参照 |
| 3 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `LOGICAL` | — | — | 射影に用いた意味体系 version |
| 4 | `feature_normalization_version_id` | Feature Normalization Version ID | `uuid` | `yes` | — | `LOGICAL` | — | — | 入力 `item_feature` 集合が使用した正規化 version（再現性） |
| 5 | `item_social` | Item Social | `numeric(6,4)` | `yes` | — | — | — | — | Social 座標（0.0〜1.0） |
| 6 | `item_symbolic` | Item Symbolic | `numeric(6,4)` | `yes` | — | — | — | — | Symbolic 座標（0.0〜1.0） |
| 7 | `generated_at` | Generated At | `timestamptz` | `yes` | — | — | — | — | Meaning 射影完了日時（UTC） |
| 8 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | 行作成日時 |
| 9 | `updated_at` | Updated At | `timestamptz` | `yes` | — | — | — | `now()` | 行更新日時（再 UPSERT 時） |

> **`item_social` / `item_symbolic` の型**: MVP では **スカラー `numeric(6,4)`** を採用（`user_meaning` 対称・JSONB ベクトルは不採用）。Human Review 論点は §17.1 No.1。

> **`feature_normalization_version_id`**: 同一 version の `item_feature` 8 行と **一致** させる。`item_feature` 行ごとに version が異なる場合は **射影前に整合を取る**（通常 BATCH-013 単一 run では同一 version）。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `item_meaning_id` | サロゲート UUID | — |
| UNIQUE | `item_id`, `semantic_config_version_id` | 商品 × 意味 version あたり 1 行 | 冪等 UPSERT キー（§12.1） |

---

## 8. 外部キー・参照関係

### 8.1 参照先（本テーブルから）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `item_id` | `item.item_id` | `ON` | `ON DELETE RESTRICT` | 物理ER §9・`item_テーブル定義書` §8.2 |
| `semantic_config_version_id` | `semantic_config_version.semantic_config_version_id` | `LOGICAL` | Index 推奨 | `semantic_config_version_テーブル定義書` §8 |
| `feature_normalization_version_id` | `feature_normalization_version.feature_normalization_version_id` | `LOGICAL` | Index 推奨 | `feature_normalization_version_テーブル定義書` §8 |

### 8.2 被参照

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| reco（Matching） | `item_id` + `semantic_config_version_id` | reads | アプリ層 | IF-DB-RECO（Matching 実行時） |
| BATCH-016 | 分布集計入力 | aggregates | アプリ層 | `meaning_distribution_metric` 生成 |

### 8.3 生成元（論理関係・物理 FK なし）

| 生成元 | 関係 | 備考 |
| ------ | ---- | ---- |
| `item_feature`（8 行 / version） | derives_from | 同一 `item_id` + `semantic_config_version_id` + 8 `feature_code` |
| BATCH-013 / IF-DB-BATCH-014 | generates | 正規化と射影を同一処理単位 |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `item_meaning_pkey` | `item_meaning_id` | btree（PK） | 主キー | 自動生成 |
| `uq_item_meaning_item_scv` | `item_id`, `semantic_config_version_id` | unique btree | 冪等 UPSERT | §7 |
| `idx_item_meaning_lookup` | `item_id`, `semantic_config_version_id` | btree | Online Matching 参照 | `item_feature.idx_item_feature_lookup` と同型 |
| `idx_item_meaning_scv` | `semantic_config_version_id` | btree | version 単位の再生成・監視 | 任意（DDL Task で採否） |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `item_meaning_pkey` | PRIMARY KEY | `item_meaning_id` | 主キー | — |
| `fk_item_meaning_item_id` | FOREIGN KEY | `item_id` | `item(item_id)` ON DELETE RESTRICT | §8.1 |
| `uq_item_meaning_item_scv` | UNIQUE | `item_id`, `semantic_config_version_id` | 冪等キー | §7 |
| `chk_item_meaning_social_range` | CHECK | `item_social` | `item_social >= 0.0 AND item_social <= 1.0` | 物理ER §11 `chk_feature_value_range` と同型 |
| `chk_item_meaning_symbolic_range` | CHECK | `item_symbolic` | `item_symbolic >= 0.0 AND item_symbolic <= 1.0` | 同上 |

---

## 11. 状態・enum

本テーブルは **状態カラムを持たない**（論理ER §15 対象外）。Feature 軸 enum は生成元 `item_feature.feature_code` を参照（enum定義書 §6 / `feature_definition`）。

| カラム | enum / code | 定義元 | 備考 |
| ------ | ----------- | ------ | ---- |
| — | — | — | 本テーブル固有 enum なし |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| UPSERT | batch（BATCH-013） | 8 軸 `item_feature.normalized_value` が揃っている | 全業務列 + `updated_at` | `item_id` + `semantic_config_version_id` | IF-DB-BATCH-014 |
| SELECT | batch / reco | Matching / 監視 | — | — | Online 参照 |
| INSERT / UPDATE / DELETE | api | — | — | **禁止** | Online 推薦中に更新しない |
| DELETE | batch（メンテナンス） | §13 方針 | 孤児行等 | 定期 | 通常は UPSERT のみ |

### 12.1 BATCH-013 射影 UPSERT フロー

```text
1. 対象 item_id + semantic_config_version_id の item_feature 8 行を取得
2. いずれか normalized_value が NULL → 本テーブル UPSERT スキップ（error_log 等）
3. GiftMeaningSpace §5 射影式で item_social / item_symbolic を算出
4. feature_normalization_version_id は 8 行の共通 version を記録（不一致時は Human エスカレーション）
5. UPSERT ON CONFLICT (item_id, semantic_config_version_id)
6. generated_at = now(), updated_at = now()
```

### 12.2 UPSERT 疑似 SQL

```sql
INSERT INTO item_meaning (
  item_id,
  semantic_config_version_id,
  feature_normalization_version_id,
  item_social,
  item_symbolic,
  generated_at
) VALUES (
  :item_id,
  :semantic_config_version_id,
  :feature_normalization_version_id,
  :item_social,
  :item_symbolic,
  now()
)
ON CONFLICT (item_id, semantic_config_version_id)
DO UPDATE SET
  feature_normalization_version_id = EXCLUDED.feature_normalization_version_id,
  item_social = EXCLUDED.item_social,
  item_symbolic = EXCLUDED.item_symbolic,
  generated_at = EXCLUDED.generated_at,
  updated_at = now();
```

### 12.3 再生成判定

テーブル一覧 §7 補足・バッチ設計方針書 §13 に従う。

| 要因 | 本テーブル更新 |
| ---- | -------------- |
| `item_feature` 再生成（hash / normalization version 変更） | ○（BATCH-013 追随） |
| `semantic_config_version_id` 変更（射影重み変更含む） | ○（新 version キーで UPSERT。旧 version 行は保持） |
| `item` 本文のみ変更で Feature 不変 | ×（`item_feature` 不変なら Meaning も不変） |
| Online Matching 実行 | ×（参照のみ） |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | **長期**（派生 / 推薦用正本。`semantic_config_version` ごとの再現用に履歴 version 行を保持） |
| 削除方式 | 原則 **物理 DELETE しない**（UPSERT 更新） |
| 削除条件 | 親 `item` 削除は RESTRICT。version 失効時の孤児行整理は運用メンテナンス（低頻度） |
| 論理削除 | 列なし |
| アーカイブ | MVP 対象外 |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `item_meaning` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: **`item`・`semantic_config_version`・`feature_normalization_version` 作成後**。**`item_feature` 作成後**（生成元依存）。`item_embedding` より **前または並行可** |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | batch / reco（service role 経由） |
| 書き込み権限 | batch のみ（BATCH-013） |
| service role利用 | Batch DML に限定。api から直接 DML 禁止 |
| 個人情報・機微情報 | 商品意味スコアのみ。ユーザー入力は含まない |
| ログ出力制限 | secret・API キーをログに含めない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / FK / CHECK / UNIQUE が定義どおり | migration |
| 2 | FK 整合 | 存在しない `item_id` への INSERT が拒否される | migration |
| 3 | 値域 CHECK | `item_social` / `item_symbolic` が 0.0〜1.0 外で拒否される | migration |
| 4 | 冪等 UPSERT | 同一 `item_id` + `semantic_config_version_id` で 2 行目が INSERT されない | integration |
| 5 | 射影整合 | BATCH-013 後、8 軸 Feature から算出した Social / Symbolic と DB 行が一致 | integration |
| 6 | IF 整合 | IF-DB-BATCH-014 経路で `item_feature` と本テーブルが同一 run で更新される | integration |
| 7 | Online 参照 | reco Matching が `semantic_config_version_id` 一致行を参照できる | integration |
| 8 | 権限 | api ロールからの DML が拒否される | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | `item_social` / `item_symbolic` の物理型 | scalar vs JSONB ベクトル | Human | Task PR Human Review | MVP 案: `numeric(6,4)` スカラー（§6） |
| 2 | 射影重みスナップショット | version 変更後の再現性 | Human | 同上 | MVP 案: **非保持**（`semantic_config_version` 正本参照） |
| 3 | 加重平均 vs 単純平均 | GiftMeaningSpace §5 は両方許容 | Human | 同上 | Config 未設定時は単純平均 |
| 4 | 論理ER §10.2 追記 | `item_meaning` エンティティ未列挙 | Human | 別 docs Task | 本定義書で差分明示済み（§5.4） |
| 5 | #514 merge 後突合 | `item_feature` 列名・`generation_status` 連携 | Human | #514 PR 後 | 未 merge 時は物理ER §11 を正本 |

### 17.1 Human Review 論点（Issue #515）

| No | 論点 | MVP 提案 | 備考 |
| --: | ---- | -------- | ---- |
| 1 | Social / Symbolic 列型 | **`numeric(6,4)` スカラー 2 列** | `user_meaning` 対称。JSONB は不採用 |
| 2 | 冪等キー | **`UNIQUE (item_id, semantic_config_version_id)`** | `item_feature` 8 行 : 本テーブル 1 行 |
| 3 | mean / std | **本テーブルに持たない** | `meaning_distribution_metric`（BATCH-016）へ委譲 |
| 4 | 射影重み | **行に持たない** | `semantic_config_version` 参照 |
| 5 | `feature_normalization_version_id` | **保持する**（LOGICAL） | `item_feature` 集合との再現性 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §9 FK・§11 制約方針 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §10.2 user_meaning 対称・§16 責務境界 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §7 No.30 |
| 正本定義表 | `docs/05_アプリケーション設計/アプリ/database/正本定義表.md` | Item Meaning 正本区分 |
| GiftMeaningSpace | `docs/04_ドメインモデル設計/GiftMeaningSpace定義書.md` | §5–§7 射影ルール |
| Matching | `docs/04_ドメインモデル設計/Matching定義書.md` | Meaning 比較 |
| Feature定義書 | `docs/04_ドメインモデル設計/Feature定義書.md` | 8 軸 Feature |
| バッチ設計方針書 | `docs/05_アプリケーション設計/アプリ/batch/バッチ設計方針書.md` | §13 生成パイプライン |
| バッチ処理一覧 | `docs/05_アプリケーション設計/アプリ/batch/バッチ処理一覧.md` | BATCH-012 / BATCH-013 |
| バッチ依存関係図 | `docs/05_アプリケーション設計/アプリ/batch/バッチ依存関係図.md` | BATCH-012 → BATCH-013 |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-DB-BATCH-014 |
| ログ・Observability | `docs/05_アプリケーション設計/アプリ/ログ・Observability設計書.md` | 分布メトリクス名 |
| item 定義書 | `docs/06_実装設計/database/item_テーブル定義書.md` | §8.2 被参照 |
| item_generation_queue | `docs/06_実装設計/database/item_generation_queue_テーブル定義書.md` | Queue 経路 |
| semantic_config_version | `docs/06_実装設計/database/semantic_config_version_テーブル定義書.md` | version / 射影重み |
| feature_definition | `docs/06_実装設計/database/feature_definition_テーブル定義書.md` | 8 軸 |
| feature_normalization_version | `docs/06_実装設計/database/feature_normalization_version_テーブル定義書.md` | 正規化 version |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | feature_code |
| item_feature（任意） | `docs/06_実装設計/database/item_feature_テーブル定義書.md` | #514 merge 後 |

---

## 19. レビュー観点

- 物理ER §9（`item_id` ON・1:N）・テーブル一覧 §7 No.30 と矛盾していない
- GiftMeaningSpace §5–§7 の Social / Symbolic 射影と `item_social` / `item_symbolic` 列が整合している
- `user_meaning`（`user_social` / `user_symbolic`）との対称性が §5.4 で整理されている
- BATCH-013 / IF-DB-BATCH-014 による `item_feature` → `item_meaning` 生成関係が §5.2 / §12 で明示されている
- 冪等キー `item_id` + `semantic_config_version_id` が §7 / §12.1 で定義されている
- mean / std 等分布統計が本テーブルに混在せず、`meaning_distribution_metric` と責務分離されている（§5.5）
- 論理ER §10.2 未列挙差分が §5.4 で明示されている
- Online 更新禁止・Batch 更新主体が §5 / §12 で明示されている
- apps/** / OpenAPI / generated 変更が含まれていない
- secret や `.env` 実値が含まれていない
