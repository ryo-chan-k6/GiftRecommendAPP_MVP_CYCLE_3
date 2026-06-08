# Reason Template テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                                         |
| -------------- | ------------------------------------------------------------ |
| ドキュメントID | `DB-TBL-MVP-reason_template`                                 |
| ドキュメント名 | Reason Template テーブル定義書                               |
| 対象システム   | Gift Recommendation Service MVP                              |
| MVP対象        | `yes`                                                        |
| 作成日         | 2026-06-08                                                   |
| 更新日         | 2026-06-08（Human Review 議論反映・AI Review 追随: 版管理・解決優先順位） |

---

## 2. 概要

`reason_template` は、Online 推薦における **推薦理由文（Reason）生成テンプレート** の設定正本を保持する。

reco が Reason Generator（MOD-RECO-023）実行時に解決し、`recommendation_reason.template_id` および `reason_basis_json` に使用テンプレートを記録する。Public API には公開しない（内部 Config）。

`model_version` テーブルとは独立した設定正本とし、テンプレートの版は本テーブル内の `template_name` + `template_version` で管理する。

---

## 3. 目的

- Reason 生成に用いるテンプレート本文・適用条件を DB 上で管理する
- `relationship_master` / `occasion_master` と整合したテンプレート解決の正本を提供する
- `template_name` + `template_version` による版管理と、PDCA に必要な利用記録の整合基盤とする
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
| 主な参照主体 | reco（Reason 生成時のテンプレート解決） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8 |

---

## 5. 用途・責務

- **template_type**（summary / detail / point / caution）ごとの文面テンプレートを保持する
- **relationship_code / occasion_code / feature_code** により適用条件を絞り込む（NULL はワイルドカード）
- **`template_body`** にプレースホルダ付きテンプレート本文を保持する（Reason生成定義書の `template_text` に相当）
- **`template_name` + `template_version`** でテンプレートの版を管理する（§5.3）
- **`is_active = true`** の行のみを reco が解決対象とする
- reco 解決時、`recommendation_reason.template_id` は本テーブルの `reason_template_id`（uuid）を **論理参照**する（§8.1）。MVP 初期 DDL では物理 FK なし

### 5.1 論理ER §11.1 と Reason生成定義書 §15.2 の差分整理（MVP 統合案）

| 観点 | 論理ER §11.1 | Reason生成定義書 §15.2 | MVP 物理カラム案 |
| ---- | ------------ | ---------------------- | ---------------- |
| テンプレート ID | `reason_template_id` | `reason_template_id` | `reason_template_id`（uuid PK） |
| 識別名 | `template_name` | —（`reason_basis.template_id` は文字列識別子） | `template_name`（版を含めない安定 ID。例: `social_reason_boss_thanks`） |
| 版 | — | — | `template_version`（integer。§5.3） |
| 種別 | `template_type` | `template_type` | `template_type` |
| 本文 | `template_body` | `template_text` | `template_body`（`template_text` は論理別名） |
| 適用 Relationship | — | `relationship_code` | `relationship_code`（nullable） |
| 適用 Occasion | — | `occasion_code` | `occasion_code`（nullable） |
| 適用 Feature | — | `feature_code` | `feature_code`（nullable） |
| 表現トーン | — | `tone` | **不採用**（§5.4） |
| 適用モデル | — | `model_version_id` | **不採用**（§5.4） |
| 有効フラグ | `is_active` | `is_active` | `is_active` |
| 作成日時 | `created_at` | — | `created_at` |

> **統合方針（MVP）**: 論理ER の簡易属性に、Reason生成定義書の条件列（`relationship_code` / `occasion_code` / `feature_code`）を追加する。`tone` / `model_version_id` は Human Review にて不採用とする。`template_body` = `template_text`（論理別名）。

### 5.2 対象外

- Reason 生成ロジック・Badge マッピング（Reason生成定義書 §8〜§16 の責務）
- `recommendation_reason` の Snapshot 列定義（別テーブル定義 Task）
- LLM prompt version 管理（reco 実装の責務）
- `model_version` テーブルとの参照・依存（本テーブルは独立正本）
- Run / Result レベルの集合版 ID（`reason_template_version_id`。MVP 非採用。§5.3）
- Public API による Reason Template 公開（MVP 対象外。内部参照のみ）
- YAML / JSON ファイルによるテンプレート正本（§17 No.3 で採用方針を Human Review）

### 5.3 版管理・利用記録（Human Review 決定）

テンプレートの版管理と利用記録は以下とする。

