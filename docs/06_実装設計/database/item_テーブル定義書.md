# Item テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                            |
| -------------- | ------------------------------- |
| ドキュメントID | `DB-TBL-MVP-item`               |
| ドキュメント名 | Item テーブル定義書             |
| 対象システム   | Gift Recommendation Service MVP |
| MVP対象        | `yes`                           |
| 作成日         | 2026-06-12                      |
| 更新日         | 2026-06-12（Human Review #495 反映） |

---

## 2. 概要

`item` は、Online推薦で参照する **内部商品正本** を保持する Item 系テーブルである。

楽天商品検索API由来の商品属性を Batch で取り込み、Staging 経由で Upsert する。Online推薦（api / reco）は **参照のみ** とし、推薦実行中の更新は行わない（論理ER §16.1）。

---

## 3. 目的

- 楽天 `itemCode` を `source` + `external_item_code` で一意に識別し、商品正本を DB 上で管理する
- `normalized_hash` による疑似差分判定と Upsert 冪等方針を物理定義する
- `active_status` / `is_active` による推薦候補フィルタと API 非 active 判定（GRS-ITM-002）の根拠を提供する
- 後続 DDL / seed / Batch 実装 Task が migration を作成できる粒度まで設計を確定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `item` |
| 論理テーブル名 | Item |
| 分類 | Item系 |
| 正本区分 | 内部商品正本 |
| 主な更新主体 | batch |
| 主な参照主体 | api（商品詳細）、reco（Retrieval / Matching / Ranking） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11 |

---

## 5. 用途・責務

- 楽天商品検索API由来の **商品名・説明・価格・URL・ジャンル・ショップ** 等の正本属性を保持する（正本定義表 §6.1）
- `staging_item` からの Upsert 先として、Batch 取込パイプラインの最終正本となる
- Online推薦の Pre Hard Filter で `is_active = true` の行のみ候補化する（状態遷移設計書 §7.1.3）
- `recommendation_result_item` への Snapshot 参照元となる（物理 FK ON。Snapshot 列は Item 更新で上書きしない）
- **子テーブル責務の境界**: 画像 URL は `item_image`、レビュー要約は `item_review_summary`、ランキング補助は `item_popularity_signal` が担当（論理ER §8.3 / §8.4）

### 5.1 対象外

- 商品画像 URL の保持（`item_image` の責務。別 Task #497）
- レビュー平均・件数の保持（`item_review_summary` の責務）
- 人気ランキングシグナル（`item_popularity_signal` の責務）
- Item Feature / Embedding / Meaning 等の派生データ（Item派生データ系テーブルの責務）
- Raw JSON 本体（Object Storage 管理。DB には `raw_product_metadata` のメタのみ）
- OpenAPI / generated の変更（Epic 終盤 Task #469 へ委譲）

### 5.2 Online / Batch 責務境界

