# Feature Normalization Version テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                           |
| -------------- | ---------------------------------------------- |
| ドキュメントID | `DB-TBL-MVP-feature_normalization_version`     |
| ドキュメント名 | Feature Normalization Version テーブル定義書   |
| 対象システム   | Gift Recommendation Service MVP                |
| MVP対象        | `yes`                                          |
| 作成日         | 2026-06-08                                     |
| 更新日         | 2026-06-08（AI Review #460 指摘反映）           |

---

## 2. 概要

`feature_normalization_version` は、User Feature / Item Feature の **sigmoid 正規化パラメータ（center / k 等）** を version 管理する Master / Config 系テーブルである。

batch / reco が Feature 生成時に参照し、`user_feature` / `item_feature` に `feature_normalization_version_id` を記録して正規化の再現性を担保する。Public API には公開しない（内部管理用）。

---

## 3. 目的

- Feature raw 値の sigmoid 正規化パラメータを DB 上で version 管理する
- Item Feature 再生成の冪等キー（テーブル一覧 §7）に含まれる version ID の正本を提供する
- batch / reco が同一正規化設定で User / Item Feature を再現可能にする

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `feature_normalization_version` |
| 論理テーブル名 | Feature Normalization Version |
| 分類 | Master / Config系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | batch（Item Feature 生成）、reco（User Feature 生成） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11 |

---

## 5. 用途・責務

- **normalization_method** により正規化方式（MVP: `sigmoid`）を識別する
- **parameter_json** に sigmoid の `center_feature` / `k_feature` 等を保持する（Featureルール定義書 §14.3）
- **`is_current = true`** の行を batch / reco が現行正規化 version として解決する（解決単位は §17 参照）
- **`feature_normalization_version_id`（UUID）** をサロゲート PK とし、派生 Feature 行への参照キーとする
- `user_feature.feature_normalization_version_id` / `item_feature.feature_normalization_version_id` は本テーブルを **論理参照**する（物理ER §9・§11。MVP 初期 DDL では物理 FK なし）

### 5.1 semantic_config_version / normalization_rule との分離

| 観点 | `semantic_config_version` / `normalization_rule` | `feature_normalization_version` |
| ---- | ------------------------------------------------ | ------------------------------- |
| 分類 | Semantic / Feature 定義系（設定正本 Rule テーブル） | Master / Config 系（独立 version テーブル） |
| 管理対象 | 意味推定ロジック・Feature ルール・Concept 定義。`normalization_rule` は Feature 軸別の正規化ルール定義（Featureルール定義書 §17.5） | Feature raw 値の正規化パラメータ正本（sigmoid center / k 等。MVP は全 8 軸共通） |
| 派生への紐づけ | `semantic_config_version_id` を Feature / Semantic 系に保持 | `feature_normalization_version_id` を user_feature / item_feature に保持 |
| Featureルール定義書 | §14.8 / §16.1 は正規化パラメータを semantic_config_version 配下と記載 | 論理ER §11.1 / 物理ER §9・§11 / テーブル一覧 §9 は独立テーブルを定義 |

> **Featureルール定義書との関係**: Featureルール定義書 §14.8 は正規化パラメータを `semantic_config_version` 配下と記載するが、本テーブルは物理設計正本（論理ER §11.1 / 物理ER / テーブル一覧 §9）に従い独立テーブルとして定義する。`normalization_rule`（Semantic / Feature 定義系）は Feature 軸別ルール定義の責務であり、本テーブルの `parameter_json`（全軸共通 sigmoid パラメータ）とは粒度が異なる。§14.8 との整合は Human Review 論点（§17.1 No.1）。

### 5.2 対象外

- Semantic / Feature ルール本体（`semantic_config_version` 配下 Rule テーブルの責務）
- LLM / Embedding モデル識別（`model_version` の責務）
- Ranking パラメータ（`ranking_config` の責務）
- Feature 分布統計の集計・監視（`normalization_distribution_metric` 等の責務）
- Public API による正規化 version 公開

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `feature_normalization_version_id` | Feature Normalization Version ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK。user_feature / item_feature の再現性参照キー |
| 2 | `normalization_method` | Normalization Method | `text` | `yes` | — | — | — | — | 正規化方式。MVP は `sigmoid`（Featureルール定義書 §14.2） |
| 3 | `parameter_json` | Parameter JSON | `jsonb` | `yes` | — | — | — | — | 正規化パラメータ正本。構造は §6.1 参照 |
| 4 | `is_current` | Current Flag | `boolean` | `yes` | — | — | — | `false` | 現行 version フラグ。`true` は `normalization_method` あたり最大 1 行（§7・§10） |
| 5 | `generated_at` | Generated At | `timestamptz` | `yes` | — | — | — | `now()` | version レコード作成日時（UTC）。論理ER §11.1 に整合 |

