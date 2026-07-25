# Lambda Context Rule テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                      |
| -------------- | ----------------------------------------- |
| ドキュメントID | `DB-TBL-MVP-lambda_ctx_rule`              |
| ドキュメント名 | Lambda Context Rule テーブル定義書        |
| 対象システム   | Gift Recommendation Service MVP           |
| MVP対象        | `yes`                                     |
| 作成日         | 2026-07-25                                |
| 更新日         | 2026-07-25                                |

---

## 2. 概要

`lambda_ctx_rule` は、**Relationship × Occasion** に対する **`lambda_ctx`（贈答リスク許容度）の基準値**を、`semantic_config_version` 単位で保持する Semantic / Feature 定義系テーブルである。

本テーブルは **Rule Lookup 用の設定正本**である。Run 固定の算出結果列 `user_meaning.lambda_ctx` とは責務を分離する（Issue #843 / Human 判断: 案A 専用テーブル）。

MOD-RECO-009 User Context Builder が `LambdaContextRuleRepository.get_lambda_ctx(semantic_config_version_id, relationship_code, occasion_code)` 経由で参照する。**Public API では返却しない**（API-PUB-007 / API-PUB-008 非公開。`pair_rule` と同型）。

---

## 3. 目的

- `lambda_ctx` Rule Lookup の物理正本を DB 制約で管理する
- reco（MOD-RECO-009）が Run 解決済み `semantic_config_version_id` と `relationship_code` / `occasion_code` で基準値を参照できるようにする
- `user_meaning.lambda_ctx`（結果列）と Rule 設定正本の責務分離を物理設計で固定する
- 後続 DDL / seed / Reco DB Repository Task の前提を整える

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `lambda_ctx_rule` |
| 論理テーブル名 | Lambda Context Rule |
| 分類 | Semantic / Feature 定義系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | reco（MOD-RECO-009 `lambda_ctx` Rule Lookup） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11 |
| 物理形態決定 | Issue #843 Human 判断: **案A 専用テーブル**（案B JSON / 案C 既存 Rule 拡張は不採用） |

---

## 5. 用途・責務

- **`semantic_config_version_id` 単位**で、Relationship × Occasion = **1 行**の `lambda_ctx` 基準値を保持する
- Lookup キーは Port I/F に合わせ **`relationship_code` + `occasion_code`** を物理列として保持する（`pair_id` は持たない）
- **`is_active = true`** の行のみ reco が参照する
- 行なし / `null` 相当は MOD-RECO-009 側で **0.5 フォールバック**（`user_meaning_テーブル定義書` / Matching定義書と整合）
- MVP 初期 seed は **行なし（0 件）** を既定とする（全リクエストがフォールバック）。代表組み合わせの seed 追加は後続 seed Task で行う

### 5.1 関連テーブルとの関係

| 観点 | 参照先 | 本テーブルとの関係 |
| ---- | ------ | ------------------ |
| version ヘッダ | `semantic_config_version` | `semantic_config_version_id` で所属 version を特定（物理 FK ON） |
| Relationship | `relationship_master` | `relationship_code` 論理参照（relationship_rule と同型） |
| Occasion | `occasion_master` | `occasion_code` 論理参照（occasion_rule と同型） |
| Pair 組み合わせマスタ | `pair_master` | **直接 FK しない**。任意の Master 組み合わせに Rule を疎に定義可能 |
| Feature Pair 補正 | `pair_rule` | Feature 軸の delta 補正。本テーブルの責務外 |
| 算出結果 | `user_meaning.lambda_ctx` | Run 固定の結果列。本テーブルは設定正本のみ |

### 5.2 `user_meaning.lambda_ctx` との責務分離

| 対象 | 責務 | 更新主体 |
| ---- | ---- | -------- |
| `lambda_ctx_rule.lambda_ctx` | Rule Lookup 設定値（version 管理） | database（seed / 運用） |
| `user_meaning.lambda_ctx` | MOD-RECO-009 算出結果の Run 固定保存 | reco（Run ごと INSERT） |

