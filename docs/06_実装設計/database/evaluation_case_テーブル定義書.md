# Evaluation Case テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                            |
| -------------- | ------------------------------- |
| ドキュメントID | `DB-TBL-MVP-evaluation_case`    |
| ドキュメント名 | Evaluation Case テーブル定義書  |
| 対象システム   | Gift Recommendation Service MVP |
| MVP対象        | `partial`                       |
| 作成日         | 2026-06-16                      |
| 更新日         | 2026-06-16                      |

---

## 2. 概要

`evaluation_case` は、オフライン評価（BATCH-018）で利用する **個別評価ケース正本** を保持する Evaluation系テーブルである。

親 `evaluation_dataset` に属する固定入力条件・期待結果の組み合わせを DB 上で管理し、MOD-BATCH-039 / IF-SHARED-004 経由で reco pipeline を `mode=evaluation` 実行する際の入力正本となる。Public API には本テーブルの主キーを直接公開しない（内部正本）。

---

## 3. 目的

- データセット内の個別評価ケース（入力条件・期待結果・ラベル）を不変の正本として保存する
- `evaluation_dataset` との **物理 FK（ON）** により親子関係（contains 1:N）を確定する
- BATCH-018 が `is_active = true` のケースを読み取り、IF-SHARED-004 / API-INT-002 `mode=evaluation` へ渡す入力を提供する
- 後続 `evaluation_result`（#567 以降）から `evaluation_case_id` で被参照される実行単位の入力正本とする

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `evaluation_case` |
| 論理テーブル名 | Evaluation Case |
| 分類 | Evaluation系 |
| 正本区分 | 内部正本 |
| 主な更新主体 | database（seed / 運用更新）、batch（評価データ投入） |
| 主な参照主体 | batch（BATCH-018 / MOD-BATCH-039）、reco（evaluation mode 実行時） |
| MVP対象 | `partial` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §7・§9 Mermaid ER |

---

## 5. 用途・責務

- **ケース識別**（`case_label`）と **入力条件**（`input_condition_json`）、**期待結果**（`expected_result_json`）をデータセット単位で保持する
- **有効フラグ**（`is_active`）により、無効ケースを BATCH-018 実行対象外とする
- **`evaluation_case_id`（UUID）** をサロゲート PK とし、子 `evaluation_result` から参照される（後続 Task）
- 評価実行状態（`evaluation_status`）・Config version 固定・メトリクス算出結果は本テーブルでは保持しない（`evaluation_run` / `evaluation_result` / `evaluation_metric` の責務）

### 5.1 evaluation_dataset との親子関係

| 観点 | 方針 |
| ---- | ---- |
| 親 | `evaluation_dataset`（Evaluation Dataset 正本） |
| 関係 | **contains**（1:N）。物理ER §9 |
| FK | `evaluation_case.evaluation_dataset_id` → `evaluation_dataset.evaluation_dataset_id`。**物理 FK ON** / `ON DELETE RESTRICT` |
| 読取 | BATCH-018 は親 Dataset 解決後、当該 `evaluation_dataset_id` かつ `is_active = true` の行を SELECT |
| 書込 | database（seed / 運用）および batch（評価データ投入）。Dataset 作成時に Case を同時投入する想定 |

> **親定義書（#565）**: `evaluation_dataset_テーブル定義書` §5.1 / §8.1 / §12.1。親 Epic merge 前は PR #570 ブランチを参照。本定義書 §8 と双方向整合する。

### 5.2 evaluation_run / evaluation_result との分離

| 観点 | `evaluation_case` | `evaluation_run` | `evaluation_result` |
| ---- | ----------------- | ---------------- | ------------------- |
| 管理単位 | 固定評価ケース（入力 + 期待） | データセットに対する評価実行 | ケース × Run の実行結果 |
| 状態 | `is_active` のみ | `evaluation_status` | なし（Log / 派生） |
| 被参照 | `evaluation_result.evaluation_case_id`（後続） | `evaluation_result.evaluation_run_id` | — |
| 定義 Task | 本 Task（#566） | #567 | 後続 Task |