| 主体 | 許可操作 | 禁止 |
| ---- | -------- | ---- |
| batch | INSERT / UPDATE（Upsert・状態更新・`last_checked_at` 更新） | Online推薦実行中の同時更新はアプリ設計で排他 |
| api / reco | SELECT | INSERT / UPDATE / DELETE |
| Online推薦中 | — | **本テーブルを更新しない**（論理ER §16.1・状態遷移設計書 §7.1.3） |

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `item_id` | Item ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | 内部商品 ID。API `itemId` へのマッピングは api 実装 Task で定義 |
| 2 | `source` | Source | `text` | `yes` | — | — | — | `'rakuten'` | 外部 EC ソース識別子。MVP は `rakuten` 固定 |
| 3 | `external_item_code` | External Item Code | `text` | `yes` | — | — | — | — | 楽天 `itemCode`。Upsert 自然キー（`source` と複合 unique） |
| 4 | `item_name` | Item Name | `varchar(255)` | `yes` | — | — | — | — | 商品名。API-PUB-003 `itemName` / API-PUB-002 Snapshot の正本 |
| 5 | `item_caption` | Item Caption | `text` | `no` | — | — | — | — | 商品説明。API-PUB-003 `itemDescription` の正本 |
| 6 | `catchcopy` | Catchcopy | `varchar(500)` | `no` | — | — | — | — | キャッチコピー。API-PUB-003 `itemCatchcopy` の正本 |
| 7 | `price` | Price | `integer` | `yes` | — | — | — | — | 価格（JPY・税込前提は画面側方針）。API `itemPrice` の正本。0 以上 |
| 8 | `item_url` | Item URL | `text` | `yes` | — | — | — | — | 外部 EC 商品 URL。API `itemUrl` の正本 |
| 9 | `external_genre_id` | External Genre ID | `bigint` | `no` | — | `LOGICAL` | — | — | 楽天 `genreId`。`external_genre.external_genre_id`（`bigint` PK）への論理参照（§8.1） |
| 10 | `shop_code` | Shop Code | `text` | `no` | — | — | — | — | 楽天 `shopCode`。API `shopName` は JOIN 導出（本テーブルには保持しない） |
| 11 | `normalized_hash` | Normalized Hash | `varchar(64)` | `yes` | — | — | — | — | 正規化 Payload の SHA-256 等（hex）。差分判定・Upsert 冪等の基準（§12.2） |
| 12 | `active_status` | Active Status | `text` | `yes` | — | — | — | `'active'` | `item_active_status` enum（enum定義書 §6.10） |
| 13 | `is_active` | Active Flag | `boolean` | `yes` | — | — | — | `true` | 推薦・表示候補フラグ。Pre Hard Filter / API `isActive` の判定根拠 |
| 14 | `first_fetched_at` | First Fetched At | `timestamptz` | `yes` | — | — | — | — | 初回取込日時（INSERT 時設定。以降不変） |
| 15 | `last_checked_at` | Last Checked At | `timestamptz` | `yes` | — | — | — | — | 最終確認日時。hash 変更なし時も Batch が更新（外部商品データ連携設計書 §10.2 の `last_seen_at` 相当） |
| 16 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | 行作成日時 |
| 17 | `updated_at` | Updated At | `timestamptz` | `yes` | — | — | — | `now()` | 行更新日時（Upsert / 状態更新時に更新） |

> **論理ER / 正本定義表との差分**: 正本定義表 §6.1 は `genreId` → `Item.genre_id` と記載するが、論理ER §8.2・物理ER §9 では `external_genre_id` を採用する。本定義書は **論理ER / 物理ER を正** とする。

> **`last_checked_at` と `last_seen_at`**: 外部商品データ連携設計書は Batch 文脈で `last_seen_at` と表記するが、論理ER §8.2 の物理列名は `last_checked_at` を正とする。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `item_id` | サロゲート UUID | api / reco の JOIN キー |
| UNIQUE | `source`, `external_item_code` | Upsert 自然キー | 物理ER §10 `uq_item_source_external_code` |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| — | — | なし（outgoing） | — | Item 系根テーブル。子テーブルから ON FK 被参照 |

### 8.1 Outgoing（論理参照）

| カラム | 参照先 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `external_genre_id` | `external_genre.external_genre_id` | classifies | `LOGICAL` | 物理ER §9・`external_genre_テーブル定義書` §8.2 と一致。Human Review #495 §18.1 No.1 決定済み |

