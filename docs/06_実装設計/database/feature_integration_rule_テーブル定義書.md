# Feature Integration Rule テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                   |
| -------------- | -------------------------------------- |
| ドキュメントID | `DB-TBL-partial-feature_integration_rule` |
| ドキュメント名 | Feature Integration Rule テーブル定義書 |
| 対象システム   | Gift Recommendation Service MVP        |
| MVP対象        | `partial`                              |
| 作成日         | 2026-06-11                             |
| 更新日         | 2026-06-11                             |

---

## 2. 概要

`feature_integration_rule` は、User Feature 生成時に **複数の Feature 入力**（Relationship / Occasion 基準値、Pair 補正、Concept 由来 Delta 等）を **1 つの `user_feature_raw` に統合する重み（weight）** を、`semantic_config_version` 単位で保持する Semantic / Feature 定義系テーブルである。

Featureルール定義書 §12・§18.1 の Feature Integration を物理化する。**Public API では返却しない**（API-PUB-007 / API-PUB-008 非公開）。物理ER・テーブル一覧では **MVP partial（△）** とし、DDL 作成要否は Human Review で確定する。

---

## 3. 目的

- Feature 8 軸ごとに、統合対象入力（§12.1）への **重み係数** を version 管理する（Featureルール定義書 §12.3）
- reco が User Feature 生成時（§18.1）に `relationship_rule` / `occasion_rule` / `pair_rule` / `concept_feature_rule` の出力を統合する際の係数を参照できるようにする
- MVP partial 採用時でも、後続 DDL Task が CREATE TABLE を起こせる物理スキーマを確定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `feature_integration_rule` |
| 論理テーブル名 | Feature Integration Rule |
| 分類 | Semantic / Feature 定義系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | reco（User Feature 生成時の統合係数参照） |
| MVP対象 | `partial`（テーブル一覧 △・物理ER §8 partial） |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11 |

---

## 5. 用途・責務

- **`semantic_config_version_id` 単位**で、Feature 1 軸 × 統合入力 1 種別 = **1 行**を保持する（正規化行モデル）
- **`input_source`** は Featureルール定義書 §12.1 の統合対象に対応する（`relationship_feature` / `occasion_feature` / `pair_delta` / `preferred_delta` / `avoid_delta` / `free_text_delta`）
- **`weight`** は §12.3 の初期重みを正本とする。reco は §12.2 の統合式に従い各入力に `weight` を乗算する
- **`is_active = true`** の行のみ reco が参照する
- 統合式本体（`weighted_average` / `sigmoid_normalize` 等）は **reco 実装の責務**。本テーブルは **係数の設定正本** に限定する

### 5.1 統合式との対応（Featureルール定義書 §12.2）

| 統合段階 | 式（要約） | 本テーブルが保持する係数 |
| -------- | ---------- | ------------------------ |
| external | `weighted_average(relationship_feature, occasion_feature) + pair_delta` | `relationship_feature` / `occasion_feature` の weight、`pair_delta` の weight |
| internal | `preferred_delta + avoid_delta + free_text_delta` | 各 Delta 入力の weight |
| 合成 | `user_feature_raw = external + internal` | reco が上記係数適用後に加算（式はコード側） |
| 正規化 | `user_feature_normalized = sigmoid_normalize(user_feature_raw)` | 本テーブル対象外（`feature_normalization_version` の責務） |

> §12.4 の `confidence` 乗算は Concept 抽出結果に対する reco 実行時補正であり、本テーブルでは保持しない。

### 5.2 関連テーブルとの関係

| 観点 | 参照先 | 本テーブルとの関係 |
| ---- | ------ | ------------------ |
| version ヘッダ | `semantic_config_version` | `semantic_config_version_id` で所属 version を特定（物理 FK ON） |
| Feature 軸 | `feature_definition` | 同一 version 内の `feature_code` と整合。MVP 8 軸 CHECK |
| Relationship 基準値 | `relationship_rule` | 統合入力 `relationship_feature` の元データ |
| Occasion 基準値 | `occasion_rule` | 統合入力 `occasion_feature` の元データ |
| Pair 補正 | `pair_rule` | 統合入力 `pair_delta` の元データ |
| Concept 補正 | `concept_feature_rule` | 統合入力 `preferred_delta` / `avoid_delta` / `free_text_delta` の元データ |

