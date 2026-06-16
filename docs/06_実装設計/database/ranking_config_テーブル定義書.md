# Ranking Config テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                               |
| -------------- | ---------------------------------- |
| ドキュメントID | `DB-TBL-MVP-ranking_config`        |
| ドキュメント名 | Ranking Config テーブル定義書      |
| 対象システム   | Gift Recommendation Service MVP    |
| MVP対象        | `yes`                              |
| 作成日         | 2026-06-08                         |
| 更新日         | 2026-06-08（Human Review #454 追随） |

---

## 2. 概要

`ranking_config` は、Online 推薦における **Ranking 計算パラメータ（重み・MMR・top_k 等）** の設定正本を保持する。

reco が Recommendation Run 実行時に解決し、`recommendation_run.ranking_config_id` として再現性のために固定する。

---

## 3. 目的

- context_score / popularity_score / risk_penalty / final_score 等の Ranking 設定を DB 上で version 管理する
- Run 単位で使用した Ranking Config を再現可能にする
- Ranking定義書の MVP 初期パラメータを seed / 運用更新の正本として保持する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `ranking_config` |
| 論理テーブル名 | Ranking Config |
| 分類 | Master / Config系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | reco（Config 解決・Run 記録） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8 |

---

## 5. 用途・責務

- Ranking 計算に用いる **パラメータ JSON（`parameter_json`）** を version 単位で保持する
- `config_name` + `config_version` で設定 lineage を識別する
- `is_current = true` の行を reco が現行 Config として解決する（解決単位は §17 参照）
- Run 開始時に解決した `ranking_config_id` を `recommendation_run` に **論理参照**として記録する（MVP 初期 DDL では物理 FK なし）

### 5.1 対象外

- Matching / context_score 算出ロジック（Matching定義書の責務）
- Semantic / Feature 生成ルール（`semantic_config_version` の責務）
- LLM / Embedding モデル識別（`model_version` の責務）
- 推薦理由テンプレート（`reason_template` の責務）
- Public API による Ranking Config 公開（MVP 対象外。内部参照のみ）

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `ranking_config_id` | Ranking Config ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK。Run / Evaluation Run の再現性参照キー |
| 2 | `config_name` | Config Name | `text` | `yes` | — | — | — | — | 設定系列名。MVP 初期値 `default_ranking`。snake_case 英小文字・数字・アンダースコア |
| 3 | `config_version` | Config Version | `text` | `yes` | — | — | — | — | 系列内 version ラベル。例: `v001`。同一 `config_name` 内で一意 |
| 4 | `parameter_json` | Parameter JSON | `jsonb` | `yes` | — | — | — | — | Ranking パラメータ正本。構造は §6.1 参照 |
| 5 | `is_current` | Current Flag | `boolean` | `yes` | — | — | — | `false` | 現行 Config フラグ。`true` は `config_name` あたり最大 1 行（§10） |
| 6 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | レコード作成日時（UTC） |

### 6.1 `parameter_json` 参照構造（MVP）

物理 DDL では JSON Schema CHECK は設けず、reco / seed 側で整合を担保する。MVP で参照するキーは Ranking定義書に基づく。

| キー | 型 | MVP必須 | 説明 | 参照 |
| ---- | -- | ------- | ---- | ---- |
| `ranking_weights` | object | `yes` | context / popularity / risk の重み | Ranking定義書 §6.2 |
| `ranking_weights.context` | number | `yes` | `w_context`。初期値 `0.70` | 同上 |
| `ranking_weights.popularity` | number | `yes` | `w_popularity`。初期値 `0.20` | 同上 |
| `ranking_weights.risk` | number | `yes` | `w_risk`。初期値 `0.10` | 同上 |
| `lambda_mmr` | number | `yes` | MMR バランス。初期値 `0.75` | Ranking定義書 §10.5 |
| `mmr_candidate_limit` | integer | `yes` | MMR 適用対象件数。初期値 `50` | 同上 |
| `top_k_default` | integer | `yes` | 通常表示件数。初期値 `10` | Ranking定義書 §11.2 |
| `diversity_method` | string | `yes` | 多様性制御方式。MVP は `mmr` | Ranking定義書 §10 |

