# Concept Feature Rule テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                   |
| -------------- | -------------------------------------- |
| ドキュメントID | `DB-TBL-MVP-concept_feature_rule`      |
| ドキュメント名 | Concept Feature Rule テーブル定義書    |
| 対象システム   | Gift Recommendation Service MVP        |
| MVP対象        | `yes`                                  |
| 作成日         | 2026-06-11                             |
| 更新日         | 2026-06-11（Human Review Issue #476 反映） |

---

## 2. 概要

`concept_feature_rule` は、**Semantic Concept** から User / Item Feature への **補正値（delta）** を、`semantic_config_version` 単位で保持する Semantic / Feature 定義系テーブルである。

Featureルール定義書 §6・§17.4 の Concept Feature Rule を物理化し、API-PUB-008（Feature ルール取得）の `conceptFeatureRules[]` の DB 正本となる。reco / batch は Semantic 抽出結果（Concept + confidence）に本 Rule を適用し、Feature 生成へ反映する。

---

## 3. 目的

- 初期 **18 Concept** に対する Concept → Feature 補正 Rule を version 管理する（Featureルール定義書 §20.1）
- reco / batch が Feature 生成時に `concept_feature_delta * confidence` 相当の補正を参照できるようにする
- seed 投入後、Public API から Concept Feature Rule を安定返却できるようにする

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `concept_feature_rule` |
| 論理テーブル名 | Concept Feature Rule |
| 分類 | Semantic / Feature 定義系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | reco（User Feature 生成）、batch（Item Feature 生成）、api（API-PUB-008 経由の参照） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11 |

---

## 5. 用途・責務

- **`semantic_config_version_id` 単位**で、Concept 1 件 × Feature 1 軸 = **1 行**を保持する（正規化行モデル）
- **`semantic_concept_id`** は `semantic_concept` への **物理 FK** を採用する（semantic_concept テーブル定義書 §8.1）。Featureルール定義書 §17.4 の `concept_code` は **子 Rule 側では FK 列で表現**し、Public API 表面では `semantic_concept.concept_code` を JOIN して `conceptCode` として返す（semantic_rule と同型）
- **`feature_delta`** は Concept 由来の Feature 補正の **大きさ**（0.0〜1.0）。適用時の符号・方向は **`polarity`** で表現する（API-PUB-008 §7.3.1）
- **`is_active = true`** の行のみ API-PUB-008 が返却する（契約上、返却行は active のみ）
- MVP seed は **初期 18 Concept** を対象とする。**稀疏 seed**（全 18×8 完全行列は必須としない — §17.1 No.5 決定済み）。version 内で同一 Concept × Feature の重複は禁止（§17.1 No.4 決定済み）

### 5.1 関連テーブルとの関係

| 観点 | 参照先 | 本テーブルとの関係 |
| ---- | ------ | ------------------ |
| version ヘッダ | `semantic_config_version` | `semantic_config_version_id` で所属 version を特定（物理 FK ON） |
| Semantic Concept | `semantic_concept` | `semantic_concept_id` で **物理 FK** 参照。18 Concept 正本 |
| Feature 軸 | `feature_definition` | 同一 version 内の `feature_code` と整合。MVP 8 軸 CHECK |
| Relationship 基準値 | `relationship_rule` | base value の責務。本テーブルは Concept delta 補正 |
| Occasion 基準値 | `occasion_rule` | base value の責務。本テーブルは Concept delta 補正 |
| Pair 補正 | `pair_rule` | Pair delta 補正。Public API 非公開。本テーブルは Concept 補正 |

### 5.2 API-PUB-008 マッピング（`conceptFeatureRules[]`）

| API フィールド | DB 列 / 導出 | 備考 |
| -------------- | ------------ | ---- |
| `semanticConfigVersionId` | `semantic_config_version_id` | 現行 version 解決は api アプリ層 |
| `conceptFeatureRules[].conceptCode` | `semantic_concept.concept_code`（`semantic_concept_id` で JOIN） | API-PUB-007 と同一コード体系 |
| `conceptFeatureRules[].featureCode` | `feature_code` | MVP 8 軸。enum定義書 §6.16 |
| `conceptFeatureRules[].featureDelta` | `feature_delta` | `numeric(4,3)` 相当。0.0〜1.0 |
| `conceptFeatureRules[].polarity` | `polarity` | 任意応答。`positive` / `negative` / `mixed` |

