# Model Version テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                               |
| -------------- | ---------------------------------- |
| ドキュメントID | `DB-TBL-MVP-model_version`         |
| ドキュメント名 | Model Version テーブル定義書         |
| 対象システム   | Gift Recommendation Service MVP    |
| MVP対象        | `yes`                              |
| 作成日         | 2026-06-08                         |
| 更新日         | 2026-06-08（AI Review #453 再指摘反映） |

---

## 2. 概要

`model_version` は、Embedding / LLM / Ranking 等の **技術的モデル version** を管理する Master / Config 系テーブルである。

`semantic_config_version`（意味の作り方）とは分離し、Run 実行時・Batch 生成時に使用するモデル version を固定して再現性を担保する。Public API には `model_version_id` を返却しない（内部管理用）。

---

## 3. 目的

- Embedding / LLM / Ranking 等のモデル identifier と version を DB 上で一意に管理する
- reco の Config / Version 解決（MOD-RECO-003）および batch の Item Embedding 生成が参照する正本を提供する
- `recommendation_run` / `item_embedding` / `evaluation_run` 等が参照する version ID の整合基盤とする

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `model_version` |
| 論理テーブル名 | Model Version |
| 分類 | Master / Config系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | reco（Run 実行時 version 解決）、batch（Embedding 生成） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8 |

---

## 5. 用途・責務

- **provider / model_name / model_type / version_label** により、利用モデルを一意に識別する
- **`is_current`** により、reco / batch が解決する「現行 version」を `model_type` 単位で管理する（Embedding / LLM / Ranking 等ごとに 1 件）
- **`model_version_id`（UUID）** をサロゲート PK とし、Run・派生データへの参照キーとする
- `recommendation_run.model_version_id` は本テーブルを **論理参照**する（MVP 初期 DDL では物理 FK なし。Run 開始時に ID を固定し再現性を担保）
- `item_embedding.model_version_id` は本テーブルを **ON 方針**で参照する（Item 派生データ系。物理 FK DDL は `item_embedding` 定義 Task で `model_version` 先行 CREATE 後に付与。DELETE RESTRICT 想定）

### 5.1 semantic_config_version との分離

| 観点 | `semantic_config_version` | `model_version` |
| ---- | ------------------------- | --------------- |
| 管理対象 | 意味推定ロジック（Feature 定義・Rule 等） | Embedding / LLM / Ranking 等の技術的モデル version（`model_type` 単位） |
| ドメイン不変条件 | CF-01 | CF-02（Ranking 文脈）/ CF-03（Run 固定） |
| Run 固定 | Run 開始時に固定 | Run 開始時に固定 |

> **ドメインモデルとの関係**: ドメインモデル CF-02 は `model_version` を「順位決定ロジック」として述べるが、本テーブルはテーブル一覧 §9・§14 No.6 に従い embedding / LLM / ranking 等の技術 version を `model_type` で束ねて管理する。CF-02 の解釈（Ranking 専用か複数 model_type か）は Human Review 論点（§17.1 No.1）。

### 5.2 対象外

- 意味体系 version（`semantic_config_version` の責務）
- Ranking パラメータ JSON（`ranking_config` の責務）
- 理由文テンプレート（`reason_template` の責務）
- Feature 正規化統計量 version（`feature_normalization_version` の責務）
- Public API への `model_version_id` 公開

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `model_version_id` | Model Version ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK。Run・Embedding 等の参照キー |
| 2 | `provider` | Provider | `varchar(50)` | `yes` | — | — | — | — | モデル提供元識別子（例: `openai`）。secret は保持しない |
| 3 | `model_name` | Model Name | `varchar(100)` | `yes` | — | — | — | — | API 上のモデル identifier（例: `text-embedding-3-small`） |
| 4 | `model_type` | Model Type | `text` | `yes` | — | — | — | — | モデル種別。MVP 候補: `embedding` / `llm` / `ranking`（§11 参照） |
| 5 | `version_label` | Version Label | `varchar(50)` | `yes` | — | — | — | — | 運用上の version ラベル（例: `v1`, `2026-06-08`）。同一モデルの世代識別 |
| 6 | `is_current` | Is Current | `boolean` | `yes` | — | — | — | `false` | 当該 `model_type` の現行 version フラグ。`true` は model_type あたり最大 1 件（§7・§10） |
| 7 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | レコード作成日時 |

