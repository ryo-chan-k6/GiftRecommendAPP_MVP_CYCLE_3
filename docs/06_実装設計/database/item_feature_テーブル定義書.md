# Item Feature テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                         |
| -------------- | ---------------------------- |
| ドキュメントID | `DB-TBL-MVP-item_feature`    |
| ドキュメント名 | Item Feature テーブル定義書  |
| 対象システム   | Gift Recommendation Service MVP |
| MVP対象        | `yes`                        |
| 作成日         | 2026-06-14                   |
| 更新日         | 2026-06-14（Human Review #514 反映） |

---

## 2. 概要

`item_feature` は、商品ごとの **MVP 8 次元 Feature 値**（Social 3 + Symbolic 5）を保持する Item派生データ系テーブルである。

BATCH-011（`feature_input_hash` 算出）→ BATCH-012（raw Feature 生成）→ BATCH-013（正規化）の出力先であり、Matching / Ranking で参照する **商品側 Feature 正本** となる。Batch で事前生成し、Online 推薦では **参照のみ** とする（論理ER §16.1）。

---

## 3. 目的

- 商品 × 意味定義 version × Feature 軸ごとの raw / normalized Feature 値を DB 上で保持する
- 冪等キー（`item_id` + `semantic_config_version_id` + `feature_code` + `feature_input_hash` + `feature_normalization_version_id`）を物理 DDL で確定し、再生成の冪等性と正規化 version 変更後の履歴区別を担保する
- `feature_input_hash` / `feature_normalization_version_id` の保持方針を明記し、後続 DDL Task が migration を作成できる粒度を提供する
- reco が Online 推薦時に Item Feature を安定参照できる正本を提供する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `item_feature` |
| 論理テーブル名 | Item Feature |
| 分類 | Item派生データ系 |
| 正本区分 | 派生 / 推薦用正本 |
| 主な更新主体 | batch（BATCH-012 raw 生成、BATCH-013 正規化） |
| 主な参照主体 | reco（Matching / Ranking）、batch（再生成判定・skip 判定） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11 |

---

## 5. 用途・責務

- **8 軸 × 商品 × 意味 version** の Feature 値正本（テーブル一覧 §7 No.29）
- BATCH-012 が `item_semantic` / 商品メタデータ / Feature Rule から **raw Feature** を生成し、本テーブルへ Upsert する
- BATCH-013 が `raw_feature_value` を sigmoid 正規化し、`normalized_feature_value` を更新する
- `feature_input_hash` を行に保持し、BATCH-011 算出結果との整合・再生成判定・冪等キー構成要素とする
- `feature_normalization_version_id` を行に保持し、正規化パラメータ変更後の再現性・冪等キー構成要素とする（`feature_normalization_version_テーブル定義書` §7.1）
- `semantic_config_version_id` を行に保持し、意味定義 version 変更後の派生データ世代を区別する

### 5.1 行モデル（MVP）

| 観点 | 方針 |
| ---- | ---- |
| 粒度 | **1 商品 × 1 `semantic_config_version_id` × 1 `feature_code` × 1 冪等キー組** あたり 1 行 |
| 軸数 | MVP 固定 **8 行 / 商品 / 意味 version / 冪等キー組**（`feature_code` 8 値） |
| 履歴 | 冪等キーが変わる再生成（hash / normalization version 変更等）は **別行 INSERT**。同一冪等キーは Upsert 上書き |
| Online 参照 | Run 開始時に解決した `semantic_config_version_id` で、対象 `item_id` の **8 行** を読み取る |

### 5.2 `feature_input_hash` 保持方針

| 観点 | 方針 |
| ---- | ---- |
| 保存先 | **本テーブル各行**（`feature_input_hash` 列。永続化正本） |
| 算出主体 | batch（BATCH-011。算出対象フィールドの詳細はバッチ仕様 Task の責務） |
| 再生成判定 | `feature_input_hash` 変更時は `item_generation_queue` に `generation_type = feature` で登録（`item_generation_queue_テーブル定義書` §5.4・§5.6） |
| 冪等キー | テーブル一覧 §7・物理ER §11 `uq_item_feature_idempotent` の構成要素 |
| IF 連携 | IF-DB-BATCH-012（Feature 入力 hash 保存）は本テーブル行への記録と整合する |

