# Reason Template テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                               |
| -------------- | ---------------------------------- |
| ドキュメントID | `DB-TBL-MVP-reason_template`       |
| ドキュメント名 | Reason Template テーブル定義書     |
| 対象システム   | Gift Recommendation Service MVP    |
| MVP対象        | `yes`                              |
| 作成日         | 2026-06-08                         |
| 更新日         | 2026-06-08                         |

---

## 2. 概要

`reason_template` は、Online 推薦における **推薦理由文（Reason）生成テンプレート** の設定正本を保持する。

reco が Reason Generator（MOD-RECO-023）実行時に解決し、`recommendation_reason.template_id` および `reason_basis_json` に使用テンプレートを記録する。Public API には公開しない（内部 Config）。

---

## 3. 目的

- Reason 生成に用いるテンプレート本文・適用条件・表現トーンを DB 上で管理する
- `relationship_master` / `occasion_master` / `model_version` と整合したテンプレート解決の正本を提供する
- `recommendation_reason` が参照する template 識別子の整合基盤とする

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `reason_template` |
| 論理テーブル名 | Reason Template |
| 分類 | Master / Config系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | reco（Config 解決・Reason 生成） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8 |

---

## 5. 用途・責務

- **template_type**（summary / detail / point / caution）ごとの文面テンプレートを保持する
- **relationship_code / occasion_code / feature_code** により適用条件を絞り込む（NULL はワイルドカード）
- **`template_body`** にプレースホルダ付きテンプレート本文を保持する（Reason生成定義書の `template_text` に相当）
- **`is_active = true`** の行のみを reco が解決対象とする
- `recommendation_reason.template_id` は本テーブルの `reason_template_id` を **論理参照**する（MVP 初期 DDL では物理 FK なし）

### 5.1 論理ER §11.1 と Reason生成定義書 §15.2 の差分整理（MVP 統合案）

| 観点 | 論理ER §11.1 | Reason生成定義書 §15.2 | MVP 物理カラム案 |
| ---- | ------------ | ---------------------- | ---------------- |
| テンプレート ID | `reason_template_id` | `reason_template_id` | `reason_template_id`（uuid PK） |
| 識別名 | `template_name` | —（`reason_basis.template_id` は文字列識別子） | `template_name`（UNIQUE。例: `social_reason_boss_thanks_v1`） |
| 種別 | `template_type` | `template_type` | `template_type` |
| 本文 | `template_body` | `template_text` | `template_body`（`template_text` は論理別名） |
| 適用 Relationship | — | `relationship_code` | `relationship_code`（nullable） |
| 適用 Occasion | — | `occasion_code` | `occasion_code`（nullable） |
| 適用 Feature | — | `feature_code` | `feature_code`（nullable） |
| 表現トーン | — | `tone` | `tone`（nullable） |
| 適用モデル | — | `model_version_id` | `model_version_id`（uuid, nullable） |
| 有効フラグ | `is_active` | `is_active` | `is_active` |
| 作成日時 | `created_at` | — | `created_at` |

> **統合方針（MVP 案）**: 論理ER の簡易属性に、Reason生成定義書の条件列・トーン・モデル参照を追加する。`template_name` は `reason_basis_json.template_id` の文字列識別子と対応させ、UUID PK とは別に保持する。

### 5.2 対象外

- Reason 生成ロジック・Badge マッピング（Reason生成定義書 §8〜§16 の責務）
- `recommendation_reason` の Snapshot 列定義（別テーブル定義 Task）
- LLM prompt version 管理（`model_version` / reco 実装の責務）
- Public API による Reason Template 公開（MVP 対象外。内部参照のみ）
- YAML / JSON ファイルによるテンプレート正本（§17 No.4 で採用方針を Human Review）

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `reason_template_id` | Reason Template ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK。`recommendation_reason.template_id` の参照キー |
| 2 | `template_name` | Template Name | `text` | `yes` | — | — | `yes` | — | 業務識別子。snake_case 英小文字・数字・アンダースコア。`reason_basis_json.template_id` と対応 |
| 3 | `template_type` | Template Type | `text` | `yes` | — | — | — | — | テンプレート種別。`summary` / `detail` / `point` / `caution`（§11） |
| 4 | `template_body` | Template Body | `text` | `yes` | — | — | — | — | テンプレート本文。プレースホルダ可。Reason生成定義書の `template_text` に相当 |
| 5 | `relationship_code` | Relationship Code | `text` | `no` | — | `LOGICAL` | — | `NULL` | 適用 Relationship。NULL は全 Relationship。`relationship_master.relationship_code` を論理参照 |
| 6 | `occasion_code` | Occasion Code | `text` | `no` | — | `LOGICAL` | — | `NULL` | 適用 Occasion。NULL は全 Occasion。`occasion_master.occasion_code` を論理参照 |
| 7 | `feature_code` | Feature Code | `text` | `no` | — | — | — | `NULL` | 適用 Feature。NULL は Feature 非依存。MVP feature 名（§11） |
| 8 | `tone` | Tone | `varchar(50)` | `no` | — | — | — | `NULL` | 表現トーン（例: `丁寧で控えめ`）。Reason生成定義書 §14 参照 |
| 9 | `model_version_id` | Model Version ID | `uuid` | `no` | — | `LOGICAL` | — | `NULL` | 適用モデル version。`model_version.model_version_id` を論理参照 |
| 10 | `is_active` | Active Flag | `boolean` | `yes` | — | — | — | `true` | 有効フラグ。`false` の行は解決対象外 |
| 11 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | レコード作成日時（UTC） |

