# Normalization Rule テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                   |
| -------------- | -------------------------------------- |
| ドキュメントID | `DB-TBL-MVP-normalization_rule`        |
| ドキュメント名 | Normalization Rule テーブル定義書      |
| 対象システム   | Gift Recommendation Service MVP        |
| MVP対象        | `yes`                                  |
| 作成日         | 2026-06-12                             |
| 更新日         | 2026-06-12                             |

---

## 2. 概要

`normalization_rule` は、**意味定義 version（`semantic_config_version`）** ごとに、User Feature / Item Feature 生成時に適用する **正規化方式と正規化パラメータ version の紐づけ** を保持する Semantic / Feature 定義系テーブルである。

GiftMeaningSpace §7.4 および Matching / Ranking 定義書の「正規化ルールは `semantic_config_version` 側で管理」方針を物理化する。sigmoid の `center_feature` / `k_feature` 等の **パラメータ正本は `feature_normalization_version` に委譲**し、本テーブルは **ルール定義（方式 + version 参照）** に限定する（Featureルール定義書 §14.8 / §16.2）。

**Public API では返却しない**（内部 Rule。API-PUB-007 / API-PUB-008 非公開）。

---

## 3. 目的

- 意味定義 version 単位で、Feature raw 値の正規化に用いる `normalization_method` と `feature_normalization_version_id` を設定正本として管理する
- batch / reco が `semantic_config_version` 解決後に正規化 version を Lookup し、`user_feature` / `item_feature` へ記録する ID を決定できるようにする
- 後続 DDL / seed Task が migration を作成できる粒度まで設計を確定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `normalization_rule` |
| 論理テーブル名 | Normalization Rule |
| 分類 | Semantic / Feature 定義系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | batch（Item Feature 生成）、reco（User Feature 生成） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11 |

---

## 5. 用途・責務

- **`semantic_config_version_id` 単位**で、MVP では **1 version = 1 行**（全 8 Feature 軸共通の正規化 binding）を保持する
- **`normalization_method`** は適用する正規化方式（MVP: `sigmoid`）を識別する
- **`feature_normalization_version_id`** は正規化パラメータ正本（`parameter_json`）を保持する `feature_normalization_version` 行への **参照キー** である。パラメータ本体は本テーブルに保持しない
- **`is_active = true`** の行のみ batch / reco が現行 binding として参照する
- batch / reco は本テーブル解決後、`feature_normalization_version` から `parameter_json` を取得して sigmoid を実行し、派生行に `feature_normalization_version_id` を記録する

### 5.1 `feature_normalization_version` との責務分離

| 観点 | `normalization_rule`（本テーブル） | `feature_normalization_version` |
| ---- | ----------------------------------- | -------------------------------- |
| 分類 | Semantic / Feature 定義系（`semantic_config_version` 子 Rule） | Master / Config 系（独立 version テーブル） |
| 管理単位 | 意味定義 version ごとの **正規化適用方針** | 正規化方式ごとの **パラメータ version** |
| 保持内容 | `normalization_method` + `feature_normalization_version_id` 参照 | `parameter_json`（`center_feature` / `k_feature` 等） |
| 親子関係 | `semantic_config_version` の子（物理 FK ON）。`feature_normalization_version` へ **物理 FK ON**（binding 正本） | ルート Config テーブル。`normalization_rule` から物理 FK 被参照。派生 Feature からは LOGICAL 参照 |
| 派生への影響 | どの正規化 version を使うかを **意味体系 version に紐づける** | 実際の sigmoid 計算パラメータの **再現性正本** |
| Public API | 非公開 | 非公開 |

> **Featureルール定義書との関係**: §14.8 はパラメータ正本を `feature_normalization_version` とする。本テーブルは GiftMeaningSpace §7.4 の「`semantic_config_version` に正規化ルールを含める」方針を満たす **binding 層** として、意味 version と正規化 version を接続する。§16.2 の「Feature正規化 → feature_normalization_version」と矛盾しない。

### 5.2 関連テーブルとの関係

| 観点 | 参照先 | 本テーブルとの関係 |
| ---- | ------ | ------------------ |
| version ヘッダ | `semantic_config_version` | `semantic_config_version_id` で所属 version を特定（物理 FK ON） |
| 正規化パラメータ正本 | `feature_normalization_version` | `feature_normalization_version_id` で **物理 FK ON**（`ON DELETE RESTRICT`）。`normalization_method` との列間整合は seed + CHECK で担保 |
| Feature 統合 | `feature_integration_rule` | 統合後 raw 値の正規化は本テーブル → `feature_normalization_version` 経由で実施 |
| 派生 Feature | `user_feature` / `item_feature` | 解決済み `feature_normalization_version_id` を派生行に記録（各派生テーブル責務） |