| 観点 | 方針 |
| ---- | ---- |
| 版の単位 | `template_name`（安定 ID。版サフィックス `_v1` 等は含めない）+ `template_version`（整数。1 から採番） |
| 行の一意性 | `(template_name, template_version)` で一意 |
| 現行版 | 同一 `template_name` について **現行版は 1 件のみ** `is_active = true` とする（seed / 運用ルール） |
| 改訂 | 文面変更時は `template_version` をインクリメントした **新規 INSERT**。旧版は `is_active = false` |
| 利用記録（方式 B） | **Reason 単位**で記録。Run / Result レベルの集合版 ID は MVP では採用しない |
| `recommendation_reason.template_id` | `reason_template_id`（uuid）を格納 |
| `reason_basis_json` | `template_name` + `template_version` を **必須** で併記（§6.2） |

**PDCA 改善ループ（運用イメージ）:**

```text
低評価 Reason 分析
→ reason_basis_json の template_name / template_version で特定
→ template_body 修正版を template_version + 1 で INSERT
→ 旧版 is_active = false
→ Offline Evaluation で再評価
```

### 5.4 Human Review 不採用列

| 列 | 不採用理由 |
| -- | ---------- |
| `tone` | トーン差は `template_body` と条件列（`relationship_code` 等）で表現する。tone ごとにテンプレートを分ける想定はない。PDCA の頻繁チューニング対象は `template_body` の版昇格である |
| `model_version_id` | `reason_template` は `model_version` に従属しない独立正本。`recommendation_run.model_version_id` は Embedding / Ranking 等の再現性用として別途保持する |

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `reason_template_id` | Reason Template ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK。`recommendation_reason.template_id` の参照キー |
| 2 | `template_name` | Template Name | `text` | `yes` | — | — | — | — | テンプレート安定 ID。版を含めない。snake_case 英小文字・数字・アンダースコア |
| 3 | `template_version` | Template Version | `integer` | `yes` | — | — | — | `1` | テンプレート版。同一 `template_name` 内で 1 から採番 |
| 4 | `template_type` | Template Type | `text` | `yes` | — | — | — | — | テンプレート種別。`summary` / `detail` / `point` / `caution`（§11） |
| 5 | `template_body` | Template Body | `text` | `yes` | — | — | — | — | テンプレート本文。プレースホルダ可。Reason生成定義書の `template_text` に相当 |
| 6 | `relationship_code` | Relationship Code | `text` | `no` | — | `LOGICAL` | — | `NULL` | 適用 Relationship。NULL は全 Relationship。`relationship_master.relationship_code` を論理参照 |
| 7 | `occasion_code` | Occasion Code | `text` | `no` | — | `LOGICAL` | — | `NULL` | 適用 Occasion。NULL は全 Occasion。`occasion_master.occasion_code` を論理参照 |
| 8 | `feature_code` | Feature Code | `text` | `no` | — | — | — | `NULL` | 適用 Feature。NULL は Feature 非依存。MVP feature 名（§11） |
| 9 | `is_active` | Active Flag | `boolean` | `yes` | — | — | — | `true` | 有効フラグ。`false` の行は解決対象外 |
| 10 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | レコード作成日時（UTC） |

> **論理ER との差分**: 論理ER §11.1 は最小属性のみ列挙する。本定義書は条件列・`template_version` を MVP 統合案として追加し、`tone` / `model_version_id` は不採用とする。`template_text` は物理列 `template_body` に相当する。

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

### 6.2 `reason_basis_json` 記録項目（MVP）

Reason 単位の利用記録（方式 B）。`recommendation_reason.reason_basis_json` に以下を保持する。

| JSON key | 必須 | 内容 |
| -------- | ---- | ---- |
| `template_name` | `yes` | 使用した `reason_template.template_name` |
| `template_version` | `yes` | 使用した `reason_template.template_version` |
| `template_type` | 推奨 | 使用した `template_type`（summary / detail / point / caution） |
| `used_features` | `yes` | Reason生成定義書 §14.3 既存方針 |
| `used_scores` | `yes` | 同上 |
| `used_semantic_evidence` | 推奨 | 同上 |

> Reason生成定義書 §14.2 の `template_id`（文字列識別子例）は、MVP では `template_name` + `template_version` に置き換える。後続 Task で Reason生成定義書との整合を follow-up する。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `reason_template_id` | サロゲート UUID | `recommendation_reason.template_id` の参照キー |
| UNIQUE | `reason_template_id` | PK と同一 | — |
| UNIQUE | `template_name`, `template_version` | 版付き業務識別子の一意性 | §5.3 |

> **template 解決キー（MVP）**: reco は Run 時に `template_type` + `relationship_code` + `occasion_code` + `feature_code`（NULL 許容）+ `is_active = true` で候補を絞り込む。同一 `template_name` については現行版 1 件のみ `is_active = true` とする運用（§5.3）。候補が複数残る場合は §7.1 の優先順位で 1 件に決定する。

### 7.1 テンプレート解決優先順位（MVP）