### 5.3 Public API 非公開方針

| API | 方針 | 根拠 |
| --- | ---- | ---- |
| API-PUB-007 | `feature_integration_rule` 行・重みを応答に含めない | 内部 Rule 非公開 |
| API-PUB-008 | `feature_integration_rule` は返却しない Rule 種別 | 契約仕様書 §7.3.1 |

> 統合係数は Reco 内部完結。`weight` および `input_source` は Public 表面に露出しない。

### 5.4 対象外

- 各 Rule テーブル自体の定義（`relationship_rule` / `occasion_rule` / `pair_rule` / `concept_feature_rule` の責務）
- 統合式・正規化アルゴリズムの実装（reco の責務）
- `input_type_rule` の入力種別適用詳細
- User Feature 生成結果（`user_feature` の責務）
- Item Feature 統合（Item 側は Concept Feature Rule 中心。§18.2）

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `feature_integration_rule_id` | Feature Integration Rule ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK |
| 2 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `yes` | — | — | 所属する意味定義 version。`semantic_config_version` を参照 |
| 3 | `feature_code` | Feature Code | `text` | `yes` | — | — | — | — | MVP 8 軸コード。enum定義書 §6.16 正本 |
| 4 | `input_source` | Integration Input Source | `text` | `yes` | — | — | — | — | 統合対象入力種別（§12.1）。§11 許容値 |
| 5 | `weight` | Integration Weight | `numeric(4,3)` | `yes` | — | — | — | — | 統合重み係数。§12.3 初期値を seed 正本とする |
| 6 | `is_active` | Active Flag | `boolean` | `yes` | — | — | — | `true` | 有効フラグ。`false` は reco 参照対象外 |

> **論理ER / Featureルール定義書との差分**: 論理ER §10.2 には抽象エンティティ `feature_rule` が列挙され、Featureルール定義書 §16.1 では `integration_rule` を semantic_config_version 管理対象として列挙するが、§17 には個別論理項目表がない。物理テーブルでは `feature_integration_rule` へ **分解**し（物理ER §5 No.5・テーブル一覧 §8）、§12.3 の重みを **行モデル** で保持する。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `feature_integration_rule_id` | サロゲート UUID | |
| UNIQUE | `feature_integration_rule_id` | PK と同一 | — |
| UNIQUE | `semantic_config_version_id`, `feature_code`, `input_source` | version 内で Feature 軸 × 入力種別は 1 行 | Index 名: `uq_feature_integration_rule_version_feature_source` |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `semantic_config_version_id` | `semantic_config_version.semantic_config_version_id` | `ON` | RESTRICT | 物理ER §9 / semantic_config_version §8.1（contains） |

### 8.1 論理参照（MVP 初期 DDL）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `feature_code` | `feature_definition.feature_code`（同一 `semantic_config_version_id`） | `LOGICAL` | CHECK + seed | version 内 8 軸存在は seed / アプリ validation で担保 |

> `feature_definition` への物理 FK は version 内 code 参照のため MVP では付与しない（relationship_rule と同型）。

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `feature_integration_rule_pkey` | `feature_integration_rule_id` | btree（PK） | 主キー | 自動生成 |
| `uq_feature_integration_rule_version_feature_source` | `semantic_config_version_id`, `feature_code`, `input_source` | btree（unique） | version 内 Rule 一意 | §7 と同一 |
| `idx_feature_integration_rule_version_feature_active_lookup` | `semantic_config_version_id`, `feature_code`, `is_active`, `input_source` | btree | reco 統合係数 Lookup | Run 解決済み version + feature で 6 入力分を参照 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `feature_integration_rule_pkey` | PRIMARY KEY | `feature_integration_rule_id` | 主キー | — |
| `uq_feature_integration_rule_version_feature_source` | UNIQUE | `semantic_config_version_id`, `feature_code`, `input_source` | version 内一意 | |
| `fk_feature_integration_rule_semantic_config_version` | FOREIGN KEY | `semantic_config_version_id` | `semantic_config_version` ON DELETE RESTRICT | semantic_config_version §8.1 |
| `chk_feature_code_mvp` | CHECK | `feature_code` | MVP 8 軸 IN 句 | feature_definition / 物理ER §11 と同一 |
| `chk_input_source_mvp` | CHECK | `input_source` | §11 許容値 IN 句 | Featureルール定義書 §12.1 対応 |
| `chk_weight_range` | CHECK | `weight` | `weight >= 0.0 AND weight <= 2.0` | §12.3 初期値（最大 1.0）を包含。将来調整余地 |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `feature_code` | `feature_code` | enum定義書 §6.16 | MVP 8 値 | 物理ER §11 |
| `input_source` | `integration_input_source` | Featureルール定義書 §12.1 | `relationship_feature` / `occasion_feature` / `pair_delta` / `preferred_delta` / `avoid_delta` / `free_text_delta` | MVP 6 値固定。enum定義書未整備のため CHECK で担保 |
| `weight` | — | Featureルール定義書 §12.3 | 0.0〜2.0（CHECK） | MVP 初期 seed は §12.3 の値 |

