# Semantic Config テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                               |
| -------------- | ---------------------------------- |
| ドキュメントID | `DB-TBL-MVP-semantic_config`       |
| ドキュメント名 | Semantic Config テーブル定義書     |
| 対象システム   | Gift Recommendation Service MVP    |
| MVP対象        | `yes`                              |
| 作成日         | 2026-06-08                         |
| 更新日         | 2026-06-09                         |

---

## 2. 概要

`semantic_config` は、Semantic / Feature 定義体系の **設定系列（Config lineage）の大枠** を保持する Semantic / Feature定義系テーブルである。

意味推定ロジックの version 詳細（`version_label` / `is_current` / Rule 群）は子テーブル `semantic_config_version` が管理し、本テーブルは系列識別子・説明・系列有効フラグを担う。Public API には本テーブルの主キーを直接公開しない（内部 Config）。

---

## 3. 目的

- Semantic / Feature 定義の **設定系列** を DB 上で識別・説明する
- `semantic_config_version` の親エンティティとして、物理 FK（ON）の被参照元となる
- reco / api が Config 解決時に参照する系列メタデータ（`config_name` 等）の正本を提供する
- API-PUB-007 が返却する `configName`（任意項目）の表面値の参照元候補とする

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `semantic_config` |
| 論理テーブル名 | Semantic Config |
| 分類 | Semantic / Feature定義系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | reco（Config 系列解決）、api（API-PUB-007 の `configName` 表面参照） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8 |

---

## 5. 用途・責務

- **設定系列の識別**（`config_name`）と **説明**（`config_description`）を保持する
- **系列単位の有効フラグ**（`is_active`）により、無効系列を reco / seed 解決対象外とする
- **`semantic_config_id`（UUID）** をサロゲート PK とし、子テーブル `semantic_config_version` から **物理 FK（ON）** で参照される
- Run 再現性に用いる version ID（`semantic_config_version_id`）は本テーブルでは保持しない（子テーブル責務）

### 5.1 semantic_config_version との分離

| 観点 | `semantic_config` | `semantic_config_version` |
| ---- | ----------------- | ------------------------- |
| 管理単位 | 設定系列（lineage）の大枠 | 系列内の version（Rule / Concept / Feature 定義セット） |
| 主な列 | `config_name`, `config_description`, `is_active` | `version_label`, `is_current`, `valid_from`, `valid_to` |
| Run 固定 | 直接参照しない | `recommendation_run.semantic_config_version_id` で固定 |
| 物理 FK | 被参照元（親） | 親 `semantic_config_id` を参照（ON） |

### 5.2 Public API との関係

| 観点 | 方針 |
| ---- | ---- |
| `semantic_config_id` | Public API 非公開（内部 DB キー） |
| `config_name` | API-PUB-007 の `configName`（任意）として **表面公開候補**。version 詳細・Rule パラメータは非公開 |
| `semantic_config_version_id` / Rule 詳細 | Public API 非公開（§17.1 No.5） |
| Semantic Concept / Feature Definition | `semantic_config_version` 配下。API-PUB-007 が返却 |
| API-PUB-007 MVP 前提 | default 系列（`config_name = 'mvp_semantic_config'`）のスナップショット返却を前提とする（§17.1 No.5） |

### 5.3 対象外

- Semantic Concept / Feature Definition / 各種 Rule の定義（`semantic_config_version` 配下テーブルの責務）
- Feature 正規化統計量 version（`feature_normalization_version` の責務）
- 技術的モデル version（`model_version` の責務）
- Ranking パラメータ（`ranking_config` の責務）
- `semantic_config` 行自体の Public CRUD API（MVP 対象外）

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `semantic_config_id` | Semantic Config ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK。`semantic_config_version.semantic_config_id` の参照先 |
| 2 | `config_name` | Config Name | `text` | `yes` | — | — | `yes` | — | 設定系列名。MVP 初期値 `mvp_semantic_config`。snake_case 英小文字・数字・アンダースコア |
| 3 | `config_description` | Config Description | `text` | `no` | — | — | — | `NULL` | 系列の説明。運用・監査用。Public API 非公開 |
| 4 | `is_active` | Active Flag | `boolean` | `yes` | — | — | — | `true` | 系列有効フラグ。`false` の系列は version 解決対象外（§17.1 No.1） |
| 5 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | レコード作成日時（UTC） |

