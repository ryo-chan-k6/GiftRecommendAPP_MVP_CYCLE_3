# Item Popularity Signal テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                                  |
| -------------- | ------------------------------------- |
| ドキュメントID | `DB-TBL-MVP-item_popularity_signal`   |
| ドキュメント名 | Item Popularity Signal テーブル定義書 |
| 対象システム   | Gift Recommendation Service MVP       |
| MVP対象        | `yes`                                 |
| 作成日         | 2026-06-12                            |
| 更新日         | 2026-06-12（Human Review #504 反映）  |

---

## 2. 概要

`item_popularity_signal` は、楽天商品ランキング API（BATCH-002）由来の **人気補助シグナル（順位明細）** を保持する Item 系 Snapshot / 派生テーブルである。

親ヘッダ `ranking_snapshot` 配下に 1:N で保持し、冪等キー `ranking_snapshot_id + rank` で Snapshot 単位の全件反映を行う。商品正本（`item`）とは分離し、ランキング順位は補助シグナルとして扱う（論理ER §8.4・バッチ設計方針書 §12.3）。

**Public API では内部スコアを返却しない**。`popularityBadge` の表示用表面（`label` / `rank`）のみ API-PUB-003 で optional 公開する。

---

## 3. 目的

- 楽天ランキング API の `rank` / `itemCode` 等を **Snapshot 明細** として保持し、Reco の Popularity 補正（MOD-RECO-017）の入力とする
- 冪等キー（`ranking_snapshot_id + rank`）と Item 紐づけ（`item_id` / `external_item_code`）方針を明記し、BATCH-002 / IF-DB-BATCH-008 の再実行性を担保する
- `staging_ranking_signal` → `ranking_snapshot` → `item_popularity_signal` の 2 層 Snapshot 経路を物理 DDL 粒度まで確定する
- 後続 DDL Task が migration を作成できる粒度まで設計を確定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `item_popularity_signal` |
| 論理テーブル名 | Item Popularity Signal |
| 分類 | Item系 |
| 正本区分 | Snapshot / 派生 |
| 主な更新主体 | batch（BATCH-002 / IF-DB-BATCH-008） |
| 主な参照主体 | batch（item 補完取得候補抽出）、reco（IF-DB-RECO-006：最新 Snapshot 経由）、api（IF-DB-API-007：`popularityBadge` JOIN） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §4.1 Item系・§8–§11・§16 |

---

## 5. 用途・責務

- 楽天ランキング API レスポンスの **順位明細**（`rank` + `itemCode`）を `ranking_snapshot_id` 配下に保持する
- テーブル一覧 §5 補足どおり、ランキングは商品正本へ直接反映せず **補助シグナル** として管理する（`item` の価格・名称等は商品検索 API 正本）
- 同一 `ranking_snapshot` 再処理時は `ranking_snapshot_id + rank` で Upsert し、二重登録を防ぐ（バッチ設計方針書 §11.5）
- Online 推薦では **全履歴を直接参照せず**、最新 `ranking_snapshot` から導出した明細を Popularity 補正に利用する（バッチ設計方針書 §12.3）
- `item_image` / `item_review_summary` と同型で、**行に `source` / `source_api` を持たない**（§5.3）

### 5.1 対象外

- ランキング観測ヘッダ（`ranking_snapshot` の責務。#496 merge 済み）
- 商品正本属性（`item` の責務。`itemName` / `itemPrice` / `itemUrl` / `imageUrl` は反映しない — 論理ER §8.4）
- Staging 中間データ（`staging_ranking_signal` の責務）
- 内部 Popularity スコア算出ロジック（`MOD-RECO-017` 実装 Task）
- Public API への内部スコア公開（`popularityScore` / `finalScore` 等は非公開 — API-PUB-003）
- OpenAPI / generated 変更（Epic 終盤 Task #469 へ委譲）

### 5.2 `staging_ranking_signal` → `ranking_snapshot` → `item_popularity_signal` 経路

`ranking_snapshot_テーブル定義書` §5.2 と同一の 2 層構造を採用する。