### 11.1 MVP 初期重み（seed 正本・Featureルール定義書 §12.3）

| `input_source` | MVP 初期 `weight` | 適用対象 Feature 軸 |
| -------------- | ----------------: | ------------------- |
| `relationship_feature` | 0.500 | 8 軸共通（軸ごとに同一初期値） |
| `occasion_feature` | 0.500 | 8 軸共通 |
| `pair_delta` | 1.000 | 8 軸共通 |
| `preferred_delta` | 1.000 | 8 軸共通 |
| `avoid_delta` | 1.000 | 8 軸共通 |
| `free_text_delta` | 0.700 | 8 軸共通 |

> MVP では軸別に重みを変えない（48 行 / version = 8 feature × 6 input_source）。軸別チューニングは post-MVP 運用で `weight` UPDATE または新 version INSERT で対応する。

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | reco | User Feature 生成時。`semantic_config_version_id` + `feature_code` + `is_active=true` | — | — | 6 `input_source` 分の `weight` を取得し §12.2 を適用 |
| SELECT | reco | 該当行なし | — | — | §12.3 初期値をコード側フォールバックとするかは reco 実装 Task の論点（DB 未作成時） |
| INSERT | database（seed） | 新 version 初回投入 | 全列 | version ごと Upsert | 8 軸 × 6 入力 = 48 行 |
| UPDATE | database（運用） | 重みチューニング・無効化 | `weight`, `is_active` | — | **`feature_code` / `input_source` 変更禁止**（新 version INSERT 推奨） |
| DELETE | — | MVP では原則禁止 | — | — | `is_active=false` で無効化 |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（設定正本。version 履歴として保持） |
| 削除方式 | 物理 DELETE 原則禁止 |
| 論理削除 | `is_active = false` |
| version 切替 | 新 `semantic_config_version` 作成時に 48 行を新規 INSERT |
| partial 未作成時 | reco が §12.3 定数で統合する場合、本テーブルは参照されない（二重管理リスクは §17 で整理） |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `feature_integration_rule` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: `semantic_config_version`・`feature_definition` 作成後、Rule 群の一部として適用。**MVP partial のため DDL Task でスキップ可** |
| rollback方針 | forward migration 主体 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | reco（service role）のみ。api は Public 返却しないため直接参照不要 |
| 書き込み権限 | database seed / 運用のみ |
| Public API | **非公開**。API-PUB-007 / API-PUB-008 応答に統合係数を含めない |
| ログ出力制限 | 統合係数を過剰ログ出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / FK / CHECK が定義どおり（partial 採用時） | migration |
| 2 | UNIQUE | 同一 version で同一 feature × input_source の重複 INSERT が拒否される | migration |
| 3 | input_source CHECK | 許容外 `input_source` が拒否される | migration |
| 4 | weight CHECK | `weight` が 0.0〜2.0 外で拒否される | migration |
| 5 | reco 参照 | version + feature で active 6 行が取得され §12.2 に適用される | integration |
| 6 | Public API | API-PUB-007 / API-PUB-008 が `feature_integration_rule` を返却しない | contract |
| 7 | seed 整合 | §12.3 初期重み 48 行が seed に存在（partial 採用時） | manual |
| 8 | partial 未作成 | DDL スキップ時に reco 定数フォールバックが §12.3 と一致 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | MVP で物理テーブルを作成するか | テーブル一覧 △・物理ER partial。Featureルール定義書 §17.6 は YAML/JSON も許容 | Human | DDL Task 前 | DDL Task / reco 実装と連動 |
| 2 | DB 未作成時の reco フォールバック | partial スキップ時に §12.3 定数をコード側で保持する必要 | Human | reco 実装 Task 前 | 二重管理回避方針 |
| 3 | 軸別重みチューニング | MVP は 8 軸同一重み。post-MVP で軸別化するか | Human | 運用設計時 | seed 設計へ引き継ぎ |

