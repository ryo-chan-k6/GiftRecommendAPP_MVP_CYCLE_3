# Item Image テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                            |
| -------------- | ------------------------------- |
| ドキュメントID | `DB-TBL-MVP-item_image`         |
| ドキュメント名 | Item Image テーブル定義書       |
| 対象システム   | Gift Recommendation Service MVP |
| MVP対象        | `yes`                           |
| 作成日         | 2026-06-12                      |
| 更新日         | 2026-06-12（Human Review #497 反映） |

---

## 2. 概要

`item_image` は、楽天商品検索 API（`item_search`）由来の **商品画像 URL 参照情報** を保持する Item 系テーブルである。

`mediumImageUrls` / `smallImageUrls` を配列展開して保存し、推薦結果表示・商品詳細 API の画像表示および `recommendation_result_item.item_image_url_snapshot` の元データとなる。

MVP では画像バイナリを保存しない。Public API では `item` 経由の JOIN で `itemImageUrl` / `images[]` として表面化する（API-PUB-003）。

---

## 3. 目的

- 商品ごとの複数画像 URL と主画像（`is_primary`）を DB 上で管理する
- BATCH-007（Item Image Updater）による **最新のみ Upsert + item 単位同期置換** の正本として、後続 Batch / api / reco が参照できる粒度を定義する
- `item_review_summary` / `item_popularity_signal` と同型の Item 子テーブルとして、**出所列（`source` / `source_api`）を持たない** 方針を物理 DDL で確定する
- 後続 DDL Task が migration を作成できる粒度まで設計を確定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `item_image` |
| 論理テーブル名 | Item Image |
| 分類 | Item系 |
| 正本区分 | 内部正本 / 外部参照 |
| 主な更新主体 | batch（BATCH-005 / BATCH-007） |
| 主な参照主体 | api（商品詳細）、reco（Result Snapshot 生成時） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11 |

---

## 5. 用途・責務

- 楽天商品検索 API レスポンスの `smallImageUrls` / `mediumImageUrls` を **URL 参照行** として保持する
- 主画像選定（§5.3）に従い `is_primary` を 1 件に定め、一覧・詳細・Snapshot の代表画像 URL を提供する
- **履歴は持たない**。Batch が item 単位で最新 API 結果に同期置換し、消えた URL 行は DELETE する（§5.4）
- Online 推薦中は **更新しない**（論理ER §16.1・`item_テーブル定義書` §5.2 と同型）

### 5.1 対象外

- 商品正本属性（`item` の責務）
- 画像バイナリ・CDN（MVP 対象外）
- レビュー要約（`item_review_summary` の責務）
- Staging 中間データ（`staging_item_image_テーブル定義書` #523 の責務）
- `source` / `source_system` / `source_api` 列（Item 子テーブル共通方針で **行に持たない**。§5.2）
- `is_active` 列（同期置換で代替。§17.1 No.3）
- OpenAPI / generated 変更（Epic 終盤 Task #469 へ委譲）

### 5.2 出所・トレース方針（`source` 系列列なし）

| 観点 | 方針 |
| ---- | ---- |
| 取得元 API | 楽天商品検索 API（`item_search`）。テーブル責務で暗黙（`item_review_summary` と同型） |
| マーケット識別 | 親 `item.source`（`item_id` FK 経由。MVP: `rakuten`） |
| API トレース | `staging_item_image.raw_metadata_id` → `raw_product_metadata.source_api`（監査・デバッグ時） |
| 本テーブル列 | **`source` / `source_system` / `source_api` は MVP 物理 DDL に含めない**（Human Review #497 No.2） |

### 5.3 主画像選定方針

論理ER §8.3・外部商品データ連携設計書 §11.4 と同一。

```text
1. mediumImageUrls[0] に対応する行（image_size_type = medium, display_order = 0）
2. 上記が無い場合 smallImageUrls[0]（image_size_type = small, display_order = 0）
3. 画像行が 0 件の場合は DB 上の主画像なし（UI プレースホルダー）
```

Batch 反映時に `is_primary` を上記優先順で **1 件のみ** `true` に設定する（§10 partial unique）。

### 5.4 正本モデル（最新のみ・同期置換）