> **用語補足**: `model_version` / `ranking_config` は `created_at` を採用するが、論理ER §11.1 は本テーブルに `generated_at` のみ定義する。採用理由の最終判断は §17.1 No.3。

### 6.1 `parameter_json` 参照構造（MVP）

物理 DDL では JSON Schema CHECK は設けず、batch / reco / seed 側で整合を担保する。MVP で参照するキーは Featureルール定義書 §14.3 に基づく。

| キー | 型 | MVP必須 | 説明 | 参照 |
| ---- | -- | ------- | ---- | ---- |
| `center_feature` | number | `yes` | sigmoid の中立点。初期値 `0.5` | Featureルール定義書 §14.3 |
| `k_feature` | number | `yes` | sigmoid の感度係数。初期値 `4.0` | 同上 |

**MVP 初期値例（seed 参照用）:**

```json
{
  "center_feature": 0.5,
  "k_feature": 4.0
}
```

**正規化式（参照）:**

```text
normalized_value = sigmoid(k_feature * (raw_value - center_feature))
sigmoid(x) = 1 / (1 + exp(-x))
```

> **将来拡張キー（MVP では未使用）**: `z-score + sigmoid` 拡張用の `mu_feature` / `sigma_feature`（Feature 軸別）は §17.1 No.4 / No.7 へ委譲。DDL CHECK への追加は後続 Task で判断する。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `feature_normalization_version_id` | サロゲート UUID | 派生 Feature 再現性参照 |
| UNIQUE | `feature_normalization_version_id` | PK と同一 | — |
| UNIQUE（部分） | `normalization_method`（`is_current = true` の行のみ） | normalization_method 単位で現行 version を 1 件に制限 | Index 名: `uq_feature_norm_version_current_per_method` |

> version lineage は `feature_normalization_version_id`（UUID）で識別する。パラメータ変更は新規 INSERT とし、既存行の `parameter_json` UPDATE は原則禁止（ranking_config と同様の immutable version 方針）。

### 7.1 item_feature 冪等キー（テーブル一覧 §7）

Item Feature 再生成の冪等キーは、テーブル一覧 §7 および物理ER §11 `uq_item_feature_idempotent` に従う。

| 項目 | 内容 |
| ---- | ---- |
| Index 名 | `uq_item_feature_idempotent` |
| 対象カラム | `item_id`, `semantic_config_version_id`, `feature_code`, `feature_input_hash`, `feature_normalization_version_id` |
| 用途 | 同一商品・同一意味 version・同一入力 hash・同一正規化 version での再生成を冪等化 |
| 正規化 version の役割 | `feature_normalization_version_id` が変わると別行として INSERT され、正規化パラメータ変更後の再生成を区別する |

> `user_feature` は Run 単位の派生データであり、item_feature と同型の冪等 unique は MVP では定義しない（論理ER §11.1 / 物理ER §9 は `user_feature` への LOGICAL 参照を定義。論理ER §14 関係表は `item_feature` のみ記載 — 差分は §8.1 参照）。

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| — | — | なし | — | 本テーブルは Config 根。他テーブルから参照される |

### 8.1 被参照（論理）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `user_feature` | `feature_normalization_version_id` | normalizes | `LOGICAL`（方針） | 論理ER §11.1・物理ER §9。reco が Run 実行時に解決・記録。物理 FK は `user_feature` テーブル定義 Task で DDL 確定 |
| `item_feature` | `feature_normalization_version_id` | normalizes | `LOGICAL`（方針） | 論理ER §11.1・物理ER §9・§11。batch が生成時に解決・記録。§7.1 冪等キーに含む。物理 FK は `item_feature` テーブル定義 Task で DDL 確定 |