| 観点 | 方針 |
| ---- | ---- |
| Staging 変換 | `raw_product_metadata` → `staging_ranking_signal`（BATCH-005） |
| 正本反映 | `staging_ranking_signal` または API 直接レスポンス → `ranking_snapshot`（ヘッダ get-or-create）→ **本テーブル**（明細全件反映） |
| Staging 物理 FK | `staging_ranking_signal` → 本テーブルは **LOGICAL**（物理ER §17 No.3） |
| 親ヘッダ物理 FK | `ranking_snapshot_id` → `ranking_snapshot.ranking_snapshot_id` は **物理 FK ON**（物理ER §9） |
| 反映 I/F | IF-DB-BATCH-008（INSERT / REPLACE SNAPSHOT） |

### 5.3 出所・トレース方針（`source` 系列列なし）

| 観点 | 方針 |
| ---- | ---- |
| 取得元 API | 楽天商品ランキング API。`item_image` / `item_review_summary` と同型で **行に `source` / `source_api` は持たない** |
| マーケット識別 | 親 `ranking_snapshot.source`（MVP: `rakuten`）。`item_id` 解決後は `item.source` と一致すべき |
| API トレース | `staging_ranking_signal.raw_metadata_id` → `raw_product_metadata`（監査時） |
| 本テーブル列 | **`source` / `source_system` / `source_api` は MVP 物理 DDL に含めない** |

### 5.4 ヘッダ / 明細の冗長列

論理ER §8.2・§8.4 および `staging_ranking_signal` は `external_genre_id` / `period` / `last_build_date` を明細側にも保持する。

| 観点 | 方針 |
| ---- | ---- |
| 観測コンテキストの正本 | **`ranking_snapshot` ヘッダ**（`ranking_snapshot_テーブル定義書` §5.2 注記） |
| 明細側冗長列 | **`external_genre_id` / `period` / `last_build_date` を保持する**（JOIN 省略・Staging 直写・監査のため） |
| 整合ルール | INSERT / Upsert 時は **同一 API レスポンス内のヘッダ値と一致** させる。ヘッダ列は不変のため明細 UPDATE は原則 `item_id` 補完のみ |
| `fetched_at` | 本サービスが当該明細行を反映した日時（行単位メタ）。観測キーには含めない |

### 5.5 正本モデル（Snapshot 明細・履歴）

`item_image` の「item 単位最新のみ」とは **異なる** Snapshot モデルである。

| 観点 | 方針 |
| ---- | ---- |
| 履歴単位 | **`ranking_snapshot` ヘッダ単位**（`last_build_date` 等が異なれば別 Snapshot として履歴保持） |
| 明細冪等キー | `ranking_snapshot_id + rank`（テーブル一覧 §14 No.2） |
| item 単位最新のみ | **採用しない**。同一 `item_id` が複数 Snapshot にまたがって rank を持ちうる |
| Online 参照 | 最新 `ranking_snapshot` 選択後に本テーブルを JOIN（§12.4） |
| 物理 DELETE | **過去 Snapshot 配下は禁止**。同一 `ranking_snapshot_id` 内の **同期置換 DELETE のみ許可**（§12.1 ステップ 5・§14） |
| 観測の変化 | `last_build_date` が異なる取得は **別 Snapshot として履歴追記**。昨日 1 位・今日圏外は別ヘッダで表現し、過去 Snapshot は削除しない |

### 5.6 楽天ランキング API マッピング

論理ER §8.4 に準拠。

| 楽天ランキング API | 物理カラム | 備考 |
| ------------------ | ---------- | ---- |
| `itemCode` | `external_item_code` | Item 紐づけキー。`item.source` + `external_item_code` で `item_id` 解決 |
| `rank` | `rank` | 人気補助シグナル。冪等キー構成要素 |
| `genreId` | `external_genre_id` | 冗長列。ヘッダ `ranking_snapshot.external_genre_id` と一致 |
| `period` | `period` | 冗長列。ヘッダと一致 |
| `lastBuildDate` | `last_build_date` | 冗長列。ヘッダ観測キーと一致 |
| `itemName` | **反映しない** | `item.item_name` 正本（商品検索 API） |
| `itemPrice` | **反映しない** | `item.price` 正本 |
| `imageUrl` | **反映しない** | `item_image` 正本 |
| `itemUrl` | **反映しない** | `item.item_url` 正本 |
| — | `item_id` | 解決できた場合のみ設定（LOGICAL FK） |
| — | `ranking_snapshot_id` | 親ヘッダ FK（物理 ON） |
| — | `fetched_at` | 明細反映日時（UTC） |