| 観点 | 方針 |
| ---- | ---- |
| 履歴管理 | **行わない**。過去 URL 版を別行で保持しない |
| Upsert キー | `item_id` + `image_url`（§7） |
| 同期置換 | 当該 `item_id` について、今回 Staging / API 集合に **含まれない既存行を DELETE** |
| 論理削除 | `is_active` 列なし。無効 URL は DELETE で除去 |
| Snapshot | 推薦実行時点の `is_primary=true` の URL を `item_image_url_snapshot` に固定（既存 Snapshot は上書きしない） |

### 5.5 `staging_item_image` → `item_image` 反映関係

| 観点 | 方針 |
| ---- | ---- |
| データフロー | `raw_product_metadata` → `staging_item_image`（BATCH-005）→ `item_image`（BATCH-007） |
| 物理ER 関係 | `staging_item_image` → `item_image` : `upserts`（LOGICAL。Staging 系は物理 FK なし） |
| item 解決 | `staging_item_image.external_item_code` + `item.source` で `item_id` を解決（`item` Upsert 後） |
| 反映順序 | `item_テーブル定義書` §12.1：`item` Upsert 後に `item_image` を反映 |
| 冪等性 | Upsert キー + 同期 DELETE により Batch 再実行で同一結果 |
| Staging 正本 | `staging_item_image_テーブル定義書`（#523）。`is_primary_candidate` は BATCH-005 で確定し BATCH-007 で `is_primary` へ引き継ぐ（Human Review #523 §17.1 No.4） |

### 5.6 楽天 API マッピング

| 楽天商品検索 API | 物理カラム / 処理 | 備考 |
| ---------------- | ----------------- | ---- |
| `mediumImageUrls[]` | `image_url`, `image_size_type='medium'`, `display_order`=配列 index | 主画像候補優先 |
| `smallImageUrls[]` | `image_url`, `image_size_type='small'`, `display_order`=配列 index | サムネイル候補 |
| `imageFlag` | 反映しない（行の有無で判定） | 画像なし時は行 0 件 + UI プレースホルダー |
| — | `fetched_at` | 当該 item の画像反映 Batch 完了時刻（UTC） |
| — | `is_primary` | §5.3 に従い Batch が算出 |

> **`normalized_hash` との関係**: `item_テーブル定義書` §12.3 どおり、画像 URL は hash 入力に含むが **列は本テーブルのみ** に保持する。

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `item_image_id` | Item Image ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | 商品画像行 ID |
| 2 | `item_id` | Item ID | `uuid` | `yes` | — | `ON` | — | — | 内部商品 ID。`item.item_id` 参照 |
| 3 | `image_url` | Image URL | `text` | `yes` | — | — | — | — | 画像 URL（楽天 CDN 等）。Upsert 自然キー構成要素 |
| 4 | `image_size_type` | Image Size Type | `text` | `yes` | — | — | — | — | `small` / `medium` |
| 5 | `display_order` | Display Order | `integer` | `yes` | — | — | — | `0` | 同一 `item_id` 内の表示順（API 配列 index 由来） |
| 6 | `is_primary` | Primary Flag | `boolean` | `yes` | — | — | — | `false` | 主画像か。`item_id` あたり最大 1 件 `true`（§10） |
| 7 | `fetched_at` | Fetched At | `timestamptz` | `yes` | — | — | — | — | 当該行の最終反映日時（UTC） |

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `item_image_id` | サロゲート UUID | — |
| UNIQUE | `item_id`, `image_url` | Upsert / 冪等キー | 論理ER §14.3「itemCode + image_url」相当（item 解決後） |
| UNIQUE（partial） | `item_id` WHERE `is_primary = true` | 主画像 1 件制約 | Index 名: `uq_item_image_primary_per_item`（§9） |

---

## 8. 外部キー・参照関係

### 8.1 参照先（本テーブルから）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `item_id` | `item.item_id` | `ON` | `ON DELETE RESTRICT` | `item_テーブル定義書` §8.2 被参照と一致。Human Review #497 No.5 |

### 8.2 被参照

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| — | — | — | — | 本テーブルは Snapshot **元データ**。`recommendation_result_item` は snapshot 列に URL をコピー保持（物理 FK なし） |

### 8.3 Result Snapshot 参照