### 8.2 被参照

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `item_image` | `item_id` | has | `ON` | 別 Task #497 |
| `item_review_summary` | `item_id` | has | `ON` | 別 Task |
| `item_popularity_signal` | `item_id` | has | `LOGICAL` | item 未解決時は code 紐づけ |
| `item_feature` / `item_meaning` / `item_embedding` / `item_generation_queue` | `item_id` | has / queued | `ON` | Item派生データ系 |
| `recommendation_result_item` | `item_id` | snapshotted_by | `ON` | Snapshot は Item 更新で上書きしない |
| `staging_item` | `external_item_code` | upserts | `LOGICAL` | Upsert キーは `source` + `external_item_code` |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `item_pkey` | `item_id` | btree（PK） | 主キー | 自動生成 |
| `uq_item_source_external_code` | `source`, `external_item_code` | unique btree | Upsert キー | 物理ER §10 |
| `idx_item_active_status` | `active_status`, `is_active` | btree | Retrieval 前フィルタ | 物理ER §10 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `item_pkey` | PRIMARY KEY | `item_id` | 主キー | — |
| `uq_item_source_external_code` | UNIQUE | `source`, `external_item_code` | Upsert 自然キー | staging → item 冪等 |
| `chk_item_source_mvp` | CHECK | `source` | `source = 'rakuten'` | MVP 単一ソース |
| `chk_item_price_non_negative` | CHECK | `price` | `price >= 0` | 価格下限 |
| `chk_item_active_status` | CHECK | `active_status` | `active_status IN ('active','inactive','unavailable','excluded')` | enum定義書 §6.10 |
| `chk_item_active_status_is_active` | CHECK | `active_status`, `is_active` | `is_active = (active_status = 'active')` | Pre Filter / API 整合 |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `active_status` | `item_active_status` | enum定義書 §6.10 | `active` / `inactive` / `unavailable` / `excluded` | 状態遷移設計書 §7.1 |
| `is_active` | — | 派生 boolean | `true` / `false` | `active_status = 'active'` のときのみ `true`（§10 CHECK） |

### 11.1 `active_status` と API / 推薦の対応

| `active_status` | `is_active` | API-PUB-003 | 推薦候補 |
| --------------- | ----------- | ----------- | -------- |
| `active` | `true` | 200 正常系 | 候補対象 |
| `inactive` | `false` | 422 / `GRS-ITM-002` | 対象外 |
| `unavailable` | `false` | 422 / `GRS-ITM-002` | 対象外 |
| `excluded` | `false` | 422 / `GRS-ITM-002` | 対象外 |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| SELECT | api | `item_id` 指定 | — | — | API-PUB-003。存在なし 404、非 active 422 |
| SELECT | reco | Retrieval / Matching | — | — | `is_active = true` を Pre Filter で適用 |
| INSERT | batch | `source` + `external_item_code` 未登録 | 全業務列 + `first_fetched_at` | Upsert キーで冪等 | staging_item 由来 |
| UPDATE | batch | hash 変更あり | 業務列 + `normalized_hash` + `updated_at` | 同一 hash 再投入は no-op（下記） | 子テーブル・派生キューは別処理 |
| UPDATE | batch | hash 変更なし | `last_checked_at`, `updated_at` のみ | 同一 hash で繰り返し安全 | 外部商品データ連携設計書 §10.2 |
| UPDATE | batch | 販売不可 / 取得不可 | `active_status`, `is_active`, `updated_at` | — | `unavailable` / `inactive` 等へ遷移 |
| DELETE | — | MVP では原則禁止 | — | — | `active_status` 変更で無効化。物理削除は原則しない（物理ER §13） |

### 12.1 Staging → Item Upsert フロー

```text
staging_item（external_item_code + normalized_hash）
  → product_diff_result 判定（任意）
  → item Upsert（uq_item_source_external_code）
  → item_image / item_review_summary 等は別 Task
  → item_generation_queue 登録（hash 変更時）
```

### 12.2 `normalized_hash` 冪等方針

| 項目 | 方針 |
| ---- | ---- |
| 算出主体 | batch（正規化 Payload 生成後。アルゴリズム詳細は Batch 仕様 Task） |
| 保存先 | `item.normalized_hash`（本テーブル）、`staging_item.normalized_hash`（中間） |
| Upsert キー | **`source` + `external_item_code`**（`normalized_hash` は更新判定に使用。unique キーではない） |
| hash 変更なし | 業務列は更新せず `last_checked_at` のみ更新 |
| hash 変更あり | 業務列 + `normalized_hash` を UPDATE。派生再生成キューへ登録 |

### 12.3 `normalized_hash` 算出対象（正本参照）

外部商品データ連携設計書 §6.4 を正本とする。MVP では以下を hash 入力に含める（**Human Review #495 §18.1 No.2 決定済み**）。正規化順序・NULL 扱いは Batch 仕様 Task で確定する。

