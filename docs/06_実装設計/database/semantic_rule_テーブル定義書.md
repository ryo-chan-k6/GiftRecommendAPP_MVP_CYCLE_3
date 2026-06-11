# Semantic Rule テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                              |
| -------------- | --------------------------------- |
| ドキュメントID | `DB-TBL-MVP-semantic_rule`        |
| ドキュメント名 | Semantic Rule テーブル定義書      |
| 対象システム   | Gift Recommendation Service MVP   |
| MVP対象        | `yes`                             |
| 作成日         | 2026-06-11                        |
| 更新日         | 2026-06-11（Human Review 決定反映） |

---

## 2. 概要

`semantic_rule` は、User 入力文・商品情報（商品名・説明等）から **Semantic Concept を抽出するルール** を、`semantic_config_version` 単位で保持する Semantic / Feature 定義系テーブルである。

reco / batch の Semantic Rule Resolver が参照する設定正本であり、**Public API 表面には含めない**（API-PUB-007 / API-PUB-008）。

---

## 3. 目的

- keyword / phrase / pattern / llm 各方式の抽出ルールを version 管理する
- ルール適用時の抽出先 Concept（`semantic_concept_id`）と重み（`weight`）を正本化する
- seed 投入後、reco / batch が安定して Semantic 抽出を実行できるようにする
- 派生データ（`user_semantic` / `item_semantic`）は `concept_code` 参照を基本とし、本テーブルは Rule 正本に限定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `semantic_rule` |
| 論理テーブル名 | Semantic Rule |
| 分類 | Semantic / Feature 定義系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | reco（User Semantic 抽出）、batch（Item Semantic 生成） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11 |

---

## 5. 用途・責務

- **`semantic_config_version_id` 単位**で抽出ルール行を保持する（行数は seed / 運用で可変）
- **`rule_type`** はルール適用方式（`keyword` / `phrase` / `pattern` / `llm`）。Semanticルール定義書 §6.1 / §17.1 正本
- **`source_text_pattern`** はキーワード・フレーズ・正規表現等のマッチパターン（Semanticルール定義書 §17.1 の `match_pattern` に相当）
- **`semantic_concept_id`** はマッチ時に付与する Concept の内部 PK（`semantic_concept` への物理 FK）
- **`weight`** はルール適用時の初期重み（Semanticルール定義書 §17.1 の `default_confidence` に相当。抽出結果の `confidence` 算出の入力）
- **`is_active = true`** の行のみ reco / batch が適用対象とする

### 5.1 semantic_config_version / semantic_concept との関係

| 観点 | `semantic_config_version` | `semantic_concept` | `semantic_rule`（本テーブル） |
| ---- | --------------------------- | -------------------- | ------------------------------- |
| 分類 | version ヘッダ | Concept 定義行 | 抽出ルール行 |
| 管理対象 | version ラベル・現行フラグ | `concept_code` / ラベル / 説明 | パターン・rule_type・重み |
| FK | — | `semantic_config_version_id`（ON） | `semantic_config_version_id`（ON）+ `semantic_concept_id`（ON） |
| Public API | `semanticConfigVersionId` | `semanticConcepts[]`（code のみ表面） | **非公開** |

> **version 内 Concept 整合（決定済み・§17.1 No.4）**: `semantic_concept_id` が同一 `semantic_config_version_id` に属することは **seed / reco 運用で担保**する。DB 上の複合 FK は **MVP では採用しない**。

### 5.2 API-PUB-007 非公開マッピング

| DB 列 | API 項目 | Public 公開 | 備考 |
| ----- | -------- | ----------- | ---- |
| `semantic_rule_id` | — | **非公開** | 内部 UUID |
| `semantic_config_version_id` | — | **非公開** | version は親スナップショット経由のみ |
| `rule_type` | — | **非公開** | 内部 Rule 方式 |
| `source_text_pattern` | — | **非公開** | API-PUB-007 §5.4 / §7.3.1 明示 |
| `semantic_concept_id` | — | **非公開** | 内部 UUID。表面は `conceptCode` のみ |
| `weight` | — | **非公開** | API-PUB-007 §7.3.1 明示 |
| `is_active` | — | **非公開** | 適用対象は reco 側で active のみ |

### 5.3 対象外