### 5.3 Public API 非公開方針

| API | 方針 | 根拠 |
| --- | ---- | ---- |
| API-PUB-007 | `normalization_rule` 行・binding を応答に含めない | 内部 Rule |
| API-PUB-008 | `normalization_rule` は返却しない Rule 種別 | 契約仕様書 §7.3.1 と同型（内部 Rule 群） |

> `feature_normalization_version_id` および `parameter_json` は Public Response に露出しない（`feature_normalization_version` テーブル定義書 §5.2 参照）。

### 5.4 論理ER / Featureルール定義書との差分

| 観点 | 正本の記載 | 本テーブルの扱い |
| ---- | ---------- | ---------------- |
| 論理ER §10.2 | 抽象 `feature_rule` に加え `normalization_rule` を **独立エンティティ**として追記（本 Issue スコープ） | 物理ER §5 No.5 の `feature_rule` 分解一覧にも含む。パラメータ version は `feature_normalization_version` に分離 |
| Featureルール §17 | `normalization_rule` 専用論理項目節なし | §14 + GiftMeaningSpace §7.4 から物理項目を **導出** |
| Matching / Ranking 定義書 | 正規化ルールは `semantic_config_version` 管理 | 本テーブルが binding 正本。パラメータは §14.8 どおり `feature_normalization_version` |

### 5.5 対象外

- sigmoid パラメータ本体（`center_feature` / `k_feature` / 将来の μ / σ）— `feature_normalization_version.parameter_json` の責務
- Feature raw 値の統合ロジック（`feature_integration_rule` / reco の責務）
- User / Item Feature 生成結果（`user_feature` / `item_feature` の責務）
- 正規化分布の監視・集計（`normalization_distribution_metric` の責務）

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `normalization_rule_id` | Normalization Rule ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK。Public API 非公開 |
| 2 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `yes` | — | — | 所属する意味定義 version。`semantic_config_version` を参照 |
| 3 | `normalization_method` | Normalization Method | `text` | `yes` | — | — | — | — | 正規化方式。MVP は `sigmoid`（Featureルール定義書 §14.2） |
| 4 | `feature_normalization_version_id` | Feature Normalization Version ID | `uuid` | `yes` | — | `yes` | — | — | 適用する正規化パラメータ version。`feature_normalization_version` を物理 FK 参照 |
| 5 | `is_active` | Active Flag | `boolean` | `yes` | — | — | — | `true` | 有効フラグ。`false` は batch / reco 参照対象外 |

> **MVP 行モデル**: version あたり 1 行（全 8 軸共通 binding）。`feature_code` 列は持たない（§17.1 No.2 参照）。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `normalization_rule_id` | サロゲート UUID | |
| UNIQUE | `normalization_rule_id` | PK と同一 | — |
| UNIQUE | `semantic_config_version_id` | MVP は version 内 1 行 | Index 名: `uq_normalization_rule_version` |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `semantic_config_version_id` | `semantic_config_version.semantic_config_version_id` | `ON` | RESTRICT | 物理ER §9 / semantic_config_version §8.1（contains） |
| `feature_normalization_version_id` | `feature_normalization_version.feature_normalization_version_id` | `ON` | RESTRICT | 物理ER §9（resolves）。アプリ設計で固定される binding 正本のため物理 FK を採用（§17.1 No.3 **決定済み**） |

### 8.1 列間整合（DB FK 外）

| カラム | 参照先属性 | 整合方式 | 備考 |
| ------ | ---------- | -------- | ---- |
| `normalization_method` | `feature_normalization_version.normalization_method` | seed + CHECK + 運用 validation | 参照先 version の `normalization_method` と一致必須。単一列 FK では表現できないため列間整合として担保 |

> batch / reco は (1) 本テーブルで binding 解決 → (2) `feature_normalization_version` で `parameter_json` 取得 → (3) 派生行に `feature_normalization_version_id` 記録、の 3 段階とする。

