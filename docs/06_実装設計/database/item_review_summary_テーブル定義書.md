# Item Review Summary テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                            |
| -------------- | ------------------------------- |
| ドキュメントID | `DB-TBL-MVP-item_review_summary` |
| ドキュメント名 | Item Review Summary テーブル定義書 |
| 対象システム   | Gift Recommendation Service MVP |
| MVP対象        | `yes`                           |
| 作成日         | 2026-06-12                      |
| 更新日         | 2026-06-12                      |

---

## 2. 概要

`item_review_summary` は、楽天商品検索 API（`item_search`）由来の **レビュー平均・レビュー件数** を保持する Item 系派生テーブルである。

`reviewAverage` / `reviewCount` を item あたり最大 1 行に集約し、商品詳細 API の `reviewSummary`、Popularity 補助シグナル、および `recommendation_result_item` の Snapshot 列の元データとなる。

MVP では **Feature 推定には利用しない**（表示・Popularity 補助・Snapshot 用途のみ）。Online 推薦中は更新しない。

---

## 3. 目的

- 商品ごとのレビュー要約（平均・件数）を DB 上で管理する
- BATCH-007（Item Review Summary Updater / `MOD-BATCH-025`）による **item 単位 Upsert（履歴なし）** の正本として、後続 Batch / api / reco が参照できる粒度を定義する
- `item_image` / `item_popularity_signal` と同型の Item 子テーブルとして、**出所列（`source` / `source_api`）を持たない** 方針を物理 DDL で確定する
- `item` との **1対0または1** 関係を UNIQUE(`item_id`) で表現し、後続 DDL Task が migration を作成できる粒度まで設計を確定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `item_review_summary` |
| 論理テーブル名 | Item Review Summary |
| 分類 | Item系 |
| 正本区分 | 派生 / 外部参照 |
| 主な更新主体 | batch（BATCH-007 / `MOD-BATCH-025`） |
| 主な参照主体 | api（商品詳細）、reco（Ranking 補助・Result Snapshot 生成時） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11 |

---

## 5. 用途・責務

- 楽天商品検索 API レスポンスの `reviewAverage` / `reviewCount` を **スカラー要約** として保持する
- **履歴は持たない**。Batch が item 単位で最新 API 結果に Upsert する（§5.4）
- **Feature 推定（Item Feature / Item Meaning / Matching スコア）には利用しない**。表示・Popularity 補助・Snapshot 固定用途に限定する（§5.5）
- Online 推薦中は **更新しない**（論理ER §16.1・`item_テーブル定義書` §5.2 と同型）
- `normalized_hash` 算出対象には含むが、**列は本テーブルのみ** に保持する（`item_テーブル定義書` §12.3）

### 5.1 対象外

- 商品正本属性（`item` の責務）
- レビュー本文・個別レビュー履歴（MVP 対象外）
- 商品画像（`item_image` の責務）
- 人気シグナル明細（`item_popularity_signal` の責務）
- Staging 中間データ（`staging_item` のレビュー列は Staging 定義 Task へ委譲）
- `source` / `source_system` / `source_api` 列（Item 子テーブル共通方針で **行に持たない**。§5.2）
- `is_active` 列（§17.1 No.3）
- OpenAPI / generated 変更（Epic 終盤 Task #469 へ委譲）

### 5.2 出所・トレース方針（`source` 系列列なし）

| 観点 | 方針 |
| ---- | ---- |
| 取得元 API | 楽天商品検索 API（`item_search`）。テーブル責務で暗黙（`item_image` と同型） |
| マーケット識別 | 親 `item.source`（`item_id` FK 経由。MVP: `rakuten`） |
| API トレース | `staging_item.raw_metadata_id` → `raw_product_metadata.source_api`（監査・デバッグ時） |
| 本テーブル列 | **`source` / `source_system` / `source_api` は MVP 物理 DDL に含めない** |

> 外部商品データ連携設計書 §228: ランキング API 由来の `reviewAverage` は本テーブルへ直接反映しない。**商品検索 API 由来を正** とする。

### 5.3 1対0または1 関係

| 観点 | 方針 |
| ---- | ---- |
| カーディナリティ | `item` 1 件に対し `item_review_summary` は **0 行または 1 行**（物理ER §8: `1:0..1`） |
| 一意制約 | `UNIQUE (item_id)` で item あたり最大 1 行を担保（§7） |
| 0 行の意味 | 当該 item についてレビュー要約が未反映、または Batch が行を作成していない状態 |
| 1 行の意味 | 最新のレビュー平均・件数が反映済み |

