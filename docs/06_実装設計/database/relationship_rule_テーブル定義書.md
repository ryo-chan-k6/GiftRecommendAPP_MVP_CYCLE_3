# Relationship Rule テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                   |
| -------------- | -------------------------------------- |
| ドキュメントID | `DB-TBL-MVP-relationship_rule`         |
| ドキュメント名 | Relationship Rule テーブル定義書       |
| 対象システム   | Gift Recommendation Service MVP        |
| MVP対象        | `yes`                                  |
| 作成日         | 2026-06-11                             |
| 更新日         | 2026-06-11                             |

---

## 2. 概要

`relationship_rule` は、**Relationship（贈り手と受け手の関係性）** から User Feature の **基準値（base value）** を生成する Rule を、`semantic_config_version` 単位で保持する Semantic / Feature 定義系テーブルである。

Featureルール定義書 §6・§17.1 の Relationship Rule を物理化し、API-PUB-008（Feature ルール取得）の `baseValueRules[]`（`ruleType: relationship`）の DB 正本となる。

---

## 3. 目的

- Relationship 12 分類 × Feature 8 軸の基準値を version 管理する（Featureルール定義書 §20.1）
- reco が User Feature 生成時に Relationship 由来の `raw_value` 基準値を参照できるようにする
- seed 投入後、Public API から Relationship 基準値 Rule を安定返却できるようにする

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `relationship_rule` |
| 論理テーブル名 | Relationship Rule |
| 分類 | Semantic / Feature 定義系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | reco（User Feature 生成）、api（API-PUB-008 経由の参照） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11 |

---

## 5. 用途・責務

- **`semantic_config_version_id` 単位**で、Relationship 1 分類 × Feature 1 軸 = **1 行**を保持する
- MVP では **12 relationship_code × 8 feature_code = 96 行 / version** を seed 正本とする（Featureルール定義書 §6.2 / §20.1）
- **`feature_base_value`** は Relationship 由来の Feature 基準値（0.0〜1.0）。API-PUB-008 `featureBaseValue` の正本
- **`is_active = true`** の行のみ API-PUB-008 が返却する（契約上、返却行は active のみ）
- **`ruleType: relationship`** は API 応答時の定数であり、DB 列としては保持しない（API-PUB-008 §7.3.1）

### 5.1 関連テーブルとの関係

| 観点 | 参照先 | 本テーブルとの関係 |
| ---- | ------ | ------------------ |
| version ヘッダ | `semantic_config_version` | `semantic_config_version_id` で所属 version を特定（物理 FK ON） |
| Relationship コード | `relationship_master` | `relationship_code` で LOGICAL 参照。12 分類の正本は Master |
| Feature 軸 | `feature_definition` | 同一 version 内の `feature_code` と整合。MVP 8 軸 CHECK |
| Occasion 基準値 | `occasion_rule` | 同型 Rule。本テーブルは Relationship 専用 |
| Pair 補正 | `pair_rule` | Relationship × Occasion 補正。本テーブルは base value の責務 |

### 5.2 API-PUB-008 マッピング（`baseValueRules[]` / `ruleType: relationship`）

| API フィールド | DB 列 / 定数 | 備考 |
| -------------- | ------------ | ---- |
| `semanticConfigVersionId` | `semantic_config_version_id` | 現行 version 解決は api アプリ層 |
| `baseValueRules[].ruleType` | 定数 `'relationship'` | DB 非保持。api が付与 |
| `baseValueRules[].relationshipCode` | `relationship_code` | API-PUB-005 と同一コード体系 |
| `baseValueRules[].featureCode` | `feature_code` | MVP 8 軸。enum定義書 §6.16 |
| `baseValueRules[].featureBaseValue` | `feature_base_value` | `numeric(4,3)` 相当。0.0〜1.0 |

> OpenAPI / generated 追随は Epic 終盤 Task #469 の責務。本 Task では契約 docs との列マッピングのみ確定する。

### 5.3 対象外

- Occasion 基準値（`occasion_rule` の責務）
- Pair 補正（`pair_rule` の責務）
- Concept 補正（`concept_feature_rule` の責務）
- User Feature 生成結果（`user_feature` の責務）
- `input_type_rule` / `feature_integration_rule` の内部 Rule 詳細

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `relationship_rule_id` | Relationship Rule ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK |
| 2 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `yes` | — | — | 所属する意味定義 version。`semantic_config_version` を参照 |
| 3 | `relationship_code` | Relationship Code | `text` | `yes` | — | — | — | — | Relationship コード。`relationship_master.relationship_code` と整合 |
| 4 | `feature_code` | Feature Code | `text` | `yes` | — | — | — | — | MVP 8 軸コード。enum定義書 §6.16 正本 |
| 5 | `feature_base_value` | Feature Base Value | `numeric(4,3)` | `yes` | — | — | — | — | Relationship 由来 Feature 基準値。0.0〜1.0 |
| 6 | `is_active` | Active Flag | `boolean` | `yes` | — | — | — | `true` | 有効フラグ。`false` は API 返却対象外 |