> **論理ER §11.1 との関係**: 論理ER §10.2 は `config_description` を主要属性に列挙するが NULL 許容とする。MVP 物理 DDL でも NULL 許容とし、seed では説明文を付与する。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `semantic_config_id` | サロゲート UUID | 子テーブル FK の参照先 |
| UNIQUE | `semantic_config_id` | PK と同一 | — |
| UNIQUE | `config_name` | 設定系列名の一意性 | 同一名称の重複系列を禁止 |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| — | — | なし | — | 本テーブルは Semantic Config 系列の根。外向き FK なし |

### 8.1 被参照（物理 FK ON）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `semantic_config_version` | `semantic_config_id` | has | `ON` | 物理ER §9。1:N。DELETE RESTRICT 想定（§17 No.4） |

> **子テーブル側 DDL 方針（引き継ぎ）**: `semantic_config_version.semantic_config_id` → `semantic_config.semantic_config_id` に `REFERENCES ... ON DELETE RESTRICT` を付与する。親系列削除前に version 行の整理が必要。

### 8.2 間接被参照（論理）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `recommendation_run` | `semantic_config_version_id` | used_by | `LOGICAL` | 本テーブル経由で間接参照。Run は version ID を固定 |
| `semantic_concept` / `feature_definition` / 各種 `*_rule` | `semantic_config_version_id` | defines / contains | `ON`（version 経由） | 孫テーブル。本 Task では FK 詳細を確定しない |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `semantic_config_pkey` | `semantic_config_id` | btree（PK） | 主キー | 自動生成 |
| `uq_semantic_config_config_name` | `config_name` | btree（unique） | 系列名一意 | §7 と同一 |
| `idx_semantic_config_active_name` | `is_active`, `config_name` | btree | 有効系列の解決 | reco / seed 参照 |
| `idx_semantic_config_created_at` | `created_at` DESC | btree | 監査・運用参照 | 物理ER §10 Index 方針（時系列列） |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `semantic_config_pkey` | PRIMARY KEY | `semantic_config_id` | 主キー | — |
| `uq_semantic_config_config_name` | UNIQUE | `config_name` | 系列名一意 | — |
| `chk_config_name_format` | CHECK | `config_name` | `config_name ~ '^[a-z][a-z0-9_]*$'` | snake_case。先頭英字 |
| `chk_config_description_length` | CHECK | `config_description` | `config_description IS NULL OR char_length(config_description) <= 500` | 運用説明の上限（§17 No.3） |

> **`is_active` の partial unique**: MVP では **付与しない**（Human Review #467 決定。A/B 用に複数系列を同時 `is_active=true` とする想定。§17.1 No.2）。

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| — | — | なし | — | 状態カラムなし。`is_active` は boolean |

Feature 8 軸（`formality` 等）は本テーブルには保持せず、`feature_definition`（`semantic_config_version` 配下）および Featureルール定義書 §5 が正本とする。

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | reco | Config 系列解決時 | — | — | §12.1 の解決順序に従う |
| SELECT | api | API-PUB-007 応答組立 | — | — | MVP では default 系列（`mvp_semantic_config`）の現行 version 解決後、`config_name` を `configName` にマッピング |
| INSERT | database（seed / 運用） | 新系列追加 | 全列 | seed は Upsert 想定 | MVP 初期は default 系列 seed 必須。Treatment 系列は追加 seed 可（§17.1 No.2） |
| UPDATE | database（運用） | 説明変更・系列無効化 | `config_description`, `is_active` | — | `config_name` / PK の変更は原則禁止 |
| DELETE | — | MVP では原則禁止 | — | — | 子 version 存在時は FK RESTRICT（§17.1 No.4）。`is_active = false` で無効化 |

### 12.1 Config 系列・version 解決順序（Human Review 決定）

reco / api が Semantic Config を解決する際の順序は以下とする（§17.1 No.1）。

1. **親系列フィルタ**: `semantic_config.is_active = true` の系列のみ対象。`is_active = false` の系列は **解決対象外**（スキップ。エラーにしない）
2. **系列選択**:
   - Run 実行時に Treatment 系列が **明示割当** されている場合はその系列を使用（割当ロジックは MOD-RECO-003 Task で具体化。本 Task では決定しない）
   - 割当なし、または複数 `is_active = true` が存在する fallback 時は **`config_name = 'mvp_semantic_config'` 固定**
3. **子 version 解決**: 選択系列配下で `semantic_config_version.is_current = true` の version を解決

