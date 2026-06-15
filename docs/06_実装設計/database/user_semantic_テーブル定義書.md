# User Semantic テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                            |
| -------------- | ------------------------------- |
| ドキュメントID | `DB-TBL-MVP-user_semantic`      |
| ドキュメント名 | User Semantic テーブル定義書    |
| 対象システム   | Gift Recommendation Service MVP |
| MVP対象        | `yes`                           |
| 作成日         | 2026-06-15                      |
| 更新日         | 2026-06-15                      |

---

## 2. 概要

`user_semantic` は、Online 推薦時に reco（`MOD-RECO-004` User Semantic Extractor）がユーザー入力から抽出した **Semantic Concept 派生データ** を保持する User 意味推定系テーブルである。

`recommendation_run_id` を親キーとし、抽出時に参照した `semantic_config_version_id` を行に固定して `extracted_semantic_json`（Concept 抽出結果）を保存する。テーブル一覧 §4 補足どおり **Run 単位**で保持し、Batch は更新しない（論理ER §16.2）。

---

## 3. 目的

- `recommendation_request` の好み条件・避けたい条件・NG 条件・自由記述等から抽出した Semantic Concept を DB 上の派生正本として保持する
- `semantic_config_version_id` を行に固定し、Rule / Concept 定義 version 変更後も **再現性** を担保する
- `user_feature` / `user_meaning` 生成（後続 reco モジュール）の入力正本として後続 Task / reco が参照できる粒度を提供する
- `item_semantic`（Item 側 Semantic 派生）との **対称関係と差分**を明示し、後続 DDL Task が migration を作成できる粒度まで物理定義を確定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `user_semantic` |
| 論理テーブル名 | User Semantic |
| 分類 | User意味推定系 |
| 正本区分 | 派生 |
| 主な更新主体 | reco（Online 推薦パイプライン） |
| 主な参照主体 | reco（`MOD-RECO-005` / `MOD-RECO-006` User Feature 生成、`user_meaning` 射影等） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §4.1・§9・§10 |

---

## 5. 用途・責務

- **MOD-RECO-004（User Semantic Extractor）** の DB 保存先（機能×モジュール対応表・インターフェース一覧 IF-DB-RECO-003）
- `recommendation_request` の入力テキスト（`preferred_text` / `non_preferred_text` / `ng_text` 等）と `relationship_code` / `occasion_code` 文脈を入力に Semantic Concept を抽出し、結果を `extracted_semantic_json` に格納する
- **Run 単位保存**（テーブル一覧 §4 補足）。同一 `recommendation_run_id` に対し MVP では **1 行**を基本とする
- **version スナップショット**: Run 開始時に解決済みの `semantic_config_version_id`（`recommendation_run.semantic_config_version_id` と整合）を行に保持し、後から `is_current` が切替わっても当該行の意味は不変
- api は直接 DML しない（認証・認可方針書 §9.3）。作成は reco のみ

### 5.1 対象外

- User Feature / User Meaning の生成結果（別 Task / 別テーブル）
- `recommendation_request` / `recommendation_run` 本体（親 Request / Run 正本は別定義書）
- `phase_log` / `api_call_log` 本体（LLM 呼び出し Log は別テーブル。本テーブルは **構造化抽出結果** の正本）
- batch による INSERT / UPDATE / DELETE
- DDL / migration 本体（DDL Task へ委譲）
- OpenAPI / generated 変更（Epic 終盤 Task #469 へ委譲）

### 5.2 Online / Batch 責務境界

| 主体 | 許可操作 | 禁止 |
| ---- | -------- | ---- |
| reco（Online 推薦） | INSERT（Run 内 1 回。§12.2） | UPDATE / DELETE（MVP） |
| batch | — | 本テーブルへの一切の DML |
| api | — | 直接参照・DML なし（MVP） |
| Online 推薦中 | **本テーブルを reco が生成する** | batch による更新 |

> 論理ER §16.1 の「Online 推薦中に更新しない」一覧は **Batch 所有テーブル**向け。`user_semantic` は reco が Online 中に **新規 INSERT** する派生データであり、一覧未列挙は意図的（Item 側 `item_semantic` が batch 更新・reco 参照のみであるのと対称）。

