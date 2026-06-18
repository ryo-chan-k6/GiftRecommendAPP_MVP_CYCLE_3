# Evaluation Dataset テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                               |
| -------------- | ---------------------------------- |
| ドキュメントID | `DB-TBL-MVP-evaluation_dataset`    |
| ドキュメント名 | Evaluation Dataset テーブル定義書  |
| 対象システム   | Gift Recommendation Service MVP    |
| MVP対象        | `partial`                          |
| 作成日         | 2026-06-16                         |
| 更新日         | 2026-06-16（Human Review §17.1 確定） |

---

## 2. 概要

`evaluation_dataset` は、オフライン評価（BATCH-018）で利用する **評価用データセット正本** を保持する Evaluation系テーブルである。

`evaluation_case`（評価ケース）および `evaluation_run`（評価実行単位）の親エンティティとして、データセット識別子・名称・version・有効フラグを担う。Public API には本テーブルの主キーを直接公開しない（内部正本）。

---

## 3. 目的

- オフライン評価の入力データセットを DB 上で識別・説明する
- `evaluation_case` / `evaluation_run` の親エンティティとして、物理 FK（ON）の被参照元となる
- BATCH-018 / MOD-BATCH-039 が参照する評価データセット正本を提供する
- 同一データセットに対する再評価時も、既存 Run / Result を上書きせず追記する前提の version 管理基盤とする

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `evaluation_dataset` |
| 論理テーブル名 | Evaluation Dataset |
| 分類 | Evaluation系 |
| 正本区分 | 内部正本 |
| 主な更新主体 | database（seed / 運用更新）、batch（評価データ投入） |
| 主な参照主体 | batch（BATCH-018 / MOD-BATCH-039）、reco（evaluation mode 実行時） |
| MVP対象 | `partial` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §7・§9 Mermaid ER |

---

## 5. 用途・責務

- **データセット識別**（`dataset_name` + `dataset_version`）と **説明**（`dataset_description`）を保持する
- **データセット単位の有効フラグ**（`is_active`）により、無効データセットを BATCH-018 解決対象外とする
- **`evaluation_dataset_id`（UUID）** をサロゲート PK とし、子テーブル `evaluation_case` / `evaluation_run` から **物理 FK（ON）** で参照される
- 評価ケース内容（`input_condition_json` / `expected_result_json`）や評価実行状態（`evaluation_status`）は本テーブルでは保持しない（子テーブル責務）

### 5.1 evaluation_case / evaluation_run との分離

| 観点 | `evaluation_dataset` | `evaluation_case` | `evaluation_run` |
| ---- | -------------------- | ----------------- | ---------------- |
| 管理単位 | データセット（名称 + version） | データセット内の個別ケース | データセットに対する評価実行単位 |
| 主な列 | `dataset_name`, `dataset_description`, `dataset_version`, `is_active` | `input_condition_json`, `expected_result_json`, `case_label` | `evaluation_status`, `semantic_config_version_id`, `model_version_id`, `ranking_config_id` |
| 状態カラム | なし（`is_active` のみ） | なし（`is_active` のみ） | `evaluation_status` |
| 物理 FK | 被参照元（親） | 親 `evaluation_dataset_id` を参照（ON） | 親 `evaluation_dataset_id` を参照（ON） |
| 定義 Task | 本 Task（#565） | #566 | #567 |

### 5.2 BATCH-018 / I/F との関係

| 観点 | 方針 |
| ---- | ---- |
| 読取 I/F | BATCH-018 開始時に `evaluation_dataset` を SELECT（`evaluation_dataset_id` または `dataset_name` + `dataset_version` 指定） |
| 書込 I/F | 本テーブルへの INSERT / UPDATE は **database（seed / 運用）** および **batch（評価データ投入）** が担う。IF-DB-BATCH-018 の INSERT 対象は `evaluation_run` / `evaluation_result` / `evaluation_metric`（本テーブルは読取正本） |
| IF-SHARED-004 | `evaluation_case` を入力に reco pipeline を evaluation mode で実行。データセット本体は事前に本テーブル + `evaluation_case` で整備済みであること |
| workflow 入力 | `batch-offline-evaluation.yml` の `evaluation_dataset_id` 等で対象データセットを指定（`バッチ実行スケジュール設計書`） |