| 入力項目 | hash対象 | `item` 列への反映 |
| -------- | -------- | ----------------- |
| `itemCode` | ○ | `external_item_code` |
| `itemName` | ○ | `item_name` |
| `catchcopy` | ○ | `catchcopy` |
| `itemCaption` | ○ | `item_caption` |
| `itemPrice` | ○ | `price` |
| `itemUrl` | ○ | `item_url` |
| `genreId` | ○ | `external_genre_id`（楽天 `genreId`・`bigint`） |
| `shopCode` | ○ | `shop_code` |
| `availability` | ○ | `active_status` / `is_active` 判定に利用 |
| `mediumImageUrls` / `smallImageUrls` | ○ | **`item_image` 側**（本テーブル列なし） |
| `reviewAverage` / `reviewCount` | ○ | **`item_review_summary` 側**（本テーブル列なし） |
| `attributeIds` | ○ | MVP では `external_attribute` テーブル未作成のため Batch 正規化 Payload に含めるのみ |

---

## 13. API 公開列マッピング（API-PUB-003）

| API 項目 | DB 列 / 導出 | 公開 | 備考 |
| -------- | ------------ | ---- | ---- |
| `itemId` | `item_id` | 公開 | 表面 ID 変換は api 実装 Task |
| `itemName` | `item_name` | 公開 | 必須 |
| `itemPrice` | `price` | 公開 | 必須 |
| `itemUrl` | `item_url` | 公開 | 必須 |
| `itemCatchcopy` | `catchcopy` | optional | — |
| `itemDescription` | `item_caption` | optional | — |
| `shopName` | — | optional | `shop_code` から外部マスタ JOIN または Batch 付帯情報。MVP 列なし |
| `genreId` / `genreName` | `external_genre_id` → JOIN | optional | Human Review #405。Feature 内部値は非公開 |
| `itemImageUrl` / `images[]` | `item_image` JOIN | optional | 本テーブル非保持 |
| `reviewSummary` | `item_review_summary` JOIN | optional | 本テーブル非保持 |
| `popularityBadge` | `item_popularity_signal` JOIN | optional | 内部スコア非公開 |
| `isActive` | `is_active` | 公開 | `false` は HTTP 422（GRS-ITM-002） |

---

## 14. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 商品有効期間中（長期） |
| 削除方式 | Upsert / 状態更新。物理 DELETE 原則禁止 |
| 削除条件 | — |
| 論理削除 | `active_status` を `inactive` / `unavailable` / `excluded` に変更し `is_active = false` |
| アーカイブ | MVP 対象外 |

---

## 15. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `item` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: **Item 群**。`external_genre` を **先行 CREATE 推奨**（`external_genre_テーブル定義書` §14）。`external_genre_id` は LOGICAL のため FK 依存なし。子テーブル `item_image` 等は **本テーブル作成後** |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 16. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | api / reco / batch（service role 経由） |
| 書き込み権限 | batch のみ。Online推薦中の DML 更新なし |
| service role利用 | Batch Upsert、api/reco 参照に限定 |
| 個人情報・機微情報 | 商品公開情報のみ。secret 非含有 |
| ログ出力制限 | 大量商品属性を error ログに過剰出力しない |

---

## 17. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / CHECK / UNIQUE が定義どおり | migration |
| 2 | Upsert キー | 同一 `source` + `external_item_code` で重複 INSERT が拒否される | migration |
| 3 | active 整合 | `active_status` と `is_active` の CHECK が成立 | migration |
| 4 | Batch 整合 | hash 変更なし時に `last_checked_at` のみ更新される | integration |
| 5 | API 整合 | 非 active で 422 / `GRS-ITM-002`、active で 200 | contract |
| 6 | Online 境界 | reco 実行中に batch が item を更新しない運用が担保される | manual |

---

## 18. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review #495 にて No.1〜2 を決定済み（下記参照） |

### 18.1 Human Review 決定事項（Issue #495）

