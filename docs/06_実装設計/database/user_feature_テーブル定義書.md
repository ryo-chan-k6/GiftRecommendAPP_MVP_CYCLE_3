# User Feature テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                            |
| -------------- | ------------------------------- |
| ドキュメントID | `DB-TBL-MVP-user_feature`       |
| ドキュメント名 | User Feature テーブル定義書     |
| 対象システム   | Gift Recommendation Service MVP |
| MVP対象        | `yes`                           |
| 作成日         | 2026-06-15                      |
| 更新日         | 2026-06-15                      |

---

## 2. 概要

`user_feature` は、**1 回の Online 推薦実行（`recommendation_run`）** あたりの **MVP 8 次元 Feature 値**（Social 3 + Symbolic 5）を保持する User意味推定系テーブルである。

User Feature Generator（`MOD-RECO-007`）が Relationship / Occasion / Pair / Concept 由来入力を統合・正規化した結果を保存し、Matching / Ranking で参照する **ユーザー側 Feature 正本** となる。reco が Online 推薦時に **生成・参照** し、batch は更新しない（論理ER §16.3）。

---

## 3. 目的

- `recommendation_run_id` × `feature_code` 単位で正規化済み Feature 値を DB 上で保持する
- `feature_normalization_version_id` の保持方針を明記し、推薦再現性を担保する
- `item_feature` との対称関係・差分（Run 単位 vs 商品単位、reco vs batch 更新主体）を整理する
- IF-DB-RECO-003（User Semantic / Feature 保存）の永続化先として、後続 DDL Task が migration を作成できる粒度を提供する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `user_feature` |
| 論理テーブル名 | User Feature |
| 分類 | User意味推定系 |
| 正本区分 | 派生 |
| 主な更新主体 | reco（Online 推薦パイプライン） |
| 主な参照主体 | reco（Matching / Ranking / User Meaning 射影） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11 |

---

## 5. 用途・責務

- **8 軸 × Recommendation Run** の User Feature 正本（テーブル一覧 §4 No.8）
- `relationship_rule` / `occasion_rule` 基準値、 `pair_rule` 補正、 `concept_feature_rule` Delta、`feature_integration_rule` 重みを統合した **正規化後 Feature 値** を保存する（Featureルール定義書 §12・§18.1）
- `feature_normalization_version_id` を行に保持し、Run 実行時点の正規化パラメータ再現性を担保する（`feature_normalization_version_テーブル定義書` §8.2）
- `source_type` を **`aggregated` 固定** で保持し、Relationship / Occasion / Concept 等の寄与分解は MVP では保存しない（enum定義書 §12.1）
- `semantic_config_version_id` は **本テーブルには持たず**、`recommendation_run.semantic_config_version_id` を正とする（§8.4・§17.1 No.3 **推奨**）

### 5.1 行モデル（MVP）

| 観点 | 方針 |
| ---- | ---- |
| 粒度 | **1 `recommendation_run_id` × 1 `feature_code`** あたり 1 行 |
| 軸数 | MVP 固定 **8 行 / Run**（`feature_code` 8 値） |
| 履歴 | **1 Run あたり 8 行のみ**。同一 Run の再 INSERT は禁止（unique 制約）。Run 再実行は **新規 `recommendation_run_id`**（`recommendation_run_テーブル定義書` §17.1 No.6） |
| Online 参照 | 同一 Run 内の Matching / Ranking で **8 行を一括読取** |

### 5.2 `feature_normalization_version_id` 保持方針

| 観点 | 方針 |
| ---- | ---- |
| 解決経路 | Run 解決済み `semantic_config_version_id` → `normalization_rule`（binding）→ `feature_normalization_version_id`（`normalization_rule_テーブル定義書` §5.1） |
| 記録タイミング | User Feature 生成完了時に reco が解決し、8 行すべてに同一 ID を記録 |
| FK 方針 | **LOGICAL**（物理 FK なし。`feature_normalization_version_テーブル定義書` §8.2・§17.1 No.4 決定済み） |
| 冪等キー | item_feature と同型の 5 列冪等 unique は **採用しない**（Run 単位派生のため。§7 注記） |
| Public API | 非公開（内部 reco 参照のみ） |