> MVP 初期 DDL では本テーブル側に被参照 FK を載せない（model_version / relationship_master と同型の Master / Config 系慣例）。整合は batch / reco 側 version 解決 + seed 正本 + 派生行 INSERT 時の存在確認で担保する。
>
> **論理ER §14 との差分**: 論理ER §14 関係表は `feature_normalization_version` → `item_feature` のみ記載するが、物理ER §9 および論理ER §11.1 は `user_feature` への参照も定義する。本定義書は物理ER を正として両方を LOGICAL 参照とする。論理ER §14 への `user_feature` 追記は別 docs Task で検討する。

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `feature_normalization_version_pkey` | `feature_normalization_version_id` | btree（PK） | 主キー | 自動生成 |
| `uq_feature_norm_version_current_per_method` | `normalization_method` | btree（unique, partial） | 現行 version 解決 | `WHERE is_current = true` |
| `idx_feature_norm_version_method_generated` | `normalization_method`, `generated_at` DESC | btree | version 履歴参照 | 運用・監査 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `feature_normalization_version_pkey` | PRIMARY KEY | `feature_normalization_version_id` | 主キー | — |
| `uq_feature_norm_version_current_per_method` | UNIQUE（部分） | `normalization_method` | `is_current = true` は normalization_method あたり 1 行 | MVP 方針。§17.1 No.2 |
| `chk_normalization_method_mvp` | CHECK | `normalization_method` | `normalization_method IN ('sigmoid')` | MVP 1 値。`z_score_sigmoid` 等は §17.1 No.4 / No.7 |
| `chk_parameter_json_object` | CHECK | `parameter_json` | `jsonb_typeof(parameter_json) = 'object'` | 配列・スカラー禁止 |
| `chk_parameter_json_center_feature` | CHECK | `parameter_json` | `(parameter_json->>'center_feature')::numeric BETWEEN 0.0 AND 1.0` | MVP 全軸共通中立点 |
| `chk_parameter_json_k_feature` | CHECK | `parameter_json` | `(parameter_json->>'k_feature')::numeric > 0` | 感度係数は正数 |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `normalization_method` | `normalization_method` | Featureルール定義書 §14.2（本 Task で候補値） | `sigmoid` | 将来 `z_score_sigmoid` 等は §17.1 No.4 / No.7。enum Task 正本化は後続 |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | batch | Item Feature 生成前 | — | — | `is_current = true` かつ `normalization_method = 'sigmoid'` を解決 |
| SELECT | reco | User Feature 生成前（Run 実行時） | — | — | 同上 |
| SELECT | batch / reco | 再現参照 | — | — | 保存済み `feature_normalization_version_id` を参照（`is_current` 変更の影響を受けない） |
| INSERT | database（seed / 運用） | 新 version 追加 | 全列 | Upsert 想定（PK 単位） | パラメータ変更は新 version INSERT |
| UPDATE | database（運用） | 現行切替のみ | `is_current` | トランザクション内で旧 current を `false`、新 current を `true` | `parameter_json` の UPDATE 禁止方針 |
| DELETE | — | MVP では原則禁止 | — | — | 履歴保持のため物理 DELETE しない |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（設定正本・再現性）。過去 user_feature / item_feature 再現のため履歴 version も保持 |
| 削除方式 | 物理 DELETE 原則禁止 |
| 削除条件 | 参照が存在しない場合のみ運用判断で DELETE 可（Human Review 必須） |
| 論理削除 | MVP では専用列なし。`is_current = false` で非現行化 |
| アーカイブ | MVP 対象外 |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `feature_normalization_version` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: Master / Config 群（`user_feature` / `item_feature` より前。派生テーブルが LOGICAL 参照する前提） |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | batch / reco（service role 経由） |
| 書き込み権限 | database 運用・seed のみ。Online / Batch 実行中の DML 更新なし |
| service role利用 | version 解決・seed 投入に限定。web client から Direct DB アクセス不可 |
| 個人情報・機微情報 | 含まない |
| ログ出力制限 | `feature_normalization_version_id` / `parameter_json` を Public ログ・Response に過剰出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / CHECK / partial unique が定義どおり | migration |
| 2 | PK | 主キー制約が機能する | migration |
| 3 | is_current | 同一 `normalization_method` で `is_current=true` が 2 行以上になる INSERT/UPDATE が拒否される | migration |
| 4 | CHECK | 不正 `parameter_json`（center_feature 範囲外、k_feature 非正など）が拒否される | migration |
| 5 | batch 整合 | Item Feature 生成時に解決した `feature_normalization_version_id` が item_feature に記録される | integration |
| 6 | reco 整合 | User Feature 生成時に解決した ID が user_feature に記録される | integration |
| 7 | 被参照 FK | `user_feature` / `item_feature` 側 FK は各テーブル定義 Task で検証 | migration（後続 Task） |
| 8 | 冪等キー | item_feature の unique（§7.1 / 物理ER §11 `uq_item_feature_idempotent`）に `feature_normalization_version_id` が含まれる | integration |
| 9 | seed 整合 | Featureルール定義書 §14.3 初期値と seed の `parameter_json` が一致 | manual |
| 10 | 権限 | web client から Direct DB アクセス不可 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review 前の論点は §17.1 を参照 |

