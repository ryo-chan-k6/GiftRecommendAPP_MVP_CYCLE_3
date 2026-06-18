# Input Type Rule テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                   |
| -------------- | -------------------------------------- |
| ドキュメントID | `DB-TBL-MVP-input_type_rule`           |
| ドキュメント名 | Input Type Rule テーブル定義書           |
| 対象システム   | Gift Recommendation Service MVP        |
| MVP対象        | `yes`（DDL・seed 作成対象）            |
| 作成日         | 2026-06-11                             |
| 更新日         | 2026-06-11（Human Review #477 反映）   |

---

## 2. 概要

`input_type_rule` は、レコメンド入力の **入力種別（Input Type）** ごとに、どの Feature ルール適用経路をたどるかを、`semantic_config_version` 単位で保持する Semantic / Feature 定義系テーブルである。

Featureルール定義書 §2.1 / §11 の Input Type Rule を物理化する。Human Review #477 により **MVP から物理テーブル・migration・seed を作成する**（§17.1 No.1）。テーブル一覧 §8 上の分類は `partial`（△）だが、reco のディスパッチ正本は本テーブルとする。**Public API では返却しない**（API-PUB-007 / API-PUB-008 非公開）。

---

## 3. 目的

- 入力種別（relationship / occasion / preferred_condition 等）と Feature ルール適用経路の対応を version 管理する
- reco が User Feature 生成時に、入力ブロック種別に応じた Rule ディスパッチを DB から参照できるようにする
- 後続 DDL / seed Task が migration を作成できる粒度まで設計を確定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `input_type_rule` |
| 論理テーブル名 | Input Type Rule |
| 分類 | Semantic / Feature 定義系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | reco（User Feature 生成時の入力種別ディスパッチ） |
| MVP対象 | `yes`（DDL・seed 作成対象。テーブル一覧 §8 分類は `partial`（△）だが Human Review #477 で MVP migration 対象） |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11 |

---

## 5. 用途・責務

- **`semantic_config_version_id` 単位**で、入力種別 **1 件 = 1 行**を保持する（ディスパッチ設定モデル）
- **`input_type`** は Featureルール定義書 §11.1 の 7 分類を正とする
- **`application_method`** は §11.1 の「Featureルール上の扱い」を物理コード化したディスパッチ先
- **`invert_delta`** は `non_preferred_condition` 向けに Concept Feature Delta の反転適用を示す（§11.3）
- **`participates_in_feature_integration`** は `feature_integration_rule`（#478・partial）への統合対象かを示す。`ng_condition` / `budget_condition` は **false**（Hard Filter 分離）
- **`is_active = true`** の行のみ reco が参照する

### 5.1 Featureルール定義書 §11.1 との対応

| `input_type` | 内容 | `application_method`（本テーブル） | Feature 統合参加 | 備考 |
| ------------ | ---- | ---------------------------------- | ---------------- | ---- |
| `relationship` | 関係性 | `relationship_rule` | `true` | Relationship Rule を適用（§11.1） |
| `occasion` | 贈答目的 | `occasion_rule` | `true` | Occasion Rule を適用 |
| `preferred_condition` | 好み条件 | `concept_feature_delta_add` | `true` | Concept Feature Delta を加算（§11.2） |
| `non_preferred_condition` | 避けたい条件 | `concept_feature_delta_invert` | `true` | Delta 反転または抑制（§11.3）。`invert_delta=true` |
| `ng_condition` | 絶対NG条件 | `hard_filter_excluded` | `false` | Feature 化せず Hard Filter（§11.5） |
| `budget_condition` | 予算条件 | `hard_filter_excluded` | `false` | Feature 化せず Hard Filter（§11.5） |
| `free_text` | 自由入力 | `semantic_extraction_then_apply` | `true` | Semantic Concept 抽出後に Concept Feature Rule を適用（§11.1） |

> **Hard Filter 分離**: `ng_condition` / `budget_condition` は Feature ルール対象外である。本テーブルでは **ディスパッチ上「Feature 統合に参加しない」** ことを明示するのみとし、Hard Filter 条件本体は RecommendationRequest / Hard Filter モジュールの責務とする（Featureルール定義書 §2.2・§11.5）。

### 5.2 関連テーブルとの関係