### 5.3 Observability との境界

| 観点 | 方針 |
| ---- | ---- |
| trace キー | 本テーブルは trace キーではない。評価実行 trace は `evaluation_run_id`（`ログ・Observability設計書`） |
| phase_log / error_log | `owner_type=evaluation_run` で子 Run に紐づく。本テーブルには Log 列を持たない |

### 5.4 子テーブル Task への引き継ぎ

| 子テーブル | 参照列 | 関係 | FK制約 | Index |
| ---------- | ------ | ---- | ------ | ----- |
| `evaluation_case` | `evaluation_dataset_id` | contains | `ON` / `ON DELETE RESTRICT` | `idx_evaluation_case_dataset_id` / `uq_evaluation_case_dataset_label` / `idx_evaluation_case_dataset_active`（partial・#566 §17.1 確定） |
| `evaluation_run` | `evaluation_dataset_id` | executed_by | `ON` / `ON DELETE RESTRICT` | `idx_evaluation_run_dataset_id`（Index 引き継ぎ。`evaluation_run_テーブル定義書` §9） |
| `evaluation_result` | `evaluation_dataset_id` | 冗長保持（再現性） | `ON` / `ON DELETE RESTRICT` | `idx_evaluation_result_dataset_id`（#573 §17.1 No.1 確定） |

> **物理ER §9 整合**: Human Review #565 §17.1 No.4 により `evaluation_run.evaluation_dataset_id` への物理 FK ON を確定。Human Review #573 §17.1 No.1 により `evaluation_result.evaluation_dataset_id` も物理 FK ON を確定。物理ER §9 FK 表・§17.7 / §17.10 に反映。

### 5.5 対象外

- 評価ケース定義（`evaluation_case` の責務）
- 評価実行状態・Config version 固定（`evaluation_run` の責務）
- 評価結果・メトリクス（`evaluation_result` / `evaluation_metric` の責務）
- 評価メトリクス算出ロジック（BATCH-018 バッチ仕様書の責務）
- Public API によるデータセット CRUD（MVP 対象外）

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `evaluation_dataset_id` | Evaluation Dataset ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK。子テーブル `evaluation_dataset_id` の参照先 |
| 2 | `dataset_name` | Dataset Name | `text` | `yes` | — | — | — | — | データセット系列名。snake_case 英小文字・数字・アンダースコア。同一系列内で `dataset_version` と組み合わせて一意 |
| 3 | `dataset_description` | Dataset Description | `text` | `no` | — | — | — | `NULL` | データセットの説明。運用・監査用。Public API 非公開 |
| 4 | `dataset_version` | Dataset Version | `varchar(50)` | `yes` | — | — | — | — | データセット version ラベル。semver 形式（例: `v1.0.0`）。同一 `dataset_name` 内で一意 |
| 5 | `is_active` | Active Flag | `boolean` | `yes` | — | — | — | `true` | 有効フラグ。`false` のデータセットは BATCH-018 解決対象外 |
| 6 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | レコード作成日時（UTC） |

> **論理ER §12.2 との関係**: 論理ERが列挙する主要属性（`evaluation_dataset_id`, `dataset_name`, `dataset_description`, `dataset_version`, `is_active`, `created_at`）をすべて物理化する。状態カラムは論理ERどおり本テーブルには持たない。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `evaluation_dataset_id` | サロゲート UUID | 子テーブル FK の参照先 |
| UNIQUE | `evaluation_dataset_id` | PK と同一 | — |
| UNIQUE | `dataset_name`, `dataset_version` | 系列名 + version の組み合わせ一意 | 同一系列の重複 version を禁止。再評価は新規 `evaluation_run` 追記で対応（§12.2） |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| — | — | なし | — | 本テーブルは Evaluation系の根。外向き FK なし |