**MVP 初期値例（seed 参照用）:**

```json
{
  "ranking_weights": {
    "context": 0.70,
    "popularity": 0.20,
    "risk": 0.10
  },
  "lambda_mmr": 0.75,
  "mmr_candidate_limit": 50,
  "top_k_default": 10,
  "diversity_method": "mmr"
}
```

> **Ranking定義書 §13 との関係**: MVP DB では Ranking パラメータ（重み・MMR・top_k 等）の正本は本テーブル `parameter_json` とする。`model_version` は LLM / Embedding / Reason 生成など技術モデル識別の正本であり、Ranking パラメータは含まない。責務分担の Human 決定は §17.1 を参照。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `ranking_config_id` | サロゲート UUID | Run 再現性参照 |
| UNIQUE | `ranking_config_id` | PK と同一 | — |
| UNIQUE | `config_name`, `config_version` | 設定 lineage の一意性 | 同一系列への重複 version 禁止 |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| — | — | なし | — | 本テーブルは Config 根。他テーブルから参照される |

### 8.1 被参照（論理）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `recommendation_run` | `ranking_config_id` | used_by | `LOGICAL` | 物理ER §9。Run 再現性保持 |
| `evaluation_run` | `ranking_config_id` | used_by | `LOGICAL` | 論理ER §12.2。Evaluation 系（MVP partial） |

