# Semantic Config Version テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                    |
| -------------- | --------------------------------------- |
| ドキュメントID | `DB-TBL-MVP-semantic_config_version`    |
| ドキュメント名 | Semantic Config Version テーブル定義書  |
| 対象システム   | Gift Recommendation Service MVP         |
| MVP対象        | `yes`                                   |
| 作成日         | 2026-06-09                              |
| 更新日         | 2026-06-10（Human Review: Public 参照・JOIN・有効期間 seed・Run 参照方針反映） |

---

## 2. 概要

`semantic_config_version` は、Semantic / Feature 定義体系の **version 単位の設定正本** を保持する Semantic / Feature定義系テーブルである。

親テーブル `semantic_config` が設定系列（lineage）の大枠を管理し、本テーブルは系列内の version（`version_label` / `is_current` / 有効期間）および Run 再現性に固定する version ID を担う。`model_version`（技術的モデル version）とは分離する。

Public API（API-PUB-007）では **`configName` + `versionLabel` の composite 参照**を表面公開する（§5.3・§17.1）。`config_name` は本テーブルに保持せず、api が親 `semantic_config` と **アプリ層 JOIN** で解決する。内部 UUID 主キー（`semantic_config_version_id`）は直接公開しない。

---

## 3. 目的

- Semantic Concept / Feature Definition / 各種 Rule の version 単位の正本を DB 上で管理する
- reco / api が Config / Version 解決時に参照する現行 version の正本を提供する
- `recommendation_run` / `evaluation_run` が参照する `semantic_config_version_id` の整合基盤とする
- API-PUB-007 / API-PUB-008 の `configName` / `versionLabel` マッピングの物理正本とする（API 契約本文の追随は Contract Task）

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `semantic_config_version` |
| 論理テーブル名 | Semantic Config Version |
| 分類 | Semantic / Feature定義系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | reco（Config / Version 解決）、api（API-PUB-007 応答組立） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8 |

---

## 5. 用途・責務

- **親 `semantic_config_id`** により設定系列に属する version を識別する
- **`version_label`** により系列内の version ラベルを保持する
- **`is_current`** により、reco / api が解決する「現行 version」を **`semantic_config_id` 単位**で管理する（§7・§10・§17.1 No.6）
- **`semantic_config_version_id`（UUID）** をサロゲート PK とし、Run・派生データ・子テーブルへの参照キーとする
- `recommendation_run.semantic_config_version_id` は本テーブルを **論理参照**する（MVP 初期 DDL では物理 FK なし。Run 開始時に ID を固定し再現性を担保）
- `evaluation_run.semantic_config_version_id` は本テーブルを **論理参照**する（Evaluation 系。MVP partial）

### 5.1 model_version との分離

| 観点 | `semantic_config_version` | `model_version` |
| ---- | ------------------------- | --------------- |
| 管理対象 | 意味推定ロジック（Feature 定義・Rule 等） | Embedding / LLM / Ranking 等の技術的モデル |
| ドメイン不変条件 | CF-01 | CF-02 |
| 処理フェーズ | 入力 → concept → feature → meaning | meaning → score → ranking |
| Run 固定 | Run 開始時に固定 | Run 開始時に固定 |
| Public API | `configName` + `versionLabel` を composite 参照として表面公開 | `model_version_id` は非公開 |

### 5.2 semantic_config との分離・解決階層

| 観点 | `semantic_config`（親） | `semantic_config_version`（本テーブル） |
| ---- | ----------------------- | --------------------------------------- |
| 管理単位 | 設定系列（lineage）の大枠 | 系列内の version |
| 主な列 | `config_name`, `is_active` | `version_label`, `is_current`, `valid_from`, `valid_to` |
| 解決順位 | **第 1 層**: `is_active = true` の系列のみ対象 | **第 2 層**: 対象系列内で `is_current = true` の version を解決 |
| Run 固定 | 直接参照しない | `recommendation_run.semantic_config_version_id` で固定 |

> **解決階層（MVP 方針・決定済み）**: reco / api の Config Resolver は、**第 1 層**で親 `semantic_config.is_active = true` の系列のみを対象とし、**第 2 層**で当該 `semantic_config_id` に属する `is_current = true` の version 行を解決する。系列が `is_active = false` の場合、その系列に属する version は解決対象外とする（§17.1 No.5）。
>
> **参照主体の分担**: reco（IF-DB-RECO-001）は本テーブルを中心に解決する。api（IF-DB-API-005）は Public 応答組立時に親 `semantic_config` と **アプリ層 JOIN** し、`config_name` を取得する（§5.3.1）。