| Snapshot 列 | 元データ | 備考 |
| ----------- | -------- | ---- |
| `item_image_url_snapshot` | `item_image.image_url` WHERE `is_primary = true` | 論理ER §7.3。主画像なし時は NULL / 省略し UI プレースホルダー |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `item_image_pkey` | `item_image_id` | btree（PK） | 主キー | 自動生成 |
| `uq_item_image_item_url` | `item_id`, `image_url` | unique btree | Upsert キー | §7 |
| `uq_item_image_primary_per_item` | `item_id` | unique partial | 主画像 1 件 | `WHERE is_primary = true` |
| `idx_item_image_item_id` | `item_id` | btree | api / reco JOIN | API-PUB-003 `images[]` 取得 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `item_image_pkey` | PRIMARY KEY | `item_image_id` | 主キー | — |
| `uq_item_image_item_url` | UNIQUE | `item_id`, `image_url` | Upsert 自然キー | §7 |
| `uq_item_image_primary_per_item` | UNIQUE | `item_id` | `is_primary = true` は item あたり 1 行 | partial unique |
| `fk_item_image_item_id` | FOREIGN KEY | `item_id` | `item(item_id)` ON DELETE RESTRICT | §8.1 |
| `chk_item_image_size_type` | CHECK | `image_size_type` | `image_size_type IN ('small', 'medium')` | API-PUB-003 `images[].kind` と整合 |
| `chk_item_image_display_order` | CHECK | `display_order` | `display_order >= 0` | 配列 index 由来 |
| `chk_item_image_url_not_empty` | CHECK | `image_url` | `char_length(trim(image_url)) > 0` | 空 URL 禁止 |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `image_size_type` | （code 未定義） | 論理ER §8.3 / API-PUB-003 | `small` / `medium` | enum定義書未 YAML 化。CHECK で担保 |
| — | — | — | — | 状態カラムなし（`is_active` 不採用） |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | api | `item_id` 指定 | — | — | API-PUB-003 JOIN。主画像 + 複数枚 |
| SELECT | reco | Result Snapshot 生成 | — | — | `is_primary=true` の URL を snapshot 列へコピー |
| UPSERT | batch（BATCH-007） | `item_id` + `image_url` | `image_size_type`, `display_order`, `is_primary`, `fetched_at` | Upsert キーで冪等 | §12.1 |
| DELETE | batch（BATCH-007） | 同期置換：今回集合外の URL | — | 再実行で同一結果 | §12.1 ステップ 3 |
| INSERT / UPDATE / DELETE | api / reco | — | — | **禁止** | Online 推薦中に更新しない |

### 12.1 item 単位同期置換フロー

```text
1. item Upsert 完了（item_id 確定）
2. staging_item_image から当該 item の画像行集合 S を取得
3. S の各行を item_id + image_url で UPSERT（display_order / image_size_type / fetched_at 更新）
4. is_primary / display_order を §5.3 で再計算し UPDATE
5. DELETE FROM item_image WHERE item_id = :id AND image_url NOT IN (S の URL 集合)
6. S が空の場合：当該 item_id の item_image 行をすべて DELETE（画像なし商品）
```

### 12.2 Upsert 疑似コード

```sql
INSERT INTO item_image (
  item_id, image_url, image_size_type, display_order, is_primary, fetched_at
) VALUES (...)
ON CONFLICT (item_id, image_url) DO UPDATE SET
  image_size_type = EXCLUDED.image_size_type,
  display_order = EXCLUDED.display_order,
  is_primary = EXCLUDED.is_primary,
  fetched_at = EXCLUDED.fetched_at;

-- 同期置換（ステップ 5）
DELETE FROM item_image
 WHERE item_id = :item_id
   AND image_url NOT IN (:url_list);
```

---

## 13. API 公開列マッピング（API-PUB-003）

| API 項目 | DB 列 / 導出 | 公開 | 備考 |
| -------- | ------------ | ---- | ---- |
| `itemImageUrl` | `image_url` WHERE `is_primary = true` | optional | 主画像なし時は省略 |
| `images[]` | `item_image` 全行 JOIN | optional | 複数枚 |
| `images[].url` | `image_url` | 必須（配列要素内） | — |
| `images[].kind` | `image_size_type` | optional | `small` / `medium` |
| `images[].isPrimary` | `is_primary` | optional | 1 件 `true` |

---