### 5.3 `source_type` 保持方針

| 観点 | 方針 |
| ---- | ---- |
| 論理 ID | `user_feature_source_type`（enum定義書 §12.1） |
| MVP 値 | **`aggregated` 固定**（全 8 行） |
| 寄与分解 | Relationship / Occasion / Concept 等の個別 source は **DB に保存しない** |
| Semantic `source_type` との関係 | 別論理 ID。同名 enum 混在を避ける（enum定義書 §12.1 末尾） |

### 5.4 Online 推薦パイプラインとの関係

```text
recommendation_run INSERT（version / pair 解決済み）
  → user_semantic 生成（別 Task / MOD-RECO-006）
  → User Feature Generator（MOD-RECO-007）
      → relationship_rule / occasion_rule 基準値
      → pair_rule 補正
      → concept_feature_rule（user_semantic 入力）
      → feature_integration_rule 重み適用
      → input_type_rule 経路分岐
      → sigmoid 正規化（feature_normalization_version 参照）
  → user_feature INSERT（8 行）— IF-DB-RECO-003
  → user_meaning 射影（別 Task / MOD-RECO-008）
  → Matching / Ranking
```

> `user_semantic` テーブル定義書（#553）未 merge 時は、上記の semantic 入力前提を論理ER §7.2 / §10.2 参照で整理する（本 Task の out_of_scope）。

### 5.5 `item_feature` との対称関係（概要）

| 観点 | `user_feature` | `item_feature` |
| ---- | -------------- | -------------- |
| 分類 | User意味推定系 | Item派生データ系 |
| 親キー | `recommendation_run_id` | `item_id` + `semantic_config_version_id` |
| 更新主体 | reco（Online） | batch（BATCH-012 / BATCH-013） |
| 値列 | `feature_value`（正規化後 1 列） | `raw_feature_value` + `normalized_feature_value` |
| 入力 hash | **なし** | `feature_input_hash` 必須 |
| 冪等 unique | `recommendation_run_id` + `feature_code` | 5 列冪等キー（§7） |
| semantic version | Run 経由（列なし） | 行に `semantic_config_version_id` |

詳細は §8.4 を正とする。

### 5.6 対象外

- `user_semantic` / `user_meaning` の本体定義（別 Task / Batch R07）
- `item_feature` 等 Item 派生データ系テーブル
- User Feature 統合・正規化アルゴリズムの実装詳細（reco モジュール実装 Task）
- `feature_input_hash` / `item_generation_queue`（Item 側 Batch 専用）
- Feature Rule 本体（`relationship_rule` 等 Semantic / Feature 定義系テーブル）
- api からの直接 DML
- Public API への Feature 値・normalization version の露出（#469 委譲）
- DDL / migration 本体（DDL Task へ委譲）

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `user_feature_id` | User Feature ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK |
| 2 | `recommendation_run_id` | Recommendation Run ID | `uuid` | `yes` | — | `ON` | — | — | 親 Run。`recommendation_run.recommendation_run_id` 参照 |
| 3 | `feature_code` | Feature Code | `text` | `yes` | — | — | — | — | MVP 8 軸コード。enum定義書 §6.16 正本 |
| 4 | `feature_normalization_version_id` | Feature Normalization Version ID | `uuid` | `yes` | — | — | — | — | 適用正規化 version。LOGICAL 参照 |
| 5 | `feature_value` | Feature Value | `numeric(8,6)` | `yes` | — | — | — | — | sigmoid 正規化後の 0.0〜1.0 値（Matching 用） |
| 6 | `source_type` | Source Type | `text` | `yes` | — | — | — | `'aggregated'` | MVP は `aggregated` 固定（enum定義書 §12.1） |
| 7 | `generated_at` | Generated At | `timestamptz` | `yes` | — | — | — | — | 当該行の Feature 生成完了日時（UTC） |

