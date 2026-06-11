# Semantic Concept テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                   |
| -------------- | -------------------------------------- |
| ドキュメントID | `DB-TBL-MVP-semantic_concept`          |
| ドキュメント名 | Semantic Concept テーブル定義書        |
| 対象システム   | Gift Recommendation Service MVP        |
| MVP対象        | `yes`                                  |
| 作成日         | 2026-06-11                             |
| 更新日         | 2026-06-11                             |

---

## 2. 概要

`semantic_concept` は、自然言語と 8 次元 Feature の **中間概念（Semantic Concept）** を、`semantic_config_version` 単位で保持する Semantic / Feature 定義系テーブルである。

API-PUB-007（Semantic 設定取得）の `semanticConcepts` 配列の正本となり、reco / batch が Semantic 抽出・Feature 変換時に参照する。

---

## 3. 目的

- MVP 初期 **18 Concept** の `concept_code` / 表示ラベル / 説明を version 管理する
- `semantic_rule` / `concept_feature_rule` が参照する Concept 正本を提供する
- seed 投入後、Public API から Concept 一覧を安定返却できるようにする

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `semantic_concept` |
| 論理テーブル名 | Semantic Concept |
| 分類 | Semantic / Feature 定義系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | reco（User Semantic 抽出・Feature 生成）、batch（Item Semantic 生成）、api（API-PUB-007 経由の参照） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11 |

---

## 5. 用途・責務

- **`semantic_config_version_id` 単位**で Concept 行を保持する（MVP seed は **18 行**）
- **`concept_code`** は snake_case 英語物理名（SemanticConcept定義書 §4.2）。version 内で一意
- **`concept_label`** は UI / API 表示ラベル（API-PUB-007 `conceptLabel`）
- **`concept_description`** は Concept 意味説明（API-PUB-007 `conceptDescription`、DB 上は NULL 許容）
- **`is_active = true`** の行のみ API-PUB-007 が返却する（契約上、返却行は active のみ）
- **内部 PK `semantic_concept_id` は Public API 非公開**。表面識別子は `conceptCode` のみ（API-PUB-007 §14 決定事項 No.2）

### 5.1 semantic_config_version との関係

| 観点 | `semantic_config_version` | `semantic_concept`（本テーブル） |
| ---- | --------------------------- | -------------------------------- |
| 分類 | Semantic / Feature 定義系（version ヘッダ） | Semantic / Feature 定義系（Concept 定義行） |
| 管理対象 | 意味体系 version ラベル・現行フラグ | Concept コード・ラベル・説明 |
| 行数 | version ごとに 1 行（+ 履歴） | version ごとに **MVP seed 18 行**（追加拡張可） |
| Public API | `semanticConfigVersionId`（API-PUB-007） | `semanticConcepts[]`（API-PUB-007） |

### 5.2 API-PUB-007 マッピング

| DB 列 | API 項目 | Public 公開 | 備考 |
| ----- | -------- | ----------- | ---- |
| `semantic_concept_id` | — | **非公開** | 内部 UUID |
| `semantic_config_version_id` | `semanticConfigVersionId`（親 version） | version 単位で間接公開 | 行単位では返さない |
| `concept_code` | `conceptCode` | 公開 | camelCase キーで表現 |
| `concept_label` | `conceptLabel` | 公開 | — |
| `concept_description` | `conceptDescription` | 公開（任意） | NULL の場合は応答から省略可 |
| `is_active` | `isActive` | 公開 | 応答に含める行は `true` のみ |

> API-PUB-007 応答例の `warm_gratitude` は **例示用**であり、MVP seed 正本は SemanticConcept定義書 §6.1 の 18 `concept_code` とする（§17.1 No.2）。

### 5.3 対象外