### 8.2 被参照

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| — | — | — | — | MVP では他テーブルからの物理 FK なし。batch / reco が version 単位で Lookup |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `normalization_rule_pkey` | `normalization_rule_id` | btree（PK） | 主キー | 自動生成 |
| `uq_normalization_rule_version` | `semantic_config_version_id` | btree（unique） | version 内 1 行 | §7 と同一 |
| `idx_normalization_rule_version_active_lookup` | `semantic_config_version_id`, `is_active` | btree | batch / reco binding Lookup | active 行取得 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `normalization_rule_pkey` | PRIMARY KEY | `normalization_rule_id` | 主キー | — |
| `uq_normalization_rule_version` | UNIQUE | `semantic_config_version_id` | MVP は version あたり 1 行 | §17.1 No.2 |
| `fk_normalization_rule_semantic_config_version` | FOREIGN KEY | `semantic_config_version_id` | `semantic_config_version` ON DELETE RESTRICT | semantic_config_version §8.1 |
| `fk_normalization_rule_feature_normalization_version` | FOREIGN KEY | `feature_normalization_version_id` | `feature_normalization_version` ON DELETE RESTRICT | feature_normalization_version §8.1。§17.1 No.3 **決定済み** |
| `chk_normalization_method_mvp` | CHECK | `normalization_method` | `normalization_method IN ('sigmoid')` | feature_normalization_version と同一 MVP 1 値 |
| `chk_feature_norm_version_id_not_null` | CHECK | `feature_normalization_version_id` | `NOT NULL` | 型上必須だが DDL 明示用 |

> **`parameter_json` は本テーブルに持たない**（Human Review 論点: カラム vs JSONB → パラメータは `feature_normalization_version` の JSONB 正本に集約。§17.1 No.1）。

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `normalization_method` | `normalization_method` | Featureルール定義書 §14.2 | `sigmoid` | enum 正本化は後続 enum Task。CHECK で担保 |
| `feature_normalization_version_id` | — | `feature_normalization_version` | 有効 UUID | Public 非公開 |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | batch | Item Feature 生成前 | — | — | `semantic_config_version_id` + `is_active=true` で binding 解決 |
| SELECT | reco | User Feature 生成前 | — | — | 同上 |
| SELECT | batch / reco | 再現参照 | — | — | 派生行に保存済み `feature_normalization_version_id` を直接参照（binding 変更の影響を受けない） |
| INSERT | database（seed） | 新 `semantic_config_version` 投入時 | 全列 | Upsert 想定（version UNIQUE） | 初期 seed は現行 `feature_normalization_version`（`is_current=true`）を参照 |
| UPDATE | database（運用） | binding 変更 | `feature_normalization_version_id`, `is_active` | version UNIQUE 下で 1 行 UPDATE | `normalization_method` 変更は新 version 行 INSERT を推奨 |
| DELETE | — | MVP では原則禁止 | — | — | 履歴保持 |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 意味定義 version と同寿命。過去 version の binding も再現性のため保持 |
| 削除方式 | 物理 DELETE 原則禁止 |
| 削除条件 | 親 `semantic_config_version` 削除前に子行整理（RESTRICT）。参照中の `feature_normalization_version` は `normalization_rule` 経由で DELETE RESTRICT |
| 論理削除 | `is_active = false` |
| version 切替 | 新 `semantic_config_version` 作成時に新規 INSERT（1 行） |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `normalization_rule` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: `semantic_config_version`・`feature_normalization_version` 作成後、Semantic Rule 群の一部として適用 |
| rollback方針 | forward migration 主体 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | batch / reco（service role 経由） |
| 書き込み権限 | database seed / 運用のみ |
| Public API | 非公開（§5.3） |
| ログ出力制限 | `feature_normalization_version_id` を Public ログに過剰出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / FK / CHECK | migration |
| 2 | UNIQUE | 同一 `semantic_config_version_id` の重複 INSERT が拒否される | migration |
| 3 | FK | 存在しない `semantic_config_version_id` / `feature_normalization_version_id` が拒否される | migration |
| 4 | batch 整合 | Item Feature 生成時に binding 経由で解決した `feature_normalization_version_id` が `item_feature` に記録される | integration |
| 5 | reco 整合 | User Feature 生成時に同様に `user_feature` へ記録される | integration |
| 6 | seed 整合 | 各 `semantic_config_version` seed に 1 行 binding が存在し、現行 `feature_normalization_version` を参照する | manual |
| 7 | 責務分離 | 本テーブルに `parameter_json` / `center_feature` / `k_feature` 列が存在しない | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review 前の論点は §17.1 を参照 |

### 17.1 Human Review 観点（Issue #493）