- Semantic 抽出**結果**（`user_semantic` / `item_semantic` / `semantic_extraction_result` 相当の責務）
- Hard Filter 候補（`hard_filter_candidate` の責務）
- Concept → Feature 補正ルール（`concept_feature_rule` / 各種 Feature Rule の責務）
- `input_type` / `source_type` の適用条件列（論理ER §10.2 未収載。`input_type_rule` または後続 Task で扱う — §17.1 No.2）
- Public API 応答への Rule 詳細露出（OpenAPI 同期は #469 へ委譲）

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `semantic_rule_id` | Semantic Rule ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK。Public API 非公開 |
| 2 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `yes` | — | — | 所属する意味定義 version。`semantic_config_version` を参照 |
| 3 | `rule_type` | Rule Type | `text` | `yes` | — | — | — | — | 抽出方式。`keyword` / `phrase` / `pattern` / `llm` |
| 4 | `source_text_pattern` | Source Text Pattern | `text` | `yes` | — | — | — | — | マッチパターン（キーワード・フレーズ・正規表現等） |
| 5 | `semantic_concept_id` | Semantic Concept ID | `uuid` | `yes` | — | `yes` | — | — | マッチ時の抽出先 Concept。`semantic_concept` を参照 |
| 6 | `weight` | Weight | `numeric(5,4)` | `yes` | — | — | — | `1.0000` | ルール適用時の初期重み（0.0000〜1.0000） |
| 7 | `is_active` | Active Flag | `boolean` | `yes` | — | — | — | `true` | 有効フラグ。`false` は適用対象外 |

> **論理ER との対応**: 論理ER §10.2 を MVP 物理テーブルの正とする。Semanticルール定義書 §17.1 の `match_pattern` → `source_text_pattern`、`default_confidence` → `weight`、`concept_code` → `semantic_concept_id` FK で表現する（#471 方針）。

> **論理ER との差分**: Semanticルール定義書 §17.1 の `input_type` / `source_type` は論理ER §10.2 に未収載。MVP 物理テーブルでは **非保持**（§17.1 No.2）。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `semantic_rule_id` | サロゲート UUID | |
| UNIQUE | `semantic_rule_id` | PK と同一 | — |
| UNIQUE | `semantic_config_version_id`, `rule_type`, `source_text_pattern`, `semantic_concept_id` | version 内で同一ルールの重複禁止 | Index 名: `uq_semantic_rule_version_type_pattern_concept` |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `semantic_config_version_id` | `semantic_config_version.semantic_config_version_id` | `ON` | RESTRICT | 物理ER §9 / semantic_config_version テーブル定義書 §8.1 |
| `semantic_concept_id` | `semantic_concept.semantic_concept_id` | `ON` | RESTRICT | semantic_concept テーブル定義書 §8.1。子 Rule 側 DDL |

### 8.1 被参照（論理）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `user_semantic` | `extracted_semantic_json` 内 concept 参照 | generates_with | `LOGICAL` | 派生は `concept_code` 参照を推奨（semantic_concept §8.2） |
| `item_semantic` | `semantic_json` 内 concept 参照 | generates_with | `LOGICAL` | batch 設計方針書の `semantic_concepts` 配列は code 参照 |

> 本テーブルは Rule 正本のため、派生テーブルからの物理 FK 被参照は想定しない。

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `semantic_rule_pkey` | `semantic_rule_id` | btree（PK） | 主キー | 自動生成 |
| `uq_semantic_rule_version_type_pattern_concept` | `semantic_config_version_id`, `rule_type`, `source_text_pattern`, `semantic_concept_id` | btree（unique） | ルール重複防止 | |
| `idx_semantic_rule_version_active` | `semantic_config_version_id`, `is_active` | btree | 現行 version の active ルール一覧 | reco / batch 適用時 |
| `idx_semantic_rule_concept_id` | `semantic_concept_id` | btree | Concept 単位の Rule 参照 | semantic_concept 子 FK 用 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `semantic_rule_pkey` | PRIMARY KEY | `semantic_rule_id` | 主キー | — |
| `uq_semantic_rule_version_type_pattern_concept` | UNIQUE | `semantic_config_version_id`, `rule_type`, `source_text_pattern`, `semantic_concept_id` | ルール一意 | |
| `chk_rule_type_mvp` | CHECK | `rule_type` | `rule_type IN ('keyword','phrase','pattern','llm')` | Semanticルール定義書 §17.1。`hybrid` は抽出結果側（§6.1） |
| `chk_source_text_pattern_length` | CHECK | `source_text_pattern` | `char_length(source_text_pattern) BETWEEN 1 AND 2000` | パターン上限（seed / 正規表現長さ） |
| `chk_weight_range` | CHECK | `weight` | `weight >= 0.0000 AND weight <= 1.0000` | 初期重み範囲 |