### 5.3 Public API 非公開方針

| API | 方針 | 根拠 |
| --- | ---- | ---- |
| API-PUB-007 | `lambda_ctx_rule` 行・値を応答に含めない | 内部 Rule。`pair_rule` と同型 |
| API-PUB-008 | `lambda_ctx_rule` は返却しない | Feature ルール取得対象外 |

> `lambda_ctx` は Reco 内部完結。Public 表面に露出しない。

### 5.4 対象外

- `user_meaning.lambda_ctx` 結果列の定義（`user_meaning_テーブル定義書` の責務）
- Feature 軸の Pair 補正（`pair_rule` の責務）
- DDL / migration / seed SQL 実体（後続 Task）
- `apps/reco/**` の DB Repository 実装（後続 Reco Task）
- `pair_rule.lambda_ctx_delta` 列の追加（本 Task では採用しない。§17）

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `lambda_ctx_rule_id` | Lambda Context Rule ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK |
| 2 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `yes` | — | — | 所属する意味定義 version。`semantic_config_version` を参照 |
| 3 | `relationship_code` | Relationship Code | `text` | `yes` | — | — | — | — | Relationship コード。`relationship_master.relationship_code` と整合 |
| 4 | `occasion_code` | Occasion Code | `text` | `yes` | — | — | — | — | Occasion コード。`occasion_master.occasion_code` と整合 |
| 5 | `lambda_ctx` | Lambda Context | `numeric(6,4)` | `yes` | — | — | — | — | Rule Lookup 基準値。0.0〜1.0（`user_meaning.lambda_ctx` と同型） |
| 6 | `is_active` | Active Flag | `boolean` | `yes` | — | — | — | `true` | 有効フラグ。`false` は reco 参照対象外 |

> **キー設計理由**: Port I/F が `relationship_code` × `occasion_code` のため、物理列も codes を直持ちする。`pair_id` FK は採用しない（`pair_master` に無い組み合わせへの疎な Rule 定義を許容し、Lookup を JOIN なしで行う）。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `lambda_ctx_rule_id` | サロゲート UUID | |
| UNIQUE | `lambda_ctx_rule_id` | PK と同一 | — |
| UNIQUE | `semantic_config_version_id`, `relationship_code`, `occasion_code` | version 内で Relationship × Occasion は 1 行 | Index 名: `uq_lambda_ctx_rule_version_rel_occ` |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `semantic_config_version_id` | `semantic_config_version.semantic_config_version_id` | `ON` | RESTRICT | 物理ER §9 / semantic_config_version §8.1 |