### 5.3 `extracted_semantic_json` 保持方針

Semanticルール定義書 §3.1・§7・§11・§14 を正本とする。`semantic_config_version_id` は **列で保持**し、JSON 内には重複保存しない。

| キー | 必須 | 型 | 説明 |
| ---- | ---- | -- | ---- |
| `concepts` | ○ | array | 抽出 Concept の配列（0 件以上） |
| `concepts[].concept_code` | ○ | string | `semantic_concept.concept_code` と同一命名（snake_case） |
| `concepts[].confidence` | ○ | number | 0.0〜1.0。Semanticルール定義書 §9 |
| `concepts[].input_intent` | ○ | string | User 側は `prefer` / `avoid` / `neutral` / `ng_candidate`（§7.1） |
| `concepts[].assertion_polarity` | △ | string | MVP は `asserted` 固定可 |
| `concepts[].extraction_method` | ○ | string | `keyword` / `phrase` / `pattern` / `llm` / `hybrid` |
| `concepts[].source_type` | ○ | string | `preferred_condition` / `non_preferred_condition` / `ng_condition` / `free_text` / `user_input` 等 |
| `concepts[].evidence_texts` | △ | string[] | 根拠テキスト（複数可） |

**JSON 例**

```json
{
  "concepts": [
    {
      "concept_code": "formal_refined",
      "confidence": 0.88,
      "input_intent": "prefer",
      "assertion_polarity": "asserted",
      "extraction_method": "phrase",
      "source_type": "preferred_condition",
      "evidence_texts": ["上品で落ち着いたもの"]
    },
    {
      "concept_code": "too_casual",
      "confidence": 0.75,
      "input_intent": "avoid",
      "assertion_polarity": "asserted",
      "extraction_method": "keyword",
      "source_type": "non_preferred_condition",
      "evidence_texts": ["カジュアルすぎる"]
    }
  ]
}
```

| 観点 | 方針 |
| ---- | ---- |
| Concept 参照 | JSON 内は **`concept_code` 参照**（`semantic_concept_id` への物理 FK は張らない） |
| version 内 valid 性 | 抽出時、当該 `semantic_config_version_id` かつ `is_active = true` の Concept のみ出力 |
| 重複 Concept | 同一 `concept_code` は **confidence 最大値で統合**（Semanticルール定義書 §14.2） |
| 採用閾値 | MVP は `confidence >= 0.60` を通常採用ライン（Semanticルール定義書 §9.4） |
| Public API | 本テーブル / `extracted_semantic_json` は **Public 非公開**（内部派生データ） |

### 5.4 `item_semantic` との対称関係・差分

| 観点 | `item_semantic`（#513 正本） | `user_semantic`（本定義） |
| ---- | ---------------------------- | ------------------------- |
| 分類 | Item派生データ系 | User意味推定系 |
| 親キー | `item_id` | `recommendation_run_id` |
| JSON 列名 | `semantic_json` | `extracted_semantic_json`（論理ER §10.2 準拠） |
| 更新主体 | batch（BATCH-010） | reco（MOD-RECO-004） |
| 実行環境 | Batch 事前生成 | Online 推薦時生成 |
| 保存単位 | `item_id` + `semantic_config_version_id` | `recommendation_run_id`（§7） |
| `semantic_config_version_id` FK | **物理 FK ON** | **LOGICAL**（Index のみ。§8.1） |
| reco 操作 | SELECT のみ | INSERT（生成主体） |
| 入力 | 商品属性・説明文 | Request テキスト・関係・シーン文脈 |
| `input_intent` 典型 | `neutral`（Item） | `prefer` / `avoid` / `ng_candidate`（User） |
| `source_type` 典型 | `item_name` / `item_description` 等 | `preferred_condition` / `non_preferred_condition` 等 |

**共通方針**

- `concepts[]` 配列スキーマ・`concept_code` 参照・confidence 値域・version 行スナップショットは **同型**
- `semantic_config_version` / `semantic_concept` / `semantic_rule` との LOGICAL 参照方針は **同型**