> `item_generation_queue` 行には `feature_input_hash` を持たない（Human Review #507 §17.1 No.4）。hash の正本は派生テーブル側（本テーブル）である。

### 5.3 `feature_normalization_version_id` 保持方針

| 観点 | 方針 |
| ---- | ---- |
| 解決経路 | `semantic_config_version_id` → `normalization_rule`（binding）→ `feature_normalization_version_id`（`normalization_rule_テーブル定義書` §5.1） |
| 記録タイミング | BATCH-012 / BATCH-013 実行時に batch が解決し、派生行へ記録 |
| FK 方針 | **LOGICAL**（物理 FK なし。大量派生再現記録のため。`feature_normalization_version_テーブル定義書` §8.2・§17.1 No.4 決定済み） |
| 冪等キー | normalization version 変更時は **別行** として保持し、過去正規化結果の再現性を担保する |
| Public API | 非公開（内部 batch / reco 参照のみ） |

### 5.4 BATCH パイプラインとの関係

```text
item_generation_queue（generation_type = semantic | feature）
  → BATCH-010 item_semantic（semantic 区間。本 Task の入力前提）
  → BATCH-011 feature_input_hash 算出
  → BATCH-012 Item Feature 生成 → item_feature（raw_feature_value, feature_input_hash 等）
  → BATCH-013 Feature 正規化 → item_feature（normalized_feature_value 更新）
  → item_meaning 射影（別 Task / BATCH-013 連携）
```

再実行単位（バッチ依存関係図）: **`item_id` + `semantic_config_version_id` + `feature_input_hash`**（Feature 生成失敗時）。

### 5.5 対象外

- `item_semantic` / `item_meaning` / `item_embedding` の本体定義（別 Task）
- `user_feature`（User意味推定系・Run 単位派生）
- `feature_input_hash` 算出アルゴリズム詳細（BATCH-011 バッチ仕様書）
- Feature Rule 本体（`relationship_rule` 等 Semantic / Feature 定義系テーブル）
- api からの直接 DML
- Public API への Feature 値・hash・normalization version の露出（#469 委譲）
- DDL / migration 本体（DDL Task へ委譲）

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `item_feature_id` | Item Feature ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK |
| 2 | `item_id` | Item ID | `uuid` | `yes` | — | `ON` | — | — | 対象商品。`item.item_id` 参照 |
| 3 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `ON` | — | — | 意味定義 version。`semantic_config_version` 参照 |
| 4 | `feature_code` | Feature Code | `text` | `yes` | — | — | — | — | MVP 8 軸コード。enum定義書 §6.16 正本 |
| 5 | `feature_input_hash` | Feature Input Hash | `varchar(64)` | `yes` | — | — | — | — | BATCH-011 算出 hash。冪等キー構成要素 |
| 6 | `feature_normalization_version_id` | Feature Normalization Version ID | `uuid` | `yes` | — | — | — | — | 適用正規化 version。LOGICAL 参照 |
| 7 | `raw_feature_value` | Raw Feature Value | `numeric(8,6)` | `yes` | — | — | — | — | BATCH-012 出力の raw 値 |
| 8 | `normalized_feature_value` | Normalized Feature Value | `numeric(8,6)` | `no` | — | — | — | — | BATCH-013 出力。Matching 用 0.0〜1.0 |
| 9 | `generated_at` | Generated At | `timestamptz` | `yes` | — | — | — | — | 当該行の Feature 生成完了日時（UTC）。BATCH-012 完了時に設定 |