### 8.1 論理参照（MVP 初期 DDL）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `relationship_code` | `relationship_master.relationship_code` | `LOGICAL` | seed + CHECK | relationship_rule §8.1 と同型。物理 FK は MVP では付与しない |
| `occasion_code` | `occasion_master.occasion_code` | `LOGICAL` | seed + CHECK | occasion_rule §8.1 と同型 |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `lambda_ctx_rule_pkey` | `lambda_ctx_rule_id` | btree（PK） | 主キー | 自動生成 |
| `uq_lambda_ctx_rule_version_rel_occ` | `semantic_config_version_id`, `relationship_code`, `occasion_code` | btree（unique） | version 内 Rule 一意 | §7 と同一 |
| `idx_lambda_ctx_rule_version_rel_occ_active_lookup` | `semantic_config_version_id`, `relationship_code`, `occasion_code`, `is_active` | btree | reco Rule Lookup | Port I/F と一致 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `lambda_ctx_rule_pkey` | PRIMARY KEY | `lambda_ctx_rule_id` | 主キー | — |
| `uq_lambda_ctx_rule_version_rel_occ` | UNIQUE | `semantic_config_version_id`, `relationship_code`, `occasion_code` | version 内一意 | |
| `fk_lambda_ctx_rule_semantic_config_version` | FOREIGN KEY | `semantic_config_version_id` | `semantic_config_version` ON DELETE RESTRICT | semantic_config_version §8.1 |
| `chk_lambda_ctx_rule_lambda_ctx_range` | CHECK | `lambda_ctx` | `lambda_ctx >= 0.0 AND lambda_ctx <= 1.0` | Matching定義書 §4.5 / `user_meaning` と同値域 |
| `chk_lambda_ctx_rule_relationship_code_length` | CHECK | `relationship_code` | `char_length(relationship_code) BETWEEN 1 AND 64` | Master と同程度 |
| `chk_lambda_ctx_rule_occasion_code_length` | CHECK | `occasion_code` | `char_length(occasion_code) BETWEEN 1 AND 64` | Master と同程度 |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `relationship_code` | — | `relationship_master` / Featureルール §5.1 | seed 投入済みコード | 存在整合は LOGICAL |
| `occasion_code` | — | `occasion_master` / Featureルール §7.1 | seed 投入済みコード | 存在整合は LOGICAL |
| `lambda_ctx` | — | Matching定義書 §4.5 | 0.0〜1.0 | CHECK で担保 |
| `is_active` | — | — | `true` / `false` | boolean |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | reco | `get_lambda_ctx`。`semantic_config_version_id` + `relationship_code` + `occasion_code` + `is_active=true` | — | — | 0 行 → Repository は `null` → MOD-RECO-009 が 0.5 フォールバック |
| INSERT | database（seed） | 新 version 初回投入 / 代表組み合わせ追加 | 全列 | version ごと Upsert | MVP 初期は **0 行可** |
| UPDATE | database（運用） | 基準値調整・無効化 | `lambda_ctx`, `is_active` | — | **codes 変更禁止**（新 version INSERT 推奨） |
| DELETE | — | MVP では原則禁止 | — | — | `is_active=false` で無効化 |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（設定正本。version 履歴として保持） |
| 削除方式 | 物理 DELETE 原則禁止 |
| 論理削除 | `is_active = false` |
| version 切替 | 新 `semantic_config_version` 作成時に必要行を新規 INSERT |
| MVP 初期 seed | **行なし**（全件 0.5 フォールバック）。代表組み合わせ追加は後続 seed Task |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `lambda_ctx_rule` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | `semantic_config_version`・`relationship_master`・`occasion_master` 作成後。Rule 群の一部として `pair_rule` 近傍で適用 |
| rollback方針 | forward migration 主体 |
| 破壊的変更有無 | `no`（初回 CREATE） |
| seed ファイル（後続） | 例: `08b_lambda_ctx_rule.sql` または投入順再採番（初期データ定義書で整理） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | reco（service role）のみ。api は Public 返却しないため直接参照不要 |
| 書き込み権限 | database seed / 運用のみ |
| Public API | **非公開**。API-PUB-007 / API-PUB-008 応答に含めない |
| ログ出力制限 | Rule 設定値を過剰ログ出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / FK / CHECK が定義どおり | migration |
| 2 | UNIQUE | 同一 version で同一 relationship × occasion の重複 INSERT が拒否される | migration |
| 3 | 値域 CHECK | `lambda_ctx` が 0.0〜1.0 外で拒否される | migration |
| 4 | reco Lookup | version + codes + active で 1 行取得できる | integration |
| 5 | フォールバック | 行なしで Repository が `null` → 0.5 | unit / integration |
| 6 | Public API | API-PUB-007 / API-PUB-008 が本テーブルを返却しない | contract |
| 7 | 責務分離 | `user_meaning.lambda_ctx` と混同していない | docs review |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | 代表組み合わせ seed の初期値・件数 | MVP 初期は 0 行で可だが、運用開始時に載せる relationship × occasion と値（例: 0.3 / 0.5 / 0.7）が未確定 | Human | seed Task 前 | 本 Task の既定は **0 行** |
| 2 | DDL グループ番号（`db/ddl/d0x`） | 既存 d01〜d12 への割当 | Human + Worker | DDL Task | 後続 Task で確定 |