### 5.3 BATCH-018 / IF-SHARED-004 / API-INT-002 との I/F

| 観点 | 方針 |
| ---- | ---- |
| 読取 I/F | BATCH-018 / MOD-BATCH-039 が `evaluation_dataset_id` 解決後、本テーブルを SELECT（`is_active = true`） |
| reco 実行 | IF-SHARED-004: `evaluation_case` + `mode=evaluation` → reco pipeline → `recommendation_result` / metrics |
| Internal API | API-INT-002 `execution.mode=evaluation` / `execution.evalCaseId`（`evaluation_case_id` または `case_label` 解決は実装 Task） |
| 書込 I/F | INSERT / UPDATE は **database（seed / 運用）** および **batch（評価データ投入）**。BATCH-018 本体は本テーブルへ INSERT しない（読取のみ） |
| 不正ケース | Validation 失敗時は **GRS-EVAL-002**（対象 case を除外して継続。`エラーコード定義書`） |

### 5.4 recommendation_request との may_reference 関係

論理ER §12.1: `RECOMMENDATION_REQUEST ||--o{ EVALUATION_CASE : "may_reference"`。

| 観点 | 方針 |
| ---- | ---- |
| 用途 | 実際の Online 推薦 Request から評価ケースを派生・再現した場合の **任意 trace** |
| 物理列 | `recommendation_request_id`（nullable UUID） |
| FK | **LOGICAL FK**（物理 FK なし）。Index のみ |
| MVP | 列は保持するが、seed 中心のオフライン評価では **NULL が通常** |
| 入力正本 | 評価実行時の入力は **`input_condition_json`**（`recommendation_request` 行のコピーではない） |

### 5.5 input_condition_json / expected_result_json の責務

| 列 | 責務 | MVP 方針 |
| -- | ---- | -------- |
| `input_condition_json` | reco へ渡す **評価用入力条件正本**（API-PUB-002 / API-INT-002 整合 JSONB） | **NOT NULL**。snake_case 内部形式 |
| `expected_result_json` | 人手評価・自動 metric 比較の **期待結果**（Golden / Regression 用） | **nullable**。`golden` Dataset では seed 投入時に必須とする運用 |

#### 5.5.1 input_condition_json 推奨キー（MVP）

`recommendation_request_テーブル定義書` §5.5 および API-PUB-002 を正とする **validated 相当** の snake_case JSON。

| キー（推奨） | 型 | 必須 | 説明 |
| ------------ | -- | ---- | ---- |
| `relationship_code` | string | yes | `relationship_master` コード |
| `occasion_code` | string | yes | `occasion_master` コード |
| `budget_min` / `budget_max` | number | no | 予算範囲（円） |
| `preferred_text` | string | no | 好み条件 |
| `non_preferred_text` | string | no | 避けたい条件 |
| `ng_text` | string | no | NG 条件 |
| `free_text` | string | no | 自由入力 |
| `execution` | object | yes | 実行条件。`mode` は **`evaluation` 固定** |
| `execution.mode` | string | yes | `evaluation` |
| `execution.top_k` | integer | no | 取得件数（デフォルトは ranking config 依存） |
| `execution.include_reason` | boolean | no | Reason 生成有無 |
| `execution.include_debug_info` | boolean | no | evaluation 時 **true 推奨**（API-INT-002） |

> **個別物理列化**: Evaluation評価定義書 §14.2 `offline_eval_case` の個別列（`relationship_code` 等）は **MVP では採用しない**。論理ER §12.2 JSONB 集約を優先（§17.1 No.2）。

#### 5.5.2 expected_result_json 推奨キー（MVP）

Evaluation評価定義書 §5.2 評価ケース構成を JSON キーとして保持する。