> 内部 PK `concept_feature_rule_id` および `semantic_concept_id` は Public API 非公開。OpenAPI / generated 追随は Epic 終盤 Task #469 の責務。

### 5.3 Feature 生成との関係（reco / batch）

Featureルール定義書 §3.6 / §9.2 より、Concept 由来補正は概ね以下で適用する。

```text
applied_delta = feature_delta * source_weight * confidence
```

- `feature_delta` / `polarity` は本テーブル正本
- `confidence` は Semantic 抽出結果（`user_semantic` / `item_semantic`）側
- `source_weight` は入力種別等の重み（MVP では Rule 統合ロジック側で扱う。`input_type_rule` は partial）

### 5.4 対象外

- Semantic Concept 定義本体（`semantic_concept` の責務）
- Semantic 抽出ルール（`semantic_rule` の責務）
- Relationship / Occasion 基準値（`relationship_rule` / `occasion_rule` の責務）
- Pair 補正（`pair_rule` の責務。Public API 非公開）
- User / Item Feature 生成結果（`user_feature` / `item_feature` の責務）
- `input_type_rule` / `feature_integration_rule` の内部 Rule 詳細

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `concept_feature_rule_id` | Concept Feature Rule ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK。Public API 非公開 |
| 2 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `yes` | — | — | 所属する意味定義 version。`semantic_config_version` を参照 |
| 3 | `semantic_concept_id` | Semantic Concept ID | `uuid` | `yes` | — | `yes` | — | — | 補正対象 Concept。`semantic_concept` を参照（物理 FK） |
| 4 | `feature_code` | Feature Code | `text` | `yes` | — | — | — | — | MVP 8 軸コード。enum定義書 §6.16 正本 |
| 5 | `feature_delta` | Feature Delta | `numeric(4,3)` | `yes` | — | — | — | `0.000` | Concept 由来 Feature 補正の大きさ。0.0〜1.0 |
| 6 | `polarity` | Polarity | `text` | `yes` | — | — | — | `'positive'` | 補正の極性。`positive` / `negative` / `mixed` |
| 7 | `is_active` | Active Flag | `boolean` | `yes` | — | — | — | `true` | 有効フラグ。`false` は API 返却対象外 |

> **論理ER / Featureルール定義書との差分**: 論理ER §10.2 には抽象エンティティ `feature_rule` が列挙され、Featureルール定義書 §17.4 には `concept_code` が論理項目として記載されている。物理テーブルでは `concept_feature_rule` へ **分解**し（物理ER §5 No.5・テーブル一覧 §8）、Concept 参照は semantic_concept テーブル定義書 §8.1 に従い **`semantic_concept_id` 物理 FK** とする。`concept_code` は API 応答時に JOIN で導出する（semantic_rule §6 注記と同型）。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `concept_feature_rule_id` | サロゲート UUID | |
| UNIQUE | `concept_feature_rule_id` | PK と同一 | — |
| UNIQUE | `semantic_config_version_id`, `semantic_concept_id`, `feature_code` | version 内で Concept × Feature 軸は 1 行 | Index 名: `uq_concept_feature_rule_version_concept_feature` |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `semantic_config_version_id` | `semantic_config_version.semantic_config_version_id` | `ON` | RESTRICT | 物理ER §9 / semantic_config_version §8.1 |
| `semantic_concept_id` | `semantic_concept.semantic_concept_id` | `ON` | RESTRICT | semantic_concept §8.1。同一 version 内 Concept のみ参照可（§10.1） |

### 8.1 論理参照（MVP 初期 DDL）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `feature_code` | `feature_definition.feature_code`（同一 `semantic_config_version_id`） | `LOGICAL` | CHECK + seed | version 内 8 軸存在は seed / アプリ validation で担保 |

