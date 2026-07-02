# Matching Config テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                               |
| -------------- | ---------------------------------- |
| ドキュメントID | `DB-TBL-MVP-matching_config`       |
| ドキュメント名 | Matching Config テーブル定義書     |
| 対象システム   | Gift Recommendation Service MVP    |
| MVP対象        | `yes`                              |
| 作成日         | 2026-07-02                         |
| 更新日         | 2026-07-02（Issue #906 初版）      |

---

## 2. 概要

`matching_config` は、Online 推薦における **Matching 計算パラメータ（Social / Symbolic Feature 重み・距離方式・閾値等）** の設定正本を保持する。

reco が Recommendation Run 実行時に解決し、`recommendation_run.matching_config_id` として再現性のために固定する。

---

## 3. 目的

- Social / Symbolic 集約重みおよび Matching 算出パラメータを DB 上で version 管理する
- Run 単位で使用した Matching Config を再現可能にする
- Matching定義書 §7.2 / §8.2 / §13.1 の MVP 初期パラメータを seed / 運用更新の正本として保持する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `matching_config` |
| 論理テーブル名 | Matching Config |
| 分類 | Master / Config系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | reco（Config 解決・Run 記録） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8 |

---

## 5. 用途・責務

- Matching 計算に用いる **パラメータ JSON（`parameter_json`）** を version 単位で保持する
- `config_name` + `config_version` で設定 lineage を識別する
- `is_current = true` の行を reco が現行 Config として解決する（解決単位は §17 参照）
- Run 開始時に解決した `matching_config_id` を `recommendation_run` に **論理参照**として記録する（MVP 増分 DDL では物理 FK なし）

### 5.1 対象外

- Ranking / final_score 算出パラメータ（`ranking_config` の責務）
- Semantic / Feature 生成ルール（`semantic_config_version` の責務）
- LLM / Embedding モデル識別（`model_version` の責務）
- Feature 正規化パラメータ（`feature_normalization_version` の責務）
- Public API による Matching Config 公開（MVP 対象外。内部参照のみ）

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `matching_config_id` | Matching Config ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK。Run / Evaluation Run の再現性参照キー |
| 2 | `config_name` | Config Name | `text` | `yes` | — | — | — | — | 設定系列名。MVP 初期値 `mvp_matching_config`。snake_case 英小文字・数字・アンダースコア |
| 3 | `config_version` | Config Version | `text` | `yes` | — | — | — | — | 系列内 version ラベル。例: `v001`。同一 `config_name` 内で一意 |
| 4 | `parameter_json` | Parameter JSON | `jsonb` | `yes` | — | — | — | — | Matching パラメータ正本。構造は §6.1 参照 |
| 5 | `is_current` | Current Flag | `boolean` | `yes` | — | — | — | `false` | 現行 Config フラグ。`true` は `config_name` あたり最大 1 行（§10） |
| 6 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | レコード作成日時（UTC） |

### 6.1 `parameter_json` 参照構造（MVP）

物理 DDL では JSON Schema CHECK は設けず、reco / seed 側で整合を担保する。MVP で参照するキーは Matching定義書 §13.1 に基づく。