> **論理ER §7.2 / §10.2 との差分（§8.4）**: 論理ERは `feature_definition_id` を主要属性に列挙するが、item_feature #514 §17.1 No.1 と対称に MVP 物理 DDL では **`feature_code` のみ** を保持し、`feature_definition_id` 列は持たない（§17.1 No.1 **推奨**）。
>
> **Featureルール定義書 §17.5 との差分**: 論理モデルは `raw_value` / `normalized_value` の両保持を許容するが、論理ER §7.2・物理ER §11 は User 側を **`feature_value` 1 列** とする。MVP は **正規化後のみ永続化**（raw は reco 内一時変数）（§17.1 No.2 **推奨**）。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `user_feature_id` | サロゲート UUID | — |
| UNIQUE | `user_feature_id` | PK と同一 | — |
| UNIQUE | `recommendation_run_id`, `feature_code` | Run 内 8 軸一意 | Index 名: `uq_user_feature_per_run_axis`（§17.1 No.4 **推奨**） |

> **item_feature 冪等キーとの差分**: `feature_normalization_version_テーブル定義書` §7.1 注記どおり、Run 単位派生の `user_feature` には item_feature 同型の 5 列冪等 unique（`feature_input_hash` 含む）は **MVP では定義しない**。Run 内では `recommendation_run_id` + `feature_code` で 8 行を固定する。

---

## 8. 外部キー・参照関係

### 8.1 参照先（本テーブルから）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `recommendation_run_id` | `recommendation_run.recommendation_run_id` | `ON` | `ON DELETE RESTRICT` | `recommendation_run_テーブル定義書` §8.2 generates・1:N |

### 8.2 論理参照（物理 FK なし）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `feature_code` | `feature_definition.feature_code`（Run 解決済み `semantic_config_version_id` 内） | `LOGICAL` | reco が INSERT 前に存在確認 | `recommendation_run.semantic_config_version_id` 経由で version 特定。`feature_definition_テーブル定義書` §8.1 |
| `feature_normalization_version_id` | `feature_normalization_version.feature_normalization_version_id` | `LOGICAL` | reco が INSERT 前に存在確認 | `feature_normalization_version_テーブル定義書` §8.2 |

### 8.3 被参照

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| reco（Matching / Ranking） | 全業務列 | reads | アプリ層 | 同一 Run の 8 行読取 |
| `user_meaning` 生成（MOD-RECO-008） | `feature_value` 等 | derives | 別 Task | User Meaning は本 Task の out_of_scope |

### 8.4 論理ER / 物理ER / `item_feature` 差分整理

| 論点 | 論理ER §7.2 | 論理ER §10.2 | 物理ER §11 | `item_feature` | 本定義書の採用 |
| ---- | ----------- | ------------ | ---------- | -------------- | -------------- |
| 軸参照キー | `feature_definition_id` | `feature_definition_id` | `feature_code`（enum 連携） | `feature_code` のみ（#514 No.1） | **`feature_code` のみ**（§17.1 No.1 推奨） |
| 意味 version | 未列挙 | 未列挙 | — | `semantic_config_version_id` 列 | **Run 経由。列は持たない**（§17.1 No.3 推奨） |
| 値列 | `feature_value` | `feature_value` | `chk_feature_value_range` 対象 | raw + normalized 2 列 | **`feature_value` 1 列（正規化後）**（§17.1 No.2 推奨） |
| normalization FK | 未列挙（§7.2） | `feature_normalization_version_id` | LOGICAL | LOGICAL | **LOGICAL 維持** |
| 入力 hash | — | — | — | `feature_input_hash` 必須 | **非採用** |
| source_type | `source_type` | `source_type` | — | — | **`aggregated` 固定** |
| 冪等 unique | — | — | — | 5 列 | **`recommendation_run_id` + `feature_code`** |