### 5.4 正本モデル（item 単位 Upsert・履歴なし）

| 観点 | 方針 |
| ---- | ---- |
| 履歴管理 | **行わない**。過去版を別行で保持しない |
| Upsert キー | `item_id` のみ（§7） |
| 同期置換 | **画像のような URL 集合 DELETE は不要**（スカラー 1 行のため） |
| 論理削除 | `is_active` 列なし |
| Snapshot | 推薦実行時点の `review_average` / `review_count` を Snapshot 列へコピー（既存 Snapshot は上書きしない） |

### 5.5 Feature 推定・Popularity との責務境界

| 用途 | 利用 | 備考 |
| ---- | ---- | ---- |
| 商品詳細 / 一覧表示 | ○ | API-PUB-003 `reviewSummary` |
| Recommendation Result Item Snapshot | ○ | `review_average_snapshot` / `review_count_snapshot` |
| Popularity 補助（`popularity_score`） | ○ | 外部商品データ連携設計書 §13.3 の補助シグナル。主価値は意味マッチング |
| Item Feature / Item Meaning 推定 | **×** | インターフェース一覧・IF-DB-BATCH-007 方針 |
| Matching / Ranking の意味スコア | **×** | ランキングは補正要素に留める |

### 5.6 `staging_item` → `item_review_summary` 反映関係

| 観点 | 方針 |
| ---- | ---- |
| データフロー | `raw_product_metadata` → `staging_item`（BATCH-005）→ `item_review_summary`（BATCH-007） |
| 物理ER 関係 | `staging_item` → `item` Upsert 後に子テーブル反映（LOGICAL 経路） |
| item 解決 | `staging_item.external_item_code` + `item.source` で `item_id` を解決（`item` Upsert 後） |
| 反映順序 | `item_テーブル定義書` §12.1：`item` Upsert 後に `item_review_summary` を反映 |
| 冪等性 | `item_id` Upsert により Batch 再実行で同一結果 |

### 5.7 楽天 API マッピング

| 楽天商品検索 API | Staging 列 | 物理カラム | 備考 |
| ---------------- | ---------- | ---------- | ---- |
| `reviewAverage` | `review_average` | `review_average` | 外部商品データ連携設計書 §9.2 |
| `reviewCount` | `review_count` | `review_count` | 整数。0 件レビューもあり得る |
| — | — | `fetched_at` | 当該 item のレビュー反映 Batch 完了時刻（UTC） |

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `item_review_summary_id` | Item Review Summary ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | レビュー要約行 ID |
| 2 | `item_id` | Item ID | `uuid` | `yes` | — | `ON` | `yes` | — | 内部商品 ID。`item.item_id` 参照。item あたり 1 行（§7） |
| 3 | `review_average` | Review Average | `numeric(3,1)` | `no` | — | — | — | — | レビュー平均（例: `4.2`）。`review_count = 0` 時は NULL 可 |
| 4 | `review_count` | Review Count | `integer` | `yes` | — | — | — | — | レビュー件数。`>= 0` |
| 5 | `fetched_at` | Fetched At | `timestamptz` | `yes` | — | — | — | — | 当該行の最終反映日時（UTC） |

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `item_review_summary_id` | サロゲート UUID | — |
| UNIQUE | `item_id` | Upsert / 冪等キー・1:0..1 担保 | item あたり最大 1 行 |

---

## 8. 外部キー・参照関係

### 8.1 参照先（本テーブルから）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `item_id` | `item.item_id` | `ON` | `ON DELETE RESTRICT` | `item_テーブル定義書` §8.2 被参照と一致。`item_image` と同型（§17.1 No.5） |

### 8.2 被参照

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| — | — | — | — | 本テーブルは Snapshot **元データ**。`recommendation_result_item` は snapshot 列に値をコピー保持（物理 FK なし） |

### 8.3 Result Snapshot 参照