### 5.5 `semantic_config_version_id` 紐づけ方針

| 観点 | 方針 |
| ---- | ---- |
| 解決タイミング | **Run 開始時**に reco が Config Resolver で解決し、`recommendation_run.semantic_config_version_id` に固定（`recommendation_run_テーブル定義書` §8.1） |
| 行への固定 | 抽出完了時、Run と **同一の** `semantic_config_version_id` を本行へ保存（再現性・監査用の明示コピー） |
| Run との関係 | 通常は `user_semantic.semantic_config_version_id = recommendation_run.semantic_config_version_id`。不一致は **実装バグ**として扱う |
| `item_semantic` との差分 | Item 側は BATCH-010 実行時に独立解決 + **物理 FK ON**。User 側は Run 固定 version を継承 + **LOGICAL FK**（`semantic_config_version_テーブル定義書` §8.2・`item_semantic_テーブル定義書` §17.1 No.1 注記） |
| `user_feature` 連携 | 後続 Task で同一 `recommendation_run_id` / `semantic_config_version_id` を参照して Feature 生成 |

### 5.6 MOD-RECO-004 / IF-DB-RECO-003 入出力

| 方向 | 内容 |
| ---- | ---- |
| 入力 | `recommendation_run_id`、`recommendation_request`（preferred / non_preferred / ng / free text）、`relationship_code` / `occasion_code`、`semantic_config_version_id`（Run から）、`semantic_rule` / `semantic_concept`（LOGICAL 参照） |
| 出力 | 本テーブルへの INSERT（IF-DB-RECO-003）。`semantic_extraction_result` 相当の構造化データ |
| モジュール | `MOD-RECO-004` User Semantic Extractor |
| タイミング | Online 推薦パイプラインの Semantic 抽出フェーズ（処理構成定義書・処理フロー概要図） |

> IF-DB-RECO-003 は `user_semantic` / `user_feature` / `user_meaning` をまとめて記載するが、**本テーブルは User Semantic 行のみ**を責務とする。Feature / Meaning は別テーブル Task。

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `user_semantic_id` | User Semantic ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | 派生行 ID |
| 2 | `recommendation_run_id` | Recommendation Run ID | `uuid` | `yes` | — | `ON` | `yes` | — | 親 Run。`recommendation_run.recommendation_run_id` 参照 |
| 3 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `LOGICAL` | — | — | 抽出時に利用した意味定義 version（Run 固定値と整合） |
| 4 | `extracted_semantic_json` | Extracted Semantic JSON | `jsonb` | `yes` | — | — | — | — | Concept 抽出結果（§5.3） |
| 5 | `generated_at` | Generated At | `timestamptz` | `yes` | — | — | — | — | 抽出完了日時（UTC） |

> 論理ER §10.2 の属性（`user_semantic_id` / `recommendation_run_id` / `semantic_config_version_id` / `extracted_semantic_json` / `generated_at`）と一致。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `user_semantic_id` | サロゲート UUID | — |
| UNIQUE | `recommendation_run_id` | **1 Run あたり 1 行**（MVP） | テーブル一覧 §4 補足「保存単位 recommendation_run_id」 |

**履歴方針**: MVP では Run 再実行は **新規 `recommendation_run` 行**として扱い、本テーブルも新 Run に紐づく新行を INSERT する。同一 Run 内の再抽出は **行を UPDATE しない**（失敗時は Run 失敗扱い・再 Run は新行）。

> 物理ER §9 は `generates` 1:N と記載するが、MVP は UNIQUE(`recommendation_run_id`) で実質 1:1 に制約。将来の複数抽出行が必要になった場合は UNIQUE 見直しを別 Task 化する（§17.1 No.2）。

---

## 8. 外部キー・参照関係

### 8.1 参照先（本テーブルから）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `recommendation_run_id` | `recommendation_run.recommendation_run_id` | `ON` | `ON DELETE RESTRICT` | `recommendation_run_テーブル定義書` §8.2 と同型 |
| `semantic_config_version_id` | `semantic_config_version.semantic_config_version_id` | `LOGICAL` | reco INSERT 前に存在確認 + Index | §17.1 No.1 提案。`item_semantic` は ON |

