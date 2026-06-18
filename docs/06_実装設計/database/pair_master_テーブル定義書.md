# Pair Master テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                               |
| -------------- | ---------------------------------- |
| ドキュメントID | `DB-TBL-MVP-pair_master`           |
| ドキュメント名 | Pair Master テーブル定義書         |
| 対象システム   | Gift Recommendation Service MVP    |
| MVP対象        | `yes`                              |
| 作成日         | 2026-06-08                         |
| 更新日         | 2026-06-08（Human Review #465 反映） |

---

## 2. 概要

`pair_master` は、贈答シーンにおける **Relationship × Occasion の有効な組み合わせ（Pair）** を管理するマスタである。

Reco 実行時に `relationship_code` と `occasion_code` から `pair_id` を解決し、再現性確保のため `recommendation_run` に固定する。Public API では Pair 情報を公開しない。

---

## 3. 目的

- Relationship × Occasion の有効組み合わせを DB 上で一意に管理する
- Reco 実行時の Pair 解決（`relationship_code` + `occasion_code` → `pair_id`）の正本とする
- `recommendation_run.pair_id` の物理 FK 参照先として、Run 単位の再現性を担保する
- `pair_rule` 等の後続 Rule テーブルが参照する Pair 体系の基盤とする

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `pair_master` |
| 論理テーブル名 | Pair Master |
| 分類 | Master / Config系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | api（Pair 解決）、reco（Feature 生成時の Pair 参照） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8〜§11 |

---

## 5. 用途・責務

- Relationship × Occasion の **有効な組み合わせ** を `pair_id`（サロゲートキー）で識別する
- Reco 実行時、`relationship_code` と `occasion_code` から `pair_id` を解決する（`is_active = true` の行のみ対象。relationship_master / occasion_master と同様の無効化手段）
- 解決した `pair_id` を `recommendation_run` に保持し、同一 Run の再現性を担保する（物理ER §17 No.1）
- **Public API（API-PUB-005 / API-PUB-006）では Pair 情報を返却しない**。Pair 利用は Reco 内部処理または Internal API 側で扱う

### 5.1 対象外

- Pair ごとの Feature 補正値（`pair_rule` の責務）
- Relationship / Occasion 個別マスタの定義（`relationship_master` / `occasion_master` の責務）
- Pair 一覧の Public API 公開
- `recommendation_request` への `pair_id` 保持（Request は `relationship_code` / `occasion_code` のみ。物理ER §17 No.1）

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `pair_id` | Pair ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | Pair のサロゲートキー。`recommendation_run.pair_id` の参照先 |
| 2 | `relationship_code` | Relationship Code | `text` | `yes` | — | `yes` | — | — | `relationship_master.relationship_code` への物理 FK |
| 3 | `occasion_code` | Occasion Code | `text` | `yes` | — | `yes` | — | — | `occasion_master.occasion_code` への物理 FK |
| 4 | `is_active` | Active Flag | `boolean` | `yes` | — | — | — | `true` | 有効フラグ。`false` の行は Pair 解決対象外（Master 系と同様、MVP 物理 DDL に採用） |

> **論理ER との差分**: 論理ER §11.1 には `pair_master` エンティティが未掲載である。本テーブルは物理ER §4.1 No.3 に基づき物理設計で追加する（テーブル一覧 §14 No.13）。論理ER 側の整理は別 Task とする。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `pair_id` | サロゲートキー（uuid）を採用 | 物理ER §5 主キー方針に整合 |
| UNIQUE | `relationship_code`, `occasion_code` | 組み合わせ一意 | 制約名 `uq_pair_relationship_occasion`（物理ER §10・§11） |

---

## 8. 外部キー・参照関係

### 8.1 参照先（Outgoing FK）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `relationship_code` | `relationship_master.relationship_code` | `ON` | `RESTRICT` | Master 物理 FK。Human Review #443 踏襲方針 |
| `occasion_code` | `occasion_master.occasion_code` | `ON` | `RESTRICT` | Master 物理 FK。Human Review #448 踏襲方針 |

> `recommendation_request.relationship_code` / `occasion_code` は Master を **論理参照**（LOGICAL）とするが、本テーブルは Master への **物理 FK** を採用する。Pair 組み合わせの参照整合性を DB 制約で担保するため。