| 観点 | 参照先 | 本テーブルとの関係 |
| ---- | ------ | ------------------ |
| version ヘッダ | `semantic_config_version` | `semantic_config_version_id` で所属 version を特定（物理 FK ON） |
| Relationship 基準値 | `relationship_rule` | `application_method=relationship_rule` 時に reco が参照 |
| Occasion 基準値 | `occasion_rule` | `application_method=occasion_rule` 時に reco が参照 |
| Concept 補正 | `concept_feature_rule` | preferred / non_preferred / free_text 経路で参照 |
| Semantic 抽出 | `semantic_rule` | `free_text` 経路の前段 |
| Feature 統合 | `feature_integration_rule` | `participates_in_feature_integration=true` の入力のみ統合対象（partial・#478）。**統合重み（`default_source_weight` 相当）は `feature_integration_rule`（#478）で一元管理**し、本テーブルでは保持しない（§17.1 No.6） |
| 統合重み | `feature_integration_rule` | Featureルール §12.3 の source weight は #478 の責務。`input_type_rule` はディスパッチのみ |

### 5.3 Public API 非公開方針

| API | 方針 | 根拠 |
| --- | ---- | ---- |
| API-PUB-007 | `input_type_rule` 行・ディスパッチ設定を応答に含めない | 内部 Rule。契約仕様書 §5 |
| API-PUB-008 | `input_type_rule` は返却しない Rule 種別 | 契約仕様書 §7.3.1「返却しない Rule 種別」 |

> 入力種別ディスパッチは Reco 内部完結。`application_method` は Public 表面に露出しない。

### 5.4 論理ER / Featureルール定義書との差分

| 観点 | 正本の記載 | 本テーブルの扱い |
| ---- | ---------- | ---------------- |
| 論理ER §10.2 | 抽象エンティティ `feature_rule` | 物理ER §5 No.5 に従い `input_type_rule` へ **分解** |
| Featureルール §17 | `input_type_rule` 専用論理項目節なし | §11.1 / §11.5 のドメイン定義から物理項目を **導出** |
| Featureルール §17.6 | YAML / JSON + seed 推奨 | Human Review #477 で **MVP から DB テーブル化を採用**（§17.1 No.1）。§17.6 は実装形式の一般論であり、本テーブルは migration + seed を正本とする |

### 5.5 対象外

- 各 Rule 本体の詳細行（`relationship_rule` / `concept_feature_rule` 等の責務）
- Hard Filter 条件の評価ロジック（Hard Filter モジュールの責務）
- Feature 統合の重み付けアルゴリズム詳細（`feature_integration_rule` の責務）
- User / Item Feature 生成結果（`user_feature` / `item_feature` の責務）

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `input_type_rule_id` | Input Type Rule ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK。Public API 非公開 |
| 2 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `yes` | — | — | 所属する意味定義 version。`semantic_config_version` を参照 |
| 3 | `input_type` | Input Type | `text` | `yes` | — | — | — | — | 入力種別。§11.1 の 7 分類 |
| 4 | `application_method` | Application Method | `text` | `yes` | — | — | — | — | Rule ディスパッチ先コード（§5.1） |
| 5 | `invert_delta` | Invert Delta Flag | `boolean` | `yes` | — | — | — | `false` | Concept Delta 反転適用。`non_preferred_condition` では `true` |
| 6 | `participates_in_feature_integration` | Feature Integration Participation | `boolean` | `yes` | — | — | — | `true` | `feature_integration_rule` 統合対象か。Hard Filter 系は `false` |
| 7 | `display_order` | Display Order | `integer` | `yes` | — | — | — | `1` | ディスパッチ評価順（小さいほど先）。運用・デバッグ用 |
| 8 | `is_active` | Active Flag | `boolean` | `yes` | — | — | — | `true` | 有効フラグ。`false` は reco 参照対象外 |

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `input_type_rule_id` | サロゲート UUID | |
| UNIQUE | `input_type_rule_id` | PK と同一 | — |
| UNIQUE | `semantic_config_version_id`, `input_type` | version 内で入力種別は 1 行 | Index 名: `uq_input_type_rule_version_input_type` |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `semantic_config_version_id` | `semantic_config_version.semantic_config_version_id` | `ON` | RESTRICT | 物理ER §9 / semantic_config_version §8.1 |

### 8.1 論理参照（ディスパッチ先 Rule）