> **用語補足**: batch 設計書等では Embedding 文脈で `embedding_model_version_id` と記載される場合があるが、物理列名は論理ER・テーブル一覧に従い `model_version_id` を正とする（同一概念）。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `model_version_id` | UUID サロゲートキー | 自然キーは provider + model_name + model_type + version_label |
| UNIQUE | `provider`, `model_name`, `model_type`, `version_label` | モデル世代の一意性 | 同一組み合わせの重複 INSERT を禁止 |
| UNIQUE（部分） | `model_type`（`is_current = true` の行のみ） | model_type 単位で現行 version を 1 件に制限 | Index 名: `uq_model_version_current_per_type` |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| — | — | なし | — | 本テーブルは Config 根。他テーブルから参照される |

### 8.1 被参照（論理 / ON 方針）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `recommendation_run` | `model_version_id` | used_by | `LOGICAL` | 物理ER §9。Run 開始時に固定。MVP は物理 FK なし |
| `item_embedding` | `model_version_id` | generates_with | `ON`（方針） | 論理ER §11・テーブル一覧 §14 No.6。物理 FK は `item_embedding` テーブル定義 Task で DDL 確定。物理ER §9 には未記載 |
| `evaluation_run` | `model_version_id` | used_by | `LOGICAL` | 論理ER §12.2。Evaluation 系 Task で FK 方針を確定 |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `model_version_pkey` | `model_version_id` | btree（PK） | 主キー | 自動生成 |
| `uq_model_version_identity` | `provider`, `model_name`, `model_type`, `version_label` | unique（btree） | モデル世代の一意性 | §7 と同一 |
| `uq_model_version_current_per_type` | `model_type` | unique（btree, partial） | 現行 version 解決 | `WHERE is_current = true` |
| `idx_model_version_type_current` | `model_type`, `is_current` | btree | reco / batch の現行 version 参照 | 部分 Index なしでも利用可 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `model_version_pkey` | PRIMARY KEY | `model_version_id` | 主キー | — |
| `uq_model_version_identity` | UNIQUE | `provider`, `model_name`, `model_type`, `version_label` | モデル世代一意 | — |
| `uq_model_version_current_per_type` | UNIQUE（部分） | `model_type` | `is_current = true` の行のみ。model_type あたり 1 件 | Human Review 論点（§17） |
| `chk_model_type_mvp` | CHECK | `model_type` | `model_type IN ('embedding', 'llm', 'ranking')` | MVP 3 値。後続 enum Task で正本化 |
| `chk_provider_format` | CHECK | `provider` | `provider ~ '^[a-z][a-z0-9_]*$'` | snake_case。先頭英字 |
| `chk_version_label_length` | CHECK | `version_label` | `char_length(version_label) BETWEEN 1 AND 50` | — |
| `chk_model_name_length` | CHECK | `model_name` | `char_length(model_name) BETWEEN 1 AND 100` | §6 型定義と整合 |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `model_type` | `model_type` | 本 Task（候補）→ 後続 enum Task | `embedding`, `llm`, `ranking` | テーブル一覧 §9: embedding model / LLM / ranking model。YAML 正本化は enum Task へ引き継ぎ |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | reco | Run 開始前 | — | — | `is_current = true` かつ対象 `model_type` で現行 version を解決。解決失敗時 GRS-CFG-003 |
| SELECT | batch | Item Embedding 生成前 | — | — | `model_type = embedding` の現行 version を参照 |
| SELECT | reco / batch | 再現性参照 | — | — | 過去 Run / Embedding は保存済み `model_version_id` を参照（`is_current` 変更の影響を受けない） |
| INSERT | database（seed / 運用） | 新モデル version 追加 | 全列 | Upsert 想定 | MVP では管理 UI なし |
| UPDATE | database（seed / 運用） | 現行 version 切替 | `is_current` | 同一 model_type で旧 current を `false` にしてから新 current を `true` | 部分 unique により同時 2 件 true を防止 |
| DELETE | — | MVP では原則禁止 | — | — | 参照中 Run / Embedding がある場合 RESTRICT。無効化は新 version 追加 + `is_current` 切替 |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（設定正本）。過去 Run / Embedding 再現のため履歴 version も保持 |
| 削除方式 | 物理 DELETE 原則禁止 |
| 削除条件 | 参照が存在しない場合のみ運用判断で DELETE 可（Human Review 必須） |
| 論理削除 | MVP では専用列なし。`is_current = false` で非現行化 |
| アーカイブ | MVP 対象外 |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `model_version` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §8・§15: Master / Config 群（`pair_master` より後、`ranking_config` より前） |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | reco / batch（service role 経由） |
| 書き込み権限 | database 運用・seed のみ。Online Run 実行中の DML 更新なし |
| service role利用 | version 解決・seed 投入に限定。web client から Direct DB アクセス不可 |
| 個人情報・機微情報 | 含まない。API キー・secret は本テーブルに保存しない |
| ログ出力制限 | `model_version_id` は内部値。Public ログ・Response に過剰出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / CHECK / partial unique が定義どおり | migration |
| 2 | PK / UNIQUE | 同一 provider + model_name + model_type + version_label の重複が拒否される | migration |
| 3 | is_current | 同一 model_type で `is_current = true` が 2 件以上になる INSERT/UPDATE が拒否される | migration |
| 4 | 被参照 FK | `item_embedding` 側 FK（`fk_item_embedding_model_version` 等）は item_embedding 定義 Task で検証 | migration（後続 Task） |
| 5 | version 解決 | reco が `is_current = true` の embedding / ranking version を解決できる | integration |
| 6 | 再現性 | 過去 Run の `model_version_id` が version 非現行化後も参照可能 | integration |
| 7 | 権限 | web client から Direct DB アクセス不可 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review 前の論点は §17.1 を参照 |