### 5.7 Online 参照時の最新 Snapshot 選択（reco / api 共通）

MVP では reco（IF-DB-RECO-006）と api（IF-DB-API-007）で **同一条件** を用いる（Human Review #504 No.3 確定）。

| 観点 | 方針 |
| ---- | ---- |
| 対象ジャンル | 参照対象 `item.external_genre_id` |
| period | MVP 固定 **`daily`** |
| source | MVP 固定 **`rakuten`** |
| 最新の定義 | 同一 `(source, external_genre_id, period)` で **`last_build_date` 最大** の `ranking_snapshot` |
| タイブレーク | `last_build_date` 同値時は **`fetched_at DESC`**（`ranking_snapshot` Index 方針と一致） |
| 明細 JOIN | 上記で得た `ranking_snapshot_id` で本テーブルを JOIN |
| 該当なし | 最新 Snapshot または明細が無い場合、Popularity 補助なし / `popularityBadge` は **省略** |

> 将来、リクエストコンテキスト（Occasion 等）に応じて `period` や対象ジャンルを変える拡張は api / reco 実装 Task で検討する。

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `item_popularity_signal_id` | Item Popularity Signal ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | 明細行 ID |
| 2 | `ranking_snapshot_id` | Ranking Snapshot ID | `uuid` | `yes` | — | `ON` | — | — | 親 Snapshot ヘッダ。`ranking_snapshot.ranking_snapshot_id` 参照 |
| 3 | `item_id` | Item ID | `uuid` | `no` | — | `LOGICAL` | — | `NULL` | 内部商品 ID。未解決時は `NULL`（`external_item_code` のみ保持） |
| 4 | `external_item_code` | External Item Code | `text` | `yes` | — | — | — | — | 楽天 `itemCode`。Item 紐づけキー |
| 5 | `external_genre_id` | External Genre ID | `bigint` | `yes` | — | `LOGICAL` | — | — | ランキング対象ジャンル（冗長）。`external_genre.external_genre_id` 参照 |
| 6 | `rank` | Rank | `integer` | `yes` | — | — | — | — | 楽天ランキング順位（1 始まり想定） |
| 7 | `period` | Ranking Period | `varchar(32)` | `yes` | — | — | — | — | ランキング期間（例: `daily`）。ヘッダと一致 |
| 8 | `last_build_date` | Last Build Date | `timestamptz` | `yes` | — | — | — | — | 楽天 API `lastBuildDate`（冗長）。ヘッダ観測キーと一致 |
| 9 | `fetched_at` | Fetched At | `timestamptz` | `yes` | — | — | — | — | 当該明細行の最終反映日時（UTC） |
| 10 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | 行作成日時（物理ER §5 timestamp 方針） |
| 11 | `updated_at` | Updated At | `timestamptz` | `yes` | — | — | — | `now()` | 行更新日時（`item_id` 補完時等） |

> **論理ER §8.2 との差分**: 論理ER主要属性表に `ranking_snapshot_id` が未列挙だが、物理設計（物理ER §9・`ranking_snapshot` 定義書 §8.2）では **必須 FK 列** とする。論理ER §9.1 の Staging 直接 upserts はヘッダ介在の 2 層構造で解釈する。

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `item_popularity_signal_id` | サロゲート UUID | — |
| UNIQUE | `ranking_snapshot_id`, `rank` | Snapshot 明細冪等キー | 物理ER §10 `uq_ips_snapshot_rank`・テーブル一覧 §14 No.2 |

---

## 8. 外部キー・参照関係

### 8.1 参照先（本テーブルから）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `ranking_snapshot_id` | `ranking_snapshot.ranking_snapshot_id` | `ON` | `ON DELETE RESTRICT` | 親ヘッダ必須。`ranking_snapshot_テーブル定義書` §8.2 と対 |
| `item_id` | `item.item_id` | `LOGICAL` | Index 推奨 | `item_テーブル定義書` §8.2。未解決時 `NULL` 許容 |
| `external_genre_id` | `external_genre.external_genre_id` | `LOGICAL` | Index 推奨 | `external_genre_テーブル定義書` §8.2。Batch 系方針 |