### 8.2 被参照

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `user_feature`（後続 Task） | `recommendation_run_id` | input | `LOGICAL` / 部分 `ON` | Feature 生成入力。別 Task で確定 |
| reco | `recommendation_run_id` 経由 SELECT | reads | アプリ層 | User Feature / Meaning 生成 |
| `semantic_concept` | `extracted_semantic_json` 内 `concept_code` | generates_with | `LOGICAL` | `concept_code` + 行の `semantic_config_version_id` で特定 |
| `semantic_rule` | 間接（MOD-RECO-004 実行） | applied_by | アプリ層 | Rule 正本は `semantic_rule` テーブル |

### 8.3 `recommendation_run` との生成経路

```text
recommendation_request（入力テキスト正本）
    ↓ executes
recommendation_run INSERT（semantic_config_version_id 固定）
    ↓ Online 推薦パイプライン
MOD-RECO-004: User Semantic Extractor
    ↓ semantic_rule / semantic_concept（LOGICAL）
    ↓ extracted_semantic_json 組み立て
IF-DB-RECO-003: INSERT user_semantic（recommendation_run_id）
    ↓
MOD-RECO-005/006: user_feature 生成（後続）
    ↓
user_meaning 射影（後続 Task）
```

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `user_semantic_pkey` | `user_semantic_id` | btree（PK） | 主キー | 自動生成 |
| `uq_user_semantic_recommendation_run_id` | `recommendation_run_id` | btree（unique） | Run 単位 1 行・冪等 INSERT | §7 |
| `idx_user_semantic_version_id` | `semantic_config_version_id` | btree | version 単位参照・監査 | LOGICAL FK 整合 |
| `idx_user_semantic_generated_at` | `generated_at` DESC | btree | 時系列調査 | MVP 推奨 |

> 物理ER §10 には `user_semantic` 専用 Index 行が未記載。本 Task で上記を確定し、Epic 横断で物理ER §10 追記を別 Task 化する。

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `user_semantic_pkey` | PRIMARY KEY | `user_semantic_id` | 主キー | — |
| `uq_user_semantic_recommendation_run_id` | UNIQUE | `recommendation_run_id` | Run 単位 1 行 | §7 |
| `fk_user_semantic_recommendation_run_id` | FOREIGN KEY | `recommendation_run_id` | `recommendation_run(recommendation_run_id)` ON DELETE RESTRICT | §8.1 |
| `chk_extracted_semantic_json_object` | CHECK | `extracted_semantic_json` | `jsonb_typeof(extracted_semantic_json) = 'object'` | — |
| `chk_extracted_semantic_json_concepts_array` | CHECK | `extracted_semantic_json` | `jsonb_typeof(extracted_semantic_json -> 'concepts') = 'array'` | §5.3 |

> `semantic_config_version_id` への物理 FK 制約は MVP では **付与しない**（LOGICAL + Index）。`concept_code` 個別値の CHECK はアプリ層 + seed 整合に委ねる。

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| — | — | なし | — | 状態カラムなし |

`extracted_semantic_json` 内の `extraction_method` / `source_type` / `input_intent` は Semanticルール定義書・enum Task 横断の code 値を使用する。

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| INSERT | reco（MOD-RECO-004） | §12.1 生成条件 | 全列（初回） | `recommendation_run_id` UNIQUE | §12.2 |
| SELECT | reco | `recommendation_run_id` 指定 | — | — | Feature / Meaning 生成 |
| UPDATE | reco / batch / api | — | — | **MVP 禁止** | 再抽出は新 Run |
| DELETE | — | — | — | **MVP 禁止** | §13 |
| INSERT / UPDATE / DELETE | batch | — | — | **禁止** | §5.2 |

### 12.1 MOD-RECO-004 生成条件