| `application_method` | 参照先 Rule テーブル | FK制約 | 備考 |
| -------------------- | -------------------- | ------ | ---- |
| `relationship_rule` | `relationship_rule` | `LOGICAL` | reco が relationship 入力ブロック処理時に参照 |
| `occasion_rule` | `occasion_rule` | `LOGICAL` | reco が occasion 入力ブロック処理時に参照 |
| `concept_feature_delta_add` | `concept_feature_rule` | `LOGICAL` | preferred 経路 |
| `concept_feature_delta_invert` | `concept_feature_rule` | `LOGICAL` | non_preferred 経路。`invert_delta=true` と併用 |
| `semantic_extraction_then_apply` | `semantic_rule` → `concept_feature_rule` | `LOGICAL` | free_text 2 段階 |
| `hard_filter_excluded` | — | — | Feature Rule 非適用。Hard Filter へ委譲 |

> 子 Rule テーブルへの物理 FK は持たない。ディスパッチは `application_method` コード + reco 実装で解決する（pair_rule / relationship_rule と同型の内部 Rule 方針）。

### 8.2 被参照

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| — | — | — | — | MVP では他テーブルからの物理 FK なし。reco が version 単位で Lookup |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `input_type_rule_pkey` | `input_type_rule_id` | btree（PK） | 主キー | 自動生成 |
| `uq_input_type_rule_version_input_type` | `semantic_config_version_id`, `input_type` | btree（unique） | version 内入力種別一意 | §7 と同一 |
| `idx_input_type_rule_version_active_lookup` | `semantic_config_version_id`, `is_active`, `display_order` | btree | reco ディスパッチ一覧 Lookup | version 内 active 行を順序取得 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `input_type_rule_pkey` | PRIMARY KEY | `input_type_rule_id` | 主キー | — |
| `uq_input_type_rule_version_input_type` | UNIQUE | `semantic_config_version_id`, `input_type` | version 内一意 | |
| `fk_input_type_rule_semantic_config_version` | FOREIGN KEY | `semantic_config_version_id` | `semantic_config_version` ON DELETE RESTRICT | semantic_config_version §8.1 |
| `chk_input_type_mvp` | CHECK | `input_type` | enum定義書 §6.20 の 7 値 IN 句 | `semantic/input_type.yaml` と一致 |
| `chk_application_method_mvp` | CHECK | `application_method` | enum定義書 §6.21 の 6 値 IN 句 | `semantic/application_method.yaml` と一致 |
| `chk_invert_delta_application_method` | CHECK | `invert_delta`, `application_method` | `invert_delta = (application_method = 'concept_feature_delta_invert')` | §17.1 No.8。厳格 CHECK |
| `chk_input_type_dispatch_consistency` | CHECK | `input_type`, `application_method`, `invert_delta`, `participates_in_feature_integration` | §5.1 の 7 組み合わせのみ許容（下記 SQL） | §17.1 No.8。厳格 CHECK |

**`chk_input_type_mvp` 候補値:**

```text
relationship, occasion, preferred_condition, non_preferred_condition,
ng_condition, budget_condition, free_text
```

**`chk_application_method_mvp` 候補値:**

```text
relationship_rule, occasion_rule, concept_feature_delta_add,
concept_feature_delta_invert, hard_filter_excluded, semantic_extraction_then_apply
```

**`chk_input_type_dispatch_consistency` DDL 例:**