| Snapshot 列 | 元データ | 備考 |
| ----------- | -------- | ---- |
| `review_average_snapshot` | `item_review_summary.review_average` | 論理ER §7.3・処理構成定義書 §11.7 |
| `review_count_snapshot` | `item_review_summary.review_count` | 行不存在時は NULL / 省略（JOIN なし） |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `item_review_summary_pkey` | `item_review_summary_id` | btree（PK） | 主キー | 自動生成 |
| `uq_item_review_summary_item_id` | `item_id` | unique btree | Upsert キー・1:0..1 | §7 |
| `idx_item_review_summary_item_id` | `item_id` | btree | api / reco JOIN | API-PUB-003 `reviewSummary` 取得 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `item_review_summary_pkey` | PRIMARY KEY | `item_review_summary_id` | 主キー | — |
| `uq_item_review_summary_item_id` | UNIQUE | `item_id` | item あたり 1 行 | §7 |
| `fk_item_review_summary_item_id` | FOREIGN KEY | `item_id` | `item(item_id)` ON DELETE RESTRICT | §8.1 |
| `chk_item_review_summary_count_nonneg` | CHECK | `review_count` | `review_count >= 0` | 負数禁止 |
| `chk_item_review_summary_average_range` | CHECK | `review_average` | `review_average IS NULL OR (review_average >= 0 AND review_average <= 5)` | 楽天 API 想定レンジ |
| `chk_item_review_summary_average_when_count` | CHECK | `review_average`, `review_count` | `review_count = 0 OR review_average IS NOT NULL` | 件数 > 0 のとき平均必須 |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| — | — | — | — | 状態カラムなし（`is_active` 不採用） |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | api | `item_id` 指定 | — | — | API-PUB-003 LEFT JOIN |
| SELECT | reco | Result Snapshot 生成 / Popularity 参照 | — | — | §8.3 |
| UPSERT | batch（BATCH-007） | `item_id`（staging から解決） | `review_average`, `review_count`, `fetched_at` | Upsert キーで冪等 | §12.1 |
| INSERT / UPDATE / DELETE | api / reco | — | — | **禁止** | Online 推薦中に更新しない |
| DELETE | batch | MVP 原則 **しない** | — | — | §12.2・§17.1 No.1 |

### 12.1 item 単位 Upsert フロー

```text
1. item Upsert 完了（item_id 確定）
2. staging_item から当該 item の review_average / review_count を取得
3. 両フィールドが Staging 上で有効な場合、item_id をキーに UPSERT
4. fetched_at を反映 Batch 完了時刻（UTC）で更新
5. Staging でレビュー列が欠損している場合は §12.2 に従う（Human Review #503 No.4）
```

### 12.2 Upsert 疑似コード

```sql
INSERT INTO item_review_summary (
  item_id, review_average, review_count, fetched_at
) VALUES (...)
ON CONFLICT (item_id) DO UPDATE SET
  review_average = EXCLUDED.review_average,
  review_count = EXCLUDED.review_count,
  fetched_at = EXCLUDED.fetched_at;
```

### 12.3 `normalized_hash` との関係

| 観点 | 方針 |
| ---- | ---- |
| hash 入力 | `reviewAverage` / `reviewCount` は hash 対象（外部商品データ連携設計書 §6.4・`item_テーブル定義書` §12.3） |
| 列保持 | 値は **本テーブルのみ** に保持。`item` 列には持たない |
| 更新トリガ | hash 変更ありの item Upsert 後、BATCH-007 で本テーブルを反映 |

---

## 13. API 公開列マッピング（API-PUB-003）

| API 項目 | DB 列 / 導出 | 公開 | 備考 |
| -------- | ------------ | ---- | ---- |
| `reviewSummary` | `item_review_summary` LEFT JOIN | optional | 行不存在時は省略 |
| `reviewSummary.average` | `review_average` | optional | 例: `4.2` |
| `reviewSummary.count` | `review_count` | optional | 例: `128` |

OpenAPI schema 変更は Task #469 へ委譲。本定義書は DB ↔ 契約 docs のマッピング正本とする。

---

## 14. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 商品有効期間中（親 `item` に従う） |
| 削除方式 | MVP では Batch による物理 DELETE は **原則しない** |
| 削除条件 | 親 `item` 物理削除は RESTRICT で禁止。行不存在 = 1:0..1 の「0」 |
| 論理削除 | `is_active` 列なし（§17.1 No.3） |
| 履歴 | 保持しない。監査は Raw / Staging メタデータ |
| アーカイブ | MVP 対象外 |

---

## 15. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `item_review_summary` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: **Item 群**。`item` 作成 **後**（`item_テーブル定義書` §15） |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 16. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | api / reco / batch（service role 経由） |
| 書き込み権限 | batch のみ。Online 推薦中の DML 更新なし |
| service role利用 | BATCH-007 Upsert に限定 |
| 個人情報・機微情報 | 集計値のみ（レビュー本文・投稿者情報は保持しない） |
| ログ出力制限 | 大量 item_id を error ログに過剰出力しない |

