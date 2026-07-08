# Pair Rule テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                   |
| -------------- | -------------------------------------- |
| ドキュメントID | `DB-TBL-MVP-pair_rule`                 |
| ドキュメント名 | Pair Rule テーブル定義書               |
| 対象システム   | Gift Recommendation Service MVP        |
| MVP対象        | `yes`                                  |
| 作成日         | 2026-06-11                             |
| 更新日         | 2026-06-11                             |

---

## 2. 概要

`pair_rule` は、**Relationship × Occasion の組み合わせ（Pair）** に対する Feature **補正値（delta）** を、`semantic_config_version` 単位で保持する Semantic / Feature 定義系テーブルである。

Featureルール定義書 §9.3 / §17.3 の Pair Rule を物理化し、reco が User Feature 生成時に `relationship_rule` / `occasion_rule` の基準値へ加算する補正を参照する。**Public API では返却しない**（API-PUB-007 / API-PUB-008 非公開）。

---

## 3. 目的

- 代表的な Pair 組み合わせ × Feature 8 軸の補正値を version 管理する（Featureルール定義書 §20.1）
- reco が User Feature 生成時に Pair 由来の `feature_delta` を参照できるようにする
- `pair_master` で解決した `pair_id` を軸に、断面管理された Pair 補正を DB 制約で整合させる

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `pair_rule` |
| 論理テーブル名 | Pair Rule |
| 分類 | Semantic / Feature 定義系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | reco（User Feature 生成時の Pair 補正参照） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11 |

---

## 5. 用途・責務

- **`semantic_config_version_id` 単位**で、Pair 1 組み合わせ × Feature 1 軸 = **1 行**を保持する（正規化行モデル）
- **`pair_id`** は `pair_master` への **物理 FK** を採用する（Human Review #465）。Featureルール定義書 §17.3 の `relationship_code` / `occasion_code` は物理 DDL では保持しない
- **`feature_delta`** は Pair 由来の Feature 補正値（-1.0〜1.0）。`relationship_rule` / `occasion_rule` の基準値へ **加算**する（Featureルール定義書 §9.2）
- **`is_active = true`** の行のみ reco が参照する
- MVP では **代表的な Pair 組み合わせのみ** seed 定義する（Featureルール定義書 §20.1 / §9.3）。全 12×15 組み合わせは対象外

### 5.1 関連テーブルとの関係

| 観点 | 参照先 | 本テーブルとの関係 |
| ---- | ------ | ------------------ |
| version ヘッダ | `semantic_config_version` | `semantic_config_version_id` で所属 version を特定（物理 FK ON） |
| Pair 組み合わせ | `pair_master` | `pair_id` で **物理 FK** 参照。断面管理の正本 |
| Feature 軸 | `feature_definition` | 同一 version 内の `feature_code` と整合。MVP 8 軸 CHECK |
| Relationship 基準値 | `relationship_rule` | base value の責務。本テーブルは delta 補正 |
| Occasion 基準値 | `occasion_rule` | base value の責務。本テーブルは delta 補正 |

### 5.2 Public API 非公開方針

| API | 方針 | 根拠 |
| --- | ---- | ---- |
| API-PUB-007 | `pair_rule` 行・補正値を応答に含めない | 契約仕様書 §5 / §14 |
| API-PUB-008 | `pair_rule` は返却しない Rule 種別 | 契約仕様書 §5 / §7.3.1 |

> Pair 補正は Reco 内部完結。`pair_id` および `feature_delta` は Public 表面に露出しない。

### 5.3 対象外

- Pair 組み合わせ自体の定義（`pair_master` の責務）
- Relationship / Occasion 個別の基準値（`relationship_rule` / `occasion_rule` の責務）
- Concept 補正（`concept_feature_rule` の責務）
- User Feature 生成結果（`user_feature` の責務）
- `input_type_rule` / `feature_integration_rule` の内部 Rule 詳細

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `pair_rule_id` | Pair Rule ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK |
| 2 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `yes` | — | — | 所属する意味定義 version。`semantic_config_version` を参照 |
| 3 | `pair_id` | Pair ID | `uuid` | `yes` | — | `yes` | — | — | 補正対象 Pair。`pair_master.pair_id` を参照（物理 FK） |
| 4 | `feature_code` | Feature Code | `text` | `yes` | — | — | — | — | MVP 8 軸コード。enum定義書 §6.16 正本 |
| 5 | `feature_delta` | Feature Delta | `numeric(4,3)` | `yes` | — | — | — | `0.000` | Pair 由来 Feature 補正値。-1.0〜1.0 |
| 6 | `is_active` | Active Flag | `boolean` | `yes` | — | — | — | `true` | 有効フラグ。`false` は reco 参照対象外 |