> 論理ER 更新（`feature_definition_id` 削除 / `feature_code` 統一、§7.2 と §10.2 の整合）は別 docs Task で検討する。

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `user_feature_pkey` | `user_feature_id` | btree（PK） | 主キー | 自動生成 |
| `uq_user_feature_per_run_axis` | `recommendation_run_id`, `feature_code` | unique btree | Run 内 8 軸一意 | §7・§17.1 No.4 推奨 |
| `idx_user_feature_lookup` | `recommendation_run_id`, `feature_code` | btree | Matching / Ranking 読取 | 物理ER §10 未記載。本 Task で追加方針 |
| `idx_user_feature_run_id` | `recommendation_run_id` | btree | FK 補助・Run 単位一覧 | `recommendation_run` 被参照の JOIN 補助 |

Online 参照では、**同一 `recommendation_run_id` の 8 行**（`feature_code` 8 値）を `idx_user_feature_lookup` で一括取得する。

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `user_feature_pkey` | PRIMARY KEY | `user_feature_id` | 主キー | — |
| `uq_user_feature_per_run_axis` | UNIQUE | `recommendation_run_id`, `feature_code` | Run 内軸一意 | §7 |
| `fk_user_feature_recommendation_run_id` | FOREIGN KEY | `recommendation_run_id` | `recommendation_run(recommendation_run_id)` ON DELETE RESTRICT | §8.1 |
| `chk_user_feature_code_mvp` | CHECK | `feature_code` | MVP 8 軸のみ | `feature_definition` / 物理ER §11 `chk_feature_code_mvp` と同一 |
| `chk_user_feature_value_range` | CHECK | `feature_value` | `feature_value >= 0.0 AND feature_value <= 1.0` | 物理ER §11 `chk_feature_value_range`（user 側は `feature_value` 列） |
| `chk_user_feature_source_type_mvp` | CHECK | `source_type` | `source_type = 'aggregated'` | enum定義書 §12.1 |

> 物理ER §11 の `chk_feature_value_range` は `user_feature` / `item_feature` を併記し、User 側は **`feature_value`** 列を対象とする。Item 側は `normalized_feature_value`（`item_feature_テーブル定義書` §8.4）。

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `feature_code` | `feature_code` | enum定義書 §6.16 / `packages/code-definitions/semantic/feature_code.yaml` | MVP 8 値 | `feature_definition` と同一 CHECK |
| `source_type` | `user_feature_source_type` | enum定義書 §12.1 | `aggregated`（MVP 固定） | YAML 正本化は後続 enum Task |

### 11.1 MVP 8 軸（`feature_code`）

| feature_group | feature_code | 論理ER §10.3 |
| ------------- | ------------ | ------------ |
| Social | `formality` | 儀礼性 |
| Social | `safety` | 安全性 |
| Social | `brand_appropriateness` | ブランド適切性 |
| Symbolic | `emotion` | 感情性 |
| Symbolic | `novelty` | 新規性 |
| Symbolic | `intimacy` | 親密性 |
| Symbolic | `symbolic_identity` | 象徴性 |
| Symbolic | `story_richness` | ストーリー性 |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| INSERT | reco（MOD-RECO-007） | User Feature 生成完了 | 全業務列 | `uq_user_feature_per_run_axis` | 8 軸それぞれ 1 行。IF-DB-RECO-003 |
| SELECT | reco | 同一 Run 内 Matching / Ranking | — | — | 8 行読取 |
| UPDATE | reco / api / batch | — | — | **禁止** | 生成後は不変（Snapshot 性質） |
| DELETE | — | — | — | **MVP 禁止** | §13 |
| INSERT / UPDATE / DELETE | api / batch | — | — | **禁止** | 論理ER §16.2 / §16.3 |

### 12.1 正規化 version 解決フロー

```text
1. reco が Run INSERT 時に semantic_config_version_id を recommendation_run へ記録済み
2. normalization_rule から feature_normalization_version_id を解決（is_active=true）
3. User Feature Generator が 8 軸を統合・sigmoid 正規化
4. user_feature へ 8 行 INSERT（同一 feature_normalization_version_id）
```

### 12.2 INSERT 疑似コード