### 8.1 被参照（物理 FK ON）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `evaluation_case` | `evaluation_dataset_id` | contains | `ON` | 物理ER §9。1:N。DELETE RESTRICT（§17.1 No.4） |
| `evaluation_run` | `evaluation_dataset_id` | executed_by | `ON` | 物理ER §9・§17.1 No.4。1:N。DELETE RESTRICT |
| `evaluation_result` | `evaluation_dataset_id` | 冗長保持 | `ON` | 物理ER §9・#573 §17.1 No.1。1:N。DELETE RESTRICT |

> **子テーブル側 DDL 方針（引き継ぎ）**: 子テーブルの `evaluation_dataset_id` → `evaluation_dataset.evaluation_dataset_id` に `REFERENCES ... ON DELETE RESTRICT` を付与する。親データセット削除前に case / run / result 行の整理が必要。

### 8.2 物理ER §9 整合（Human Review #565 反映）

| 関係 | 物理ER Mermaid ER | 物理ER §9 FK 表 | 状態 |
| ---- | ----------------- | --------------- | ---- |
| `evaluation_dataset` → `evaluation_case` contains | あり | あり（ON） | 整合 |
| `evaluation_dataset` → `evaluation_run` executed_by | あり | あり（ON。§17.1 No.4 確定） | **#565 で §9 補完済み** |
| `evaluation_dataset` → `evaluation_result` 冗長保持 | — | あり（ON。#573 §17.1 No.1 確定） | **#573 で §9 補完済み** |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `evaluation_dataset_pkey` | `evaluation_dataset_id` | btree（PK） | 主キー | 自動生成 |
| `uq_evaluation_dataset_name_version` | `dataset_name`, `dataset_version` | btree（unique） | 系列 + version 一意 | §7 と同一 |
| `idx_evaluation_dataset_active_name` | `is_active`, `dataset_name` | btree | 有効データセットの解決 | BATCH-018 / seed 参照 |
| `idx_evaluation_dataset_created_at` | `created_at` DESC | btree | 監査・運用参照 | 物理ER §10 Index 方針（時系列列） |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `evaluation_dataset_pkey` | PRIMARY KEY | `evaluation_dataset_id` | 主キー | — |
| `uq_evaluation_dataset_name_version` | UNIQUE | `dataset_name`, `dataset_version` | 系列 + version 一意 | — |
| `chk_dataset_name_format` | CHECK | `dataset_name` | `dataset_name ~ '^[a-z][a-z0-9_]*$'` | snake_case。先頭英字 |
| `chk_dataset_version_format` | CHECK | `dataset_version` | `dataset_version ~ '^v[0-9]+\.[0-9]+\.[0-9]+$'` | semver 基本形（例: `v1.0.0`）。`semantic_config_version` §10 と同型 |
| `chk_dataset_description_length` | CHECK | `dataset_description` | `dataset_description IS NULL OR char_length(dataset_description) <= 500` | 運用説明の上限 |

> **`is_active` の partial unique**: MVP では **付与しない**（`semantic_config` Human Review #467 No.2 踏襲。複数データセットを同時 `is_active=true` とする想定）。

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| — | — | なし | — | 状態カラムなし。`is_active` は boolean |

`evaluation_status`（`evaluation_run` 列）は `evaluation_run_status`（enum定義書 §6.12 / `packages/code-definitions/state/evaluation_run_status.yaml`）が正本であり、本テーブルには適用しない。

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | batch | BATCH-018 開始時 | — | — | `is_active = true` かつ指定 `evaluation_dataset_id`（または `dataset_name` + `dataset_version`） |
| SELECT | reco | evaluation mode 実行時（間接） | — | — | `evaluation_case` 経由でデータセットを特定 |
| INSERT | database（seed / 運用） | 新データセット追加 | 全列 | seed は Upsert 想定 | MVP 初期は評価用サンプルデータセット seed を検討（seed Task へ委譲） |
| INSERT | batch | 評価データ投入 | 全列 | `dataset_name` + `dataset_version` で Upsert 方針を検討 | Human / 運用判断。MVP では seed 中心を想定 |
| UPDATE | database / batch（運用） | 説明変更・無効化 | `dataset_description`, `is_active` | — | `dataset_name` / `dataset_version` / PK の変更は原則禁止 |
| DELETE | — | MVP では原則禁止 | — | — | 子 case / run 存在時は FK RESTRICT。`is_active = false` で無効化 |

