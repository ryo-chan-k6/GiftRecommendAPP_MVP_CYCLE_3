# Semantic Config Version テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                    |
| -------------- | --------------------------------------- |
| ドキュメントID | `DB-TBL-MVP-semantic_config_version`    |
| ドキュメント名 | Semantic Config Version テーブル定義書  |
| 対象システム   | Gift Recommendation Service MVP         |
| MVP対象        | `yes`                                   |
| 作成日         | 2026-06-09                              |
| 更新日         | 2026-06-09                              |

---

## 2. 概要

`semantic_config_version` は、Semantic / Feature 定義体系の **version 単位の設定正本** を保持する Semantic / Feature定義系テーブルである。

親テーブル `semantic_config` が設定系列（lineage）の大枠を管理し、本テーブルは系列内の version（`version_label` / `is_current` / 有効期間）および Run 再現性に固定する version ID を担う。`model_version`（技術的モデル version）とは分離する。

Public API（API-PUB-007）では `semanticConfigVersionId` と `versionLabel` を表面公開するが、内部 UUID 主キー（`semantic_config_version_id`）は直接公開しない。

---

## 3. 目的

- Semantic Concept / Feature Definition / 各種 Rule の version 単位の正本を DB 上で管理する
- reco / api が Config / Version 解決時に参照する現行 version の正本を提供する
- `recommendation_run` / `evaluation_run` が参照する `semantic_config_version_id` の整合基盤とする
- API-PUB-007 / API-PUB-008 の `semanticConfigVersionId` / `versionLabel` マッピングの物理正本とする

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
- **`is_current`** により、reco / api が解決する「現行 version」を **`semantic_config_id` 単位**で管理する（§7・§10）
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
| Public API | `semanticConfigVersionId` / `versionLabel` を表面公開 | `model_version_id` は非公開 |

### 5.2 semantic_config との分離・解決階層

| 観点 | `semantic_config`（親） | `semantic_config_version`（本テーブル） |
| ---- | ----------------------- | --------------------------------------- |
| 管理単位 | 設定系列（lineage）の大枠 | 系列内の version |
| 主な列 | `config_name`, `is_active` | `version_label`, `is_current`, `valid_from`, `valid_to` |
| 解決順位 | **第 1 層**: `is_active = true` の系列のみ対象 | **第 2 層**: 対象系列内で `is_current = true` の version を解決 |
| Run 固定 | 直接参照しない | `recommendation_run.semantic_config_version_id` で固定 |

> **解決階層（MVP 推奨）**: reco / api の Config Resolver は、先に親 `semantic_config.is_active = true` を満たす系列を絞り込み、続けて当該 `semantic_config_id` で `is_current = true` の version 行を解決する。詳細は §17 No.1。

### 5.3 Public API との関係（API-PUB-007）

| DB 列 / 概念 | API 項目 | 公開方針 | 備考 |
| ------------ | -------- | -------- | ---- |
| `semantic_config_version_id`（uuid） | — | **非公開** | 内部 DB 主キー。API-PUB-007 §7.3.1 の「内部 DB 主キー非公開」に整合 |
| `version_label` | `versionLabel` | 表面公開（任意） | 例: `v1.0.0` |
| version 行（表面 ID） | `semanticConfigVersionId` | 表面公開（必須） | `semantic_config_version` 正本への Public 参照。例: `semantic_config_v001` |
| 親 `semantic_config.config_name` | `configName` | 表面公開（任意） | 親テーブル `semantic_config` から JOIN 解決 |

**MVP マッピング方針（暫定）:**