- Semantic 抽出ルール本体（`semantic_rule` の責務）
- Concept → Feature 補正ルール本体（`concept_feature_rule` の責務）
- Semantic 抽出結果（`user_semantic` / `item_semantic` の責務）
- `concept_group` / `polarity_default` 等のドメイン拡張属性（論理ER §10.2 未収載。§17.1 No.1）

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `semantic_concept_id` | Semantic Concept ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK。Public API 非公開 |
| 2 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `yes` | — | — | 所属する意味定義 version。`semantic_config_version` を参照 |
| 3 | `concept_code` | Concept Code | `text` | `yes` | — | — | — | — | Concept 物理名（snake_case）。SemanticConcept定義書 §4.2 正本 |
| 4 | `concept_label` | Concept Label | `varchar(100)` | `yes` | — | — | — | — | UI / API 表示ラベル。API-PUB-007 `conceptLabel` |
| 5 | `concept_description` | Concept Description | `varchar(500)` | `no` | — | — | — | `NULL` | 意味説明。API-PUB-007 `conceptDescription`（任意） |
| 6 | `is_active` | Active Flag | `boolean` | `yes` | — | — | — | `true` | 有効フラグ。`false` は API 返却対象外 |

> **論理ER との差分**: SemanticConcept定義書 §4.1 には `concept_group` / `polarity_default` / `related_feature_candidates` があるが、論理ER §10.2 には未収載。MVP 物理テーブルは論理ER §10.2 を正とし、拡張属性はドメイン定義書正本 + 後続 Rule テーブル定義 Task で扱う（§17.1 No.1）。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `semantic_concept_id` | サロゲート UUID | |
| UNIQUE | `semantic_concept_id` | PK と同一 | — |
| UNIQUE | `semantic_config_version_id`, `concept_code` | version 内で Concept code は 1 行 | Index 名: `uq_semantic_concept_version_code` |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `semantic_config_version_id` | `semantic_config_version.semantic_config_version_id` | `ON` | RESTRICT | 物理ER §9 / semantic_config_version テーブル定義書 §8.1 |

### 8.1 被参照（物理 FK ON — 子テーブル）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `semantic_rule` | `semantic_concept_id` | references | `ON` | 入力文・商品情報 → Concept 抽出ルール。詳細は semantic_rule 定義 Task |
| `concept_feature_rule` | `semantic_concept_id` | references | `ON` | Concept → Feature 補正ルール。論理ER上の `feature_rule` 分解先 |

> 子テーブル側 DDL では `REFERENCES semantic_concept(semantic_concept_id) ON DELETE RESTRICT` を付与する想定。Rule 詳細・weight / delta は各 Rule テーブル定義 Task で確定する。

### 8.2 被参照（論理）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `user_semantic` | `extracted_semantic_json` 内 concept 参照 | generates_with | `LOGICAL` | JSON 内は `concept_code` 参照を推奨。詳細は user_semantic Task |
| `item_semantic` | `semantic_json` 内 concept 参照 | generates_with | `LOGICAL` | batch 設計方針書の `semantic_concepts` 配列は code 参照 |

> MVP では派生データは **`concept_code` + `semantic_config_version_id`** で Concept を特定する設計を基本とする。`semantic_concept_id` への物理 FK は Rule 系子テーブルに限定する。

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `semantic_concept_pkey` | `semantic_concept_id` | btree（PK） | 主キー | 自動生成 |
| `uq_semantic_concept_version_code` | `semantic_config_version_id`, `concept_code` | btree（unique） | version 内 code 一意 | |
| `idx_semantic_concept_version_active_code` | `semantic_config_version_id`, `is_active`, `concept_code` | btree | API-PUB-007 一覧（active + code 順） | 物理ER §10 は個別 Index 未記載。本 Task で追加方針 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `semantic_concept_pkey` | PRIMARY KEY | `semantic_concept_id` | 主キー | — |
| `uq_semantic_concept_version_code` | UNIQUE | `semantic_config_version_id`, `concept_code` | version 内 code 一意 | |
| `chk_concept_code_format` | CHECK | `concept_code` | `concept_code ~ '^[a-z][a-z0-9_]*$'` | SemanticConcept定義書 §4.2 snake_case |
| `chk_concept_code_length` | CHECK | `concept_code` | `char_length(concept_code) BETWEEN 1 AND 64` | 命名上限 |
| `chk_concept_label_length` | CHECK | `concept_label` | `char_length(concept_label) BETWEEN 1 AND 100` | 表示ラベル上限 |
| `chk_concept_description_length` | CHECK | `concept_description` | `concept_description IS NULL OR char_length(concept_description) <= 500` | 説明上限 |

