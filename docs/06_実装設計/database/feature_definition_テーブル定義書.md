# Feature Definition テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                   |
| -------------- | -------------------------------------- |
| ドキュメントID | `DB-TBL-MVP-feature_definition`        |
| ドキュメント名 | Feature Definition テーブル定義書      |
| 対象システム   | Gift Recommendation Service MVP        |
| MVP対象        | `yes`                                  |
| 作成日         | 2026-06-08                             |
| 更新日         | 2026-06-08                             |

---

## 2. 概要

`feature_definition` は、MVP で固定の **8 次元 Feature 軸**（Social 3 + Symbolic 5）の定義を、`semantic_config_version` 単位で保持する Semantic / Feature 定義系テーブルである。

API-PUB-007（Semantic 設定取得）の `featureDefinitions` 配列の正本となり、reco / batch が Feature 生成・Matching 時に参照する。

---

## 3. 目的

- MVP 8 軸の `feature_code` / 表示ラベル / 軸グループ（`social` / `symbolic`）を version 管理する
- `user_feature` / `item_feature` が参照する Feature 軸の正本を提供する
- seed 投入後、Public API から Feature 軸一覧を安定返却できるようにする

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `feature_definition` |
| 論理テーブル名 | Feature Definition |
| 分類 | Semantic / Feature 定義系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | reco（User Feature 生成）、batch（Item Feature 生成）、api（API-PUB-007 経由の参照） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11 |

---

## 5. 用途・責務

- **`semantic_config_version_id` 単位**で 8 軸それぞれ 1 行を保持する（MVP 固定）
- **`feature_code`** は enum定義書 §6.16 / AGENTS.md の MVP 8 軸固定名と一致させる
- **`feature_group`** は `social` / `symbolic` の 2 値（API-PUB-007 `featureGroup` と一致）
- **`display_order`** は UI / API 返却順の正本（API-PUB-007 は 1 始まり整数）
- **`is_active = true`** の行のみ API-PUB-007 が返却する（契約上、返却行は active のみ）

### 5.1 semantic_config_version との関係

| 観点 | `semantic_config_version` | `feature_definition`（本テーブル） |
| ---- | --------------------------- | ----------------------------------- |
| 分類 | Semantic / Feature 定義系（version ヘッダ） | Semantic / Feature 定義系（8 軸定義行） |
| 管理対象 | 意味体系 version ラベル・現行フラグ | Feature 軸コード・ラベル・グループ |
| 行数 | version ごとに 1 行（+ 履歴） | version ごとに **8 行固定**（MVP） |
| Public API | `semanticConfigVersionId`（API-PUB-007/008） | `featureDefinitions[]`（API-PUB-007） |

### 5.2 対象外

- Feature ルール本体（`relationship_rule` / `occasion_rule` 等の責務）
- Feature 生成結果（`user_feature` / `item_feature` の責務）
- 正規化パラメータ（`feature_normalization_version` の責務）
- `pair_rule` / `input_type_rule` / `feature_integration_rule` の内部 Rule 詳細

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `feature_definition_id` | Feature Definition ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK |
| 2 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `yes` | — | — | 所属する意味定義 version。`semantic_config_version` を参照 |
| 3 | `feature_code` | Feature Code | `text` | `yes` | — | — | — | — | MVP 8 軸コード。enum定義書 §6.16 正本 |
| 4 | `feature_label` | Feature Label | `varchar(100)` | `yes` | — | — | — | — | UI / API 表示ラベル。API-PUB-007 `featureLabel` |
| 5 | `feature_group` | Feature Group | `text` | `yes` | — | — | — | — | 軸グループ。`social` / `symbolic` |
| 6 | `display_order` | Display Order | `integer` | `yes` | — | — | — | `1` | 表示順。API-PUB-007 `displayOrder`（1 始まり） |
| 7 | `is_active` | Active Flag | `boolean` | `yes` | — | — | — | `true` | 有効フラグ。`false` は API 返却対象外 |