- api 層は `semanticConfigVersionId` に **内部 uuid を返却しない**
- `versionLabel` は `version_label` をそのままマッピングする
- `semanticConfigVersionId` は version 行を Public に識別する表面 ID とする。API-PUB-007 例では `semantic_config_v001` と `versionLabel: v1.0.0` が併記されるため、単一 `version_label` 列のみでは両方を同時に表現できない場合がある。MVP seed では `version_label` を `semantic_config_v001` または `v1.0.0` のいずれかに統一し、api 層の表面 ID 解決ルールは §17 No.2 で Human Review とする

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
| 3 | `version_label` | Version Label | `varchar(50)` | `yes` | — | — | — | — | 系列内 version ラベル。API `versionLabel` のマッピング先。MVP 初期値例: `semantic_config_v001` または `v1.0.0` |
| 4 | `is_current` | Current Flag | `boolean` | `yes` | — | — | — | `false` | 現行 version フラグ。`true` は `semantic_config_id` あたり最大 1 行（§10） |
| 5 | `valid_from` | Valid From | `timestamptz` | `no` | — | — | — | `NULL` | version 有効開始（UTC）。NULL は制限なし |
| 6 | `valid_to` | Valid To | `timestamptz` | `no` | — | — | — | `NULL` | version 有効終了（UTC）。NULL は制限なし |
| 7 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | レコード作成日時（UTC） |

> **論理ER §11.1（§10.2）との関係**: 論理ERが列挙する主要属性（`semantic_config_version_id`, `semantic_config_id`, `version_label`, `is_current`, `valid_from`, `valid_to`, `created_at`）をすべて物理化する。

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
| `concept_feature_rule` | `semantic_config_version_id` | contains | `ON` | Concept → Feature 補正ルール |
| `normalization_rule` | `semantic_config_version_id` | contains | `ON` | Feature 正規化ルール |
| `input_type_rule` | `semantic_config_version_id` | contains | `ON` | MVP partial |
| `feature_integration_rule` | `semantic_config_version_id` | contains | `ON` | MVP partial |

> 子テーブル側 DDL では `REFERENCES semantic_config_version(semantic_config_version_id) ON DELETE RESTRICT` を付与する想定。Rule 定義の詳細・CHECK は各子テーブル定義 Task で確定する。

### 8.2 被参照（論理）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `recommendation_run` | `semantic_config_version_id` | used_by | `LOGICAL` | 物理ER §9。Run 開始時に固定。再現性保持 |
| `evaluation_run` | `semantic_config_version_id` | used_by | `LOGICAL` | 論理ER §12.2。Evaluation 系（MVP partial） |
| `user_semantic` | `semantic_config_version_id` | generates_with | `LOGICAL` | 派生データ。詳細は別 Task |
| `item_semantic` | `semantic_config_version_id` | generates_with | `ON` / `LOGICAL` | 派生データ。item 系 Task で FK 方針確定 |
| `item_feature` | `semantic_config_version_id` | generates_with | `ON` | Item 派生データ系。物理ER §10 Index 方針に整合 |