| No | 論点 | 決定 / 推奨案 | 状態 | 備考 |
| --: | ---- | ------------- | ---- | ---- |
| 1 | sigmoid パラメータの保持方式（カラム vs JSONB） | **本テーブルには持たない**。`feature_normalization_version.parameter_json` を正本とする（Featureルール §14.8） | **決定済み** | normalization_rule は binding のみ |
| 2 | 行モデル（`feature_code` 単位 vs version 共通） | **MVP は version あたり 1 行**（全 8 軸共通）。`uq_normalization_rule_version` を採用 | **決定済み** | feature_normalization_version MVP も全軸共通（§14.3） |
| 3 | `feature_normalization_version_id` への物理 FK vs LOGICAL | **物理 FK ON**（`ON DELETE RESTRICT`）。binding はアプリ設計で固定される正本のため整合性を DB で担保 | **決定済み** | 比較は §17.1.1。`feature_normalization_version` §8.1 を更新 |
| 4 | `normalization_method` と参照 version の整合 | seed + CHECK で `normalization_method='sigmoid'` 固定。参照先 version の method と一致を seed 運用で担保 | **決定済み** | §8.1 列間整合。将来 `z_score_sigmoid` は enum Task 連動 |
| 5 | 論理ER へのエンティティ追記 | **本 Issue スコープに含める**（§10.2 エンティティ・§10.1 ER 図・§14.5 関係表） | **決定済み** | Human Review 2026-06-12 |

#### 17.1.1 No.3 物理 FK vs LOGICAL 比較

| 観点 | 物理 FK（`ON DELETE RESTRICT`） | LOGICAL（seed + 存在確認） |
| ---- | ------------------------------- | ------------------------- |
| 参照整合性 | DB が存在しない version 参照を拒否 | seed / アプリ validation に依存 |
| 適用対象の性質 | **設定 binding 正本**（version あたり 1 行）に向く | **大量派生行**（`user_feature` / `item_feature`）の再現記録に向く |
| プロジェクト慣例 | `semantic_config_version_id` と同様、Rule 定義の必須参照は物理 FK 化しやすい | `relationship_rule` → `relationship_master`（自然キー Master）、派生 Feature → `feature_normalization_version` は LOGICAL |
| migration 順序 | `feature_normalization_version` 作成後に `normalization_rule` を CREATE | 順序制約は緩い |
| version ライフサイクル | 参照先 version の DELETE は RESTRICT で保護（immutable version 方針と整合） | 孤児参照をアプリ層で検知する必要あり |
| 被参照側の記載 | `feature_normalization_version` §8.1 に `normalization_rule`（物理 FK ON）を追記 | 派生 Feature 参照は §8.2 LOGICAL のまま |

> **決定（Human Review 2026-06-12）**: No.3 は **物理 FK** を採用。`normalization_rule` → `feature_normalization_version` は自然発生する派生参照ではなく、アプリケーション設計で固定される binding 正本である。`user_feature` / `item_feature` からの参照は引き続き LOGICAL（再現記録・大量派生行）。

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8–§11 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §10.2・§14.5（本 Issue で追記） |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §8 No.43 |
| Featureルール | `docs/04_ドメインモデル設計/Featureルール定義書.md` | §14 / §14.8 / §16.2 |
| GiftMeaningSpace | `docs/04_ドメインモデル設計/GiftMeaningSpace定義書.md` | §7.4 正規化ルール管理 |
| 親テーブル | `docs/06_実装設計/database/semantic_config_version_テーブル定義書.md` | §8.1 contains FK |
| 参照テーブル | `docs/06_実装設計/database/feature_normalization_version_テーブル定義書.md` | §5.1 責務分離・parameter_json 正本 |
| 参考 Rule | `docs/06_実装設計/database/feature_integration_rule_テーブル定義書.md` | 内部 Rule 章構成 |
| 参考 Rule | `docs/06_実装設計/database/relationship_rule_テーブル定義書.md` | semantic_config_version 子 Rule FK 方針 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | normalization_method 正本化（後続 Task） |

---

## 19. レビュー観点

- 論理ER §10.2・物理ER §8–§11・テーブル一覧 §8 No.43 と矛盾していない
- `semantic_config_version` §8.1 contains FK 方針と一致している
- `feature_normalization_version` との責務分離が §5.1 / §17.1 で明示されている
- sigmoid パラメータを本テーブルに持たず、`feature_normalization_version.parameter_json` を正本としている
- `semantic_config_version_id` への物理 FK（ON DELETE RESTRICT）が明記されている
- `feature_normalization_version_id` への物理 FK（ON DELETE RESTRICT）が明記されている
- Public API 非公開が明記されている
- OpenAPI / generated 変更が含まれていない（#469 委譲）
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