| キー（推奨） | 型 | 必須 | 説明 |
| ------------ | -- | ---- | ---- |
| `expected_concepts` | array / object | no | 期待 Semantic Concept |
| `expected_feature_tendency` | object | no | 期待 Feature 傾向（feature_code → 方向性） |
| `evaluation_focus` | string | no | 本ケースの確認観点（例: Social 適合性） |
| `golden_item_ids` | array of uuid | no | Golden Dataset 用期待商品 ID リスト（将来 HitRate 等） |
| `notes` | string | no | 運用メモ（Public 非公開） |

### 5.6 GRS-EVAL-002（Invalid Evaluation Case）との整合

| 条件 | BATCH-018 扱い |
| ---- | -------------- |
| `is_active = false` | **スキップ**（エラーにしない） |
| `input_condition_json` が NULL / 空オブジェクト | **GRS-EVAL-002** で除外 |
| 必須キー欠落（`relationship_code` / `occasion_code` / `execution.mode`） | **GRS-EVAL-002** で除外 |
| Master コード不存在 | **GRS-EVAL-002** で除外 |
| `evaluation_dataset.is_active = false` の親 | 親ごと解決対象外（親定義書 §12.1） |

### 5.7 論理ER / ドメイン定義との差分整理

| 出典 | 列・概念 | 本テーブル（MVP 物理 DDL） | 扱い |
| ---- | -------- | -------------------------- | ---- |
| 論理ER §12.2 | `evaluation_case_id`, `evaluation_dataset_id`, `input_condition_json`, `expected_result_json`, `case_label`, `is_active`, `created_at` | **すべて採用** | 論理ER 準拠 |
| Evaluation評価定義書 §14.2 | `offline_eval_case` 個別列 | **JSONB 集約** | §5.5・§17.1 No.2 |
| Evaluation評価定義書 §5.2 | `eval_case_id` | **`case_label`** | 人間可読ラベル。PK は UUID |
| 論理ER §12.1 | may_reference Request | **`recommendation_request_id` nullable** | §5.4・§17.1 No.4 |
| 状態カラム | なし | **状態列なし** | `is_active` のみ |

### 5.8 対象外

- 評価データセット定義（`evaluation_dataset` の責務）
- 評価実行・Config version 固定（`evaluation_run` の責務）
- 評価結果・メトリクス（`evaluation_result` / `evaluation_metric` の責務）
- Online 推薦 Request 正本（`recommendation_request` の責務。参照のみ）
- Public API による評価ケース CRUD（MVP 対象外）

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `evaluation_case_id` | Evaluation Case ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK。API-INT-002 `evalCaseId` / trace キー |
| 2 | `evaluation_dataset_id` | Evaluation Dataset ID | `uuid` | `yes` | — | `yes` | — | — | 親 Dataset。`evaluation_dataset.evaluation_dataset_id` 参照 |
| 3 | `case_label` | Case Label | `varchar(100)` | `yes` | — | — | — | — | データセット内ケース識別子。snake_case（例: `case_001`） |
| 4 | `input_condition_json` | Input Condition JSON | `jsonb` | `yes` | — | — | — | — | 評価入力条件正本。§5.5.1 |
| 5 | `expected_result_json` | Expected Result JSON | `jsonb` | `no` | — | — | — | `NULL` | 期待結果。§5.5.2。Golden 系は seed 運用で必須化 |
| 6 | `recommendation_request_id` | Recommendation Request ID | `uuid` | `no` | — | — | — | `NULL` | 任意 trace。Request 派生ケース時のみ。LOGICAL FK |
| 7 | `is_active` | Active Flag | `boolean` | `yes` | — | — | — | `true` | 有効フラグ。`false` は BATCH-018 対象外 |
| 8 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | レコード作成日時（UTC） |

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `evaluation_case_id` | サロゲート UUID | 子 `evaluation_result` FK の参照先（後続 Task） |
| UNIQUE | `evaluation_case_id` | PK と同一 | — |
| UNIQUE | `evaluation_dataset_id`, `case_label` | データセット内ケースラベル一意 | §17.1 No.5 |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `evaluation_dataset_id` | `evaluation_dataset.evaluation_dataset_id` | `ON` | `ON DELETE RESTRICT` | 物理 ER §9 contains。親 #565 §8.1 と双方向整合 |
| `recommendation_request_id` | `recommendation_request.recommendation_request_id` | `LOGICAL` | アプリ Validation | nullable。may_reference。Index のみ |