### 5.3 Public API との関係（API-PUB-007）

| DB 列 / 概念 | API 項目 | 公開方針 | 備考 |
| ------------ | -------- | -------- | ---- |
| `semantic_config_version_id`（uuid） | — | **非公開** | 内部 DB 主キー。Run / 子テーブル / 派生データの参照キー |
| `version_label` | `versionLabel` | 表面公開（必須） | semver 形式。MVP 初期値例: `v1.0.0` |
| 親 `semantic_config.config_name` | `configName` | 表面公開（必須） | 親テーブル正本。api がアプリ層 JOIN で解決（§5.3.1） |
| composite 参照 | `configName` + `versionLabel` | 表面公開（必須） | Public 上の version 識別子。両方の組み合わせで一意 |

**MVP マッピング方針（Human Review 決定・§17.1）:**

- Public 参照キーは **`configName` + `versionLabel` の composite** とする（単一 `semanticConfigVersionId` 表面 ID は採用しない）
- `versionLabel` は `version_label` をそのままマッピングする（semver。§10 `chk_version_label_format` 参照）
- `configName` は本テーブルに denormalize しない。DB ビューも作成しない。api Repository が `semantic_config` と JOIN して解決する
- api / reco は Public 境界で composite を受け取った場合、内部で `semantic_config_version_id`（UUID）へ解決してから Run 固定・子テーブル参照に用いる
- API-PUB-007 / API-PUB-008 / API-INT-002 の契約本文・OpenAPI 追随は **Contract Task** で実施する（本 Task scope 外）

#### 5.3.1 アプリ層 JOIN 方針（api / IF-DB-API-005）

| 観点 | 方針 |
| ---- | ---- |
| 正本 | `config_name` は親 `semantic_config` のみが保持する |
| 本テーブル | `config_name` 列は **持たない**（denormalize しない） |
| DB ビュー | **作成しない**（MVP） |
| api 解決 | `semantic_config_version` と `semantic_config` を `semantic_config_id` で JOIN |
| 現行解決（マスタ GET） | 親 `is_active = true` → 子 `is_current = true` を解決後、JOIN で `config_name` を取得 |
| 指定解決（evaluation 等） | `config_name` + `version_label` で version 行を特定（親 `is_active = true` も満たすこと） |
| reco 解決 | IF-DB-RECO-001 は本テーブル中心。親 JOIN は api マスタ参照に限定 |

**参照クエリ例（api・概念）:**

```sql
SELECT scv.*, sc.config_name
FROM semantic_config_version scv
INNER JOIN semantic_config sc ON sc.semantic_config_id = scv.semantic_config_id
WHERE sc.is_active = true
  AND scv.is_current = true;
```

### 5.4 対象外

- 設定系列の大枠（`semantic_config` の責務）
- Semantic Concept / Feature Definition / Rule の定義内容（子テーブルの責務）
- Feature 正規化統計量 version（`feature_normalization_version` の責務）
- 技術的モデル version（`model_version` の責務）
- Ranking パラメータ（`ranking_config` の責務）
- `semantic_config_version` 行自体の Public CRUD API（MVP 対象外。マスタ参照 API のみ）

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK。Run / 子テーブル / 派生データの参照キー。Public API 非公開 |
| 2 | `semantic_config_id` | Semantic Config ID | `uuid` | `yes` | — | `yes` | — | — | 親設定系列 FK。`semantic_config.semantic_config_id` を参照（ON DELETE RESTRICT） |
| 3 | `version_label` | Version Label | `varchar(50)` | `yes` | — | — | — | — | 系列内 version ラベル（semver）。API `versionLabel` のマッピング先。MVP 初期値例: `v1.0.0` |
| 4 | `is_current` | Current Flag | `boolean` | `yes` | — | — | — | `false` | 現行 version フラグ。`true` は `semantic_config_id` あたり最大 1 行（§10） |
| 5 | `valid_from` | Valid From | `timestamptz` | `no` | — | — | — | `NULL` | version 有効開始（UTC）。MVP seed では明示設定（§6.1）。NULL は制限なし |
| 6 | `valid_to` | Valid To | `timestamptz` | `no` | — | — | — | `NULL` | version 有効終了（UTC）。MVP seed では上限日を設定（§6.1）。NULL は制限なし |
| 7 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | レコード作成日時（UTC） |