### 8.2 version 内 Concept 整合（推奨 CHECK / トリガ）

`semantic_concept_id` が指す Concept の `semantic_config_version_id` は、本行の `semantic_config_version_id` と一致しなければならない。

> DDL Task では `semantic_concept` への FK に加え、複合 CHECK またはトリガで version 整合を担保する（semantic_rule と同型の子 Rule 方針）。

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `concept_feature_rule_pkey` | `concept_feature_rule_id` | btree（PK） | 主キー | 自動生成 |
| `uq_concept_feature_rule_version_concept_feature` | `semantic_config_version_id`, `semantic_concept_id`, `feature_code` | btree（unique） | version 内 Rule 一意 | §7 と同一 |
| `idx_concept_feature_rule_version_active_lookup` | `semantic_config_version_id`, `is_active`, `semantic_concept_id`, `feature_code` | btree | API-PUB-008 一覧（active Rule） | reco / batch 参照にも利用 |
| `idx_concept_feature_rule_semantic_concept_id` | `semantic_concept_id` | btree | Concept 単位の Rule 参照 | semantic_concept 子 FK 用 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `concept_feature_rule_pkey` | PRIMARY KEY | `concept_feature_rule_id` | 主キー | — |
| `uq_concept_feature_rule_version_concept_feature` | UNIQUE | `semantic_config_version_id`, `semantic_concept_id`, `feature_code` | version 内一意 | |
| `fk_concept_feature_rule_semantic_config_version` | FOREIGN KEY | `semantic_config_version_id` | `semantic_config_version` ON DELETE RESTRICT | semantic_config_version §8.1 |
| `fk_concept_feature_rule_semantic_concept` | FOREIGN KEY | `semantic_concept_id` | `semantic_concept` ON DELETE RESTRICT | semantic_concept §8.1 |
| `chk_feature_code_mvp` | CHECK | `feature_code` | MVP 8 軸 IN 句 | feature_definition / 物理ER §11 と同一 |
| `chk_feature_delta_range` | CHECK | `feature_delta` | `feature_delta >= 0.0 AND feature_delta <= 1.0` | API-PUB-008 §7.3.1 |
| `chk_polarity_mvp` | CHECK | `polarity` | `polarity IN ('positive','negative','mixed')` | enum定義書 §6.20 / API-PUB-008。packages 正本化は後続 enum Task（§17.1 No.1 決定済み） |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `feature_code` | `feature_code` | enum定義書 §6.16 | MVP 8 値 | 物理ER §11 |
| `polarity` | `polarity` | enum定義書 §6.20 / API-PUB-008 | `positive` / `negative` / `mixed` | MVP は CHECK で担保（§17.1 No.1 決定済み） |
| `feature_delta` | — | API-PUB-008 | 0.0〜1.0 | 大きさ。符号は `polarity`（§17.1 No.2 決定済み。pair_rule の signed delta とは分離） |
| `semantic_concept_id` | — | `semantic_concept` | seed 投入済み Concept のみ | 存在しない Concept は FK で拒否 |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | api | 現行 `semantic_config_version` + `is_active=true` | — | — | API-PUB-008。`semantic_concept` JOIN で `conceptCode` を付与 |
| SELECT | reco / batch | Feature 生成時。抽出 Concept + version + `is_active=true` | — | — | `feature_delta` × confidence 等で適用（§5.3） |
| SELECT | reco / batch | 該当 Concept × Feature 行なし | — | — | 当該 Concept 軸の補正なしとして扱う（0 加算） |
| INSERT | database（seed） | 新 version 初回投入 | 全列 | version ごと Upsert | MVP は初期 18 Concept 分（§20.1） |
| UPDATE | database（運用） | 補正値・極性調整・無効化 | `feature_delta`, `polarity`, `is_active` | — | **`semantic_concept_id` / `feature_code` 変更禁止**（新 version INSERT 推奨） |
| DELETE | — | MVP では原則禁止 | — | — | `is_active=false` で無効化 |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（設定正本。version 履歴として保持） |
| 削除方式 | 物理 DELETE 原則禁止 |
| 論理削除 | `is_active = false` |
| version 切替 | 新 `semantic_config_version` 作成時に初期 18 Concept 分を新規 INSERT |
| Concept 無効化連鎖 | `semantic_concept.is_active=false` の Concept を参照する行は API 返却対象外。reco 適用方針は seed / 運用で整理 |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `concept_feature_rule` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: `semantic_config_version`・`semantic_concept`・`feature_definition` 作成後、Rule 群の一部として適用 |
| rollback方針 | forward migration 主体 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | api / reco / batch（service role） |
| 書き込み権限 | database seed / 運用のみ |
| Public API | `conceptFeatureRules[]` は API-PUB-008 で公開（内部 UUID は非公開） |
| ログ出力制限 | Rule 設定値を過剰ログ出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / FK / CHECK | migration |
| 2 | UNIQUE | 同一 version で同一 Concept × feature の重複 INSERT が拒否される | migration |
| 3 | 値域 CHECK | `feature_delta` が 0.0〜1.0 外で拒否される | migration |
| 4 | FK 整合 | 存在しない `semantic_concept_id` が拒否される | migration |
| 5 | API 整合 | active 行が API-PUB-008 `conceptFeatureRules` 形式で返る（`conceptCode` JOIN 含む） | integration |
| 6 | seed 整合 | Featureルール定義書 §20.1 の初期 18 Concept 分が seed に存在 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review（Issue #476）にて §17.1 No.1〜No.5 を決定済み |