### 8.2 被参照

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| — | — | — | — | 本テーブルは末端明細。reco / api は SELECT のみ |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `item_popularity_signal_pkey` | `item_popularity_signal_id` | btree（PK） | 主キー | 自動生成 |
| `uq_ips_snapshot_rank` | `ranking_snapshot_id`, `rank` | unique btree | 冪等 Upsert キー | 物理ER §10 |
| `idx_ips_ranking_snapshot_id` | `ranking_snapshot_id` | btree | 親 Snapshot 配下明細一覧 | FK 補助 |
| `idx_ips_item_id` | `item_id` | btree | api `popularityBadge` / reco JOIN | nullable |
| `idx_ips_external_item_code` | `external_item_code` | btree | item 未解決行の補完取得候補抽出 | バッチ設計方針書 §12.3 |
| `idx_ips_genre_period` | `external_genre_id`, `period` | btree | ジャンル・期間別の分析・デバッグ | 補助 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `item_popularity_signal_pkey` | PRIMARY KEY | `item_popularity_signal_id` | 主キー | — |
| `uq_ips_snapshot_rank` | UNIQUE | `ranking_snapshot_id`, `rank` | Snapshot 内順位一意 | §7 |
| `fk_ips_ranking_snapshot_id` | FOREIGN KEY | `ranking_snapshot_id` | `ranking_snapshot(ranking_snapshot_id)` ON DELETE RESTRICT | §8.1 |
| `chk_ips_rank_positive` | CHECK | `rank` | `rank >= 1` | 楽天 rank は 1 始まり想定 |
| `chk_ips_period_length` | CHECK | `period` | `char_length(period) BETWEEN 1 AND 32` | `ranking_snapshot.period` と同型 |
| `chk_ips_external_item_code_not_empty` | CHECK | `external_item_code` | `char_length(trim(external_item_code)) > 0` | — |
| `chk_ips_genre_positive` | CHECK | `external_genre_id` | `external_genre_id >= 0` | 楽天 `genreId` |
| `chk_ips_item_or_code` | CHECK | — | `item_id IS NOT NULL OR char_length(trim(external_item_code)) > 0` | 明細行の最低識別 |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `period` | （code 未定義） | 楽天ランキング API / `ranking_snapshot` | 例: `realtime`, `daily`, `weekly`, `monthly` | varchar 保持。enum Task 化は後続可 |
| — | — | — | — | 状態カラムなし（`is_active` 不採用） |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| INSERT / UPSERT | batch（BATCH-002 / IF-DB-BATCH-008） | 親 `ranking_snapshot_id` 確定後 | 全明細列 | `ranking_snapshot_id + rank` | §12.1 |
| UPDATE（item 補完） | batch | `item_id IS NULL` かつ `item` が存在 | `item_id`, `updated_at` | `external_item_code` 一致 | §12.2 |
| DELETE（Snapshot スコープ） | batch（BATCH-002 / IF-DB-BATCH-008） | 同一 `ranking_snapshot_id` で API 応答集合 R に無い `rank` | — | 再実行で同一結果 | §12.1 ステップ 5。過去 Snapshot 配下は対象外 |
| SELECT | reco | §12.4 の最新 Snapshot 解決後 JOIN | — | — | IF-DB-RECO-006 |
| SELECT | api | `item_id` + §12.4 最新 Snapshot JOIN | — | — | `popularityBadge`（§13） |
| INSERT / UPDATE / DELETE | api / reco | — | — | **禁止** | Online 推薦中に更新しない |

### 12.1 Snapshot 配下全件反映フロー

```text
1. ranking_snapshot を観測キーで get-or-create（ranking_snapshot 定義書 §12.1）
2. API / staging_ranking_signal から順位明細集合 R を取得
3. R の各行について item_id を解決（source='rakuten' + external_item_code → item）
4. ranking_snapshot_id + rank で UPSERT（冗長列はヘッダ値と一致させる）
5. 同期置換 DELETE: 当該 ranking_snapshot_id で R に含まれない rank 行を DELETE
   （R が空の場合は当該 Snapshot 配下を全 DELETE）
6. （任意）item_id 未解決行の後続補完 UPDATE（§12.3）
```

ステップ 1〜5 は **1 トランザクション** で実行する。過去の `ranking_snapshot_id` 配下の行は DELETE しない。

### 12.2 Upsert・同期置換 疑似コード