```sql
INSERT INTO user_feature (
  recommendation_run_id,
  feature_code,
  feature_normalization_version_id,
  feature_value,
  source_type,
  generated_at
) VALUES (
  :recommendation_run_id,
  :feature_code,
  :feature_normalization_version_id,
  :feature_value,
  'aggregated',
  now()
);
-- 8 軸（feature_code 8 値）をループ実行
-- 同一 recommendation_run_id での 2 回目 INSERT は uq_user_feature_per_run_axis で拒否
```

### 12.3 Online 参照フロー（reco）

```text
1. 処理中の recommendation_run_id を固定
2. idx_user_feature_lookup で当該 Run の 8 行を取得
3. feature_code 8 件が揃うことを前提（欠損時は Matching 側でフォールバック／警告。詳細は reco 実装 Task）
4. item_feature（候補商品側）とペアで context_score 算出（Matching）
```

**Run 単位読取（疑似 SQL）:**

```sql
SELECT *
  FROM user_feature
 WHERE recommendation_run_id = :recommendation_run_id
 ORDER BY feature_code;
```

### 12.4 phase_log 連携

| 観点 | 方針 |
| ---- | ---- |
| phase_name | `user_feature_generated`（enum定義書 §6.18・状態遷移設計書） |
| 記録主体 | reco（IF-DB-RECO-009 経由で `phase_log`） |
| タイミング | 8 行 INSERT 完了後 |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | **recommendation_run と同ライフサイクル**（Online コア長期保持。具体日数は Phase2 ⑥ データ保持方針 Task で一括確定） |
| 削除方式 | MVP では **DELETE なし**（`recommendation_run_テーブル定義書` §13・§17.1 No.5 踏襲） |
| 削除条件 | — |
| 論理削除 | 採用しない |
| アーカイブ | Phase2 ⑥ で確定 |
| FK | `ON DELETE RESTRICT`。Run 削除時は user_feature を先に削除する運用は MVP では想定しない |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `user_feature` |
| migration単位 | User意味推定系 migration（`recommendation_run` 先行後） |
| 適用順序 | 物理ER §15: Master / Config → Semantic 定義 → Online推薦系（`recommendation_request` → `recommendation_run`）→ **User 派生（`user_semantic` → `user_feature` → `user_meaning`）** |
| rollback方針 | DDL Task で定義。派生データのため DROP は開発環境のみ想定 |
| 破壊的変更有無 | `no`（新規テーブル） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | `apps/reco`（service role） |
| 書き込み権限 | `apps/reco` のみ（User Feature 生成時 INSERT） |
| service role利用 | Supabase service role 経由。client 直アクセス禁止 |
| 個人情報・機微情報 | Feature 値のみ。Request テキスト本体は `recommendation_request` 参照。Feature 値は間接的にユーザー意図を反映し得るためログ出力は最小化 |
| ログ出力制限 | `feature_value` 配列の過剰ダンプを避ける。Run ID + feature_code のみの要約ログを推奨 |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | `user_feature` テーブル・FK・unique・Index が migration で作成される | migration |
| 2 | Run 内 unique | 同一 `recommendation_run_id` + `feature_code` の二重 INSERT が拒否される | integration |
| 3 | 8 軸完備 | 1 Run あたり 8 行が生成される | integration |
| 4 | FK | `recommendation_run_id` の RESTRICT が機能する | integration |
| 5 | feature_code CHECK | MVP 8 軸以外が拒否される | migration |
| 6 | 値域 CHECK | `feature_value` が 0.0〜1.0 のみ許容される | unit |
| 7 | source_type CHECK | `aggregated` 以外が拒否される | migration |
| 8 | Online 境界 | api / batch からの DML が行われない | manual |
| 9 | IF-DB-RECO-003 | reco が 8 行 INSERT 後に Matching で読取できる | integration |
| 10 | 権限 | reco のみが書き込み可能 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review #554 で §17.1 を決定予定 |

### 17.1 Human Review 決定事項（Issue #554）