## 14. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 商品有効期間中（親 `item` に従う） |
| 削除方式 | 同期置換による物理 DELETE（API から消えた URL） |
| 削除条件 | 当該 Batch 反映集合に含まれない `image_url` 行 |
| 論理削除 | `is_active` 列なし（§17.1 No.3） |
| 履歴 | 保持しない。監査は Raw / Staging メタデータ |
| アーカイブ | MVP 対象外 |

---

## 15. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `item_image` |
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
| service role利用 | BATCH-007 Upsert / 同期 DELETE に限定 |
| 個人情報・機微情報 | 公開商品画像 URL のみ |
| ログ出力制限 | 大量 image_url を error ログに過剰出力しない |

---

## 17. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / FK / CHECK / partial unique が定義どおり | migration |
| 2 | Upsert キー | 同一 `item_id` + `image_url` で重複 INSERT が拒否される | migration |
| 3 | 主画像一意 | 同一 `item_id` で `is_primary=true` が 2 行 INSERT できない | migration |
| 4 | 同期置換 | API から消えた URL 行が DELETE される | integration |
| 5 | FK 整合 | 存在しない `item_id` への INSERT が拒否される | migration |
| 6 | API 整合 | 主画像 JOIN が API-PUB-003 `itemImageUrl` / `images[]` と一致 | contract |

---

## 18. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review #497 にて No.1〜5 を決定済み（下記参照） |

### 18.1 Human Review 決定事項（Issue #497）

| No | 論点 | 決定内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | 画像 URL 履歴 vs 最新 Upsert | **最新のみ Upsert + item 単位同期置換**（消えた URL は DELETE） | Human | §5.4 / §12.1 |
| 2 | `source` / `source_system` / `source_api` 列 | **いずれも item_image 行に持たない**。マーケットは `item.source`、API トレースは staging/raw チェーン | Human | §5.2 |
| 3 | `is_active` 列 | **MVP 不採用**（`item_review_summary` / `external_genre` と同型） | Human | 同期 DELETE で代替 |
| 4 | `is_primary` partial unique | **採用**（`item_id` WHERE `is_primary = true`）。Upsert キーは `item_id` + `image_url` | Human | §7 / §9 / §10 |
| 5 | `item_id` FK ON DELETE | **`ON DELETE RESTRICT`** を採用（親 `item` 物理削除を禁止し整合） | Human | `item` は論理無効化が基本 |

---

## 19. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8 FK・§10 Index |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §8.2–§8.3・§7.3 Snapshot |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §5 No.11・§6 No.21 |
| リソース一覧 | `docs/05_アプリケーション設計/アプリ/database/リソース一覧.md` | §12.3 Item Image |
| 外部商品連携 | `docs/05_アプリケーション設計/アプリ/外部商品データ連携設計書.md` | §11 商品画像 |
| item 定義書 | `docs/06_実装設計/database/item_テーブル定義書.md` | §8.2 FK 被参照・§12.1 反映順 |
| staging_item_image 定義書 | `docs/06_実装設計/database/staging_item_image_テーブル定義書.md` | §5.5 Upsert 入力・Human Review #523 |
| API契約 | `docs/06_実装設計/api/API-PUB-003_商品詳細取得API契約仕様書.md` | 画像応答マッピング |
| バッチ処理一覧 | `docs/05_アプリケーション設計/アプリ/batch/バッチ処理一覧.md` | BATCH-005 / BATCH-007 |

---

## 20. レビュー観点

- 論理ER §8.2–§8.3・テーブル一覧 §5 No.11 と矛盾していない
- `item_テーブル定義書` §5.1 / §8.2 / §12.1 / §12.3 / §13 と責務・FK・反映順が整合している
- 主画像選定・`is_primary` / `display_order` / `image_size_type` 方針が明記されている
- `source` 系列列・`is_active` を持たない方針が §5 で明示されている
- 最新 Upsert + 同期置換（DELETE）が §12 に明記されている
- `recommendation_result_item.item_image_url_snapshot` 参照が §8.3 に整理されている
- staging → item_image Upsert 方針が §5.5 に整理されている
- DDL Task が CREATE TABLE を起こせる粒度である
- apps/** / OpenAPI / generated 変更が含まれていない
- secret や `.env` 実値が含まれていない