---

## 17. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / FK / CHECK が定義どおり | migration |
| 2 | Upsert キー | 同一 `item_id` で重複 INSERT が拒否される | migration |
| 3 | 1:0..1 | 異なる `item_id` では複数行 INSERT 可能 | migration |
| 4 | CHECK 整合 | `review_count < 0` や範囲外 `review_average` が拒否される | migration |
| 5 | FK 整合 | 存在しない `item_id` への INSERT が拒否される | migration |
| 6 | API 整合 | LEFT JOIN が API-PUB-003 `reviewSummary` と一致 | contract |

---

## 18. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | item 単位 Upsert vs 履歴保持 | MVP 物理モデルの確定 | Human | Issue #503 Due | §17.1 No.1 推奨案あり |
| 2 | Feature推定非利用の明記 | Popularity 補助との境界確認 | Human | Issue #503 Due | §17.1 No.2 推奨案あり |
| 3 | API 欠損時の行削除 vs 保持 | Staging に review 列が無い場合の挙動 | Human | Issue #503 Due | §17.1 No.4 推奨案あり |
| 4 | `ON DELETE RESTRICT` 確定 | 親 item 削除ポリシーとの整合 | Human | DDL Task 前 | §17.1 No.5 推奨案あり |

### 18.1 Human Review 推奨案（Issue #503）

| No | 論点 | 推奨内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | 履歴 vs Upsert | **item 単位 Upsert、履歴なし**（`UNIQUE(item_id)`） | Human | §5.4 / §12.1 |
| 2 | Feature 推定 | **非利用**。表示・Popularity 補助・Snapshot のみ | Human | §5.5 |
| 3 | `source` / `is_active` 列 | **いずれも行に持たない**（`item_image` 同型） | Human | §5.2 |
| 4 | Staging レビュー欠損時 | **Upsert をスキップし前回値を保持**（DELETE しない） | Human |  transient API 欠損対策 |
| 5 | `item_id` FK ON DELETE | **`ON DELETE RESTRICT`**（`item_image` #497 No.5 と同型） | Human | 親は論理無効化が基本 |

---

## 19. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8 FK（1:0..1） |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §8.2 属性・§7.3 Snapshot |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §5 No.12 |
| リソース一覧 | `docs/05_アプリケーション設計/アプリ/database/リソース一覧.md` | §12.4 Item Review Summary |
| 外部商品連携 | `docs/05_アプリケーション設計/アプリ/外部商品データ連携設計書.md` | §9.2 / §10.3 / §13.3 |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-DB-BATCH-007・Feature推定非利用 |
| 処理構成 | `docs/05_アプリケーション設計/アプリ/処理構成定義書.md` | §11.7 Snapshot マッピング |
| item 定義書 | `docs/06_実装設計/database/item_テーブル定義書.md` | §8.2 FK 被参照・§12.1 反映順・§13 |
| item_image 定義書 | `docs/06_実装設計/database/item_image_テーブル定義書.md` | Item 子テーブル共通方針参考 |
| API契約 | `docs/06_実装設計/api/API-PUB-003_商品詳細取得API契約仕様書.md` | reviewSummary マッピング |
| バッチ処理一覧 | `docs/05_アプリケーション設計/アプリ/batch/バッチ処理一覧.md` | BATCH-007 |

---

## 20. レビュー観点

- 論理ER §8.2・テーブル一覧 §5 No.12 と矛盾していない
- 物理ER §8 FK 表（`item_id` ON・1:0..1）と整合している
- `item_テーブル定義書` §5.1 / §8.2 / §12.1 / §13 と責務・FK・反映順が整合している
- `review_average` / `review_count` / `fetched_at` の型・制約・Upsert キーが DDL 展開可能な粒度である
- `source` 系列列・`is_active` を持たない方針が §5 で明示されている
- Feature 推定非利用（表示・Popularity 補助・Snapshot のみ）が §5.5 で明示されている
- `recommendation_result_item` Snapshot 参照が §8.3 に整理されている
- staging → item_review_summary Upsert 方針が §5.6 / §12 に整理されている
- Human Review 論点（§18）が Issue #503 と一致している
- apps/** / OpenAPI / generated 変更が含まれていない
- secret や `.env` 実値が含まれていない