### 17.1 MVP partial 採用方針（docs Task 時点の整理）

| 観点 | 本定義書の整理 | Human 判断待ち |
| ---- | -------------- | -------------- |
| 物理 DDL | **スキーマ定義は本書で確定**。MVP migration への含否は partial | **要判断**（テーブル一覧 △） |
| 設定正本 | DB 採用時は本テーブル。未採用時は reco 定数 / YAML（§17.6） | **要判断** |
| Public API | **非公開**（確定） | — |
| `semantic_config_version_id` FK | **物理 FK ON**（relationship_rule と同型） | — |
| 行モデル | **version × feature_code × input_source**（48 行 / version） | — |

### 17.2 Human Review 決定事項（踏襲・提案）

| No | 論点 | 提案内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | `semantic_config_version_id` FK | **物理 FK ON**、ON DELETE RESTRICT | Human | relationship_rule / pair_rule と同型 |
| 2 | version 内 UNIQUE | **採用**。`(semantic_config_version_id, feature_code, input_source)` | Human | 1 軸 × 1 入力 = 1 重み |
| 3 | `input_source` 許容値 | **MVP 6 値固定**（§12.1 対応） | Human | CHECK で担保 |
| 4 | `weight` 値域 | **0.0〜2.0**（§12.3 を包含） | Human | |
| 5 | Public API | **非公開**（API-PUB-007 / API-PUB-008） | Human | Reco 内部完結 |
| 6 | MVP DDL | **partial のため DDL Task でスキップ可**。スキップ時は reco 定数正本 | Human | テーブル一覧 △ |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8–§11・partial 方針 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §10.2（抽象 feature_rule 分解） |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §8 No.42 MVP partial |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | §6.16 feature_code |
| Featureルール | `docs/04_ドメインモデル設計/Featureルール定義書.md` | §12 / §16.1 / §17.6 / §18.1 |
| API契約 | `docs/06_実装設計/api/API-PUB-007_Semantic設定取得API契約仕様書.md` | 内部 Rule 非公開 |
| API契約 | `docs/06_実装設計/api/API-PUB-008_Featureルール取得API契約仕様書.md` | feature_integration_rule 非公開 |
| 先行テーブル | `docs/06_実装設計/database/semantic_config_version_テーブル定義書.md` | 親 FK |
| 先行テーブル | `docs/06_実装設計/database/feature_definition_テーブル定義書.md` | feature_code |
| 参考 Rule | `docs/06_実装設計/database/relationship_rule_テーブル定義書.md` | Rule 系章構成・CHECK 方針 |
| 参考 Rule | `docs/06_実装設計/database/pair_rule_テーブル定義書.md` | 内部 Rule 非公開・version 管理 |
| 先行 Task | Issue #462 / #463 / #470 / #473 / #474 / #475 | Wave1 + Wave2 Rule 群 |

---

## 19. レビュー観点

- 論理ER §10.2（抽象 `feature_rule` 分解）・物理ER §8–§11・テーブル一覧 §8 No.42 と矛盾していない
- Featureルール定義書 §12.1 / §12.2 / §12.3 の統合対象・式・初期重みが物理カラムとして整理されている
- `semantic_config_version_id` FK（物理 ON）および `feature_code` の LOGICAL 参照方針が明記されている
- MVP partial 採用方針が §17 に明記されている
- API-PUB-007 / API-PUB-008 に基づく Public API 非公開が明記されている
- relationship_rule / pair_rule テーブル定義書と Rule 系方針（UNIQUE / is_active / version 管理）が一貫している
- OpenAPI / generated 変更が含まれていない（#469 委譲）
- DDL Task が CREATE TABLE を起こせる粒度である（partial 採用時）
- secret や `.env` 実値が含まれていない
