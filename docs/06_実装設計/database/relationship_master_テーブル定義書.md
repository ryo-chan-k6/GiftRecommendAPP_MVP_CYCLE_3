# Relationship Master テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                       |
| -------------- | ------------------------------------------ |
| ドキュメントID | `DB-TBL-MVP-relationship_master`           |
| ドキュメント名 | Relationship Master テーブル定義書         |
| 対象システム   | Gift Recommendation Service MVP            |
| MVP対象        | `yes`                                      |
| 作成日         | 2026-06-07                                 |
| 更新日         | 2026-06-07                                 |

---

## 2. 概要

`relationship_master` は、贈答シーンにおける **Relationship（贈り手と受け手の関係性）** の入力マスタを保持する。

Web UI の Relationship 選択肢（API-PUB-005）および Recommendation Request の `relationship_code` 検証の正本となる。

---

## 3. 目的

- Relationship コードと表示名を DB 上で一意に管理する
- API-PUB-005 / API-PUB-002 の Relationship 入力と整合した参照データを提供する
- `pair_master` / `relationship_rule` 等の後続 Master・Rule テーブルが参照するコード体系の基盤とする

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `relationship_master` |
| 論理テーブル名 | Relationship Master |
| 分類 | Master / Config系 |
| 正本区分 | 設定正本 |
| 主な更新主体 | database（seed / 運用更新） |
| 主な参照主体 | api（マスタ取得）、reco（Feature 生成時のコード解決） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8 |

---

## 5. 用途・責務

- Relationship 選択肢の **コード・表示名・表示順・有効フラグ** を保持する
- `is_active = true` のレコードのみを API-PUB-005 が返却する（契約上、非公開列 `is_active` は Response に含めない）
- `recommendation_request.relationship_code` は本テーブルの `relationship_code` を **論理参照**する（MVP 初期 DDL では物理 FK なし。整合は api 側 validation + seed 正本で担保）

### 5.1 対象外

- Relationship ごとの Feature 補正値（`relationship_rule` の責務）
- Relationship × Occasion の組み合わせ定義（`pair_master` の責務）
- Pair / Rule 詳細の Public API 公開

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `relationship_code` | Relationship Code | `text` | `yes` | `yes` | — | `yes` | — | 関係性コード。snake_case 英小文字・数字・アンダースコア。Featureルール定義書 §5.1 のコード体系に整合 |
| 2 | `relationship_label` | Relationship Label | `varchar(50)` | `yes` | — | — | — | — | 日本語 UI 表示名。API-PUB-005 `relationshipLabel` の正本 |
| 3 | `relationship_label_jp` | Relationship Label JP | `varchar(50)` | `no` | — | — | — | `NULL` | 論理ER 互換列。MVP では API 非公開。未設定時は `relationship_label` と同一値を seed で投入可 |
| 4 | `is_active` | Active Flag | `boolean` | `yes` | — | — | — | `true` | 有効フラグ。`false` の行は API 返却対象外 |
| 5 | `display_order` | Display Order | `integer` | `yes` | — | — | — | `0` | 表示順。API-PUB-005 は `displayOrder` 昇順（同順位は `relationshipCode` 昇順） |

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `relationship_code` | コードを自然キーとして採用 | サロゲートキーは設けない |
| UNIQUE | `relationship_code` | PK と同一 | — |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| — | — | なし | — | 本テーブルは Master 根。他テーブルから参照される |

### 8.1 被参照（論理）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `recommendation_request` | `relationship_code` | selected_by | `LOGICAL` | 物理ER §9 |
| `pair_master` | `relationship_code` | 組み合わせ定義 | 後続 Task で確定 | テーブル定義 Task（pair_master）で FK 方針を確定 |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `relationship_master_pkey` | `relationship_code` | btree（PK） | 主キー | 自動生成 |
| `idx_relationship_master_active_order` | `is_active`, `display_order`, `relationship_code` | btree | API-PUB-005 の一覧取得（`is_active=true` かつ表示順） | 物理ER §10 は個別 Index 未記載。本 Task で追加方針 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `relationship_master_pkey` | PRIMARY KEY | `relationship_code` | 主キー | — |
| `chk_relationship_code_format` | CHECK | `relationship_code` | `relationship_code ~ '^[a-z][a-z0-9_]*$'` | snake_case。先頭英字 |
| `chk_relationship_label_length` | CHECK | `relationship_label` | `char_length(relationship_label) BETWEEN 1 AND 50` | API-PUB-005 / API-PUB-002 上限 |
| `chk_relationship_label_jp_length` | CHECK | `relationship_label_jp` | `relationship_label_jp IS NULL OR char_length(relationship_label_jp) BETWEEN 1 AND 50` | — |
| `chk_display_order_non_negative` | CHECK | `display_order` | `display_order >= 0` | API `displayOrder` 0 以上 |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| — | — | なし | — | 状態カラムなし。`is_active` は boolean |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | api | `is_active = true` | — | — | API-PUB-005。ORDER BY `display_order`, `relationship_code` |
| SELECT | reco | Run 実行時 | — | — | `relationship_code` の存在確認（validation） |
| INSERT / UPDATE | database（seed / 運用） | 新規 Relationship 追加・表示名変更 | 全列 | seed は Upsert 想定 | MVP では管理 UI なし。migration/seed Task で投入 |
| DELETE | — | MVP では原則禁止 | — | — | `is_active = false` で無効化 |

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
| DDL対象 | `relationship_master` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: Master / Config 群の先頭付近（`pair_master` より前） |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | api / reco（service role 経由） |
| 書き込み権限 | database 運用・seed のみ。Online / Batch 実行中の DML 更新なし |
| service role利用 | api のマスタ参照、seed 投入に限定 |
| 個人情報・機微情報 | 含まない |
| ログ出力制限 | マスタ内容を error ログに過剰出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / CHECK が定義どおり | migration |
| 2 | PK / CHECK | 不正 `relationship_code` が拒否される | migration |
| 3 | API 整合 | `is_active=true` のみ取得、`display_order` 順 | integration |
| 4 | seed 整合 | Featureルール定義書 §5.1 のコードが seed に存在 | manual |
| 5 | 権限 | web client から Direct DB アクセス不可 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | `relationship_label_jp` の MVP 運用 | 論理ER 上は列あり。API は `relationship_label` のみ公開 | Human | seed Task 前 | 推奨: seed で `relationship_label` と同一値を投入 |
| 2 | `recommendation_request` への物理 FK | 現状 LOGICAL 参照。DDL Task で FK 追加要否 | Human | DDL Task | 推奨: MVP は LOGICAL のまま（api validation） |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | テーブル分類・被参照関係 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §11.1 エンティティ属性 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §9 Master / Config系 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | コード定義正本（本テーブルは enum 列なし） |
| API契約 | `docs/06_実装設計/api/API-PUB-005_Relationshipマスタ取得API契約仕様書.md` | Response マッピング |
| Featureルール | `docs/04_ドメインモデル設計/Featureルール定義書.md` | §5.1 relationship_code 一覧 |

---

## 19. レビュー観点

- 論理ER §11.1・物理ER §8・テーブル一覧 §9 と矛盾していない
- API-PUB-005 の `relationshipLabel` / `displayOrder` マッピングが明確
- `relationship_label_jp` が API 非公開であることが明記されている
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