> **論理ER §10.2 との差分（§8.4）**: 論理ERは `feature_definition_id` を主要属性に列挙するが、物理ER §11 冪等キーは `feature_code` を使用する。MVP 物理 DDL では **`feature_code` のみ** を保持し、`feature_definition_id` 列は持たない（§17.1 No.1 **決定済み**）。
>
> **物理ER §11 との差分（CHECK 列名）**: 物理ER `chk_feature_value_range` は `feature_value` / `normalized_feature_value` と記載する。本定義書では論理ER §10.2 に合わせ **`raw_feature_value`** を raw 列名とする（§8.4・§17.1 No.2 **決定済み**）。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `item_feature_id` | サロゲート UUID | — |
| UNIQUE | `item_feature_id` | PK と同一 | — |
| UNIQUE | `item_id`, `semantic_config_version_id`, `feature_code`, `feature_input_hash`, `feature_normalization_version_id` | 再生成冪等キー | Index 名: `uq_item_feature_idempotent`（物理ER §11・テーブル一覧 §7） |

同一商品・同一意味 version・同一軸で、入力 hash または正規化 version が変わった場合は **別行** として INSERT する（履歴保持）。同一冪等キーでの再実行は Upsert 上書きとする（§12.2）。

---

## 8. 外部キー・参照関係

### 8.1 参照先（本テーブルから）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `item_id` | `item.item_id` | `ON` | `ON DELETE RESTRICT` | `item_テーブル定義書` §8.2 と同型 |
| `semantic_config_version_id` | `semantic_config_version.semantic_config_version_id` | `ON` | `ON DELETE RESTRICT` | 物理ER §9 generates_with・ON |

### 8.2 論理参照（物理 FK なし）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `feature_code` | `feature_definition.feature_code`（同一 `semantic_config_version_id` 内） | `LOGICAL` | アプリ層で存在確認 | code + version で軸特定。`feature_definition_テーブル定義書` §8.1 |
| `feature_normalization_version_id` | `feature_normalization_version.feature_normalization_version_id` | `LOGICAL` | アプリ層で存在確認 | `feature_normalization_version_テーブル定義書` §8.2・§17.1 No.4 |

### 8.3 被参照

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| reco（Matching） | 全業務列 | reads | アプリ層 | Online 参照のみ |
| `item_meaning` 生成（BATCH-013） | `normalized_feature_value` 等 | derives | 別 Task | Item Meaning は本 Task の out_of_scope |

### 8.4 論理ER / 物理ER 差分整理

| 論点 | 論理ER §10.2 | 物理ER §11 / テーブル一覧 §7 | 本定義書の採用 |
| ---- | ------------ | ----------------------------- | -------------- |
| 軸参照キー | `feature_definition_id` | `feature_code`（冪等キー） | **`feature_code` のみ**（§17.1 No.1 決定済み） |
| raw 値列名 | `raw_feature_value` | `feature_value`（CHECK 表記） | **`raw_feature_value`** |
| 入力 hash | 未列挙 | 冪等キー要素 | **`feature_input_hash` 必須列** |
| normalization FK | `feature_normalization_version_id` | LOGICAL | **LOGICAL 維持** |

> 論理ER 更新（`feature_definition_id` / `feature_input_hash` 追記）は別 docs Task で検討する。

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `item_feature_pkey` | `item_feature_id` | btree（PK） | 主キー | 自動生成 |
| `uq_item_feature_idempotent` | `item_id`, `semantic_config_version_id`, `feature_code`, `feature_input_hash`, `feature_normalization_version_id` | unique btree | 再生成冪等 | 物理ER §11 |
| `idx_item_feature_lookup` | `item_id`, `semantic_config_version_id`, `feature_code` | btree | Online 参照 | 物理ER §10。現行世代の 8 軸読取 |
| `idx_item_feature_item_id` | `item_id` | btree | FK 補助・障害調査 | batch 再実行単位の抽出 |
| `idx_item_feature_norm_version` | `feature_normalization_version_id` | btree | 正規化 version 別分析 | 運用・監査（物理ER §10 未記載。本 Task で追加方針） |