### 8.2 被参照（Incoming FK）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `recommendation_run` | `pair_id` | resolved_at_run | `ON` | 実行時解決 Pair を Run に保持（物理ER §9・§17 No.1） |
| `pair_rule` | `pair_id` | Feature 補正 | `ON` | Pair は断面管理のため `pair_id` 物理 FK を採用（Human Review #465） |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `pair_master_pkey` | `pair_id` | btree（PK） | 主キー | 自動生成 |
| `uq_pair_relationship_occasion` | `relationship_code`, `occasion_code` | unique | 組み合わせ一意 | 物理ER §10 |
| `idx_pair_master_resolve` | `relationship_code`, `occasion_code`, `is_active` | btree | Pair 解決（`is_active=true` 条件付き Lookup） | Reco 実行時の解決クエリ向け |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `pair_master_pkey` | PRIMARY KEY | `pair_id` | 主キー | — |
| `uq_pair_relationship_occasion` | UNIQUE | `relationship_code`, `occasion_code` | 組み合わせ一意 | 物理ER §11 |
| `fk_pair_master_relationship` | FOREIGN KEY | `relationship_code` | `relationship_master.relationship_code` 参照 | ON DELETE RESTRICT |
| `fk_pair_master_occasion` | FOREIGN KEY | `occasion_code` | `occasion_master.occasion_code` 参照 | ON DELETE RESTRICT |
| `chk_relationship_code_format` | CHECK | `relationship_code` | `relationship_code ~ '^[a-z][a-z0-9_]*$'` | relationship_master と同一形式 |
| `chk_occasion_code_format` | CHECK | `occasion_code` | `occasion_code ~ '^[a-z][a-z0-9_]*$'` | occasion_master と同一形式 |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| — | — | なし | — | 状態カラムなし。`is_active` は boolean |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | reco / api | `relationship_code` + `occasion_code` + `is_active = true` | — | — | Pair 解決。該当行なしは Run 失敗または validation エラー |
| SELECT | reco | Run 再現参照 | `pair_id` | — | `recommendation_run.pair_id` 経由 |
| INSERT / UPDATE | database（seed / 運用） | 新規組み合わせ追加・無効化 | 全列 | seed は Upsert 想定 | MVP では管理 UI なし。migration/seed Task で投入 |
| DELETE | — | MVP では原則禁止 | — | — | `is_active = false` で無効化。Master 削除は RESTRICT で防止 |

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 長期（設定正本） |
| 削除方式 | 物理 DELETE 原則禁止 |
| 削除条件 | — |
| 論理削除 | `is_active = false` で無効化 |
| アーカイブ | MVP 対象外 |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `pair_master` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: `relationship_master` / `occasion_master` の後、`recommendation_run` の `pair_id` FK 追加より前 |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | api / reco（service role 経由） |
| 書き込み権限 | database 運用・seed のみ。Online / Batch 実行中の DML 更新なし |
| service role利用 | Pair 解決・seed 投入に限定 |
| 個人情報・機微情報 | 含まない |
| ログ出力制限 | Pair マスタ内容を error ログに過剰出力しない |
| Public API | Pair 情報（`pair_id` 含む）は Public API 応答に含めない（API-PUB-005 / API-PUB-006 備考） |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / FK / CHECK が定義どおり | migration |
| 2 | PK / UNIQUE | 同一 `relationship_code` + `occasion_code` の重複が拒否される | migration |
| 3 | Master FK | 存在しない `relationship_code` / `occasion_code` の INSERT が拒否される | migration |
| 4 | Pair解決 | `is_active=true` の組み合わせのみ解決される | integration |
| 5 | Run FK | `recommendation_run.pair_id` が `pair_master.pair_id` を参照できる | migration |
| 6 | Public API | API-PUB-005 / API-PUB-006 が Pair 情報を返却しない | contract |
| 7 | 権限 | web client から Direct DB アクセス不可 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | 有効 Pair 組み合わせの seed 範囲 | 全組み合わせか代表組み合わせのみか | Human | seed Task 前 | seed Task 前の決定事項として申し送り（Human Review #465） |

### 17.1 Human Review 決定事項（PR #465）

| No | 論点 | 決定内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | `is_active` 列の MVP 物理 DDL 採用 | **MVP 物理 DDL に採用**する。relationship_master / occasion_master と同様の無効化手段 | Human | Master 系設計踏襲 |
| 2 | Master 物理 FK の ON DELETE 方針 | **`RESTRICT`** を採用 | Human | `relationship_code` / `occasion_code` への Outgoing FK |
| 3 | `pair_rule` の FK 参照方式 | **`pair_id` 物理 FK 参照**を採用 | Human | Pair は断面管理されるため codes 参照ではなく `pair_id` を正とする |
| 4 | `pair_id` の保持先 | **`recommendation_run`** に保持する | Human | 物理ER §17 No.1（PR #438 Human Review 踏襲） |
| 5 | Public API 非公開 | Pair 情報は API-PUB-005 / API-PUB-006 応答に含めない | Human | API契約仕様書備考 |
| 6 | Master への FK 方針（Request 側） | `recommendation_request` は Master を **LOGICAL** 参照のまま | Human | #443 / #448。本テーブルは Master へ **物理 FK** を採用 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §4.1 No.3・§9・§10・§11・§17 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | Master / Config 系（§11） |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §9 Master / Config系 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | コード定義正本（本テーブルは enum 列なし） |
| 参照テーブル定義 | `docs/06_実装設計/database/relationship_master_テーブル定義書.md` | Master 系方針（Human Review #443） |
| 参照テーブル定義 | `docs/06_実装設計/database/occasion_master_テーブル定義書.md` | Master 系方針（Human Review #448） |
| API契約 | `docs/06_実装設計/api/API-PUB-005_Relationshipマスタ取得API契約仕様書.md` | Pair 非公開方針 |
| API契約 | `docs/06_実装設計/api/API-PUB-006_Occasionマスタ取得API契約仕様書.md` | Pair 非公開方針 |
| Featureルール | `docs/04_ドメインモデル設計/Featureルール定義書.md` | §17.3 pair_rule |
| 参照テーブル定義 | `docs/06_実装設計/database/recommendation_request_テーブル定義書.md` | Request は `pair_id` 非保持・Run 側解決（Human Review #537 No.4） |

---

## 19. レビュー観点

- 論理ER §11.1 未掲載（物理ER §4.1 No.3 追加）の差分が明示されている
- 物理ER §8〜§11・テーブル一覧 §9 と矛盾していない
- `pair_id`（uuid PK）、`uq_pair_relationship_occasion`、Master 物理 FK、`recommendation_run.pair_id` 物理 FK が明確
- Public API 非公開方針が明記されている
- `relationship_master` / `occasion_master` テーブル定義書と Master 系方針（`is_active` 採用・論理削除）が一貫している
- `pair_rule` の `pair_id` 被参照（物理 FK）が明記されている
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