> **論理ER §11.1（§10.2）との関係**: 論理ERが列挙する主要属性（`semantic_config_version_id`, `semantic_config_id`, `version_label`, `is_current`, `valid_from`, `valid_to`, `created_at`）をすべて物理化する。

### 6.1 MVP seed 初期値（`valid_from` / `valid_to`）

| 項目 | MVP seed 方針 | 備考 |
| ---- | ------------- | ---- |
| 設定要否 | **seed で明示設定する**（NULL 運用は MVP 初期 seed では使わない） | §17.1 No.7 |
| `valid_from` | version 行の seed 投入日時（UTC）。`created_at` と同値でよい | seed Task で具体値を確定 |
| `valid_to` | **未来日付の上限** `9999-12-31 23:59:59+00`（UTC） | 実質無期限。PostgreSQL では `timestamptz 'infinity'` も同等だが、seed 正本は明示日時を採用 |
| 現行解決との関係 | MVP の Config 解決は **`is_active` → `is_current`** を主とする（§5.2）。有効期間は seed 正本・将来拡張・監査用 | 期間による解決ロジックは MVP では必須にしない |

**seed 例（概念）:**

```sql
valid_from = TIMESTAMPTZ '2026-06-10 00:00:00+00',
valid_to   = TIMESTAMPTZ '9999-12-31 23:59:59+00'
```

version 非現行化時は `is_current = false` に加え、運用で `valid_to` を過去日時に更新する方式を想定する（§13）。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `semantic_config_version_id` | サロゲート UUID | Run 再現性・子テーブル FK の参照先 |
| UNIQUE | `semantic_config_version_id` | PK と同一 | — |
| UNIQUE | `semantic_config_id`, `version_label` | 系列内 version の一意性 | 同一系列への重複 version 禁止 |
| UNIQUE（部分） | `semantic_config_id`（`is_current = true` の行のみ） | semantic_config_id 単位で現行 version を 1 件に制限 | Index 名: `uq_semantic_config_version_current_per_config` |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `semantic_config_id` | `semantic_config.semantic_config_id` | `ON` | DELETE RESTRICT | 物理ER §9。親系列削除前に version 行の整理が必要 |

### 8.1 被参照（物理 FK ON — 子テーブル）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `semantic_concept` | `semantic_config_version_id` | defines | `ON` | Concept 定義。詳細は各子テーブル定義 Task |
| `feature_definition` | `semantic_config_version_id` | defines | `ON` | Feature 8 軸定義 |
| `semantic_rule` | `semantic_config_version_id` | contains | `ON` | Semantic 抽出ルール |
| `relationship_rule` | `semantic_config_version_id` | contains | `ON` | Relationship → Feature 基準値ルール |
| `occasion_rule` | `semantic_config_version_id` | contains | `ON` | Occasion → Feature 基準値ルール |
| `pair_rule` | `semantic_config_version_id` | contains | `ON` | Pair 補正ルール |
| `concept_feature_rule` | `semantic_config_version_id` | contains | `ON` | Concept → Feature 補正ルール。詳細は `concept_feature_rule_テーブル定義書` §8・§17.1 |
| `normalization_rule` | `semantic_config_version_id` | contains | `ON` | Feature 正規化ルール |
| `input_type_rule` | `semantic_config_version_id` | contains | `ON` | Human Review: MVP 物理 DDL 対象 |
| `feature_integration_rule` | `semantic_config_version_id` | contains | `ON` | Human Review: MVP 物理 DDL 対象 |

> 子テーブル側 DDL では `REFERENCES semantic_config_version(semantic_config_version_id) ON DELETE RESTRICT` を付与する想定。Rule 定義の詳細・CHECK は各子テーブル定義 Task で確定する。