Online 参照では、Run 開始時に固定した `semantic_config_version_id` に対し、**item 単位で最新 `generated_at` の冪等キー組**に属する 8 行を `idx_item_feature_lookup` で取得する（§17.1 No.5 決定済み）。

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `item_feature_pkey` | PRIMARY KEY | `item_feature_id` | 主キー | — |
| `uq_item_feature_idempotent` | UNIQUE | §7 の 5 列 | 冪等キー一意 | テーブル一覧 §7 |
| `fk_item_feature_item_id` | FOREIGN KEY | `item_id` | `item(item_id)` ON DELETE RESTRICT | §8.1 |
| `fk_item_feature_semantic_config_version_id` | FOREIGN KEY | `semantic_config_version_id` | `semantic_config_version(semantic_config_version_id)` ON DELETE RESTRICT | §8.1 |
| `chk_item_feature_code_mvp` | CHECK | `feature_code` | MVP 8 軸のみ | `feature_definition` / 物理ER §11 と同一 |
| `chk_item_feature_input_hash_format` | CHECK | `feature_input_hash` | `char_length(feature_input_hash) = 64` かつ hex 形式 | SHA-256 想定（詳細は BATCH-011 仕様 Task） |
| `chk_item_feature_normalized_range` | CHECK | `normalized_feature_value` | `normalized_feature_value IS NULL OR (normalized_feature_value >= 0.0 AND normalized_feature_value <= 1.0)` | BATCH-013 完了後は NOT NULL 化をアプリ層で担保 |
| `chk_item_feature_raw_range` | CHECK | `raw_feature_value` | `raw_feature_value >= 0.0 AND raw_feature_value <= 1.0` | Feature Engine 出力を 0〜1 clip 前提（§17.1 No.2 決定済み） |

> 物理ER §11 の `chk_feature_value_range`（`feature_value` / `normalized_feature_value`）は、本定義書では `raw_feature_value` + `normalized_feature_value` に読み替える（§8.4）。

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `feature_code` | `feature_code` | enum定義書 §6.16 / `packages/code-definitions/semantic/feature_code.yaml` | MVP 8 値 | `feature_definition` と同一 CHECK |

### 11.1 MVP 8 軸（`feature_code`）

| feature_group | feature_code | 論理ER §10.3 |
| ------------- | ------------ | ------------ |
| Social | `formality` | 儀礼性 |
| Social | `safety` | 安全性 |
| Social | `brand_appropriateness` | ブランド適切性 |
| Symbolic | `emotion` | 感情性 |
| Symbolic | `novelty` | 新規性 |
| Symbolic | `intimacy` | 親密性 |
| Symbolic | `symbolic_identity` | 象徴性 |
| Symbolic | `story_richness` | ストーリー性 |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| INSERT / UPSERT | batch（BATCH-012） | 対象 item の Feature 生成 | `raw_feature_value`, `feature_input_hash`, `feature_normalization_version_id`, `generated_at` 等 | `uq_item_feature_idempotent` | 8 軸それぞれ 1 行 |
| UPDATE | batch（BATCH-013） | 同一冪等キー行が存在 | `normalized_feature_value` | 行単位 | raw 列は原則変更しない |
| SELECT | reco | Run 時 `semantic_config_version_id` 固定 | — | — | 8 軸読取。Online 更新禁止 |
| SELECT | batch | skip 判定・再生成判定 | — | — | hash / version 比較 |
| DELETE | batch（メンテナンス） | §13 保持方針に基づく | 古い世代行 | 定期実行 | 現行世代は保持 |
| INSERT / UPDATE / DELETE | api / reco | — | — | **禁止** | 論理ER §16.1 |

### 12.1 正規化 version 解決フロー

```text
1. BATCH が semantic_config_version_id を確定（Config Resolver）
2. normalization_rule から feature_normalization_version_id を解決（is_active=true）
3. BATCH-012 が item_feature 行へ feature_normalization_version_id を記録
4. BATCH-013 が同一行の normalized_feature_value を更新
```

### 12.2 BATCH-012 Upsert 疑似コード