> MVP では `feature_definition` と異なり **固定 code 一覧 CHECK は設けない**（Concept 追加拡張を許容）。MVP seed の 18 code は §10.1 を正本とし、enum / packages 正本化は後続 Task で検討する。

### 10.1 MVP 初期 Concept 一覧（seed 参照）

SemanticConcept定義書 §6.1 / §15.1 に基づく MVP seed 18 件。`concept_label` は seed 投入時に SemanticConcept定義書 §6.1 の `concept_label` 列を転記する。

| concept_code | concept_label（seed 参考） | concept_group（ドメイン参考） |
| ------------ | -------------------------- | ----------------------------- |
| `formal_refined` | 上品・端正 | social_appropriateness |
| `safe_classic` | 無難・定番 | social_appropriateness |
| `prestigious_quality` | 高級・上質 | social_appropriateness |
| `practical_useful` | 実用・機能 | practical_value |
| `emotional_warm` | 温かい気持ち | emotional_value |
| `special_memorable` | 特別・記憶に残る | special_value |
| `surprising_unique` | 意外性・ユニーク | special_value |
| `romantic_affectionate` | 愛情・ロマン | relationship_value |
| `close_personal` | 親しさ・近さ | relationship_value |
| `symbolic_identity_fit` | その人らしさ | identity_value |
| `story_narrative` | ストーリー性 | identity_value |
| `stylish_aesthetic` | おしゃれ・美意識 | aesthetic_value |
| `cute_soft` | かわいい・柔らかい | aesthetic_value |
| `casual_light` | カジュアル・軽さ | tone_control |
| `not_too_much` | 重すぎない | tone_control |
| `not_too_safe` | 無難すぎない | tone_control |
| `luxurious_rich` | 豪華・華やか | special_value |
| `cheerful_positive` | 明るい・前向き | emotional_value |

> `concept_group` 列は本テーブルに持たない。ドメイン整理・Rule 設計の参考として seed ドキュメントまたは SemanticConcept定義書を参照する。

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `concept_code` | `concept_code` | SemanticConcept定義書 §4.2 / §6.1 | snake_case 英語。MVP seed 18 値 | 固定 CHECK なし |
| — | 状態 enum | なし | — | `is_active` は boolean |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | api | 現行 `semantic_config_version` + `is_active=true` | — | — | API-PUB-007。ORDER BY `concept_code` |
| SELECT | reco / batch | Semantic 抽出・Feature 変換時 | — | — | `concept_code` 存在確認 |
| INSERT | database（seed） | 新 version 初回投入 | 全列 | version ごと 18 行 Upsert | MVP seed 18 行 |
| UPDATE | database（運用） | ラベル・説明・無効化 | `concept_label`, `concept_description`, `is_active` | — | **`concept_code` 変更禁止**（新 version INSERT 推奨） |
| DELETE | — | MVP では原則禁止 | — | — | `is_active=false` で無効化。子 Rule 参照時は RESTRICT |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（設定正本。version 履歴として保持） |
| 削除方式 | 物理 DELETE 原則禁止 |
| 論理削除 | `is_active = false` |
| version 切替 | 新 `semantic_config_version` 作成時に 18 行を新規 INSERT |
| 子 Rule 参照 | `semantic_rule` / `concept_feature_rule` が参照中は親 Concept の物理 DELETE 不可（RESTRICT） |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `semantic_concept` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: `semantic_config_version` 作成後、`feature_definition` と同順または直後、Rule 群より前 |
| rollback方針 | forward migration 主体 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | api / reco / batch（service role） |
| 書き込み権限 | database seed / 運用のみ |
| Public API | `semanticConcepts` は API-PUB-007 で公開（内部 PK は非公開） |
| ログ出力制限 | 設定内容を過剰ログ出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / CHECK / FK | migration |
| 2 | UNIQUE | 同一 version で同一 `concept_code` の重複 INSERT が拒否される | migration |
| 3 | code 形式 CHECK | 大文字・ハイフン含み code が拒否される | migration |
| 4 | API 整合 | active 行が API-PUB-007 `semanticConcepts` 形式で返る | integration |
| 5 | seed 整合 | §10.1 の 18 code が seed に存在 | manual |
| 6 | 空配列 | active Concept 0 件で API 200 + `semanticConcepts: []` | contract |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review 前の論点は §17.1 を参照 |