### 17.1 本 Task で確定する事項（案A）

| No | 論点 | 決定内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | 物理形態 | **専用テーブル `lambda_ctx_rule`**（案A） | Human | Issue #843 |
| 2 | Lookup キー | **`relationship_code` × `occasion_code`**（`pair_id` 不採用） | Worker（Port I/F 整合） | Human Review で確認 |
| 3 | 値列型 | **`numeric(6,4)`**（`user_meaning.lambda_ctx` と同型） | Worker | Human Review で確認 |
| 4 | `semantic_config_version_id` FK | **物理 FK ON**、ON DELETE RESTRICT | Worker（Rule 系踏襲） | |
| 5 | MVP 初期 seed | **0 行**（全件 0.5 フォールバック） | Worker 推奨 | Human Review で確認 |
| 6 | Public API | **非公開** | Worker（pair_rule と同型） | |
| 7 | `pair_rule.lambda_ctx_delta`（算出優先2） | **本 Task では採用しない**。MVP 算出は優先1（本テーブル Lookup）+ 優先3（0.5） | Worker 推奨 | MOD-RECO-009 §8.3.1 を更新。優先2 復活は別 Task |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §5 / §8–§11 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §8 |
| 初期データ | `docs/06_実装設計/database/初期データ定義書.md` | seed 方針 |
| Matching | `docs/04_ドメインモデル設計/Matching定義書.md` | §4.5 / §9.3 |
| モジュール仕様 | `docs/06_実装設計/reco/MOD-RECO-009_User Context Builderモジュール仕様書.md` | §8.3.1 / §16 |
| 結果列 | `docs/06_実装設計/database/user_meaning_テーブル定義書.md` | §5.4 `lambda_ctx` |
| version | `docs/06_実装設計/database/semantic_config_version_テーブル定義書.md` | §8.1 被参照 |
| 参考 Rule | `docs/06_実装設計/database/relationship_rule_テーブル定義書.md` | codes LOGICAL / UNIQUE |
| 参考 Rule | `docs/06_実装設計/database/pair_rule_テーブル定義書.md` | Public 非公開・version 管理 |
| Issue | #843 | 物理正本設計 Task |

---

## 19. レビュー観点

- 案A（専用テーブル）が Issue #843 Human 判断と一致している
- `user_meaning.lambda_ctx`（結果）と本テーブル（設定）の責務分離が明確か
- Port I/F（`get_lambda_ctx(version, relationship_code, occasion_code)`）を満たすキー設計か
- `semantic_config_version_id` 物理 FK および Master codes の LOGICAL 参照が Rule 系と一貫しているか
- `lambda_ctx` 値域 0.0〜1.0 / `numeric(6,4)` が `user_meaning` と整合しているか
- Public API 非公開が明記されているか
- MVP 初期 seed 0 行 + 0.5 フォールバック方針が明記されているか
- `pair_rule.lambda_ctx_delta` を本 Task で追加していないか（out of scope）
- DDL Task が CREATE TABLE を起こせる粒度か
- secret や `.env` 実値が含まれていないか

---

## 20. 後続 Task 分割案

| 順 | Task 案 | 内容 | 依存 |
| -- | ------- | ---- | ---- |
| 1 | DDL / migration | `lambda_ctx_rule` CREATE TABLE・Index・FK・CHECK | 本定義書 merge |
| 2 | seed（任意） | 代表 relationship × occasion の初期値投入。初期は 0 行のまま運用可 | DDL |
| 3 | Reco DB Repository | `LambdaContextRuleRepository` の Postgres 実装。InMemory 差し替え | DDL（seed は任意） |
| 4 | （任意）Pair 補正優先2 | `pair_rule.lambda_ctx_delta` 採用可否の再判断・設計 | Human 判断 |

---

## 21. 改訂履歴

| 日付 | 内容 | 関連 |
| ---- | ---- | ---- |
| 2026-07-25 | 初版（案A 専用テーブル） | Issue #843 |