### 17.1 Human Review 決定事項（Issue #476）

| No | 論点 | 決定内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | `polarity` enum 正本化タイミング | **採用**。MVP は `chk_polarity_mvp` CHECK + enum定義書 §6.20。packages/code-definitions 正本化は後続 enum Task | Human | API-PUB-008 §14 No.2 と一致 |
| 2 | `feature_delta` 値域 | **採用**。API-PUB-008 に合わせ **0.0〜1.0**（大きさ）。符号は `polarity` で表現 | Human | pair_rule の signed delta（-1.0〜1.0）とは責務分離 |
| 3 | Concept 参照列 | **採用**。`semantic_concept_id` 物理 FK を正とする。`concept_code` は API 応答時 JOIN（semantic_rule 同型） | Human | semantic_concept §8.1 / Featureルール §17.4 物理マッピング注記 |
| 4 | version 内 UNIQUE | **採用**。`(semantic_config_version_id, semantic_concept_id, feature_code)` UNIQUE | Human | relationship_rule / pair_rule と同型 |
| 5 | MVP seed 行数 | **採用**。18 Concept 対象の **稀疏** seed（全 18×8 完全行列は必須としない） | Human | Featureルール §20.1「初期18Conceptを定義」。不足行は補正なし（0 加算） |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8–§11 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §10.2 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §8 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | §6.16 feature_code / §6.20 polarity |
| API契約 | `docs/06_実装設計/api/API-PUB-008_Featureルール取得API契約仕様書.md` | conceptFeatureRules マッピング |
| API契約 | `docs/06_実装設計/api/API-PUB-007_Semantic設定取得API契約仕様書.md` | conceptCode 整合 |
| Featureルール | `docs/04_ドメインモデル設計/Featureルール定義書.md` | §17.4 / §20.1 |
| 先行 Task | Issue #462 / #463 / #471 | semantic_config / version / semantic_concept |

---

## 19. レビュー観点

- 論理ER §10.2・物理ER §8–§11・テーブル一覧 §8 と矛盾していない
- `semantic_config_version_id` FK（物理 ON）が明記されている
- `semantic_concept_id` FK（物理 ON）と API `conceptCode` JOIN 方針が明確
- API-PUB-008 `conceptFeatureRules` マッピングが明確
- `feature_delta` 値域（0.0〜1.0）と `polarity` enum（§17.1 決定済み）が明記されている
- Human Review 決定事項（§17.1 No.1〜No.5）が反映されている
- Public API 非公開列（内部 UUID）と公開列の区別が明確
- DDL Task が CREATE TABLE を起こせる粒度である