### 8.1 被参照（後続 Task 引き継ぎ）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `evaluation_result` | `evaluation_case_id` | executed_as | `ON`（#567 以降で確定） | 論理ER §12.1。1:N |

### 8.2 evaluation_dataset 定義書との双方向整合

| 項目 | `evaluation_dataset_テーブル定義書` | 本テーブル | 状態 |
| ---- | ----------------------------------- | ---------- | ---- |
| contains FK | §8.1 `evaluation_case.evaluation_dataset_id` ON | §8 `evaluation_dataset_id` ON | 整合 |
| Index 引き継ぎ | §5.4 `idx_evaluation_case_dataset_id` | §9 | 本 Task で確定 |
| BATCH-018 読取 | §12.1 子ケース `is_active=true` | §12.1 | 整合 |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `evaluation_case_pkey` | `evaluation_case_id` | btree（PK） | 主キー | 自動生成 |
| `uq_evaluation_case_dataset_label` | `evaluation_dataset_id`, `case_label` | btree（unique） | データセット内ラベル一意 | §7 |
| `idx_evaluation_case_dataset_id` | `evaluation_dataset_id` | btree | 親 FK 補助・Dataset 単位一覧 | `evaluation_dataset_テーブル定義書` §5.4 引き継ぎ |
| `idx_evaluation_case_dataset_active` | `evaluation_dataset_id`, `is_active` | btree | BATCH-018 有効ケース読取 | partial index 候補: `WHERE is_active = true`（§17.1 No.6） |
| `idx_evaluation_case_request_id` | `recommendation_request_id` | btree | may_reference 逆引き | nullable |
| `idx_evaluation_case_created_at` | `created_at` DESC | btree | 監査・運用参照 | 物理ER §10 時系列 Index 方針 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `evaluation_case_pkey` | PRIMARY KEY | `evaluation_case_id` | 主キー | — |
| `uq_evaluation_case_dataset_label` | UNIQUE | `evaluation_dataset_id`, `case_label` | データセット内一意 | — |
| `chk_case_label_format` | CHECK | `case_label` | `case_label ~ '^[a-z][a-z0-9_]*$'` | snake_case。先頭英字 |
| `chk_input_condition_not_empty` | CHECK | `input_condition_json` | `input_condition_json <> '{}'::jsonb` | 空オブジェクト禁止 |
| `fk_evaluation_case_dataset` | FOREIGN KEY | `evaluation_dataset_id` | `REFERENCES evaluation_dataset (...) ON DELETE RESTRICT` | DDL Task |

> **JSON Schema CHECK**: MVP では `input_condition_json` / `expected_result_json` の **キー構造を DB CHECK で固定しない**（batch / seed Validation で担保。GRS-EVAL-002 除外）。

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `input_condition_json` 内 | `relationship_code` | enum定義書 §6.15 / `relationship_master` | Master 有効コード | JSON 内。DB enum 列なし |
| `input_condition_json` 内 | `occasion_code` | enum定義書 §6.16 / `occasion_master` | Master 有効コード | 同上 |
| `input_condition_json.execution.mode` | `request_mode` | enum定義書 §6.13 / `request_mode.yaml` | **`evaluation` 固定** | evaluation case 行では `evaluation` のみ許容（seed / batch Validation） |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | batch | BATCH-018 開始時 | — | — | `evaluation_dataset_id` + `is_active = true` |
| SELECT | reco | evaluation mode | — | — | batch 経由で Case 解決済み前提 |
| INSERT | database（seed / 運用） | 新ケース追加 | 全列 | `evaluation_dataset_id` + `case_label` で Upsert 想定 | seed Task へ委譲 |
| INSERT | batch | 評価データ投入 | 全列 | 同上 | 運用判断 |
| UPDATE | database / batch（運用） | 期待結果・入力修正・無効化 | `input_condition_json`, `expected_result_json`, `is_active` | — | PK / `case_label` 変更は原則禁止 |
| DELETE | — | MVP では原則禁止 | — | — | `is_active = false` で無効化。子 `evaluation_result` 存在時は RESTRICT |