```sql
INSERT INTO item_feature (
  item_id,
  semantic_config_version_id,
  feature_code,
  feature_input_hash,
  feature_normalization_version_id,
  raw_feature_value,
  generated_at
) VALUES (
  :item_id,
  :semantic_config_version_id,
  :feature_code,
  :feature_input_hash,
  :feature_normalization_version_id,
  :raw_feature_value,
  now()
)
ON CONFLICT (
  item_id,
  semantic_config_version_id,
  feature_code,
  feature_input_hash,
  feature_normalization_version_id
) DO UPDATE SET
  raw_feature_value = EXCLUDED.raw_feature_value,
  generated_at = EXCLUDED.generated_at;
```

### 12.3 BATCH-013 正規化更新

```sql
UPDATE item_feature
   SET normalized_feature_value = :normalized_value
 WHERE item_id = :item_id
   AND semantic_config_version_id = :semantic_config_version_id
   AND feature_code = :feature_code
   AND feature_input_hash = :feature_input_hash
   AND feature_normalization_version_id = :feature_normalization_version_id;
```

### 12.4 Online 参照フロー（reco）

§17.1 No.5 決定済み。

```text
1. Run 開始時に semantic_config_version_id を固定
2. 候補 item_id ごとに、同一 semantic_config_version_id 配下で generated_at が最大の冪等キー組を特定
3. 当該冪等キー組の 8 軸（feature_code 8 値）を idx_item_feature_lookup で取得
4. 同一 item_id + semantic_config_version_id で feature_code 8 件が揃うことを前提（欠損時は Matching 側でフォールバック／警告。詳細は reco 実装 Task）
5. normalized_feature_value が NULL の行は Matching 対象外（BATCH 未完了）
```

**現行世代解決（疑似 SQL）:**

```sql
SELECT DISTINCT ON (item_id, feature_code)
       item_feature.*
  FROM item_feature
 WHERE item_id = ANY(:item_ids)
   AND semantic_config_version_id = :semantic_config_version_id
 ORDER BY item_id, feature_code, generated_at DESC;
```

### 12.5 skip 判定（batch）

バッチ設計方針書 §7.2 補足: 同一 `item_id` + `semantic_config_version_id` + `feature_input_hash` + `feature_normalization_version_id` で **8 軸すべて** 生成済みかつ `normalized_feature_value` が有効なら、BATCH-011〜013 を skip し `item_generation_queue` を `skipped` へ遷移し得る。

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（推薦再現性・監査）。**現行世代**（Run / batch が参照する hash + normalization version 組）は削除しない |
| 削除方式 | 原則 **物理 DELETE はメンテナンスのみ**。Online / 通常 batch では DELETE しない |
| 削除条件 | **非現行** 冪等キー行のみ。MVP は運用メンテナンス時の最小 DELETE に限定（§17.1 No.4 決定済み） |
| 論理削除 | 採用しない（`is_active` 列なし） |
| アーカイブ | MVP では対象外 |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `item_feature` |
| migration単位 | Item派生データ系 migration（`item` / `semantic_config_version` 等の先行テーブル後） |
| 適用順序 | 物理ER §15: Master / Config → Semantic 定義 → `item` → `item_semantic`（先行）→ **`item_feature`** → `item_meaning` / `item_embedding` |
| rollback方針 | DDL Task で定義。派生データのため DROP は開発環境のみ想定 |
| 破壊的変更有無 | `no`（新規テーブル） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | `apps/reco`（service role）、`apps/batch`（service role） |
| 書き込み権限 | `apps/batch` のみ（BATCH-012 / BATCH-013） |
| service role利用 | Supabase service role 経由。client 直アクセス禁止 |
| 個人情報・機微情報 | 商品 Feature 値のみ。個人データを含まない |
| ログ出力制限 | `feature_input_hash` はログに全文出力しない（先頭数文字 + 省略可） |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | `item_feature` テーブル・FK・unique・Index が migration で作成される | migration |
| 2 | 冪等キー | 同一 5 列で Upsert が上書き、いずれか変更で別行 INSERT される | integration |
| 3 | FK | `item_id` / `semantic_config_version_id` の RESTRICT が機能する | integration |
| 4 | feature_code CHECK | MVP 8 軸以外が拒否される | migration |
| 5 | 値域 CHECK | `normalized_feature_value` が 0.0〜1.0 のみ許容される | unit |
| 6 | BATCH-012/013 連携 | raw 生成後に normalized が同一冪等キー行へ更新される | integration |
| 7 | Online 境界 | api / reco からの INSERT / UPDATE / DELETE が行われない | manual |
| 8 | 権限 | batch のみが書き込み可能 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review #514 にて No.1〜5 を決定済み（下記参照） |