```sql
CHECK (
  (input_type = 'relationship'
    AND application_method = 'relationship_rule'
    AND invert_delta = false
    AND participates_in_feature_integration = true)
  OR (input_type = 'occasion'
    AND application_method = 'occasion_rule'
    AND invert_delta = false
    AND participates_in_feature_integration = true)
  OR (input_type = 'preferred_condition'
    AND application_method = 'concept_feature_delta_add'
    AND invert_delta = false
    AND participates_in_feature_integration = true)
  OR (input_type = 'non_preferred_condition'
    AND application_method = 'concept_feature_delta_invert'
    AND invert_delta = true
    AND participates_in_feature_integration = true)
  OR (input_type = 'free_text'
    AND application_method = 'semantic_extraction_then_apply'
    AND invert_delta = false
    AND participates_in_feature_integration = true)
  OR (input_type = 'ng_condition'
    AND application_method = 'hard_filter_excluded'
    AND invert_delta = false
    AND participates_in_feature_integration = false)
  OR (input_type = 'budget_condition'
    AND application_method = 'hard_filter_excluded'
    AND invert_delta = false
    AND participates_in_feature_integration = false)
)
```

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `input_type` | `input_type` | enum定義書 §6.20 / `semantic/input_type.yaml` | 7 分類（上記 CHECK） | Featureルール §11.1 と一致 |
| `application_method` | `application_method` | enum定義書 §6.21 / `semantic/application_method.yaml` | 6 ディスパッチコード | reco 実装の分岐キー |
| `invert_delta` | — | Featureルール §11.3 | `true` / `false` | non_preferred 専用。`chk_invert_delta_application_method` で厳格化 |
| `participates_in_feature_integration` | — | Featureルール §11.5 / §12 | `true` / `false` | Hard Filter 系は `false`。dispatch CHECK で固定 |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | reco | User Feature 生成前。`semantic_config_version_id` + `is_active=true` | — | — | 入力ブロック種別に応じて `application_method` を解決 |
| SELECT | reco | 該当 `input_type` 行なし（seed 漏れ等） | — | — | Featureルール §11.1 の **既定経路へフォールバック**し、**ログ / 運用アラート**を出力する（§17.1 No.7） |
| INSERT | database（seed） | 新 version 初回投入 | 全列 | version ごと Upsert | MVP は **7 行固定** seed（§17.1 No.4） |
| UPDATE | database（運用） | ディスパッチ調整・無効化 | `application_method`, `invert_delta`, `is_active` | — | **`input_type` 変更禁止**。dispatch CHECK 違反は拒否 |
| DELETE | — | MVP では原則禁止 | — | — | `is_active=false` で無効化 |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（設定正本。version 履歴として保持） |
| 削除方式 | 物理 DELETE 原則禁止 |
| 論理削除 | `is_active = false` |
| version 切替 | 新 `semantic_config_version` 作成時に 7 入力種別分を新規 INSERT |
| 正本 | 本テーブル + seed（Human Review #477。reco 定数のみを正本としない） |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `input_type_rule` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: `semantic_config_version` 作成後、Rule 群の一部として適用（Human Review #477: **MVP DDL Task で CREATE する**） |
| rollback方針 | forward migration 主体 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | reco（service role）のみ |
| 書き込み権限 | database seed / 運用のみ |
| Public API | **非公開**。API-PUB-007 / API-PUB-008 応答に含めない |
| 個人情報・機微情報 | 入力種別設定のみ。ユーザー入力本文は保持しない |
| ログ出力制限 | ディスパッチ設定を過剰ログ出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / FK / CHECK | migration |
| 2 | UNIQUE | 同一 version で同一 `input_type` の重複 INSERT が拒否される | migration |
| 3 | CHECK | 不正な `input_type` / `application_method` が拒否される | migration |
| 3a | CHECK | `chk_invert_delta_application_method` 違反が拒否される | migration |
| 3b | CHECK | `chk_input_type_dispatch_consistency` 違反（§5.1 外の組み合わせ）が拒否される | migration |
| 4 | Hard Filter 分離 | `ng_condition` / `budget_condition` 行が `participates_in_feature_integration=false` | manual |
| 5 | reco 参照 | active 行のみディスパッチに利用される | integration |
| 6 | Public API | API-PUB-007 / API-PUB-008 が `input_type_rule` を返却しない | contract |
| 7 | seed 整合 | version あたり 7 行（§11.1 全種別）が seed に存在する | manual |
| 8 | seed 漏れ時 | 行欠損時に §11.1 フォールバック + ログ / アラートが §12 と一致する | integration |

---

## 17. 未決事項

| No | 論点 | 状態 | 備考 |
| --: | ---- | ---- | ---- |
| — | — | **なし** | Human Review #477 論点は §17.1 へ移行済み |

### 17.1 Human Review 決定事項