### 12.1 データセット解決順序（BATCH-018）

BATCH-018 / MOD-BATCH-039 が評価データセットを解決する際の順序は以下とする。

1. **有効フィルタ**: `evaluation_dataset.is_active = true` のみ対象。`is_active = false` は **解決対象外**（スキップ。エラーにしない）
2. **データセット特定**:
   - workflow 入力で `evaluation_dataset_id` が指定された場合は PK で直接解決
   - 未指定時は `dataset_name` + `dataset_version` で解決（seed / 運用で事前登録済みであること）
3. **子ケース読取**: 解決した `evaluation_dataset_id` に紐づく `evaluation_case`（`is_active = true`）を読取し IF-SHARED-004 へ渡す

### 12.2 再評価方針（状態遷移設計書 §8.1.3 整合）

| 観点 | 方針 |
| ---- | ---- |
| 同一 Dataset の再評価 | 既存 `evaluation_result` / `evaluation_metric` を上書きせず、**新規 `evaluation_run` を作成**して追記 |
| Dataset version 更新 | ケース内容を変更する場合は **新しい `dataset_version`** で新規行を INSERT（既存 version 行は保持） |
| Run 再実行 | 失敗時は新しい Evaluation Run として再実行（状態遷移設計書 §11 整合） |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | **365 日**（`created_at` 基準。Human Review §17.1 No.5 確定） |
| 削除方式 | MVP では **自動 DELETE なし**（ログ・Observability設計書 §20.3） |
| 削除条件 | 将来パージ時: `is_active = false` かつ 子 `evaluation_case` / `evaluation_run` / `evaluation_result` / `evaluation_metric` が各 Retention 満了後 かつ `created_at < now() - interval '365 days'`。子行存続中は DELETE RESTRICT |
| 論理削除 | 日常運用は `is_active = false` でデータセット無効化（期日到来前の主手段） |
| アーカイブ | MVP 対象外 |

評価基準正本として **365 日** を計画値とする（`recommendation_feedback` 暫定値・`feature_distribution_metric` と同レンジ）。Batch Log 系（90 日）および `evaluation_run` 配下の `phase_log` / `error_log`（90 日）とは **別枠**。`evaluation_result`（長期保持候補）と同値とし、親子で整合させる。

> Evaluation系は MVP `partial`（テーブル一覧 §10 補足）。本番 Online 推薦の必須テーブルではないが、オフライン評価を行う場合は必要。

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `evaluation_dataset` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | Evaluation系の先頭（`evaluation_case` / `evaluation_run` より前）。物理ER §15: Batch/Log 群の前後は DDL Task で最終確定 |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | batch / reco（service role 経由） |
| 書き込み権限 | database 運用・seed、batch（評価データ投入）に限定 |
| service role利用 | BATCH-018 実行、seed 投入に限定。web client からは Direct DB アクセス不可 |
| 個人情報・機微情報 | `evaluation_case.input_condition_json` に個人情報が混入し得るが、本テーブル列には含めない |
| ログ出力制限 | 内部 PK を error ログに過剰出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / CHECK が定義どおり | migration |
| 2 | PK / UNIQUE | 同一 `dataset_name` + `dataset_version` の重複 INSERT が拒否される | migration |
| 3 | CHECK | 不正 `dataset_name` / `dataset_version` / 長すぎる `dataset_description` が拒否される | migration |
| 4 | FK 被参照 | 親行存在下で `evaluation_case` / `evaluation_run` INSERT が成功する | migration |
| 5 | DELETE RESTRICT | case / run 行存在時に親 DELETE が拒否される | migration |
| 6 | BATCH-018 整合 | `is_active = true` フィルタ・`evaluation_dataset_id` 解決がバッチ入力と整合 | integration |
| 7 | seed 整合 | MVP 評価用データセットが seed に存在（採用時） | manual |
| 8 | 権限 | web client から Direct DB アクセス不可 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review（#565）にて No.1〜No.5 を決定済み（§17.1 参照） |