### 17.1 Human Review 決定事項（Issue #514）

| No | 論点 | 決定内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | `feature_definition_id` 列の物理化要否 | **物理化しない**。`feature_code` + `semantic_config_version_id` で軸を特定する | Human | §6・§8.4 |
| 2 | `raw_feature_value` の値域 CHECK | **MVP は raw も 0.0〜1.0 CHECK**（`chk_item_feature_raw_range`）。Feature Engine 出力は clip 前提 | Human | §10 |
| 3 | `feature_input_hash` 算出対象フィールド範囲 | **本 Task では列存在・冪等キー含有のみ確定**。算出対象フィールドの詳細は BATCH-011 バッチ仕様 Task へ委譲 | Human | §5.2・§6 |
| 4 | 非現行世代行の DELETE ポリシー | **MVP は DELETE 最小**。現行世代は保持し、非現行行の削除は運用メンテナンス時のみ | Human | §13 |
| 5 | Online 参照時の「現行世代」解決 | **item 単位で最新 `generated_at` の冪等キー組 8 行**を読み取る | Human | §9・§12.4 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | FK・Index・制約方針 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §10.2 属性・§16 責務境界 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §7 No.29・冪等キー |
| Featureルール定義書 | `docs/04_ドメインモデル設計/Featureルール定義書.md` | Feature 生成・正規化 |
| item 定義書 | `docs/06_実装設計/database/item_テーブル定義書.md` | item_id FK |
| item_generation_queue 定義書 | `docs/06_実装設計/database/item_generation_queue_テーブル定義書.md` | 再生成トリガー |
| feature_definition 定義書 | `docs/06_実装設計/database/feature_definition_テーブル定義書.md` | feature_code 正本 |
| feature_normalization_version 定義書 | `docs/06_実装設計/database/feature_normalization_version_テーブル定義書.md` | §7.1 冪等キー |
| normalization_rule 定義書 | `docs/06_実装設計/database/normalization_rule_テーブル定義書.md` | binding 解決 |
| semantic_config_version 定義書 | `docs/06_実装設計/database/semantic_config_version_テーブル定義書.md` | version FK |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | feature_code |
| バッチ設計方針書 | `docs/05_アプリケーション設計/アプリ/batch/バッチ設計方針書.md` | BATCH-011〜013 |
| バッチ処理一覧 | `docs/05_アプリケーション設計/アプリ/batch/バッチ処理一覧.md` | 入出力 |
| バッチ依存関係図 | `docs/05_アプリケーション設計/アプリ/batch/バッチ依存関係図.md` | 再実行単位 |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-DB-BATCH-012 |
| code-definitions | `packages/code-definitions/semantic/feature_code.yaml` | feature_code 正本 |

---

## 19. レビュー観点

- テーブル一覧 §7 No.29・論理ER §10.2・物理ER §8–§11 と矛盾していない
- 冪等キー 5 列・`feature_input_hash` / `feature_normalization_version_id` 方針が明記されている
- `item_id` / `semantic_config_version_id` の物理 FK ON と normalization version の LOGICAL FK が整理されている
- BATCH-011 / BATCH-012 / BATCH-013・`item_generation_queue` との整合が取れている
- 論理ER §16.1 / §16.2（Batch 更新・Online 参照のみ）が反映されている
- カラム・制約・Index が DDL Task へ展開できる粒度である
- §17.1 決定事項（No.1〜5）が本文（§6 / §8.4 / §9 / §10 / §12.4 / §13）に反映されている
- secret や `.env` 実値が含まれていない