> MVP 初期 DDL では `recommendation_run` / `evaluation_run` への物理 FK を張らない。整合は reco 側 Config 解決 + seed 正本 + Run INSERT 時の存在確認で担保する。

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
| `uq_semantic_config_version_current_per_config` | UNIQUE（partial） | `semantic_config_id` | `is_current = true` は semantic_config_id あたり 1 行 | MVP 方針。§17 No.3 |
| `fk_semantic_config_version_semantic_config` | FOREIGN KEY | `semantic_config_id` | `semantic_config.semantic_config_id` ON DELETE RESTRICT | 親テーブル定義書 §8.1 と整合 |
| `chk_version_label_length` | CHECK | `version_label` | `char_length(version_label) BETWEEN 1 AND 50` | — |
| `chk_version_label_format` | CHECK | `version_label` | `version_label ~ '^[a-z][a-z0-9_.-]*$'` | snake_case / semver 風を許容。例: `semantic_config_v001`, `v1.0.0` |
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
| SELECT | api | API-PUB-007 応答組立 | — | — | 現行 version 解決後、子テーブル（Concept / Feature Definition）を JOIN |
| SELECT | reco / batch | 再現性参照 | — | — | 過去 Run / 派生データは保存済み `semantic_config_version_id` を参照（`is_current` 変更の影響を受けない） |
| INSERT | database（seed / 運用） | 新 version 追加 | 全列 | Upsert 想定 | 既存 version のパラメータ変更は新 version INSERT |
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
| 7 | API 整合 | API-PUB-007 の `semanticConfigVersionId` / `versionLabel` / `configName` マッピングが整合 | contract |
| 8 | 再現性 | 過去 Run の `semantic_config_version_id` が version 非現行化後も参照可能 | integration |
| 9 | 権限 | web client から Direct DB アクセス不可 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | `is_active`（親）と `is_current`（本テーブル）の解決階層 | 系列無効時に子 version をどう扱うかが reco / api Resolver に影響 | Human | DDL Task 前 | 本定義書 §5.2: 親 `is_active` → 子 `is_current` の 2 段階解決を推奨 |
| 2 | API `semanticConfigVersionId` と `version_label` の対応 | API 例では `semantic_config_v001` と `v1.0.0` が別フィールド。単一 `version_label` 列での表面 ID 解決ルールが api 実装に影響 | Human | API 実装前 | §5.3 参照。uuid PK は非公開 |
| 3 | `is_current` の解決単位 | MVP では `semantic_config_id` 単位 partial unique を採用。全体 1 現行も選択肢 | Human | seed Task 前 | 本定義書 §10 は semantic_config_id 単位 |
| 4 | `valid_from` / `valid_to` の MVP 運用 | NULL 許容とするが、seed で期間を設定するかは運用判断 | Human | seed Task 前 | 論理ER §11.1 に属性あり |
| 5 | `recommendation_run` / `evaluation_run` への物理 FK | MVP は LOGICAL（物理ER §9）だが、DDL Task で ON に変更するか | Human | run テーブル定義 Task | RESTRICT と Run 履歴保持の兼ね合い |
| 6 | MVP 初期 `version_label` 値 | `semantic_config_v001` と `v1.0.0` のどちらを seed 正本とするか | Human | seed Task 前 | API-PUB-007 例に両方あり |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8 テーブル一覧・§9 FK・§10 Index・§15 適用順序 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §10.2 / §11.1 エンティティ属性・§11 関係 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §8 Semantic / Feature定義系 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | コード定義正本（本テーブルは enum 列なし） |
| ドメインモデル | `docs/04_ドメインモデル設計/ドメインモデル.md` | CF-01 / CF-02 / CF-03、意味 vs モデル分離 |
| API契約 | `docs/06_実装設計/api/API-PUB-007_Semantic設定取得API契約仕様書.md` | `semanticConfigVersionId` / `versionLabel` / `configName` |
| 親テーブル定義 | `docs/06_実装設計/database/semantic_config_テーブル定義書.md` | 親 FK・`is_active` 解決・`configName` 参照 |
| 参照テーブル定義 | `docs/06_実装設計/database/ranking_config_テーブル定義書.md` | Config 系 UUID PK・`is_current` partial unique 構成参考 |
| 参照テーブル定義 | `docs/06_実装設計/database/model_version_テーブル定義書.md` | 技術 model version との責務分離参考 |
| 参照テーブル定義 | `docs/06_実装設計/database/relationship_master_テーブル定義書.md` | Master / Config 系構成踏襲 |

---

## 19. レビュー観点

- 論理ER §11.1（§10.2）・物理ER §8・§9・テーブル一覧 §8 と矛盾していない
- `semantic_config_version_id` / `semantic_config_id` / `version_label` / `is_current` / `valid_from` / `valid_to` / `created_at` がすべて定義されている
- `semantic_config_id` への物理 FK（ON DELETE RESTRICT）が明記されている
- `recommendation_run` / `evaluation_run` への LOGICAL 被参照方針が明記されている
- 子テーブル（`semantic_concept` / `feature_definition` / 各種 Rule）への ON FK 被参照が §8.1 に整理されている
- `model_version` との責務分離（CF-01 / CF-02）が明記されている
- API-PUB-007 の `semanticConfigVersionId` / `versionLabel` マッピングと内部 uuid 非公開が明記されている
- 親 `semantic_config.is_active` と本テーブル `is_current` の解決階層が §17 に整理されている
- `ranking_config` / `model_version` / `semantic_config` テーブル定義書と章構成・MVP 方針が一貫している
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