```text
1. recommendation_run が作成済み（run_status が進行可能状態）
2. recommendation_run.semantic_config_version_id が解決済み
3. recommendation_request から入力テキスト・関係・シーンを取得
4. semantic_rule / semantic_concept（当該 version）を参照して Concept 抽出
5. extracted_semantic_json を組み立て（§5.3）
6. 同一 recommendation_run_id の行が未存在であること（UNIQUE）
7. INSERT user_semantic（IF-DB-RECO-003）
8. phase_log に Semantic 抽出フェーズ完了を記録（phase_log 定義書。別テーブル）
```

**0 件 Concept**

| 条件 | 動作 |
| ---- | ---- |
| 入力テキストから閾値以上の Concept が 0 件 | `concepts: []` の行を **INSERT してよい**（Hard Filter / Feature 生成の「入力なし」判定用） |

### 12.2 INSERT 疑似 SQL

```sql
INSERT INTO user_semantic (
  recommendation_run_id,
  semantic_config_version_id,
  extracted_semantic_json,
  generated_at
) VALUES (
  :recommendation_run_id,
  :semantic_config_version_id,
  :extracted_semantic_json::jsonb,
  now()
);
```

| 観点 | 方針 |
| ---- | ---- |
| 冪等キー | `uq_user_semantic_recommendation_run_id`（§7） |
| 衝突時 | 同一 Run への 2 回目 INSERT は **エラー**（アプリ層で事前チェックまたは UNIQUE violation を Run 失敗へ） |
| version 列 | `:semantic_config_version_id` は Run 行の値と一致必須 |

### 12.3 再実行・再現性

| シナリオ | 期待動作 |
| -------- | -------- |
| 同一 Request の再推薦 | **新規 `recommendation_run` 行** + 新規 `user_semantic` 行 |
| Run 失敗後のリトライ | 同一 Run 行への再 INSERT は不可。Run 状態遷移設計書に従い新 Run または失敗確定 |
| `semantic_config_version` の事後変更 | 既存 `user_semantic` 行は不変（version スナップショット） |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | **Run / Result と同ライフサイクル**（Online コア長期保持。物理ER Retention 方針に追随） |
| 削除方式 | 原則 **物理 DELETE しない** |
| 削除条件 | 親 `recommendation_run` 削除は RESTRICT |
| 論理削除 | 列なし |
| アーカイブ | MVP 対象外 |

### 13.1 例外 DELETE（メンテナンス）

| 対象 | 方針 |
| ---- | ---- |
| 誤生成・テストデータ | 運用 DELETE（監査ログ必須・Human Review） |
| GDPR 等の削除要求 | 別運用 Task。MVP では未自動化 |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `user_semantic` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | **`recommendation_run`・`semantic_config_version` 作成後**。`user_feature` / `user_meaning` と **並行可** |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | reco（service role 経由） |
| 書き込み権限 | reco（MOD-RECO-004 / IF-DB-RECO-003）のみ |
| service role利用 | reco INSERT・SELECT に限定 |
| 個人情報・機微情報 | ユーザー自由記述を `extracted_semantic_json` に含み得る。Public API 非公開・ログ mask 必須 |
| ログ出力制限 | `extracted_semantic_json` 全文を Public ログに出力しない。必要時は concept_code 一覧程度に mask |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / FK / CHECK / UNIQUE が定義どおり | migration |
| 2 | FK 整合 | 存在しない `recommendation_run_id` への INSERT が拒否される | migration |
| 3 | UNIQUE 冪等 | 同一 `recommendation_run_id` の 2 行目 INSERT が拒否される | integration |
| 4 | version 整合 | `semantic_config_version_id` が Run 行と一致する行のみ INSERT される（アプリ層） | integration |
| 5 | JSON CHECK | `concepts` 欠落 JSON が拒否される | migration |
| 6 | MOD-RECO-004 連携 | 推薦 Run 完了後に行が存在し `generated_at` が設定される | integration |
| 7 | batch 非更新 | batch ジョブが本テーブルへ DML しない | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | `semantic_config_version_id` 物理 FK | `item_semantic` は ON・本テーブルは LOGICAL 候補。`semantic_config_version_テーブル定義書` §8.2 との最終整合 | Human | Human Review | §17.1 No.1 |
| 2 | Run あたり行数 | 物理ER 1:N vs テーブル一覧 Run 単位 1 行。MVP UNIQUE 採用の妥当性 | Human | Human Review | §17.1 No.2 |
| 3 | `extracted_semantic_json` 必須キー | `item_semantic.semantic_json` との完全同型 vs User 固有キー追加 | Human | Human Review | §17.1 No.3 |
| 4 | Run version 列の重複保持 | `recommendation_run.semantic_config_version_id` と行 version の二重保持要否 | Human | Human Review | §17.1 No.4 |