```sql
INSERT INTO item_popularity_signal (
  ranking_snapshot_id,
  item_id,
  external_item_code,
  external_genre_id,
  rank,
  period,
  last_build_date,
  fetched_at
) VALUES (...)
ON CONFLICT (ranking_snapshot_id, rank) DO UPDATE SET
  item_id = COALESCE(EXCLUDED.item_id, item_popularity_signal.item_id),
  external_item_code = EXCLUDED.external_item_code,
  external_genre_id = EXCLUDED.external_genre_id,
  period = EXCLUDED.period,
  last_build_date = EXCLUDED.last_build_date,
  fetched_at = EXCLUDED.fetched_at,
  updated_at = now();

-- 同期置換（§12.1 ステップ 5）
DELETE FROM item_popularity_signal
 WHERE ranking_snapshot_id = :ranking_snapshot_id
   AND rank NOT IN (:rank_list_from_R);
-- R が空の場合: AND 1=1（当該 Snapshot 配下を全削除）
```

### 12.3 item_id 補完（後続 Batch）

```sql
UPDATE item_popularity_signal ips
   SET item_id = i.item_id,
       updated_at = now()
  FROM item i
 WHERE ips.item_id IS NULL
   AND i.source = 'rakuten'
   AND i.external_item_code = ips.external_item_code;
```

### 12.4 最新 Snapshot 解決（reco / api）

§5.7 の条件で親ヘッダを 1 件選択し、配下明細を JOIN する。

```sql
SELECT rs.ranking_snapshot_id
  FROM ranking_snapshot rs
 WHERE rs.source = 'rakuten'
   AND rs.external_genre_id = :item_external_genre_id
   AND rs.period = 'daily'
 ORDER BY rs.last_build_date DESC, rs.fetched_at DESC
 LIMIT 1;

-- 上記 ranking_snapshot_id で item_popularity_signal を item_id 条件 JOIN
```

---

## 13. API 公開列マッピング（API-PUB-003）

| API 項目 | DB 列 / 導出 | 公開 | 備考 |
| -------- | ------------ | ---- | ---- |
| `popularityBadge` | §12.4 最新 Snapshot 経由 JOIN | optional | 明細が無い場合は **省略**（Human Review #405） |
| `popularityBadge.label` | 固定文字列 **`ランキング入り`** | optional | Human Review #504 No.2 確定。period は label に含めない |
| `popularityBadge.rank` | `rank` | optional | DB 値をそのまま返す。**順位のみ**。内部スコア非公開 |
| `popularityScore` | — | **非公開** | MOD-RECO-017 内部利用 |
| `genreId` / `genreName` | `external_genre_id` → JOIN | optional | `item` 経由でも可 |

### 13.1 `popularityBadge` 導出ルール（MVP）

| 観点 | 方針 |
| ---- | ---- |
| 表示条件 | 対象 `item_id` が §12.4 で解決した最新 Snapshot の明細に **存在するときのみ** `popularityBadge` を返す |
| `label` | 固定 **`ランキング入り`**（API-PUB-003 例と一致） |
| `rank` | 明細の `rank` を integer で返す |
| rank 閾値 | MVP では **設けない**（API が返した上位 N 件＝当該 Snapshot の全明細が対象） |
| 非表示 | 最新 Snapshot に該当明細が無い場合、`popularityBadge` オブジェクトごと省略 |

> `item_テーブル定義書` §13 と整合。本テーブルは **表示用バッジの参照元** であり、商品正本列ではない。

---

## 14. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | 親 `ranking_snapshot` と一体で **履歴追記**（MVP 初期は無期限。`ranking_snapshot_テーブル定義書` §13） |
| 削除方式 | **過去 Snapshot 配下の物理 DELETE は原則禁止**。例外: 同一 `ranking_snapshot_id` 内の **同期置換 DELETE**（§12.1 ステップ 5） |
| 削除条件 | 当該 Snapshot の API 応答集合 R に含まれない `rank` 行。R 空時は当該 Snapshot 配下を全 DELETE |
| 論理削除 | 列なし |
| アーカイブ | MVP 対象外 |

---