| No | 論点 | 推奨内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | `feature_definition_id` 列の物理化要否 | **物理化しない**。`feature_code` のみ（item_feature #514 No.1 対称） | Human | §6・§8.4 |
| 2 | raw / normalized 2 列 vs `feature_value` 1 列 | **`feature_value` 1 列**（正規化後のみ永続化。raw は reco 内一時変数） | Human | Featureルール §17.5 vs 論理ER §7.2 |
| 3 | `semantic_config_version_id` の user_feature 行 denormalize | **持たない**。`recommendation_run.semantic_config_version_id` を正とする | Human | §5.1・§8.4 |
| 4 | Run 単位 unique | **`uq_user_feature_per_run_axis`（`recommendation_run_id` + `feature_code`）を採用** | Human | §7・§9 |
| 5 | Retention / DELETE | **MVP DELETE なし**。Run と同ライフサイクル長期保持 | Human | §13・recommendation_run §13 踏襲 |
| 6 | `chk_user_feature_value_range` 対象列 | **`feature_value` 列**（物理ER §11 表記に整合） | Human | §10 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | FK・制約方針 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §7.2 / §10.2 属性・§16 責務境界 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §4 No.8 |
| Featureルール定義書 | `docs/04_ドメインモデル設計/Featureルール定義書.md` | User Feature 生成・統合・§18.1 |
| recommendation_run 定義書 | `docs/06_実装設計/database/recommendation_run_テーブル定義書.md` | recommendation_run_id FK・version コンテキスト |
| item_feature 定義書 | `docs/06_実装設計/database/item_feature_テーブル定義書.md` | 対称関係・差分正本 |
| feature_definition 定義書 | `docs/06_実装設計/database/feature_definition_テーブル定義書.md` | feature_code 正本 |
| feature_normalization_version 定義書 | `docs/06_実装設計/database/feature_normalization_version_テーブル定義書.md` | §8.2 LOGICAL FK |
| normalization_rule 定義書 | `docs/06_実装設計/database/normalization_rule_テーブル定義書.md` | binding 解決 |
| relationship_rule 定義書 | `docs/06_実装設計/database/relationship_rule_テーブル定義書.md` | 基準値入力 |
| occasion_rule 定義書 | `docs/06_実装設計/database/occasion_rule_テーブル定義書.md` | 基準値入力 |
| pair_rule 定義書 | `docs/06_実装設計/database/pair_rule_テーブル定義書.md` | Pair 補正 |
| concept_feature_rule 定義書 | `docs/06_実装設計/database/concept_feature_rule_テーブル定義書.md` | Concept Delta |
| feature_integration_rule 定義書 | `docs/06_実装設計/database/feature_integration_rule_テーブル定義書.md` | 統合重み |
| input_type_rule 定義書 | `docs/06_実装設計/database/input_type_rule_テーブル定義書.md` | 入力経路 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | feature_code・§12.1 source_type |
| 処理構成定義書 | `docs/05_アプリケーション設計/アプリ/処理構成定義書.md` | MOD-RECO-007 |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-DB-RECO-003 |
| code-definitions | `packages/code-definitions/semantic/feature_code.yaml` | feature_code 正本 |

---

## 19. レビュー観点

- テーブル一覧 §4 No.8・論理ER §7.2 / §10.2・物理ER §8–§11 と矛盾していない
- `item_feature_テーブル定義書` との対称関係・差分が §8.4 で明記されている
- `recommendation_run_id` 単位 8 行モデル・`uq_user_feature_per_run_axis` が明記されている
- `feature_normalization_version_id` の LOGICAL FK 方針が明記されている
- `source_type = aggregated` が enum定義書 §12.1 と整合している
- 論理ER §16.3（reco 生成）・IF-DB-RECO-003・MOD-RECO-007 が反映されている
- カラム・制約・Index が DDL Task へ展開できる粒度である
- §17.1 推奨事項が本文（§6 / §8.4 / §9 / §10 / §12 / §13）に反映されている
- secret や `.env` 実値が含まれていない