### 6.1 `template_body` 参照構造（MVP）

物理 DDL では JSON Schema CHECK は設けず、reco / seed 側で整合を担保する。MVP ではプレーンテキストまたは軽量プレースホルダを想定する。

| プレースホルダ例 | 用途 |
| ---------------- | ---- |
| `{relationship_label}` | Relationship 表示名の差し込み |
| `{occasion_label}` | Occasion 表示名の差し込み |
| `{feature_expression}` | Feature 表示表現の差し込み |
| `{item_name}` | 商品名（Snapshot 由来） |

**MVP 初期値例（seed 参照用）:**

```text
{relationship_label}の方への{occasion_label}に、{feature_expression}が伝わる贈り物としておすすめです。
```

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `reason_template_id` | サロゲート UUID | `recommendation_reason.template_id` の参照キー |
| UNIQUE | `reason_template_id` | PK と同一 | — |
| UNIQUE | `template_name` | 業務識別子の一意性 | `reason_basis_json.template_id` との対応 |

> **template 解決キー（MVP 案）**: reco は Run 時に `template_type` + `relationship_code` + `occasion_code` + `feature_code`（NULL 許容）+ `is_active = true` で候補を絞り込み、一致件数が複数の場合は `template_name` または優先度ルールで 1 件に決定する。詳細は §17 No.2。

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `relationship_code` | `relationship_master.relationship_code` | なし | `LOGICAL` | Human Review #443 方針踏襲。MVP は物理 FK なし |
| `occasion_code` | `occasion_master.occasion_code` | なし | `LOGICAL` | Human Review #448 方針踏襲。MVP は物理 FK なし |
| `model_version_id` | `model_version.model_version_id` | なし | `LOGICAL` | MVP は物理 FK なし。seed / reco validation で担保 |

### 8.1 被参照（論理）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `recommendation_reason` | `template_id` | used_by | `LOGICAL` | Reason生成定義書 §15.1。`reason_template_id`（uuid）を格納する案。§17 No.1 |