### 17.1 Human Review 観点（PR #453）

| No | 論点 | 推奨案 | 判断者 | 備考 |
| --: | ---- | ------ | ------ | ---- |
| 1 | `model_type` のスコープと CF-02 解釈 | 本定義書どおり `embedding` / `llm` / `ranking` の 3 値を `model_type` で管理し、Ranking Run 解決は `model_type = ranking` の現行 version を参照 | Human | ドメインモデル CF-02 は Ranking 文脈の責務分離。Embedding / LLM は batch 文脈（テーブル一覧 §9） |
| 2 | `is_current` のスコープ | model_type 単位（部分 unique 採用） | Human | 全体 1 件案は reco / batch の並列解決と両立しにくい |
| 3 | `recommendation_run` への物理 FK | MVP は `LOGICAL` のまま（物理ER §9） | Human | relationship_master / occasion_master と同型 |
| 4 | `item_embedding` への物理 FK | `ON` + `DELETE RESTRICT`。DDL は item_embedding 定義 Task で `model_version` 先行 CREATE 後に付与 | Human | 本 Task §10 には被参照側 FK を載せない（Master 定義書慣例） |
| 5 | `model_type` enum の YAML 正本化 | 後続 enum Task へ引き継ぎ。本 Task は CHECK 候補値のみ | Human | enum 定義書 + packages/code-definitions |
| 6 | `evaluation_run.model_version_id` の FK 方針 | **LOGICAL FK 維持**（物理 FK なし）。`evaluation_run_テーブル定義書` §17.1 No.3・§9 `idx_evaluation_run_model_version` | Human | Issue #567 確定 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8 分類・§9 FK・§11 制約 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §11.1 エンティティ属性・§11 関係 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §9 Master / Config系・§14 No.6 Embedding version |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | model_type 正本化（後続 Task） |
| ドメインモデル | `docs/04_ドメインモデル設計/ドメインモデル.md` | model_version 責務・CF-02 / CF-03 |
| 参照テーブル定義 | `docs/06_実装設計/database/relationship_master_テーブル定義書.md` | Master / Config 系構成 |
| 参照テーブル定義 | `docs/06_実装設計/database/occasion_master_テーブル定義書.md` | Master / Config 系構成 |
| 処理構成 | `docs/05_アプリケーション設計/アプリ/処理構成定義書.md` | Config / Version 解決 |
| バッチ設計 | `docs/05_アプリケーション設計/アプリ/batch/バッチ設計方針書.md` | Embedding 再生成判定 |

---

## 19. レビュー観点

- 論理ER §11.1・物理ER §8・§9・§11・テーブル一覧 §9 と矛盾していない
- `model_version_id`（UUID PK）および provider / model_name / model_type / version_label / is_current / created_at が定義されている
- `recommendation_run` への LOGICAL FK / `item_embedding` への ON FK 方針が明記されている（item_embedding FK DDL は後続 Task）
- `semantic_config_version` との責務分離（CF-01 / CF-02 / CF-03）と `model_type` 管理方針が明記されている
- relationship_master / occasion_master と §10 に被参照 FK を載せない Master / Config 系慣例が一貫している
- 物理ER §8 の Master / Config 並び（`pair_master` → `model_version` → `ranking_config`）と §14 適用順序が整合している
- `is_current` の model_type 単位管理と部分 unique が DDL へ展開できる粒度である
- Public API 非公開（`model_version_id`）が明記されている
- relationship_master / occasion_master テーブル定義書と Master / Config 系方針（保持・削除・seed 更新）が一貫している
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