> **論理ER / Featureルール定義書との差分**: 論理ER §10.2 には抽象エンティティ `feature_rule` が列挙され、Featureルール定義書 §17.3 には `relationship_code` / `occasion_code` が論理項目として記載されている。物理テーブルでは `pair_rule` へ **分解**し（物理ER §5 No.5・テーブル一覧 §8）、Pair 参照は **Human Review #465** に従い `pair_id` 物理 FK とする。`relationship_code` / `occasion_code` は `pair_master` 経由で間接的に特定される。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `pair_rule_id` | サロゲート UUID | |
| UNIQUE | `pair_rule_id` | PK と同一 | — |
| UNIQUE | `semantic_config_version_id`, `pair_id`, `feature_code` | version 内で Pair × Feature 軸は 1 行 | Index 名: `uq_pair_rule_version_pair_feature` |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `semantic_config_version_id` | `semantic_config_version.semantic_config_version_id` | `ON` | RESTRICT | 物理ER §9 / semantic_config_version §8.1 |
| `pair_id` | `pair_master.pair_id` | `ON` | RESTRICT | Human Review #465。Pair 断面管理のため codes 参照ではなく `pair_id` を正とする |

### 8.1 論理参照（MVP 初期 DDL）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `feature_code` | `feature_definition.feature_code`（同一 `semantic_config_version_id`） | `LOGICAL` | CHECK + seed | version 内 8 軸存在は seed / アプリ validation で担保 |

> `feature_definition` への物理 FK は version 内 code 参照のため MVP では付与しない。整合は `chk_feature_code_mvp` + seed で担保する（relationship_rule と同型）。

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `pair_rule_pkey` | `pair_rule_id` | btree（PK） | 主キー | 自動生成 |
| `uq_pair_rule_version_pair_feature` | `semantic_config_version_id`, `pair_id`, `feature_code` | btree（unique） | version 内 Rule 一意 | §7 と同一 |
| `idx_pair_rule_version_pair_active_lookup` | `semantic_config_version_id`, `pair_id`, `is_active`, `feature_code` | btree | reco Pair 補正 Lookup | Run 解決済み `pair_id` + version で 8 軸分を参照 |
| `idx_pair_rule_pair_id` | `pair_id` | btree | FK / 被参照整合 | pair_master §8.2 被参照向け |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `pair_rule_pkey` | PRIMARY KEY | `pair_rule_id` | 主キー | — |
| `uq_pair_rule_version_pair_feature` | UNIQUE | `semantic_config_version_id`, `pair_id`, `feature_code` | version 内一意 | |
| `fk_pair_rule_semantic_config_version` | FOREIGN KEY | `semantic_config_version_id` | `semantic_config_version` ON DELETE RESTRICT | semantic_config_version §8.1 |
| `fk_pair_rule_pair_master` | FOREIGN KEY | `pair_id` | `pair_master` ON DELETE RESTRICT | pair_master §8.2 |
| `chk_feature_code_mvp` | CHECK | `feature_code` | MVP 8 軸 IN 句 | feature_definition / 物理ER §11 と同一 |
| `chk_feature_delta_range` | CHECK | `feature_delta` | `feature_delta >= -1.0 AND feature_delta <= 1.0` | Featureルール定義書 §3.6 |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `feature_code` | `feature_code` | enum定義書 §6.16 | MVP 8 値 | 物理ER §11 |
| `feature_delta` | — | Featureルール定義書 §3.6 | -1.0〜1.0 | CHECK で担保。MVP 運用は通常 ±0.30 程度 |
| `pair_id` | — | `pair_master` | seed 投入済み Pair のみ | 存在しない `pair_id` は FK で拒否 |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | reco | User Feature 生成時。`semantic_config_version_id` + 解決済み `pair_id` + `is_active=true` | — | — | `relationship_rule` / `occasion_rule` 基準値へ `feature_delta` を加算（§9.2） |
| SELECT | reco | 該当 Pair × Feature 行なし | — | — | `pair_delta = 0` として補正なし（Featureルール定義書 §9.2） |
| INSERT | database（seed） | 新 version 初回投入 | 全列 | version ごと Upsert | MVP は代表 Pair のみ（§20.1） |
| UPDATE | database（運用） | 補正値調整・無効化 | `feature_delta`, `is_active` | — | **`pair_id` / `feature_code` 変更禁止**（新 version INSERT 推奨） |
| DELETE | — | MVP では原則禁止 | — | — | `is_active=false` で無効化 |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（設定正本。version 履歴として保持） |
| 削除方式 | 物理 DELETE 原則禁止 |
| 論理削除 | `is_active = false` |
| version 切替 | 新 `semantic_config_version` 作成時に代表 Pair 分を新規 INSERT |
| Pair 無効化連鎖 | `pair_master.is_active=false` の Pair を参照する行は reco 解決前に除外される想定。行自体の扱いは seed / 運用で整理 |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `pair_rule` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: `semantic_config_version`・`pair_master`・`feature_definition` 作成後、Rule 群の一部として適用 |
| rollback方針 | forward migration 主体 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | reco（service role）のみ。api は Public 返却しないため直接参照不要 |
| 書き込み権限 | database seed / 運用のみ |
| Public API | **非公開**。API-PUB-007 / API-PUB-008 応答に `pair_rule` / `feature_delta` / `pair_id` を含めない |
| ログ出力制限 | Pair 補正設定値を過剰ログ出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / FK / CHECK が定義どおり | migration |
| 2 | UNIQUE | 同一 version で同一 pair × feature の重複 INSERT が拒否される | migration |
| 3 | pair_id FK | 存在しない `pair_id` の INSERT が拒否される | migration |
| 4 | 値域 CHECK | `feature_delta` が -1.0〜1.0 外で拒否される | migration |
| 5 | reco 参照 | 解決済み `pair_id` + version で active 行のみ加算される | integration |
| 6 | Public API | API-PUB-007 / API-PUB-008 が `pair_rule` を返却しない | contract |
| 7 | seed 整合 | Featureルール定義書 §9.3 の代表 Pair が seed に存在 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | MVP seed 対象 Pair の最終範囲 | §9.3 代表 14 組み合わせのうち `pair_master` に存在する組み合わせの確定 | Human | seed Task 前 | seed Task へ引き継ぎ |