### 17.1 Human Review 観点（PR #460）

| No | 論点 | 推奨案 | 判断者 | 備考 |
| --: | ---- | ------ | ------ | ---- |
| 1 | `semantic_config_version` / Featureルール定義書 §14.8 との責務分担 | 物理設計正本どおり独立 `feature_normalization_version` を正とし、Featureルール定義書 §14.8 の整合は別 docs Task で検討 | Human | `normalization_rule`（Semantic / Feature 定義系）は軸別ルール定義。本テーブルは全軸共通 sigmoid パラメータ正本 |
| 2 | `is_current` の解決単位 | `normalization_method` 単位（部分 unique 採用） | Human | model_version（model_type 単位）/ ranking_config（config_name 単位）パターンの踏襲 |
| 3 | `generated_at` vs `created_at` | 論理ER §11.1 に従い `generated_at` を採用 | Human | model_version / ranking_config は `created_at` |
| 4 | Feature 軸別パラメータ要否 | MVP は全 8 軸共通固定パラメータ（§14.3）。将来 z-score 拡張では軸別 μ / σ が必要 | Human | `parameter_json` に `per_feature` オブジェクト追加は後続 Task |
| 5 | `user_feature` / `item_feature` への物理 FK | MVP は `LOGICAL` のまま（物理ER §9）。DDL は各派生テーブル定義 Task で確定 | Human | 本 Task §10 には被参照 FK を載せない（Master / Config 系慣例） |
| 6 | item_feature 再生成判定への Normalization Version 変更影響 | `feature_normalization_version_id` 変更時は §7.1 冪等キーにより別行 INSERT。batch 再生成判定はバッチ設計方針書と整合させる | Human | テーブル一覧 §7 / 物理ER §11 |
| 7 | `z_score_sigmoid` 拡張時の `parameter_json` キー | Featureルール定義書 §14.7 の μ / σ を JSON に含めるか、統計量テーブルへ分離するか | Human | MVP では `sigmoid` + center / k のみ |
| 8 | `normalization_method` enum の YAML 正本化 | 後続 enum Task へ引き継ぎ。本 Task は CHECK 候補値のみ | Human | enum 定義書 + packages/code-definitions |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8 分類・§9 FK・§11 制約・冪等キー |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §11.1 エンティティ属性・§14 関係 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §9 Master / Config系・§7 item_feature 冪等キー |
| Featureルール | `docs/04_ドメインモデル設計/Featureルール定義書.md` | §14 sigmoid 正規化・§14.8 / §17.5 normalization_rule |
| バッチ設計 | `docs/05_アプリケーション設計/アプリ/batch/バッチ設計方針書.md` | Item Feature 再生成判定・冪等キー |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | normalization_method 正本化（後続 Task） |
| 参照テーブル定義 | `docs/06_実装設計/database/relationship_master_テーブル定義書.md` | Master / Config 系構成 |
| 参照テーブル定義 | `docs/06_実装設計/database/model_version_テーブル定義書.md` | Config version 管理パターン（is_current / partial unique） |
| 参照テーブル定義 | `docs/06_実装設計/database/ranking_config_テーブル定義書.md` | parameter_json / immutable version パターン |

---

## 19. レビュー観点

- 論理ER §11.1・物理ER §8–§11・テーブル一覧 §9 と矛盾していない
- `feature_normalization_version_id` / `normalization_method` / `parameter_json` / `is_current` / `generated_at` がすべて定義されている
- `user_feature` / `item_feature` への LOGICAL FK 方針が明記されている（派生テーブル FK DDL は後続 Task）
- item_feature 冪等キー（§7.1 / テーブル一覧 §7）への `feature_normalization_version_id` 含有が明記されている
- Featureルール定義書 §14.2 / §14.3 の sigmoid 初期パラメータが `parameter_json` 参照として明記されている
- `semantic_config_version` / `normalization_rule` との責務分担が §5.1 / §17.1 で明示されている
- Public API 非公開（`feature_normalization_version_id`）が明記されている
- model_version / ranking_config テーブル定義書と version 管理方針が一貫している
- relationship_master / model_version と §10 に被参照 FK を載せない Master / Config 系慣例が一貫している
- 論理ER §14（item_feature のみ）と物理ER §9（user_feature 含む）の差分が §8.1 で明示されている
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