### 8.2 被参照（論理）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `recommendation_run` | `semantic_config_version_id` | used_by | `LOGICAL` | 物理ER §9。Run 開始時に固定。再現性保持 |
| `evaluation_run` | `semantic_config_version_id` | used_by | `LOGICAL` | 論理ER §12.2。Evaluation 系（MVP partial） |
| `user_semantic` | `semantic_config_version_id` | generates_with | `LOGICAL` | 派生データ。`user_semantic_テーブル定義書` §8.1・§17.1 No.1（物理 FK なし）。Run 固定 version と一致必須 |
| `item_semantic` | `semantic_config_version_id` | generates_with | `ON` | 派生データ。`item_semantic_テーブル定義書` §17.1 No.1 決定済み |
| `item_feature` | `semantic_config_version_id` | generates_with | `ON` | Item 派生データ系。物理ER §10 Index 方針に整合 |

> MVP 初期 DDL では `recommendation_run` / `evaluation_run` への物理 FK を張らない（§17.1 No.8）。整合は reco 側 Config 解決 + seed 正本 + Run INSERT 時の `semantic_config_version_id` 存在確認 + `recommendation_run.semantic_config_version_id` への Index で担保する。

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `semantic_config_version_pkey` | `semantic_config_version_id` | btree（PK） | 主キー | 自動生成 |
| `uq_semantic_config_version_config_label` | `semantic_config_id`, `version_label` | btree（unique） | 系列内 version 一意 | §7 と同一 |
| `uq_semantic_config_version_current_per_config` | `semantic_config_id` | btree（unique, partial） | 現行 version 解決 | `WHERE is_current = true` |
| `idx_semantic_config_version_config_created` | `semantic_config_id`, `created_at` DESC | btree | version 履歴参照 | 運用・監査 |
| `idx_semantic_config_version_valid_period` | `valid_from`, `valid_to` | btree | 有効期間による参照 | NULL 許容列を含む |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `semantic_config_version_pkey` | PRIMARY KEY | `semantic_config_version_id` | 主キー | — |
| `uq_semantic_config_version_config_label` | UNIQUE | `semantic_config_id`, `version_label` | 系列内 version 一意 | — |
| `uq_semantic_config_version_current_per_config` | UNIQUE（partial） | `semantic_config_id` | `is_current = true` は semantic_config_id あたり 1 行 | §17.1 No.6（系列ごとに現行1件。全体1現行は不採用） |
| `fk_semantic_config_version_semantic_config` | FOREIGN KEY | `semantic_config_id` | `semantic_config.semantic_config_id` ON DELETE RESTRICT | 親テーブル定義書 §8.1 と整合 |
| `chk_version_label_length` | CHECK | `version_label` | `char_length(version_label) BETWEEN 1 AND 50` | — |
| `chk_version_label_format` | CHECK | `version_label` | `version_label ~ '^v[0-9]+\.[0-9]+\.[0-9]+$'` | MVP は semver 基本形（例: `v1.0.0`）。pre-release  suffix は将来拡張 |
| `chk_valid_period` | CHECK | `valid_from`, `valid_to` | `valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from` | 有効期間の整合 |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| — | — | なし | — | 状態カラムなし。`is_current` は boolean |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | reco | Run 開始前 | — | — | 親 `is_active = true` → 当該 `semantic_config_id` で `is_current = true` を解決。失敗時 GRS-CFG-002 |
| SELECT | api | API-PUB-007 応答組立 | — | — | 親 `is_active = true` → 子 `is_current = true` を解決。`semantic_config` とアプリ層 JOIN で `config_name` を取得。子テーブル（Concept / Feature Definition）を JOIN |
| SELECT | api | evaluation 等の version 指定解決 | — | — | `config_name` + `version_label` で version 行を特定し、内部 `semantic_config_version_id` へ解決 |
| SELECT | reco / batch | 再現性参照 | — | — | 過去 Run / 派生データは保存済み `semantic_config_version_id` を参照（`is_current` 変更の影響を受けない） |
| INSERT | database（seed / 運用） | 新 version 追加 | 全列 | Upsert 想定 | 既存 version のパラメータ変更は新 version INSERT。`valid_from` / `valid_to` は §6.1 に従い seed で設定 |
| UPDATE | database（運用） | 現行切替のみ | `is_current` | 同一 `semantic_config_id` で旧 current を `false` にしてから新 current を `true` | 部分 unique により同時 2 件 true を防止 |
| UPDATE | database（運用） | 有効期間調整 | `valid_from`, `valid_to` | — | MVP では seed 固定を想定 |
| DELETE | — | MVP では原則禁止 | — | — | 子テーブル / Run 参照時は RESTRICT。`is_current` 切替で非現行化 |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（設定正本・再現性） |
| 削除方式 | 物理 DELETE 原則禁止 |
| 削除条件 | 子テーブル行・Run 参照が存在する場合は DELETE RESTRICT |
| 論理削除 | 専用列なし。`is_current = false` および `valid_to` による非現行化 |
| アーカイブ | MVP 対象外 |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `semantic_config_version` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: Semantic 群（`semantic_config` の直後、子テーブル `semantic_concept` 等より前） |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | api / reco（service role 経由） |
| 書き込み権限 | database 運用・seed のみ。Online / Batch 実行中の DML 更新なし |
| service role利用 | api のマスタ参照、reco Config 解決、seed 投入に限定 |
| 個人情報・機微情報 | 含まない |
| ログ出力制限 | 内部 `semantic_config_version_id`（uuid）を Public ログ・Response に過剰出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / CHECK / partial unique / FK が定義どおり | migration |
| 2 | PK / UNIQUE | 同一 `semantic_config_id` + `version_label` の重複 INSERT が拒否される | migration |
| 3 | is_current | 同一 `semantic_config_id` で `is_current=true` が 2 行以上になる INSERT/UPDATE が拒否される | migration |
| 4 | FK（親） | 存在しない `semantic_config_id` への INSERT が拒否される | migration |
| 5 | FK（親 DELETE） | 子 version 行存在時に親 `semantic_config` DELETE が拒否される | migration |
| 6 | version 解決 | reco / api が有効系列かつ `is_current = true` の version を解決できる | integration |
| 7 | API 整合 | API-PUB-007 の `configName` + `versionLabel` composite 参照とアプリ層 JOIN が整合（契約追随は Contract Task） | contract |
| 8 | 再現性 | 過去 Run の `semantic_config_version_id` が version 非現行化後も参照可能 | integration |
| 9 | seed 有効期間 | MVP seed の `valid_from` / `valid_to`（`9999-12-31 23:59:59+00`）が定義どおり | manual |
| 10 | 権限 | web client から Direct DB アクセス不可 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review にて旧 No.1〜No.6 / No.4 / No.5 を決定済み（§17.1 参照） |