> MVP 初期 DDL では物理 FK を張らない。整合は reco / batch 側 Config 解決 + seed 正本 + Run INSERT 時の存在確認で担保する。`evaluation_run` 側 Index は `idx_evaluation_run_ranking_config`（`evaluation_run_テーブル定義書` §9・§17.1 No.3 確定）。

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `ranking_config_pkey` | `ranking_config_id` | btree（PK） | 主キー | 自動生成 |
| `uq_ranking_config_name_version` | `config_name`, `config_version` | btree（unique） | 設定 lineage 一意 | §7 |
| `uq_ranking_config_current_per_name` | `config_name` | btree（unique, partial） | 現行 Config 解決 | `WHERE is_current = true` |
| `idx_ranking_config_name_created` | `config_name`, `created_at` DESC | btree | version 履歴参照 | 運用・監査 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `ranking_config_pkey` | PRIMARY KEY | `ranking_config_id` | 主キー | — |
| `uq_ranking_config_name_version` | UNIQUE | `config_name`, `config_version` | lineage 一意 | — |
| `uq_ranking_config_current_per_name` | UNIQUE（partial） | `config_name` | `is_current = true` は config_name あたり 1 行 | MVP 方針。§17 No.2 |
| `chk_config_name_format` | CHECK | `config_name` | `config_name ~ '^[a-z][a-z0-9_]*$'` | snake_case |
| `chk_config_version_format` | CHECK | `config_version` | `config_version ~ '^v[0-9]{3,}$'` | 例: `v001` |
| `chk_parameter_json_object` | CHECK | `parameter_json` | `jsonb_typeof(parameter_json) = 'object'` | 配列・スカラー禁止 |
| `chk_ranking_weights_sum` | CHECK | `parameter_json` | MVP 重み合計 ≈ 1.0（許容誤差 0.001） | `(parameter_json->'ranking_weights'->>'context')::numeric + ...` |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| — | — | なし | — | 状態カラムなし。`is_current` は boolean |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | reco | Run 開始時 | — | — | `is_current = true` かつ対象 `config_name` を解決 |
| SELECT | reco | 再現参照 | — | — | `ranking_config_id` 指定 |
| INSERT | database（seed / 運用） | 新 version 追加 | 全列 | seed は Upsert 想定 | 既存 version の UPDATE 禁止方針 |
| UPDATE | database（運用） | 現行切替のみ | `is_current` | トランザクション内で旧 current を false、新 current を true | パラメータ変更は新 version INSERT |
| DELETE | — | MVP では原則禁止 | — | — | 履歴保持のため物理 DELETE しない |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（設定正本・再現性） |
| 削除方式 | 物理 DELETE 原則禁止 |
| 削除条件 | — |
| 論理削除 | なし（version 追加で履歴管理） |
| アーカイブ | MVP 対象外 |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `ranking_config` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: Master / Config 群（`model_version` と同順、`reason_template` より前後は DDL Task で確定） |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | reco（service role 経由） |
| 書き込み権限 | database 運用・seed のみ。Online / Batch 実行中の DML 更新なし |
| service role利用 | reco Config 解決、seed 投入に限定 |
| 個人情報・機微情報 | 含まない |
| ログ出力制限 | `parameter_json` 全文を error ログに過剰出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / CHECK / partial unique が定義どおり | migration |
| 2 | PK / UNIQUE | 同一 `config_name` + `config_version` の重複 INSERT が拒否される | migration |
| 3 | is_current | 同一 `config_name` で `is_current=true` が 2 行以上になる INSERT/UPDATE が拒否される | migration |
| 4 | CHECK | 不正 `parameter_json`（重み合計不一致等）が拒否される | migration |
| 5 | reco 整合 | Run 開始時に解決した `ranking_config_id` が Run に記録される | integration |
| 6 | seed 整合 | Ranking定義書 MVP 初期値と seed の `parameter_json` が一致 | manual |
| 7 | 権限 | web client から Direct DB アクセス不可 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review (#454) にて No.1 を決定済み（下記参照） |
| 2 | `is_current` の解決単位 | MVP では `config_name` 単位 partial unique を採用。全体 1 現行も選択肢 | Human | seed Task 前 | 本定義書 §10 は config_name 単位 |
| 3 | `parameter_json` の MVP 必須キー | CHECK で重み合計のみ担保。追加キー（threshold_rule 等）は将来拡張 | Human | seed Task 前 | §6.1 を seed 正本候補とする |

### 17.1 Human Review 決定事項（PR #454）

| No | 論点 | 決定内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | `ranking_config` と `model_version` の責務分担 | `model_version` は LLM / Embedding / Reason 生成など外部モデル version 正本。Ranking パラメータ（重み・MMR・top_k 等）は含まない。`ranking_config` は Ranking パラメータ正本。`config_name` 単位で `is_current` を解決する。両者は独立 Config 次元で FK なし。Run 再現性は `recommendation_run.model_version_id` + `recommendation_run.ranking_config_id` で保持する。Ranking定義書 §13 の旧表現は MVP DB 正本として `ranking_config` にマッピングする | Human | Ranking定義書を同一 PR で追随更新 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8 テーブル一覧・§9 FK・§11 制約方針 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §11.1 エンティティ属性 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §9 Master / Config系 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | コード定義正本（本テーブルは enum 列なし） |
| Ranking定義書 | `docs/04_ドメインモデル設計/Ranking定義書.md` | パラメータ・重み・MMR・top_k |
| 参照テーブル定義 | `docs/06_実装設計/database/relationship_master_テーブル定義書.md` | Master / Config 系構成踏襲 |
| 参照テーブル定義 | `docs/06_実装設計/database/occasion_master_テーブル定義書.md` | Master / Config 系構成踏襲 |

---

## 19. レビュー観点

- 論理ER §11.1・物理ER §8・§9・テーブル一覧 §9 と矛盾していない（`model_version` との責務分担は §17.1 の Human 決定に基づく）
- `ranking_config_id` / `config_name` / `config_version` / `parameter_json` / `is_current` / `created_at` がすべて定義されている
- `recommendation_run.ranking_config_id` の LOGICAL 参照方針が明記されている
- Ranking定義書 MVP 初期パラメータが `parameter_json` 参照として明記されている
- `relationship_master` / `occasion_master` テーブル定義書と章構成・MVP 方針が一貫している
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