### 17.1 Human Review 提案（Issue #553）

| No | 論点 | 提案内容 | 判断者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | `semantic_config_version_id` FK | **LOGICAL 維持**（Index `idx_user_semantic_version_id`）。物理 FK は付与しない | Human | `item_semantic` ON との意図的差分。`recommendation_run` も version は LOGICAL |
| 2 | Unique キー | **`recommendation_run_id` UNIQUE**（Run あたり 1 行） | Human | テーブル一覧 §4 補足。再推薦は新 Run |
| 3 | JSON スキーマ | **`concepts[]` 配列**。User は `input_intent` **必須**。`source_type` は User 入力系 code | Human | §5.3 |
| 4 | version 重複保持 | **行にも保持**（Run 値と一致必須）。`user_feature` 後続参照・監査のため | Human | `item_semantic` の version スナップショットと同型 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | User意味推定系・§9 generates |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §10.2 属性・§16 責務境界 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §4 No.7 |
| 正本定義表 | `docs/05_アプリケーション設計/アプリ/database/正本定義表.md` | User Semantic 派生正本 |
| リソース責務定義表 | `docs/05_アプリケーション設計/アプリ/database/リソース責務定義表.md` | User意味推定責務 |
| SemanticConcept定義書 | `docs/04_ドメインモデル設計/SemanticConcept定義書.md` | Concept 体系 |
| Semanticルール定義書 | `docs/04_ドメインモデル設計/Semanticルール定義書.md` | User 入力抽出・§11 |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-DB-RECO-003 |
| 機能×モジュール対応表 | `docs/05_アプリケーション設計/アプリ/機能×モジュール対応表.md` | MOD-RECO-004 |
| Recoモジュール一覧 | `docs/05_アプリケーション設計/アプリ/reco/Recoモジュール一覧.md` | MOD-RECO-004 詳細 |
| 認証・認可方針書 | `docs/05_アプリケーション設計/基盤/認証・認可方針書.md` | reco 作成権限 |
| recommendation_run 定義書 | `docs/06_実装設計/database/recommendation_run_テーブル定義書.md` | §8.2 被参照 |
| recommendation_request 定義書 | `docs/06_実装設計/database/recommendation_request_テーブル定義書.md` | 入力テキスト正本 |
| semantic_config_version 定義書 | `docs/06_実装設計/database/semantic_config_version_テーブル定義書.md` | §8.2 generates_with |
| semantic_concept 定義書 | `docs/06_実装設計/database/semantic_concept_テーブル定義書.md` | concept_code |
| semantic_rule 定義書 | `docs/06_実装設計/database/semantic_rule_テーブル定義書.md` | 抽出 Rule 正本 |
| item_semantic 定義書 | `docs/06_実装設計/database/item_semantic_テーブル定義書.md` | 対称正本（#513） |

---

## 19. レビュー観点

- 論理ER §10.2・テーブル一覧 §4 No.7 と矛盾していない
- `recommendation_run_id` の FK（ON）・IF-DB-RECO-003 保存 I/F が §5.6 / §12 で明示されている
- `semantic_config_version_id` の LOGICAL 方針・Run 固定 version との整合が §5.4 / §5.5 / §8.1 で明示されている
- `item_semantic` との対称関係および差分（§5.4）が整理されている
- `extracted_semantic_json` が Semanticルール定義書・`semantic_concept` の concept_code 参照方針と一致している
- 論理ER §16（reco Online 生成・batch 非更新）が §5.2 に反映されている
- apps/** / OpenAPI / generated / DDL 変更が含まれていない
- secret や `.env` 実値が含まれていない