> **論理ER との差分**: 論理ER §10.2 に `feature_definition_id` 列名で派生テーブルが参照する記載がある一方、物理ER §11 の `item_feature` 冪等キーは `feature_code` を使用する。本定義書は **設定正本として feature_code を正**とし、派生テーブルの FK 列設計は各派生テーブル定義 Task で確定する（§8.1）。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `feature_definition_id` | サロゲート UUID | |
| UNIQUE | `feature_definition_id` | PK と同一 | — |
| UNIQUE | `semantic_config_version_id`, `feature_code` | version 内で Feature 軸は 1 行 | Index 名: `uq_feature_definition_version_code` |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `semantic_config_version_id` | `semantic_config_version.semantic_config_version_id` | `ON` | RESTRICT | 物理ER §9。Semantic 定義 version ヘッダ |

### 8.1 被参照（論理）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `user_feature` | `feature_definition_id`（論理ER §10.2） | defines | `LOGICAL`（方針） | 派生テーブル定義 Task で DDL 確定 |
| `item_feature` | `feature_code`（物理ER §11 冪等キー） | defines | `LOGICAL`（方針） | code 参照。`feature_definition_id` 列要否は item_feature Task で確定 |

> MVP 8 軸は `feature_code` が安定識別子のため、派生行は **code + semantic_config_version_id** で軸を特定する設計も許容する。論理ER §10.2 と物理ER §11 の差分は Human Review 論点（§17.1 No.3）。

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `feature_definition_pkey` | `feature_definition_id` | btree（PK） | 主キー | 自動生成 |
| `uq_feature_definition_version_code` | `semantic_config_version_id`, `feature_code` | btree（unique） | version 内 8 軸一意 | |
| `idx_feature_definition_version_active_order` | `semantic_config_version_id`, `is_active`, `display_order`, `feature_code` | btree | API-PUB-007 一覧（active + 表示順） | 物理ER §10 は個別 Index 未記載。本 Task で追加方針 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `feature_definition_pkey` | PRIMARY KEY | `feature_definition_id` | 主キー | — |
| `uq_feature_definition_version_code` | UNIQUE | `semantic_config_version_id`, `feature_code` | version 内 code 一意 | |
| `chk_feature_code_mvp` | CHECK | `feature_code` | `feature_code IN ('formality','safety','brand_appropriateness','emotion','novelty','intimacy','symbolic_identity','story_richness')` | 物理ER §11。enum Task と連携 |
| `chk_feature_group_mvp` | CHECK | `feature_group` | `feature_group IN ('social','symbolic')` | API-PUB-007 enum |
| `chk_feature_group_code_consistency` | CHECK | `feature_code`, `feature_group` | Social 3 軸 / Symbolic 5 軸の対応 | §10.1 参照 |
| `chk_display_order_positive` | CHECK | `display_order` | `display_order >= 1` | API-PUB-007 は 1 始まり |
| `chk_feature_label_length` | CHECK | `feature_label` | `char_length(feature_label) BETWEEN 1 AND 100` | 表示ラベル上限 |

### 10.1 MVP 8 軸と feature_group 対応（seed / CHECK 参照）

| feature_group | feature_code | 論理ER §10.3 |
| ------------- | ------------ | ------------ |
| `social` | `formality` | Social |
| `social` | `safety` | Social |
| `social` | `brand_appropriateness` | Social |
| `symbolic` | `emotion` | Symbolic |
| `symbolic` | `novelty` | Symbolic |
| `symbolic` | `intimacy` | Symbolic |
| `symbolic` | `symbolic_identity` | Symbolic |
| `symbolic` | `story_richness` | Symbolic |