### 17.1 Human Review 決定事項（Issue #565）

| No | 論点 | 決定内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | `dataset_name` + `dataset_version` の UNIQUE | **組み合わせ UNIQUE**（`uq_evaluation_dataset_name_version`）。`dataset_name` 単独 UNIQUE は採用しない | Human | §7・§10。再評価追記方針（§12.2）と整合 |
| 2 | `dataset_version` の形式 | **semver 基本形 `v1.0.0`**（`chk_dataset_version_format`）。`semantic_config_version` 同型 | Human | §10 |
| 3 | `is_active` 列の MVP 物理 DDL 採用 | **採用**（`boolean NOT NULL DEFAULT true`）。`semantic_config` / `occasion_master` 踏襲 | Human | §6・§12.1 |
| 4 | `evaluation_run.executed_by` の物理 FK | **`evaluation_run.evaluation_dataset_id` へ物理 FK ON** / `ON DELETE RESTRICT` | Human | §8.1。物理ER §9・§17.7 に反映 |
| 5 | Evaluation Dataset の Retention | **365 日**（`created_at` 基準）。MVP は自動 DELETE なし。日常は `is_active = false` | Human | §13。`evaluation_result` 長期保持候補と同値。Batch Log 90 日とは別枠 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §7 Evaluation系分類・§9 FK・Mermaid ER |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §12.1 / §12.2 Evaluation系エンティティ |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §10 No.51 Evaluation Dataset |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | `evaluation_run_status` 参照（本テーブルは enum 列なし） |
| 状態遷移設計書 | `docs/05_アプリケーション設計/アプリ/状態遷移設計書.md` | §8.1.3 再評価追記方針 |
| リソース責務定義表 | `docs/05_アプリケーション設計/アプリ/database/リソース責務定義表.md` | §6.12 Evaluation Dataset 責務 |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-DB-BATCH-018 / IF-SHARED-004 |
| バッチ処理一覧 | `docs/05_アプリケーション設計/アプリ/batch/バッチ処理一覧.md` | BATCH-018 入出力 |
| 参照テーブル定義 | `docs/06_実装設計/database/semantic_config_テーブル定義書.md` | ルート正本テーブル章構成・`is_active` / version 方針参考 |
| 子 Task | Issue #566 `evaluation_case`（§17.1 確定済み） / Issue #567 `evaluation_run` | FK / Index 引き継ぎ先 |

---

## 19. レビュー観点

- 論理ER §12.2・物理ER Mermaid ER・テーブル一覧 §10 No.51 と矛盾していない
- `evaluation_case` との 1:N `contains` 関係が明記されている（子 #566 Human Review §17.1 No.1〜No.6 確定済み）
- `evaluation_run` との 1:N `executed_by` 関係が明記されている
- 物理ER §9 FK 表に `evaluation_run.executed_by`（ON）が反映されている
- Human Review §17.1 No.1〜No.5（UNIQUE / semver / is_active / FK / Retention）が確定している
- `dataset_name` / `dataset_version` / `is_active` の MVP 方針が明記されている
- BATCH-018 / IF-DB-BATCH-018 の読取正本責務が明記されている
- 状態遷移設計書 §8.1.3 の再評価追記方針が反映されている
- `semantic_config` テーブル定義書と章構成・MVP 方針が一貫している
- Retention **365 日**（§13 / §17.1 No.5）が明記され、Batch Log 90 日と別枠である
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