### 17.1 Human Review 決定事項（踏襲）

| No | 論点 | 決定内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | Pair 参照方式 | **`pair_id` 物理 FK** を採用。`relationship_code` / `occasion_code` は物理 DDL に保持しない | Human | pair_master PR #465 / §17.1 No.3 |
| 2 | `semantic_config_version_id` FK | **物理 FK ON**、ON DELETE RESTRICT | Human | relationship_rule / semantic_config_version と同型 |
| 3 | version 内 UNIQUE | **採用**。`(semantic_config_version_id, pair_id, feature_code)` | Human | 1 Pair × 1 Feature 軸 = 1 補正値 |
| 4 | `feature_delta` 値域 | **-1.0〜1.0**（Featureルール定義書 §3.6） | Human | 運用目安は ±0.30 程度 |
| 5 | `is_active` 列 | **MVP 物理 DDL に採用** | Human | relationship_rule と同型 |
| 6 | Public API | **非公開**（API-PUB-007 / API-PUB-008） | Human | Reco 内部完結 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8–§11 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §10.2（抽象 feature_rule 分解） |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §8・pair_master との関係 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | §6.16 feature_code |
| Featureルール | `docs/04_ドメインモデル設計/Featureルール定義書.md` | §3.6 / §9.2 / §9.3 / §17.3 / §20.1 |
| API契約 | `docs/06_実装設計/api/API-PUB-007_Semantic設定取得API契約仕様書.md` | 内部 Rule 非公開 |
| API契約 | `docs/06_実装設計/api/API-PUB-008_Featureルール取得API契約仕様書.md` | pair_rule 非公開 |
| 先行テーブル | `docs/06_実装設計/database/semantic_config_version_テーブル定義書.md` | 親 FK |
| 先行テーブル | `docs/06_実装設計/database/pair_master_テーブル定義書.md` | pair_id 物理 FK |
| 先行テーブル | `docs/06_実装設計/database/feature_definition_テーブル定義書.md` | feature_code |
| 参考 Rule | `docs/06_実装設計/database/relationship_rule_テーブル定義書.md` | Rule 系章構成・CHECK 方針 |
| 先行 Task | Issue #462 / #463 / #449 / #470 / #473 | Wave1 + pair_master + feature_definition + relationship_rule |

---

## 19. レビュー観点

- 論理ER §10.2（抽象 `feature_rule` 分解）・物理ER §8–§11・テーブル一覧 §8 と矛盾していない
- Featureルール定義書 §17.3 の論理項目が物理カラムとして整理されている（`pair_id` 置換差分が明示されている）
- pair_master テーブル定義書の `pair_id` 物理 FK 方針（Human Review #465）と一貫している
- `semantic_config_version_id` FK（物理 ON）および `feature_code` の LOGICAL 参照方針が明記されている
- `feature_delta` の -1.0〜1.0 CHECK が明記されている
- API-PUB-007 / API-PUB-008 に基づく Public API 非公開が明記されている
- relationship_rule テーブル定義書と Rule 系方針（UNIQUE / is_active / version 管理）が一貫している
- OpenAPI / generated 変更が含まれていない（#469 委譲）
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