### 12.1 BATCH-018 ケース読取順序

`evaluation_dataset_テーブル定義書` §12.1 ステップ 3 を正とする。

1. 親 `evaluation_dataset` を解決（`is_active = true`）
2. 本テーブルを `evaluation_dataset_id = :id AND is_active = true` で SELECT
3. 各行を Validation（§5.6）。合格行のみ IF-SHARED-004 へ
4. `evaluation_case_id` を API-INT-002 `execution.evalCaseId` に渡す（実装 Task で UUID / label 解決を確定）

### 12.2 再評価・ケース改訂方針

| 観点 | 方針 |
| ---- | ---- |
| ケース内容変更 | **既存行 UPDATE** ではなく、原則 **新 `dataset_version` で親 Dataset を追加**し新 Case 行を INSERT（親定義書 §12.2） |
| 軽微な expected 修正 | 運用上 UPDATE を許容する場合は **Human 承認** の上、`expected_result_json` のみ UPDATE 可 |
| 再評価 | 同一 Case 行に対し新規 `evaluation_run` を追記（結果上書きしない） |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | **親 `evaluation_dataset` に準拠**（365 日。`evaluation_dataset_テーブル定義書` §13 / §17.1 No.5） |
| 削除方式 | MVP では **自動 DELETE なし** |
| 削除条件 | 親 Dataset 削除前に Case 行を整理。子 `evaluation_result` 存在時は FK RESTRICT |
| 論理削除 | **`is_active = false`** でケース無効化 |
| アーカイブ | MVP 対象外 |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `evaluation_case` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | **`evaluation_dataset` の直後**（親 FK 依存）。`evaluation_run` より前 |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | batch / reco（service role 経由） |
| 書き込み権限 | database 運用・seed、batch（評価データ投入）に限定 |
| service role利用 | BATCH-018 / seed 投入に限定。web client から Direct DB アクセス不可 |
| 個人情報・機微情報 | `input_condition_json` / `expected_result_json` に **個人情報・secret を含めない**。自由記述は評価用ダミーデータのみ |
| ログ出力制限 | JSON 全文を error ログに過剰出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / FK / CHECK が定義どおり | migration |
| 2 | PK / UNIQUE | 同一 `evaluation_dataset_id` + `case_label` 重複 INSERT が拒否される | migration |
| 3 | FK | 存在しない `evaluation_dataset_id` への INSERT が拒否される | migration |
| 4 | DELETE RESTRICT | 子 `evaluation_result` 存在時に Case DELETE が拒否される | migration |
| 5 | CHECK | 空 `input_condition_json` / 不正 `case_label` が拒否される | migration |
| 6 | BATCH-018 整合 | `is_active` フィルタ・Dataset 単位読取が親定義書と整合 | integration |
| 7 | GRS-EVAL-002 | 必須キー欠落 Case が除外される | integration |
| 8 | IF-SHARED-004 | `mode=evaluation` 実行で input JSON が reco に渡る | integration |
| 9 | seed 整合 | MVP 評価用サンプルケースが seed に存在（採用時） | manual |
| 10 | 権限 | web client から Direct DB アクセス不可 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | `input_condition_json` 物理化方針 | API payload のみ vs 個別列併用 | Human | Human Review | §17.1 No.1 |
| 2 | Evaluation §14.2 個別列 vs JSONB | ドメイン定義書との表現差 | Human | Human Review | §17.1 No.2 |
| 3 | `expected_result_json` MVP 必須条件 | Golden のみ必須 vs 全 Case nullable | Human | Human Review | §17.1 No.3 |
| 4 | `recommendation_request_id` 採用 | may_reference の MVP 要否 | Human | Human Review | §17.1 No.4 |
| 5 | `case_label` UNIQUE 範囲 | Dataset 内一意（採用案） | Human | Human Review | §17.1 No.5 |
| 6 | partial index `is_active` | 読取性能 vs シンプル Index | Human | Human Review | §17.1 No.6 |