> **A/B 前提**: 複数系列を同時 `is_active = true` にする想定。Default = `mvp_semantic_config`、Treatment = 非 default 系列の明示割当は後続 Resolver Task（MOD-RECO-003）で設計する。

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（設定正本） |
| 削除方式 | 物理 DELETE 原則禁止 |
| 削除条件 | 子 `semantic_config_version` 行が存在する場合は DELETE RESTRICT |
| 論理削除 | `is_active = false` で系列無効化 |
| アーカイブ | MVP 対象外 |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `semantic_config` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: Semantic 群の先頭（`semantic_config_version` より前） |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | api / reco（service role 経由） |
| 書き込み権限 | database 運用・seed のみ。Online / Batch 実行中の DML 更新なし |
| service role利用 | api のマスタ参照、reco Config 解決、seed 投入に限定 |
| 個人情報・機微情報 | 含まない |
| ログ出力制限 | 内部 PK を error ログに過剰出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / CHECK が定義どおり | migration |
| 2 | PK / UNIQUE | 同一 `config_name` の重複 INSERT が拒否される | migration |
| 3 | CHECK | 不正 `config_name` / 長すぎる `config_description` が拒否される | migration |
| 4 | FK 被参照 | 親行存在下で `semantic_config_version` INSERT が成功する | migration |
| 5 | DELETE RESTRICT | version 行存在時に親 DELETE が拒否される | migration |
| 6 | reco / api 整合 | 有効系列のみ解決、`configName` マッピングが API-PUB-007 と整合 | integration |
| 7 | seed 整合 | MVP 初期 `config_name` が seed に存在 | manual |
| 8 | 権限 | web client から Direct DB アクセス不可 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review (#467) にて No.1 / No.2 / No.4 / No.5 を決定済み（§17.1 参照） |
| 3 | `config_description` の MVP 必須性と上限 | 論理ER は属性列挙だが NULL 許容。CHECK 500 文字は暫定 | Human | seed Task 前 | §6・§10 の CHECK を seed 正本と突合 |

### 17.1 Human Review 決定事項（PR #467）

| No | 論点 | 決定内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | `is_active` と `semantic_config_version.is_current` の解決階層 | 解決順序は **親系列 → 子 version**（§12.1）。`is_active = false` の系列は解決対象外（スキップ）。複数 `is_active = true` 時の fallback は **`config_name = 'mvp_semantic_config'` 固定**。Treatment 系列の Run 明示割当は MOD-RECO-003 Task で具体化する | Human | 段階A（本 PR）で決定。段階Bは Resolver Task |
| 2 | MVP の `config_name` 系列数 | **複数系列を許容**（A/B 用に複数系列を同時 `is_active = true` とする想定）。`is_active` partial unique は **付与しない**。MVP seed は default 系列（`mvp_semantic_config`）必須 | Human | §10・§12 と整合 |
| 4 | 親 DELETE と FK RESTRICT | `semantic_config_version.semantic_config_id` への **DELETE RESTRICT** を採用。子 version 存在時は親物理 DELETE 不可 | Human | §8.1・§13 と整合 |
| 5 | API-PUB-007 `configName` 公開範囲 | `semantic_config_id` / `semantic_config_version_id` / Rule 詳細は **非公開**。`config_name` は `configName` 表面公開候補。API-PUB-007 MVP は **default 系列（`mvp_semantic_config`）のスナップショット返却** を前提とする | Human | api 層マッピング（DB snake_case → API 表面表記）は API 実装 Task で確定 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8 テーブル一覧・§9 FK・§15 適用順序 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §10.2 / §11.1 エンティティ属性 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §8 Semantic / Feature定義系 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | コード定義正本（本テーブルは enum 列なし） |
| Featureルール定義書 | `docs/04_ドメインモデル設計/Featureルール定義書.md` | Feature 8 軸参照（子テーブル側） |
| API契約 | `docs/06_実装設計/api/API-PUB-007_Semantic設定取得API契約仕様書.md` | `configName` 表面マッピング |
| 参照テーブル定義 | `docs/06_実装設計/database/relationship_master_テーブル定義書.md` | Master / Config 系構成踏襲 |
| 参照テーブル定義 | `docs/06_実装設計/database/ranking_config_テーブル定義書.md` | Config 系 UUID PK・系列管理構成参考 |

---

## 19. レビュー観点

- 論理ER §10.2 / §11.1・物理ER §8・§9・テーブル一覧 §8 と矛盾していない
- `semantic_config_id` / `config_name` / `config_description` / `is_active` / `created_at` がすべて定義されている
- `semantic_config_version.semantic_config_id` への物理 FK（ON）被参照方針が明記されている
- Public API 非公開（内部 Config）と API-PUB-007 `configName` 表面公開の境界が明記されている（§17.1 No.5）
- Config 系列・version 解決順序（§12.1）が Human Review 決定事項と整合している
- `relationship_master` / `ranking_config` テーブル定義書と章構成・MVP 方針が一貫している
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