### 17.1 Human Review 決定事項（Task #463）

| No | 論点 | 決定内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | Public 参照キー | **`configName` + `versionLabel` の composite** を Public 参照とする。単一 `semanticConfigVersionId` 表面 ID は採用しない | Human | API 契約・OpenAPI 追随は Contract Task |
| 2 | `config_name` の保持先 | 親 `semantic_config` を正本とする。本テーブルへの denormalize・DB ビューは **採用しない** | Human | api（IF-DB-API-005）がアプリ層 JOIN で解決（§5.3.1） |
| 3 | MVP 初期 `version_label` | **semver 形式 `v1.0.0`** を seed 正本とする | Human | §10 `chk_version_label_format` を semver 基本形に限定 |
| 4 | 内部参照キー | Run / 子テーブル / 派生データは引き続き **`semantic_config_version_id`（UUID）** を用いる。Public 非公開 | Human | composite → UUID 解決は api / reco 境界で実施 |
| 5 | 解決階層（`is_active` → `is_current`） | **2 段階解決を採用**。第 1 層: 親 `is_active = true` の系列のみ対象。第 2 層: 対象系列内で `is_current = true` の version を解決。系列無効（`is_active = false`）時は当該系列の version は解決対象外 | Human | §5.2。失敗時 GRS-CFG-002 |
| 6 | `is_current` の解決単位 | **`semantic_config_id` 単位**とする。同一系列内で `is_current = true` は最大 1 行（partial unique）。系列ごとに現行 version を独立管理し、**システム全体で1現行に制限しない** | Human | §7・§10 `uq_semantic_config_version_current_per_config`。`ranking_config` の `config_name` 単位と同型 |
| 7 | `valid_from` / `valid_to` の MVP 運用 | **seed で明示設定**。MVP 初期 `valid_to` は **`9999-12-31 23:59:59+00`（UTC）**（未来日付の上限）。`valid_from` は seed 投入日時。現行解決は `is_current` を主とし、期間による解決は MVP 必須にしない | Human | §6.1 |
| 8 | `recommendation_run` / `evaluation_run` への FK | **MVP は LOGICAL 参照を維持**（物理 FK は張らない） | Human | 下記推奨理由参照。`model_version` / `ranking_config` と同型 |