### 17.1 Human Review 観点

| No | 論点 | 推奨案 | 判断者 | 備考 |
| --: | ---- | ------ | ------ | ---- |
| 1 | `concept_group` / `polarity_default` 列の追加 | MVP は論理ER §10.2 どおり **非保持**。ドメイン定義書正本 + Rule 側で参照 | Human | SemanticConcept定義書 §4.1 vs 論理ER |
| 2 | API-PUB-007 例示 `warm_gratitude` | seed / 契約例は **§10.1 の 18 code** を正本とする。契約書例は後続 #469 で整合 | Human | API-PUB-007 §7.4.1 |
| 3 | API 返却順 | MVP は **`concept_code` 昇順**（display_order 列なし） | Human | feature_definition の display_order との差 |
| 4 | `concept_description` DB 必須性 | DB は **NULL 許容**。seed では説明を投入推奨 | Human | API は optional |
| 5 | Concept 追加拡張 | 同一 version への追加 INSERT を運用で許容。code 変更は禁止（新 version 推奨） | Human | SemanticConcept定義書 §13 |
| 6 | 子 Rule FK | `semantic_rule` / `concept_feature_rule` は **`semantic_concept_id` 物理 FK ON** | Human | §8.1 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8–§11 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §10.2 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §8 |
| SemanticConcept定義書 | `docs/04_ドメインモデル設計/SemanticConcept定義書.md` | §4.2 / §6.1 / §15 |
| Featureルール定義書 | `docs/04_ドメインモデル設計/Featureルール定義書.md` | §10 Concept Feature Rule |
| API契約 | `docs/06_実装設計/api/API-PUB-007_Semantic設定取得API契約仕様書.md` | semanticConcepts マッピング |
| 兄弟テーブル | `docs/06_実装設計/database/feature_definition_テーブル定義書.md` | Wave2 章構成参考 |
| 親テーブル | `docs/06_実装設計/database/semantic_config_version_テーブル定義書.md` | FK / version 管理 |
| 先行 Task | Issue #462 / #463 / #470 | semantic_config / semantic_config_version / feature_definition |

---

## 19. レビュー観点

- 論理ER §10.2・物理ER §8–§11・テーブル一覧 §8 と矛盾していない
- SemanticConcept定義書 §6.1 の MVP 18 Concept が seed 方針として明記されている
- API-PUB-007 `semanticConcepts` マッピングと Public 非公開列（`semantic_concept_id`）が明確
- `semantic_config_version_id` FK（物理 ON）が明記されている
- `semantic_rule` / `concept_feature_rule` からの被参照（§8.1）が整理されている
- `concept_group` / `polarity_default` の非保持方針（§17.1 No.1）が明示されている
- DDL Task が CREATE TABLE を起こせる粒度である