> `chk_feature_group_code_consistency` は DDL Task で CASE 式またはトリガで実装する。本 Task では CHECK 方針のみ定義する。

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `feature_code` | `feature_code` | enum定義書 §6.16 | MVP 8 値 | 物理ER §11 |
| `feature_group` | `feature_group` | API-PUB-007 | `social` / `symbolic` | 本 Task で CHECK 候補値 |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | api | 現行 `semantic_config_version` + `is_active=true` | — | — | API-PUB-007。ORDER BY `display_order`, `feature_code` |
| SELECT | reco / batch | Feature 生成時 | — | — | `feature_code` 存在確認 |
| INSERT | database（seed） | 新 version 初回投入 | 全列 | version ごと 8 行 Upsert | MVP では 8 行固定 |
| UPDATE | database（運用） | ラベル・表示順・無効化 | `feature_label`, `display_order`, `is_active` | — | **`feature_code` 変更禁止**（新 version INSERT 推奨） |
| DELETE | — | MVP では原則禁止 | — | — | `is_active=false` で無効化 |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（設定正本。version 履歴として保持） |
| 削除方式 | 物理 DELETE 原則禁止 |
| 論理削除 | `is_active = false` |
| version 切替 | 新 `semantic_config_version` 作成時に 8 行を新規 INSERT |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `feature_definition` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: `semantic_config_version` 作成後、Rule 群より前 |
| rollback方針 | forward migration 主体 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | api / reco / batch（service role） |
| 書き込み権限 | database seed / 運用のみ |
| Public API | `featureDefinitions` は API-PUB-007 で公開（内部 PK は非公開） |
| ログ出力制限 | 設定内容を過剰ログ出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / CHECK | migration |
| 2 | 8 軸 CHECK | 9 軸目 code が拒否される | migration |
| 3 | UNIQUE | 同一 version で同一 code の重複 INSERT が拒否される | migration |
| 4 | API 整合 | active 8 行が API-PUB-007 形式で返る | integration |
| 5 | seed 整合 | 論理ER §10.3 の 8 軸が seed に存在 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review 前の論点は §17.1 を参照 |

### 17.1 Human Review 観点（PR #470）

| No | 論点 | 推奨案 | 判断者 | 備考 |
| --: | ---- | ------ | ------ | ---- |
| 1 | `feature_group` enum 正本化 | MVP は CHECK 候補値。packages/code-definitions 正本化は後続 enum Task | Human | API-PUB-007 と一致 |
| 2 | version 内 8 行固定 | MVP は新 version ごとに 8 行 seed。9 軸目追加は version 更新で対応 | Human | 論理ER §10.3 |
| 3 | 派生テーブル参照キー | 設定正本は `feature_code`。`user_feature.feature_definition_id` FK は派生 Task で確定 | Human | 論理ER §10.2 vs 物理ER §11 |
| 4 | `display_order` 起点 | API-PUB-007 例に合わせ **1 始まり** CHECK | Human | §10 chk_display_order_positive |
| 5 | `feature_label` 多言語 | MVP は単一 `feature_label` のみ（relationship_master 同型） | Human | |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8–§11 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §10.2 / §10.3 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §8 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | §6.16 feature_code |
| API契約 | `docs/06_実装設計/api/API-PUB-007_Semantic設定取得API契約仕様書.md` | featureDefinitions マッピング |
| Featureルール | `docs/04_ドメインモデル設計/Featureルール定義書.md` | §10.3 8 軸一覧 |
| 先行 Task | Issue #462 / #463 | semantic_config / semantic_config_version |

---

## 19. レビュー観点

- 論理ER §10.2 / §10.3・物理ER §8–§11・テーブル一覧 §8 と矛盾していない
- MVP 8 軸 `feature_code` / `feature_group` が CHECK と seed 方針で明記されている
- API-PUB-007 `featureDefinitions` マッピングが明確
- `semantic_config_version_id` FK（物理 ON）が明記されている
- Public API 非公開列（内部 UUID）と公開列の区別が明確
- 派生テーブル参照の論点（§8.1 / §17.1 No.3）が明示されている
- DDL Task が CREATE TABLE を起こせる粒度である