Run 時の条件列は **完全一致または NULL ワイルドカード一致** で候補を抽出する（例: Run の `relationship_code = 'boss'` は、行の `relationship_code` が `'boss'` または `NULL` の行に一致）。

候補が 2 件以上残る場合、reco は以下の順で 1 件に決定する。

| 順位 | ルール | 内容 |
| --: | ------ | ---- |
| 1 | 条件具体度 | 非 NULL の条件列数が多い行を優先。`relationship_code` / `occasion_code` / `feature_code` の各非 NULL を 1 点とし、最大 3 点 |
| 2 | `template_version` | 同一具体度の場合、`template_version` 最大の行を採用（§5.3 の現行版 1 件運用と整合） |
| 3 | seed 整合検知 | 上記でも複数残る場合は seed 不整合として検知し、汎用フォールバック（`template_type = summary` かつ全条件列 NULL の行）へ退避、または Reason 生成エラーとする |

**seed 運用ルール（推奨）:**

- 同一解決コンテキスト（`template_type` + 具体化した条件列の組み合わせ）に対し、`is_active = true` の行は **1 件のみ** とする
- 汎用フォールバック行（全条件列 `NULL`）は `template_type` ごとに最大 1 件の `is_active = true` とする
- 具体条件行と汎用行を併用する場合、§7.1 順位 1 により具体条件行が常に優先される

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `relationship_code` | `relationship_master.relationship_code` | なし | `LOGICAL` | Human Review #443 方針踏襲。MVP は物理 FK なし |
| `occasion_code` | `occasion_master.occasion_code` | なし | `LOGICAL` | Human Review #448 方針踏襲。MVP は物理 FK なし |

### 8.1 被参照（論理）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `recommendation_reason` | `template_id` | used_by | `LOGICAL` | `reason_template_id`（uuid）格納。`reason_basis_json` に `template_name` + `template_version` を併記（§6.2） |

> MVP 初期 DDL では物理 FK を張らない。整合は reco 側テンプレート解決 + seed 正本 + Reason INSERT 時の存在確認で担保する。

> **物理ER §9 との差分**: 現行物理ER §9 には `reason_template` → `recommendation_reason.template_id` の関係行が未記載である。物理ER 更新は本 Task scope 外のため follow-up とし、本定義書 §8.1 で LOGICAL 被参照を明記する。

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `reason_template_pkey` | `reason_template_id` | btree（PK） | 主キー | 自動生成 |
| `uq_reason_template_name_version` | `template_name`, `template_version` | btree（unique） | 版付き業務識別子一意 | §7 |
| `idx_reason_template_resolve` | `template_type`, `relationship_code`, `occasion_code`, `feature_code`, `is_active` | btree | テンプレート解決（§7） | 物理ER §10 は個別 Index 未記載。本 Task で追加方針 |
| `idx_reason_template_name_active` | `template_name`, `is_active` | btree | 現行版参照・seed 運用 | 同一 `template_name` の `is_active` 確認用 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `reason_template_pkey` | PRIMARY KEY | `reason_template_id` | 主キー | — |
| `uq_reason_template_name_version` | UNIQUE | `template_name`, `template_version` | 版付き一意 | — |
| `chk_template_name_format` | CHECK | `template_name` | `template_name ~ '^[a-z][a-z0-9_]*$'` | snake_case。先頭英字 |
| `chk_template_version` | CHECK | `template_version` | `template_version >= 1` | 版は 1 以上 |
| `chk_template_type` | CHECK | `template_type` | `template_type IN ('summary', 'detail', 'point', 'caution')` | Reason生成定義書 §15.2 |
| `chk_template_body_length` | CHECK | `template_body` | `char_length(template_body) BETWEEN 1 AND 2000` | MVP 上限（§17 で調整可） |
| `chk_relationship_code_format` | CHECK | `relationship_code` | `relationship_code IS NULL OR relationship_code ~ '^[a-z][a-z0-9_]*$'` | relationship_master と同一形式 |
| `chk_occasion_code_format` | CHECK | `occasion_code` | `occasion_code IS NULL OR occasion_code ~ '^[a-z][a-z0-9_]*$'` | occasion_master と同一形式 |
| `chk_feature_code` | CHECK | `feature_code` | `feature_code IS NULL OR feature_code IN ('formality', 'safety', 'brand_appropriateness', 'emotion', 'novelty', 'intimacy', 'symbolic_identity', 'story_richness')` | MVP feature 固定名 |

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
| INSERT | database（seed / 運用） | 新規テンプレート・新版追加 | 全列 | seed は Upsert 想定 | 版改訂は `template_version` インクリメントで新規 INSERT（§5.3） |
| UPDATE | database（seed / 運用） | 無効化のみ推奨 | `is_active` | Upsert 想定 | `template_body` の変更は新版 INSERT を推奨。同一版の上書き UPDATE は避ける |
| DELETE | — | MVP では原則禁止 | — | — | `is_active = false` で無効化 |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（設定正本）。旧版も PDCA 分析のため原則保持 |
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
| 適用順序 | 物理ER §15: Master / Config 群。`relationship_master` / `occasion_master` の後、`recommendation_reason` より前 |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | reco（service role 経由） |
| 書き込み権限 | database 運用・seed のみ。Online / Batch 実行中の DML 更新なし |
| service role利用 | reco テンプレート解決、seed 投入に限定 |
| 個人情報・機微情報 | 含まない |
| ログ出力制限 | `template_body` 全文を error ログに過剰出力しない |
| Public API | 非公開（内部 Config） |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / CHECK が定義どおり | migration |
| 2 | PK / UNIQUE | 同一 `(template_name, template_version)` の重複 INSERT が拒否される | migration |
| 3 | CHECK | 不正 `template_type` / `feature_code` / `template_version` が拒否される | migration |
| 4 | LOGICAL 参照 | 存在しない `relationship_code` / `occasion_code` が seed で投入されない | manual |
| 5 | reco 整合 | Reason 生成時に解決した `reason_template_id` が `recommendation_reason.template_id` に記録される | integration |
| 6 | reason_basis 整合 | `reason_basis_json` に `template_name` + `template_version` が記録される | integration |
| 7 | 版運用 | 同一 `template_name` で現行版が 2 件以上 `is_active = true` にならない（seed / 運用ルール） | manual |
| 8 | seed 整合 | Reason生成定義書の template 種別・代表テンプレートが seed に存在 | manual |
| 9 | 権限 | web client から Direct DB アクセス不可 | manual |