## 15. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `item_popularity_signal` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: Item 群。`ranking_snapshot` の **後**（子 FK のため）。`item` / `external_genre` は LOGICAL 参照のため順序依存なし |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 16. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | batch / reco / api（service role 経由） |
| 書き込み権限 | batch のみ（BATCH-002 / IF-DB-BATCH-008） |
| service role利用 | Batch Snapshot 反映に限定 |
| 個人情報・機微情報 | 含まない |
| ログ出力制限 | 外部 API 認証情報をログに出力しない |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review #504 にて §17.1 を決定済み |

### 17.1 Human Review 決定事項（Issue #504）

| No | 論点 | 決定内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | 同一 `ranking_snapshot_id` 再反映時の DELETE | **Snapshot スコープ同期 DELETE を採用**。R に無い `rank` 行を DELETE。過去 Snapshot 配下は削除しない | Human | §12.1 ステップ 5・§14。`item_image` 同期置換と同型（親スコープ限定） |
| 2 | `popularityBadge.label` 導出 | 固定文字列 **`ランキング入り`**。`rank` は DB 値。明細無し時は `popularityBadge` 省略。MVP で rank 閾値なし | Human | §13.1 |
| 3 | reco / api の最新 Snapshot 選択 | `item.external_genre_id` + `period='daily'` + **`last_build_date` 最大**（同値時 `fetched_at DESC`） | Human | §5.7・§12.4 |
| 4 | 冗長列（`external_genre_id` / `period` / `last_build_date`） | **明細に保持**（ヘッダ正本と整合必須） | Human | 論理ER §8.2・§8.4 |
| 5 | `source` / `source_api` 列 | **不採用** | Human | §5.3 |
| 6 | `item_id` 物理 FK | **LOGICAL**（nullable） | Human | 物理ER §9 |
| 7 | `ranking_snapshot_id` 物理 FK | **ON**（RESTRICT） | Human | `ranking_snapshot_テーブル定義書` §8.2 |
| 8 | item 単位最新のみ Upsert | **不採用** | Human | Snapshot 履歴モデル（§5.5） |
| 9 | 冪等キー | **`ranking_snapshot_id + rank`** | Human | テーブル一覧 §14 No.2 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | Item 系・FK・冪等キー方針 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §8.2–§8.4・§9 Staging 経路 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §5 No.16・§14 No.2 |
| ranking_snapshot 定義書 | `docs/06_実装設計/database/ranking_snapshot_テーブル定義書.md` | 親ヘッダ・§5.2 経路・§8.2 FK |
| item 定義書 | `docs/06_実装設計/database/item_テーブル定義書.md` | §8.2 LOGICAL FK・§13 popularityBadge |
| external_genre 定義書 | `docs/06_実装設計/database/external_genre_テーブル定義書.md` | §8.2 LOGICAL 参照 |
| item_image 定義書 | `docs/06_実装設計/database/item_image_テーブル定義書.md` | 出所列不採用・章構成参考 |
| 外部商品データ連携 | `docs/05_アプリケーション設計/アプリ/外部商品データ連携設計書.md` | 楽天ランキング API |
| バッチ設計方針書 | `docs/05_アプリケーション設計/アプリ/batch/バッチ設計方針書.md` | §11.5・§12.3 |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-DB-BATCH-008・IF-DB-RECO-006 |
| API-PUB-003 | `docs/06_実装設計/api/API-PUB-003_商品詳細取得API契約仕様書.md` | popularityBadge 公開表面 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | `period` 将来 YAML 化 |

---

## 19. レビュー観点

- 物理ER §9・§10・テーブル一覧 §5 / §14 と矛盾していない
- 論理ER §8.4 の API 項目マッピング（非反映項目含む）と一致している
- `ranking_snapshot_テーブル定義書` §8.2 / §12 と親子・冪等方針が整合している
- `item_テーブル定義書` §8.2 の `item_id` LOGICAL 参照・未解決時 code 紐づけが明記されている
- `external_genre_テーブル定義書` §8.2 と `external_genre_id`（`bigint`）LOGICAL 参照が整合している
- `staging_ranking_signal` → `ranking_snapshot` → 本テーブル経路が §5.2 に整理されている
- `source` / `source_api` 列を持たない方針が §5.3 で明示されている
- バッチ設計方針書 §11.5 の冪等キーと一致している
- §12.1 の Snapshot スコープ同期 DELETE と §14 の削除例外が明記されている
- §5.7 / §12.4 / §13.1 の最新 Snapshot 選択・`popularityBadge` 導出が Human Review #504 と一致している
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