> **論理ER との差分**: 論理ER §10.2 には抽象エンティティ `feature_rule` が列挙されているが、物理テーブルでは `relationship_rule` / `occasion_rule` 等へ **分解**する（物理ER §5 No.5・テーブル一覧 §8）。本定義書は分解後の `relationship_rule` を正とする。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `relationship_rule_id` | サロゲート UUID | |
| UNIQUE | `relationship_rule_id` | PK と同一 | — |
| UNIQUE | `semantic_config_version_id`, `relationship_code`, `feature_code` | version 内で Relationship × Feature 軸は 1 行 | Index 名: `uq_relationship_rule_version_relationship_feature` |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `semantic_config_version_id` | `semantic_config_version.semantic_config_version_id` | `ON` | RESTRICT | 物理ER §9 / semantic_config_version §8.1 |

### 8.1 論理参照（MVP 初期 DDL）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `relationship_code` | `relationship_master.relationship_code` | `LOGICAL` | seed + CHECK | Master は自然キー PK。物理 FK は MVP では付与しない方針（relationship_master §8.1 と同型） |
| `feature_code` | `feature_definition.feature_code`（同一 `semantic_config_version_id`） | `LOGICAL` | CHECK + seed | version 内 8 軸存在は seed / アプリ validation で担保 |

> `relationship_master` への物理 FK 非採用は、Master 系が Semantic version とは独立に管理されるため。整合は enum / seed / CHECK で担保する（§17.1 No.2）。

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `relationship_rule_pkey` | `relationship_rule_id` | btree（PK） | 主キー | 自動生成 |
| `uq_relationship_rule_version_relationship_feature` | `semantic_config_version_id`, `relationship_code`, `feature_code` | btree（unique） | version 内 Rule 一意 | §7 と同一 |
| `idx_relationship_rule_version_active_lookup` | `semantic_config_version_id`, `is_active`, `relationship_code`, `feature_code` | btree | API-PUB-008 一覧（active Rule） | reco 参照にも利用 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `relationship_rule_pkey` | PRIMARY KEY | `relationship_rule_id` | 主キー | — |
| `uq_relationship_rule_version_relationship_feature` | UNIQUE | `semantic_config_version_id`, `relationship_code`, `feature_code` | version 内一意 | |
| `fk_relationship_rule_semantic_config_version` | FOREIGN KEY | `semantic_config_version_id` | `semantic_config_version` ON DELETE RESTRICT | semantic_config_version §8.1 |
| `chk_relationship_code_format` | CHECK | `relationship_code` | `relationship_code ~ '^[a-z][a-z0-9_]*$'` | relationship_master と同型 |
| `chk_feature_code_mvp` | CHECK | `feature_code` | MVP 8 軸 IN 句 | feature_definition / 物理ER §11 と同一 |
| `chk_feature_base_value_range` | CHECK | `feature_base_value` | `feature_base_value >= 0.0 AND feature_base_value <= 1.0` | API-PUB-008 / API設計方針書 §7.3 |

### 10.1 MVP relationship_code 許容値（seed / CHECK 参照）

Featureルール定義書 §5.1 の 12 分類と一致させる。

| relationship_code | relationship_label（参考） |
| ----------------- | ---------------------------- |
| `lover` | 恋人 |
| `spouse` | 配偶者 |
| `family_parent` | 親 |
| `family_child` | 子ども |
| `family_sibling` | 兄弟姉妹 |
| `friend_close` | 親しい友人 |
| `friend_casual` | 友人・知人 |
| `colleague` | 同僚 |
| `boss` | 上司 |
| `subordinate` | 部下・後輩 |
| `business_partner` | 取引先 |
| `other` | その他 |