> `rule_type` の enum 正本化（packages/code-definitions）は後続 enum Task で検討する。MVP は **CHECK 4 値で足りる**（§17.1 No.1 決定済み）。

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `rule_type` | `rule_type` | Semanticルール定義書 §17.1 / §6.1 | `keyword` / `phrase` / `pattern` / `llm` | enum定義書未整備。本 Task で CHECK 候補値 |
| — | 状態 enum | なし | — | `is_active` は boolean |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | reco / batch | 現行 `semantic_config_version` + `is_active=true` | — | — | Rule Resolver がパターン一覧を取得 |
| INSERT | database（seed） | 新 version 初回投入 / ルール追加 | 全列 | version + type + pattern + concept で Upsert 想定 | YAML/JSON からの転記も可（§17.1 No.5） |
| UPDATE | database（運用） | 重み調整・無効化 | `weight`, `is_active` | — | **`source_text_pattern` / `rule_type` / `semantic_concept_id` 変更禁止**（新行 INSERT 推奨） |
| DELETE | — | MVP では原則禁止 | — | — | `is_active=false` で無効化 |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（設定正本。version 履歴として保持） |
| 削除方式 | 物理 DELETE 原則禁止 |
| 論理削除 | `is_active = false` |
| version 切替 | 新 `semantic_config_version` 作成時にルール行を新規 INSERT |
| 親 Concept 削除 | `semantic_concept` 参照中は RESTRICT（semantic_concept §13） |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `semantic_rule` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: `semantic_config_version` / `semantic_concept` / `feature_definition` 作成後、Rule 群の先頭（relationship_rule 等と同順） |
| rollback方針 | forward migration 主体 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | reco / batch（service role） |
| 書き込み権限 | database seed / 運用のみ |
| Public API | **非公開**（API-PUB-007 / 008 に Rule 詳細を含めない） |
| ログ出力制限 | `source_text_pattern` / 重みを過剰ログ出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / CHECK / FK | migration |
| 2 | rule_type CHECK | 許容外 type が拒否される | migration |
| 3 | UNIQUE | 同一 version で同一 pattern + concept の重複 INSERT が拒否される | migration |
| 4 | FK | 存在しない `semantic_concept_id` 参照が拒否される | migration |
| 5 | weight CHECK | 範囲外 weight が拒否される | migration |
| 6 | Resolver 整合 | active ルールが reco Semantic Rule Resolver で読み込める | integration |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review にて No.1〜No.6 を決定済み（§17.1 参照） |

### 17.1 Human Review 決定事項（Task #472）

| No | 論点 | 決定内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | `rule_type` enum 正本化 | MVP は **CHECK 4 値**（`keyword` / `phrase` / `pattern` / `llm`）。`hybrid` は抽出結果 `extraction_method` 側。packages 正本化は後続 enum Task | Human | Semanticルール定義書 §6.1 |
| 2 | `input_type` / `source_type` 列 | MVP は論理ER §10.2 どおり **非保持**。適用条件は `input_type_rule` または Resolver 側ロジック | Human | Semanticルール定義書 §17.1 vs 論理ER |
| 3 | `source_text_pattern` 命名 | 論理ER §10.2 の **`source_text_pattern` を物理名正**とする（`match_pattern` はドメイン論理名） | Human | API-PUB-007 非公開列名と一致 |
| 4 | version 内 Concept 整合 | `semantic_concept_id` が同一 `semantic_config_version_id` に属することを **seed / reco で担保**。複合 FK は **MVP 見送り** | Human | semantic_concept §8.2 方針と整合 |
| 5 | Rule 実装形式 | Semanticルール定義書 §17.4 どおり **YAML/JSON + seed + LLM 補助** を採用。DB テーブルは正本の一形式 | Human | seed Task で具体化 |
| 6 | `weight` 既定値 | MVP は **`1.0000` 既定**。ルール優先度差は seed で調整 | Human | `default_confidence` 相当 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8–§11 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §10.2 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §8 No.36 |
| Semanticルール定義書 | `docs/04_ドメインモデル設計/Semanticルール定義書.md` | §6.1 / §17.1 / §17.4 |
| Featureルール定義書 | `docs/04_ドメインモデル設計/Featureルール定義書.md` | Semantic Rule と Feature Rule の責務分離 |
| API契約 | `docs/06_実装設計/api/API-PUB-007_Semantic設定取得API契約仕様書.md` | 非公開境界 |
| 親テーブル | `docs/06_実装設計/database/semantic_config_version_テーブル定義書.md` | FK / §8.1 被参照 |
| 参照先 Concept | `docs/06_実装設計/database/semantic_concept_テーブル定義書.md` | semantic_concept_id FK / §8.1 |
| 兄弟テーブル | `docs/06_実装設計/database/feature_definition_テーブル定義書.md` | Wave2 章構成参考 |
| 先行 Task | Issue #462 / #463 / #470 / #471 | semantic_config / version / feature_definition / semantic_concept |

---

## 19. レビュー観点

- 論理ER §10.2・物理ER §8–§11・テーブル一覧 §8 と矛盾していない
- semantic_config_version / semantic_concept テーブル定義書 §8.1 との FK（ON / RESTRICT）が明記されている
- API-PUB-007 非公開列（`source_text_pattern` / `weight` / 内部 PK）が明確
- Semanticルール定義書 §17.1 との論理名・物理名対応が整理されている
- feature_definition / semantic_concept テーブル定義書と章構成・MVP 方針が一貫している
- `input_type` / `source_type` の非保持方針（§17.1 No.2）が決定・明示されている
- `source_text_pattern` 物理名・version 内 Concept 整合・Rule 実装形式・`weight` 既定が §17.1 に決定されている
- DDL Task が CREATE TABLE を起こせる粒度である