#### 17.1.1 No.8 推奨理由（`recommendation_run` / `evaluation_run` → LOGICAL）

| 観点 | LOGICAL 維持（推奨・採用） | 物理 FK ON の場合 |
| ---- | -------------------------- | ----------------- |
| 再現性 | 過去 Run が参照する version 行は **物理 DELETE 禁止**（§13）のため、参照先は残る。LOGICAL でも再現性は担保可能 | `ON DELETE RESTRICT` なら version 誤削除を DB が防げる（ただし §13 で DELETE 原則禁止） |
| 整合性 | Run INSERT 時に reco が解決済み `semantic_config_version_id` の **存在確認** + 参照列 Index で十分 | INSERT 時に DB が参照整合を強制。バグ検知は有利 |
| migration | Semantic 群と Run 群の **作成順・依存が緩い**。Evaluation 系（MVP partial）とも整合しやすい | `recommendation_run` DDL 時に `semantic_config_version` 先行が必須。Evaluation 未整備時に制約が重い |
| プロジェクト整合 | `model_version_テーブル定義書` §17.1 No.3、`ranking_config` と **同じ MVP 方針** | 将来の統一は可能だが MVP scope が広がる |
| 将来拡張 | `recommendation_run` テーブル定義 Task で **物理 FK ON + DELETE RESTRICT** をオプション検討可 | — |

**採用結論:** MVP は **LOGICAL のまま**。整合は reco Config 解決、Run INSERT 前の存在確認、`recommendation_run.semantic_config_version_id` / `evaluation_run.semantic_config_version_id` への Index（run テーブル定義 Task）で担保する。

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8 テーブル一覧・§9 FK・§10 Index・§15 適用順序 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §10.2 / §11.1 エンティティ属性・§11 関係 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §8 Semantic / Feature定義系 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | コード定義正本（本テーブルは enum 列なし） |
| ドメインモデル | `docs/04_ドメインモデル設計/ドメインモデル.md` | CF-01 / CF-02 / CF-03、意味 vs モデル分離 |
| API契約 | `docs/06_実装設計/api/API-PUB-007_Semantic設定取得API契約仕様書.md` | `configName` + `versionLabel` composite 参照（Contract Task で追随） |
| Human Decision | `ai-logs/human-decisions/2026-06-10-semantic-config-version-public-reference-join-policy.md` | Public 参照・JOIN 方針の判断記録 |
| 親テーブル定義 | `docs/06_実装設計/database/semantic_config_テーブル定義書.md` | 親 FK・`is_active` 解決・`configName` 参照 |
| 参照テーブル定義 | `docs/06_実装設計/database/ranking_config_テーブル定義書.md` | Config 系 UUID PK・`is_current` partial unique 構成参考 |
| 参照テーブル定義 | `docs/06_実装設計/database/model_version_テーブル定義書.md` | 技術 model version との責務分離参考 |
| 参照テーブル定義 | `docs/06_実装設計/database/relationship_master_テーブル定義書.md` | Master / Config 系構成踏襲 |

---

## 19. レビュー観点

- 論理ER §11.1（§10.2）・物理ER §8・§9・テーブル一覧 §8 と矛盾していない
- `semantic_config_version_id` / `semantic_config_id` / `version_label` / `is_current` / `valid_from` / `valid_to` / `created_at` がすべて定義されている
- `semantic_config_id` への物理 FK（ON DELETE RESTRICT）が明記されている
- `recommendation_run` / `evaluation_run` への LOGICAL 被参照方針が §8.2 / §17.1 No.8 に明記されている
- MVP seed の `valid_from` / `valid_to`（`valid_to = 9999-12-31 23:59:59+00`）が §6.1 に明記されている
- 子テーブル（`semantic_concept` / `feature_definition` / 各種 Rule）への ON FK 被参照が §8.1 に整理されている
- `model_version` との責務分離（CF-01 / CF-02）が明記されている
- `configName` + `versionLabel` composite 参照・アプリ層 JOIN・内部 uuid 非公開が §5.3 / §17.1 に明記されている
- 親 `semantic_config.is_active` → 子 `is_current` の 2 段階解決が §5.2 / §17.1 No.5 に決定されている
- `ranking_config` / `model_version` / `semantic_config` テーブル定義書と章構成・MVP 方針が一貫している
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