---

## 17. 未決事項

Human Review で判断する論点。以下は **未確定事項** であり、決定事項ではない。

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | seed 初期範囲 | MVP で投入する template_type / relationship / occasion の組み合わせ範囲 | Human | seed Task 前 | 推奨: 汎用 `summary` 1 本 + 主要 pair（上司×お礼 等）の `summary` のみ先行投入 |
| 2 | YAML seed vs DB 管理 | Reason生成定義書 §15.3 は YAML/JSON + Python 生成を高適性とする。DB 正本との役割分担 | Human | seed Task 前 | 推奨: DB を正本、YAML は seed 投入ソース（変換スクリプトは seed Task） |
| 3 | Reason生成定義書 §14.2 との整合 | `template_id` 文字列識別子例と本定義の `template_name` + `template_version` の差分 | Human | recommendation_reason 定義 Task 前 | 本定義書 §6.2 を正とする follow-up を別 Task 化 |

### 17.1 Human Review 決定事項（本更新で反映）

| No | 論点 | 決定 |
| --: | ---- | ---- |
| 1 | `model_version_id` 列 | **不採用**。`reason_template` は `model_version` に依存しない独立正本 |
| 2 | `tone` 列 | **不採用**。表現差は `template_body` と条件列で管理 |
| 3 | 版管理 | **`template_name` + `template_version` 列を採用** |
| 4 | 利用記録 | **方式 B**（Reason 単位で `template_name` + `template_version` を記録）。Run / Result の `reason_template_version_id` は MVP 非採用 |
| 5 | template 解決キー | **条件列解決**（`template_type` + `relationship_code` + `occasion_code` + `feature_code` + `is_active`） |
| 6 | `recommendation_reason.template_id` | **`reason_template_id`（uuid）格納** + `reason_basis_json` に `template_name` / `template_version` 併記 |

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
| 参照テーブル定義 | `docs/06_実装設計/database/ranking_config_テーブル定義書.md` | Config 系章構成・版管理参考 |
| 参照テーブル定義 | `docs/06_実装設計/database/pair_master_テーブル定義書.md` | Master 系章構成参考 |

---

## 19. レビュー観点

- 論理ER §11.1・物理ER §8・テーブル一覧 §9・Reason生成定義書 §15.2 と矛盾していない（`tone` / `model_version_id` 不採用は §17.1 で明示）
- `reason_template_id` / `template_name` / `template_version` / `template_type` / `template_body` / `is_active` / `created_at` が定義されている
- Reason生成定義書の条件列（`relationship_code` / `occasion_code` / `feature_code`）の MVP 採用が明記されている
- 版管理（`template_name` + `template_version`）と利用記録（方式 B）が明記されている
- テンプレート解決優先順位（§7.1）が具体化されている
- `recommendation_reason.template_id` の LOGICAL 参照方針が明記されている
- `relationship_master` / `occasion_master` への LOGICAL 参照が Human Review #443/#448 方針と一貫している
- Public API 非公開（内部 Config）が明記されている
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