| No | 論点 | 決定内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | `external_genre_id` への物理 FK vs LOGICAL | **LOGICAL 維持**（物理ER §9・`external_genre_テーブル定義書` §8.2 と一致）。型は `bigint`（#494 PK と整合） | Human | #494 merge 後突合完了。比較は §18.1.1 |
| 2 | `normalized_hash` 算出対象フィールドの確定 | **外部商品データ連携設計書 §6.4 を正本**とし、画像・レビューを hash 入力に含める（列は子テーブル） | Human | §12.3 参照。正規化順序・NULL 扱いは Batch 仕様 Task へ委譲 |

#### 18.1.1 No.1 物理 FK vs LOGICAL 比較（`external_genre_id`）

| 観点 | 物理 FK（`ON DELETE RESTRICT`） | LOGICAL（seed + 存在確認） |
| ---- | ------------------------------- | ------------------------- |
| 参照整合性 | DB が存在しない genre 参照を拒否 | batch 解決 + アプリ validation に依存 |
| 適用対象の性質 | **内部正本同士の安定参照**に向く | **外部 ID 解決前の staging 経路**や大量 Upsert に向く |
| プロジェクト慣例 | `normalization_rule` → `feature_normalization_version` は binding 正本で物理 FK ON | `staging_item` → `item` Upsert、`item` → `external_genre` は物理ER 上 LOGICAL |
| migration 順序 | `external_genre` 作成後に `item` FK 追加が必要 | `external_genre` 先行 CREATE 推奨。`item` は FK なしで CREATE 可能 |
| genre 未整備時 | #494 完了まで DDL ブロックしやすい | LOGICAL のため staging 経路と並行整備可能 |

> **決定（Human Review #495 No.1）**: MVP は **LOGICAL 維持**。#494 merge 後の再評価でも物理 FK 化は不要と判断した。

---

## 19. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §8–§11・Upsert キー・Index |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §8.2 属性・§16.1 Online 境界 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §5 No.10 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | §6.10 `item_active_status` |
| 正本定義表 | `docs/05_アプリケーション設計/アプリ/database/正本定義表.md` | §6.1 楽天商品検索API マッピング |
| 外部商品連携 | `docs/05_アプリケーション設計/アプリ/外部商品データ連携設計書.md` | §6.4 hash・§10 Upsert |
| 状態遷移 | `docs/05_アプリケーション設計/アプリ/状態遷移設計書.md` | §7.1 Item Active Status |
| API契約 | `docs/06_実装設計/api/API-PUB-003_商品詳細取得API契約仕様書.md` | Response マッピング |
| 参照先テーブル | `docs/06_実装設計/database/external_genre_テーブル定義書.md` | §8.2 被参照・型 `bigint`・#494 決定事項 |
| Upsert 元 | `docs/06_実装設計/database/staging_item_テーブル定義書.md` | §5.3 Upsert キー・§12.4 列マッピング・#517 決定事項 |
| 参考（FK 比較） | `docs/06_実装設計/database/normalization_rule_テーブル定義書.md` | §17.1.1 比較表形式 |

---

## 20. レビュー観点

- 論理ER §8.2・§15・§16.1 と矛盾していない
- 物理ER §8–§11・テーブル一覧 §5 No.10 と矛盾していない
- `normalized_hash` / `active_status` / `external_item_code` 冪等方針が §12 に明記されている
- `staging_item` → `item` Upsert キー（`source` + `external_item_code`）が明記されている
- `staging_item_テーブル定義書` §17.1（Upsert キー・hash 算出・diff_status）と整合している
- Online推薦中に `item` を更新しない方針が §5.2 に反映されている
- API-PUB-003 の `isActive` / 非 active 422 方針と整合している
- `external_genre_id` の LOGICAL 参照（`bigint`）と §18.1 決定事項が `external_genre_テーブル定義書` と整合している
- 子テーブル（`item_image` 等）の責務境界が §5.1 / §8.2 で明示されている
- apps/** / OpenAPI / generated 変更が含まれていない
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