| No | 論点 | 決定内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | MVP 物理 DDL 採用 | **MVP から物理テーブルを作成する**。migration + seed を正本とし、reco は DB Lookup を前提とする | Human | Issue #477。テーブル一覧 §8 の `partial`（△）分類は維持 |
| 2 | Public API | **非公開**（API-PUB-007 / API-PUB-008） | Human | pair_rule と同型 |
| 3 | `semantic_config_version_id` FK | **物理 FK ON**、ON DELETE RESTRICT | Human | semantic_config_version §8.1 と同型 |
| 4 | MVP seed 方針 | version あたり **7 行固定**（§11.1 全種別）。`ng_condition` / `budget_condition` もディスパッチ明示のため行保持 | Human | §5.1 表と一致 |
| 5 | `input_type` / `application_method` enum 正本化 | **本 Task（#477）で enum定義書 §6.20–§6.21 と `packages/code-definitions/semantic/*.yaml` を追加** | Human | CHECK 候補値と YAML を同期 |
| 6 | `default_source_weight` の保持 | **本テーブルでは保持しない**。統合重みは `feature_integration_rule`（#478）で一元管理 | Human | Featureルール §12.3。`input_type_rule` はディスパッチのみ |
| 7 | seed 漏れ時の reco 挙動 | Featureルール §11.1 の **既定経路へフォールバック** + **ログ / 運用アラート** | Human | §12 更新仕様に反映 |
| 8 | DDL CHECK 厳格度 | `chk_invert_delta_application_method` と `chk_input_type_dispatch_consistency` を **HARD CHECK** として DDL に含める | Human | §10 に DDL 例 |

#### 17.1.1 MVP seed 7 行（version あたり固定）

| `input_type` | `application_method` | `invert_delta` | `participates_in_feature_integration` |
| ------------ | -------------------- | -------------- | ------------------------------------- |
| `relationship` | `relationship_rule` | `false` | `true` |
| `occasion` | `occasion_rule` | `false` | `true` |
| `preferred_condition` | `concept_feature_delta_add` | `false` | `true` |
| `non_preferred_condition` | `concept_feature_delta_invert` | `true` | `true` |
| `free_text` | `semantic_extraction_then_apply` | `false` | `true` |
| `ng_condition` | `hard_filter_excluded` | `false` | `false` |
| `budget_condition` | `hard_filter_excluded` | `false` | `false` |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8 partial・§11 分解方針 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §10.2（抽象 feature_rule 分解） |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §8・MVP partial（△） |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | §6.20 `input_type` / §6.21 `application_method` |
| code-definitions | `packages/code-definitions/semantic/input_type.yaml` | 機械可読正本 |
| code-definitions | `packages/code-definitions/semantic/application_method.yaml` | 機械可読正本 |
| Featureルール | `docs/04_ドメインモデル設計/Featureルール定義書.md` | §2.1 / §11 / §17.6 |
| API契約 | `docs/06_実装設計/api/API-PUB-007_Semantic設定取得API契約仕様書.md` | 内部 Rule 非公開 |
| API契約 | `docs/06_実装設計/api/API-PUB-008_Featureルール取得API契約仕様書.md` | input_type_rule 非公開 |
| 先行テーブル | `docs/06_実装設計/database/semantic_config_version_テーブル定義書.md` | 親 FK・MVP partial 注記 |
| 先行テーブル | `docs/06_実装設計/database/feature_definition_テーブル定義書.md` | Rule 系方針参考 |
| 後続 Task | Issue #478 | `feature_integration_rule`（partial） |
| 先行 Task | Issue #462 / #463 | Wave1 merge 済み前提 |

---

## 19. レビュー観点

- 論理ER §10.2（抽象 `feature_rule` 分解）・物理ER §8 partial 方針・テーブル一覧 §8 と矛盾していない
- Featureルール定義書 §11.1 入力種別（7 分類）と適用方針が物理設計へ整理されている
- Featureルール §17 に専用論理項目節がない差分が明示されている
- `semantic_config_version_id` への物理 FK 方針（ON DELETE RESTRICT）が明記されている
- `ng_condition` / `budget_condition` の Hard Filter 分離（`participates_in_feature_integration=false`）が明記されている
- API-PUB-007 / API-PUB-008 に基づく Public API 非公開が明記されている
- Human Review #477: MVP から物理 DDL 作成が §17.1 に決定事項として記録されている
- `default_source_weight` が本テーブルに含まれず、`feature_integration_rule`（#478）へ委譲されている
- enum定義書 §6.20–§6.21 / code-definitions と CHECK 候補値が一致している
- §10 の厳格 CHECK（invert_delta + dispatch consistency）が DDL Task へ展開可能である
- OpenAPI / generated 変更が含まれていない（#469 委譲）
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