| キー | 型 | MVP必須 | 説明 | 参照 |
| ---- | -- | ------- | ---- | ---- |
| `social_feature_weights` | object | `yes` | Social 内 Feature 重み | Matching定義書 §7.2 |
| `social_feature_weights.formality` | number | `yes` | 初期値 `0.333`（均等） | 同上 |
| `social_feature_weights.safety` | number | `yes` | 初期値 `0.333` | 同上 |
| `social_feature_weights.brand_appropriateness` | number | `yes` | 初期値 `0.333` | 同上 |
| `symbolic_feature_weights` | object | `yes` | Symbolic 内 Feature 重み | Matching定義書 §8.2 |
| `symbolic_feature_weights.emotion` | number | `yes` | 初期値 `0.200`（均等） | 同上 |
| `symbolic_feature_weights.novelty` | number | `yes` | 初期値 `0.200` | 同上 |
| `symbolic_feature_weights.intimacy` | number | `yes` | 初期値 `0.200` | 同上 |
| `symbolic_feature_weights.symbolic_identity` | number | `yes` | 初期値 `0.200` | 同上 |
| `symbolic_feature_weights.story_richness` | number | `yes` | 初期値 `0.200` | 同上 |
| `distance_method` | string | `no` | 距離計算方式。MVP は `absolute_distance` | Matching定義書 §5.2 |
| `feature_match_method` | string | `no` | 一致度変換。MVP は `one_minus_distance` | Matching定義書 §6.2 |
| `context_score_formula` | string | `no` | Context Score 算出式識別子 | Matching定義書 §9 |
| `avoid_similarity_method` | string | `no` | avoid_similarity 算出方式 | Matching定義書 §10 |
| `threshold_rule` | object | `no` | strong / weak match 閾値 | Matching定義書 §12.3 |
| `threshold_rule.strong_match` | number | `no` | 初期値 `0.80` | 同上 |
| `threshold_rule.normal_match` | number | `no` | 初期値 `0.60` | 同上 |

**MVP 初期値例（seed 参照用）:**

```json
{
  "distance_method": "absolute_distance",
  "feature_match_method": "one_minus_distance",
  "social_feature_weights": {
    "formality": 0.333,
    "safety": 0.333,
    "brand_appropriateness": 0.333
  },
  "symbolic_feature_weights": {
    "emotion": 0.200,
    "novelty": 0.200,
    "intimacy": 0.200,
    "symbolic_identity": 0.200,
    "story_richness": 0.200
  },
  "context_score_formula": "lambda_ctx_weighted",
  "avoid_similarity_method": "mvp_default",
  "threshold_rule": {
    "strong_match": 0.80,
    "normal_match": 0.60
  }
}
```

> **Matching定義書 §13 との関係**: MVP DB では Matching パラメータ（Social / Symbolic 集約重み・距離方式・閾値等）の正本は本テーブル `parameter_json` とする。`model_version` は LLM / Embedding 等の技術モデル version 正本であり、Matching パラメータは含まない。責務分担の Human 決定は §17.1 を参照。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `matching_config_id` | サロゲート UUID | Run 再現性参照 |
| UNIQUE | `matching_config_id` | PK と同一 | — |
| UNIQUE | `config_name`, `config_version` | 設定 lineage の一意性 | 同一系列への重複 version 禁止 |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| — | — | なし | — | 本テーブルは Config 根。他テーブルから参照される |

### 8.1 被参照（論理）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `recommendation_run` | `matching_config_id` | used_by | `LOGICAL` | 物理ER §9。Run 再現性保持 |
| `recommendation_result` | `matching_config_id` | used_by | `LOGICAL` | Run スナップショット列コピー |
| `evaluation_run` | `matching_config_id` | used_by | `LOGICAL` | 論理ER §12.2。Evaluation 系（MVP partial） |