### 17.1 Human Review 推奨案（Issue #566）

| No | 論点 | 推奨案 | 備考 |
| --: | ---- | ------ | ---- |
| 1 | `input_condition_json` 物理化 | **API-PUB-002 validated 相当 JSONB のみ**（個別列なし） | `recommendation_request` §5.4 payload 方針と整合 |
| 2 | §14.2 個別列 | **論理ER JSONB 集約を採用** | Evaluation評価定義書 §14.2 は論理項目参考。物理 DDL は JSONB |
| 3 | `expected_result_json` 必須 | **列は nullable**。`dataset_type=golden` は seed Validation で必須 | enum 列は親 Dataset 側（#565） |
| 4 | `recommendation_request_id` | **nullable 物理列を採用**（LOGICAL FK） | may_reference。MVP seed では NULL |
| 5 | `case_label` UNIQUE | **`(evaluation_dataset_id, case_label)` UNIQUE** | Evaluation §5.3 例 `case_001` 形式 |
| 6 | partial index | **`idx_evaluation_case_dataset_active` は partial**（`WHERE is_active = true`） | BATCH-018 読取最適化 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §7 Evaluation系・§9 FK |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §12.1 / §12.2 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §10 No.52 |
| Evaluation評価定義書 | `docs/04_ドメインモデル設計/Evaluation評価定義書.md` | §5.2 / §14.2 |
| 正本定義表 | `docs/05_アプリケーション設計/アプリ/database/正本定義表.md` | §5.12 |
| 親テーブル定義 | `docs/06_実装設計/database/evaluation_dataset_テーブル定義書.md` | contains 親（#565 / PR #570） |
| Request 定義 | `docs/06_実装設計/database/recommendation_request_テーブル定義書.md` | input JSON マッピング |
| API-INT-002 | `docs/06_実装設計/api/API-INT-002_Reco推薦実行API契約仕様書.md` | evaluation mode |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-SHARED-004 |
| バッチ処理一覧 | `docs/05_アプリケーション設計/アプリ/batch/バッチ処理一覧.md` | BATCH-018 |
| エラーコード | `docs/05_アプリケーション設計/アプリ/エラーコード定義書.md` | GRS-EVAL-002 |
| 子 Task | Issue #567 `evaluation_run` | `evaluation_result` FK 引き継ぎ |

---

## 19. レビュー観点

- 論理ER §12.2・物理ER §9 contains・テーブル一覧 §10 No.52 と矛盾していない
- `evaluation_dataset` との親子関係（物理 FK ON・1:N）が明記されている
- `input_condition_json` / `expected_result_json` / `case_label` / `is_active` の責務が明記されている
- `recommendation_request` との may_reference（nullable LOGICAL FK）が整理されている
- Evaluation評価定義書 §14.2 と論理ER JSONB の差分が §5.7 で整理されている
- BATCH-018 / IF-SHARED-004 / API-INT-002 evaluation mode との I/F が一貫している
- GRS-EVAL-002 と `is_active` / Validation 除外方針が整合している
- `evaluation_dataset_テーブル定義書`（#565）§5.4 Index 引き継ぎと双方向整合している
- `evaluation_result` 後続 Task 向け `evaluation_case_id` 被参照が §8.1 で言及されている
- Human Review §17.1 推奨案が DDL Task へ展開可能な粒度である
- secret や `.env` 実値が含まれていない