> MVP 初期 DDL では物理 FK を張らない。整合は reco 側テンプレート解決 + seed 正本 + Reason INSERT 時の存在確認で担保する。

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `reason_template_pkey` | `reason_template_id` | btree（PK） | 主キー | 自動生成 |
| `uq_reason_template_name` | `template_name` | btree（unique） | 業務識別子一意 | §7 |
| `idx_reason_template_resolve` | `template_type`, `relationship_code`, `occasion_code`, `feature_code`, `is_active` | btree | テンプレート解決（§7） | 物理ER §10 は個別 Index 未記載。本 Task で追加方針 |
| `idx_reason_template_model_version` | `model_version_id` | btree | model_version 単位の参照 | nullable 列。部分利用時の JOIN 補助 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `reason_template_pkey` | PRIMARY KEY | `reason_template_id` | 主キー | — |
| `uq_reason_template_name` | UNIQUE | `template_name` | 業務識別子一意 | — |
| `chk_template_name_format` | CHECK | `template_name` | `template_name ~ '^[a-z][a-z0-9_]*$'` | snake_case。先頭英字 |
| `chk_template_type` | CHECK | `template_type` | `template_type IN ('summary', 'detail', 'point', 'caution')` | Reason生成定義書 §15.2 |
| `chk_template_body_length` | CHECK | `template_body` | `char_length(template_body) BETWEEN 1 AND 2000` | MVP 上限（§17 で調整可） |
| `chk_relationship_code_format` | CHECK | `relationship_code` | `relationship_code IS NULL OR relationship_code ~ '^[a-z][a-z0-9_]*$'` | relationship_master と同一形式 |
| `chk_occasion_code_format` | CHECK | `occasion_code` | `occasion_code IS NULL OR occasion_code ~ '^[a-z][a-z0-9_]*$'` | occasion_master と同一形式 |
| `chk_feature_code` | CHECK | `feature_code` | `feature_code IS NULL OR feature_code IN ('formality', 'safety', 'brand_appropriateness', 'emotion', 'novelty', 'intimacy', 'symbolic_identity', 'story_richness')` | MVP feature 固定名 |
| `chk_tone_length` | CHECK | `tone` | `tone IS NULL OR char_length(tone) BETWEEN 1 AND 50` | — |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `template_type` | reason_template_type | Reason生成定義書 §15.2 | `summary`, `detail`, `point`, `caution` | CHECK 制約で担保 |
| `feature_code` | MVP feature 名 | Featureルール定義書 / AGENTS.md | Social 3 + Symbolic 5（§10 `chk_feature_code`） | nullable |
| — | — | — | `is_active` は boolean | 状態 enum なし |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | reco | Reason 生成時 | — | — | `is_active = true` かつ適用条件で解決（§7） |
| SELECT | reco | Config 解決（MOD-RECO-003） | — | — | IF-DB-RECO-001。Run 開始前の参照 |
| INSERT | database（seed / 運用） | 新規テンプレート追加 | 全列 | seed は Upsert 想定 | MVP では管理 UI なし |
| UPDATE | database（seed / 運用） | 文面修正・無効化 | `template_body`, `tone`, `is_active` 等 | Upsert 想定 | 識別子変更は新規 INSERT 推奨 |
| DELETE | — | MVP では原則禁止 | — | — | `is_active = false` で無効化 |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（設定正本） |
| 削除方式 | 物理 DELETE 原則禁止 |
| 削除条件 | — |
| 論理削除 | `is_active = false` で無効化 |
| アーカイブ | MVP 対象外 |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `reason_template` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: Master / Config 群。`relationship_master` / `occasion_master` / `model_version` の後、`recommendation_reason` より前 |
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
| ログ出力制限 | `template_body` 全文を error ログに過剰出力しない |
| Public API | 非公開（内部 Config） |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / CHECK が定義どおり | migration |
| 2 | PK / UNIQUE | 同一 `template_name` の重複 INSERT が拒否される | migration |
| 3 | CHECK | 不正 `template_type` / `feature_code` が拒否される | migration |
| 4 | LOGICAL 参照 | 存在しない `relationship_code` / `occasion_code` が seed で投入されない | manual |
| 5 | reco 整合 | Reason 生成時に解決した `reason_template_id` が `recommendation_reason.template_id` に記録される | integration |
| 6 | seed 整合 | Reason生成定義書の template 種別・代表テンプレートが seed に存在 | manual |
| 7 | 権限 | web client から Direct DB アクセス不可 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | 論理ER §11.1 と Reason生成定義書 §15.2 のカラム統合 | 論理ER は `template_name` / `template_body` のみ。Reason生成定義書は条件列・`template_text`・`tone`・`model_version_id` を追加 | Human | DDL Task 前 | 本定義書 §5.1 / §6 は MVP 統合案。`template_body` = `template_text` と明記 |
| 2 | template 解決キー | `template_name` 単独参照か、条件列（type + relationship + occasion + feature）の組み合わせ解決か | Human | seed Task 前 | 本定義書 §7 は条件列解決 + `template_name` UNIQUE を MVP 案とする |
| 3 | `recommendation_reason.template_id` の型 | Reason生成定義書は文字列識別子例。物理列は uuid（`reason_template_id`）か `template_name` か | Human | recommendation_reason 定義 Task 前 | 推奨: uuid 格納。`reason_basis_json.template_id` は `template_name` を併記 |
| 4 | seed 初期範囲 | MVP で投入する template_type / relationship / occasion の組み合わせ範囲 | Human | seed Task 前 | 推奨: 主要 pair（上司×お礼 等）の `summary` のみ先行投入 |
| 5 | YAML seed vs DB 管理 | Reason生成定義書 §15.3 は YAML/JSON + Python 生成を高適性とする。DB 正本との役割分担 | Human | seed Task 前 | 推奨: DB を正本、YAML は seed 投入ソース（変換スクリプトは seed Task） |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8 テーブル一覧・§9 FK・§11 制約方針 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §11.1 エンティティ属性 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §9 Master / Config系 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | コード定義正本（`template_type` は CHECK で担保） |
| Reason生成定義書 | `docs/04_ドメインモデル設計/Reason生成定義書.md` | §14 reason_basis / §15.1〜§15.3 template 論理項目 |
| 参照テーブル定義 | `docs/06_実装設計/database/relationship_master_テーブル定義書.md` | LOGICAL 参照・Master 系構成踏襲 |
| 参照テーブル定義 | `docs/06_実装設計/database/occasion_master_テーブル定義書.md` | LOGICAL 参照・Master 系構成踏襲 |
| 参照テーブル定義 | `docs/06_実装設計/database/model_version_テーブル定義書.md` | `model_version_id` LOGICAL 参照 |
| 参照テーブル定義 | `docs/06_実装設計/database/ranking_config_テーブル定義書.md` | Config 系章構成参考 |

---

## 19. レビュー観点

- 論理ER §11.1・物理ER §8・テーブル一覧 §9・Reason生成定義書 §15.2 と矛盾していない
- `reason_template_id` / `template_name` / `template_type` / `template_body` / `is_active` / `created_at` が定義されている
- Reason生成定義書の条件列（`relationship_code` / `occasion_code` / `feature_code` / `tone` / `model_version_id`）の MVP 採否が明記されている
- `recommendation_reason.template_id` の LOGICAL 参照方針が明記されている
- `relationship_master` / `occasion_master` / `model_version` への LOGICAL 参照が Human Review #443/#448 方針と一貫している
- Public API 非公開（内部 Config）が明記されている
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