> MVP 増分 DDL では物理 FK を張らない。整合は reco / batch 側 Config 解決 + seed 正本 + Run INSERT 時の存在確認で担保する。`evaluation_run` 側 Index は `idx_evaluation_run_matching_config`（`evaluation_run_テーブル定義書` §9）。

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `matching_config_pkey` | `matching_config_id` | btree（PK） | 主キー | 自動生成 |
| `uq_matching_config_name_version` | `config_name`, `config_version` | btree（unique） | 設定 lineage 一意 | §7 |
| `uq_matching_config_current_per_name` | `config_name` | btree（unique, partial） | 現行 Config 解決 | `WHERE is_current = true` |
| `idx_matching_config_name_created` | `config_name`, `created_at` DESC | btree | version 履歴参照 | 運用・監査 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `matching_config_pkey` | PRIMARY KEY | `matching_config_id` | 主キー | — |
| `uq_matching_config_name_version` | UNIQUE | `config_name`, `config_version` | lineage 一意 | — |
| `uq_matching_config_current_per_name` | UNIQUE（partial） | `config_name` | `is_current = true` は config_name あたり 1 行 | MVP 方針。§17 No.2 |
| `chk_matching_config_name_format` | CHECK | `config_name` | `config_name ~ '^[a-z][a-z0-9_]*$'` | snake_case |
| `chk_matching_config_version_format` | CHECK | `config_version` | `config_version ~ '^v[0-9]{3,}$'` | 例: `v001` |
| `chk_matching_parameter_json_object` | CHECK | `parameter_json` | `jsonb_typeof(parameter_json) = 'object'` | 配列・スカラー禁止 |
| `chk_social_feature_weights_sum` | CHECK | `parameter_json` | Social 重み合計 ≈ 1.0（許容誤差 0.001） | §6.1 |
| `chk_symbolic_feature_weights_sum` | CHECK | `parameter_json` | Symbolic 重み合計 ≈ 1.0（許容誤差 0.001） | §6.1 |

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
| SELECT | reco | 再現参照 | — | — | `matching_config_id` 指定 |
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
| DDL対象 | `matching_config` + Run 再現性列（`matching_config_id`） |
| migration単位 | D14 増分（1 論理変更 = 1 migration） |
| 適用順序 | D01〜D13 適用後。`ranking_config` と同型の Master / Config 追加 |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（CREATE + ADD COLUMN） |

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
| 5 | reco 整合 | Run 開始時に解決した `matching_config_id` が Run に記録される | integration |
| 6 | seed 整合 | Matching定義書 MVP 初期値と seed の `parameter_json` が一致 | manual |
| 7 | 権限 | web client から Direct DB アクセス不可 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human 判断（案 B）にて No.1 を決定済み（下記参照） |
| 2 | `is_current` の解決単位 | MVP では `config_name` 単位 partial unique を採用。全体 1 現行も選択肢 | Human | seed Task 前 | 本定義書 §10 は config_name 単位 |
| 3 | `parameter_json` の MVP 必須キー | CHECK で Social / Symbolic 重み合計のみ担保。追加キー（threshold_rule 等）は将来拡張 | Human | seed Task 前 | §6.1 を seed 正本候補とする |

### 17.1 Human Review 決定事項（Issue #906 案 B）

| No | 論点 | 決定内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | `matching_config` と `model_version` の責務分担 | `model_version` は LLM / Embedding 等の技術モデル version 正本。Matching パラメータ（Social / Symbolic 集約重み・距離方式・閾値等）は含まない。`matching_config` は Matching パラメータ正本。`config_name` 単位で `is_current` を解決する。`ranking_config` と対称の独立 Config 次元で FK なし。Run 再現性は `recommendation_run.model_version_id` + `recommendation_run.matching_config_id` + `recommendation_run.ranking_config_id` で保持する。Matching定義書 §13.1 の論理表現は MVP DB 正本として `matching_config` にマッピングする | Human | Matching定義書 §13.1 を同一 PR で追随更新 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8 テーブル一覧・§9 FK・§11 制約方針 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §11.1 エンティティ属性 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §9 Master / Config系 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | コード定義正本（本テーブルは enum 列なし） |
| Matching定義書 | `docs/04_ドメインモデル設計/Matching定義書.md` | パラメータ・重み・閾値 |
| 参照対称設計 | `docs/06_実装設計/database/ranking_config_テーブル定義書.md` | Config 系構成踏襲 |
| MOD-RECO-015 | `docs/06_実装設計/reco/MOD-RECO-015_Meaning Match Aggregatorモジュール仕様書.md` | matching_config 経由解決の用語 |

---

## 19. レビュー観点

- 論理ER §11.1・物理ER §8・§9・テーブル一覧 §9 と矛盾していない（`model_version` / `ranking_config` との責務分担は §17.1 の Human 決定に基づく）
- `matching_config_id` / `config_name` / `config_version` / `parameter_json` / `is_current` / `created_at` がすべて定義されている
- `recommendation_run.matching_config_id` の LOGICAL 参照方針が明記されている
- Matching定義書 MVP 初期パラメータが `parameter_json` 参照として明記されている
- `ranking_config_テーブル定義書` と章構成・MVP 方針が一貫している
- DDL Task が CREATE TABLE / ADD COLUMN を起こせる粒度である
- secret や `.env` 実値が含まれていない