> 完全な 12 値 CHECK（`relationship_code IN (...)`）は DDL Task で実装する。初期値一覧は seed Task が Featureルール定義書 §6.2 を正本とする。

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `relationship_code` | relationship コード | Featureルール定義書 §5.1 / relationship_master | MVP 12 値 | Master seed と一致 |
| `feature_code` | `feature_code` | enum定義書 §6.16 | MVP 8 値 | 物理ER §11 |
| `feature_base_value` | — | API-PUB-008 | 0.0〜1.0 | CHECK で担保 |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | api | 現行 `semantic_config_version` + `is_active=true` | — | — | API-PUB-008。`ruleType=relationship` を付与して返却 |
| SELECT | reco | User Feature 生成時 | — | — | Request の `relationship_code` + version で 8 軸分を参照 |
| INSERT | database（seed） | 新 version 初回投入 | 全列 | version ごと 96 行 Upsert | MVP 固定行数 |
| UPDATE | database（運用） | 基準値調整・無効化 | `feature_base_value`, `is_active` | — | **`relationship_code` / `feature_code` 変更禁止**（新 version INSERT 推奨） |
| DELETE | — | MVP では原則禁止 | — | — | `is_active=false` で無効化 |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（設定正本。version 履歴として保持） |
| 削除方式 | 物理 DELETE 原則禁止 |
| 論理削除 | `is_active = false` |
| version 切替 | 新 `semantic_config_version` 作成時に 96 行を新規 INSERT |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `relationship_rule` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: `semantic_config_version`・`relationship_master`・`feature_definition` 作成後、Rule 群の一部として適用 |
| rollback方針 | forward migration 主体 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | api / reco（service role） |
| 書き込み権限 | database seed / 運用のみ |
| Public API | `baseValueRules[]` は API-PUB-008 で公開（内部 UUID は非公開） |
| ログ出力制限 | Rule 設定値を過剰ログ出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / FK / CHECK | migration |
| 2 | UNIQUE | 同一 version で同一 relationship × feature の重複 INSERT が拒否される | migration |
| 3 | 値域 CHECK | `feature_base_value` が 0.0〜1.0 外で拒否される | migration |
| 4 | API 整合 | active 96 行が API-PUB-008 `baseValueRules` 形式で返る | integration |
| 5 | seed 整合 | Featureルール定義書 §6.2 の 12×8 矩阵が seed に存在 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review 前の論点は §17.1 を参照 |

### 17.1 Human Review 観点（Issue #473）

| No | 論点 | 推奨案 | 判断者 | 備考 |
| --: | ---- | ------ | ------ | ---- |
| 1 | MVP 初期 `feature_base_value` | seed Task が Featureルール定義書 §6.2 を正本として 96 行投入 | Human | 本テーブル定義書では値本体を重複定義しない |
| 2 | `relationship_master` への物理 FK | MVP は **LOGICAL + CHECK**（Master は version 非依存） | Human | relationship_master §8.1 / recommendation_request と同型 |
| 3 | version 内 UNIQUE | `(semantic_config_version_id, relationship_code, feature_code)` を採用 | Human | 1 Relationship × 1 Feature 軸 = 1 基準値 |
| 4 | `occasion_rule` との一貫性 | 同一カラム構成・CHECK・Index 方針を occasion_rule Task へ引き継ぎ | Human | Wave2 No.5 以降 |
| 5 | 96 行不足時の API 挙動 | 契約上は部分返却可（200 + 取得できた Rule のみ）。完全性は seed / 運用で担保 | Human | API-PUB-008 空配列方針と整合 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8–§11 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §10.2（抽象 feature_rule 分解） |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §8 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | §6.16 feature_code |
| Featureルール | `docs/04_ドメインモデル設計/Featureルール定義書.md` | §5.1 / §6.2 / §17.1 / §20.1 |
| API契約 | `docs/06_実装設計/api/API-PUB-008_Featureルール取得API契約仕様書.md` | baseValueRules マッピング |
| API契約 | `docs/06_実装設計/api/API-PUB-005_Relationshipマスタ取得API契約仕様書.md` | relationshipCode 整合 |
| 先行テーブル | `docs/06_実装設計/database/semantic_config_version_テーブル定義書.md` | 親 FK |
| 先行テーブル | `docs/06_実装設計/database/relationship_master_テーブル定義書.md` | relationship_code |
| 先行テーブル | `docs/06_実装設計/database/feature_definition_テーブル定義書.md` | feature_code |
| 先行 Task | Issue #462 / #463 / #442 / #470 | Wave1 + Master + feature_definition |

---

## 19. レビュー観点

- 論理ER §10.2（抽象 `feature_rule` 分解）・物理ER §8–§11・テーブル一覧 §8 と矛盾していない
- Featureルール定義書 §17.1 の論理項目が物理カラムとして整理されている
- MVP 12 分類 × 8 軸の行数方針が明記されている
- API-PUB-008 `baseValueRules`（ruleType: relationship）の DB 列マッピングが明確
- `semantic_config_version_id` FK（物理 ON）および `relationship_code` / `feature_code` の LOGICAL 参照方針が明記されている
- `feature_base_value` の 0.0〜1.0 CHECK が明記されている
- OpenAPI / generated 変更が含まれていない（#469 委譲）
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
