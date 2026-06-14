# Staging Genre テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                             |
| -------------- | -------------------------------- |
| ドキュメントID | `DB-TBL-MVP-staging_genre`       |
| ドキュメント名 | Staging Genre テーブル定義書     |
| 対象システム   | Gift Recommendation Service MVP  |
| MVP対象        | `yes`                            |
| 作成日         | 2026-06-14                       |
| 更新日         | 2026-06-14                       |

---

## 2. 概要

`staging_genre` は、外部商品データ連携系における **ジャンル Staging 中間正本** である。

`raw_product_metadata`（`source_api = genre_search`）から BATCH-001（楽天ジャンル同期）または BATCH-005（Raw取込・Staging変換）で生成され、楽天ジャンル検索API由来の正規化ジャンル属性を一時保持する。反映フェーズで `external_genre` へ Upsert される。

Staging 系は **物理 FK なし（LOGICAL + Index）**、**成功 Batch 完了後に削除** する一時データ（物理ER §13・`staging_item_テーブル定義書` §13 と同型）。

---

## 3. 目的

- 楽天ジャンル検索APIレスポンスを Adapter で正規化した **中間行** を batch が管理する
- `raw_product_metadata` → `staging_genre` → `external_genre` のジャンル昇格フロー中核を物理定義する
- `external_genre` Upsert キー（`source` + `external_genre_id`）と列マッピングの Staging 側入力を提供する
- 後続 DDL Task が migration を作成できる粒度まで設計を確定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `staging_genre` |
| 論理テーブル名 | Staging Genre |
| 分類 | 外部商品データ連携系 |
| 正本区分 | 一時 / 中間 |
| 主な更新主体 | batch（BATCH-001 / BATCH-005・`MOD-BATCH-020` Staging Transformer / `MOD-BATCH-022` Staging Repository） |
| 主な参照主体 | batch のみ（Online / api / reco から Direct 参照しない） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11 |

---

## 5. 用途・責務

- **Raw Metadata 単位・ジャンルID単位** で Staging 行を作成し、BATCH-001 / BATCH-005 完了時点の正規化ジャンル属性を保持する
- 1 回のジャンル API レスポンス（`genre` / `ancestors` / `siblings` / `children` 等）から **複数行** を展開し、各 `external_genre_id` を 1 行として保持する
- 反映フェーズで `source` + `external_genre_id` をキーに `external_genre` へ Upsert する **入力正本** となる
- 商品 Staging（`staging_item`）・画像・ランキング Staging は **別テーブル** が担当
- Public API では返却しない（内部 Batch データ）

### 5.1 対象外

- Raw JSON 本体（Object Storage / `raw_product_metadata` の責務）
- 外部ジャンル正本（`external_genre` の責務）
- 商品 Staging（`staging_item` / `staging_item_image` / `staging_ranking_signal` の責務）
- 属性 Staging（`staging_attribute` の責務。MVP 任意）
- `api_call_log` / `fetch_cursor` 本体
- Public API 公開
- OpenAPI / generated 変更（Epic 終盤 Task #469 へ委譲）

### 5.2 `raw_product_metadata` → `staging_genre` 関係（transforms_to）

`raw_product_metadata_テーブル定義書` §5.5 / §8.2 に従う。

| 観点 | 方針 |
| ---- | ---- |
| データフロー | `api_call_log` → **`raw_product_metadata`**（`source_api = genre_search`）→ **`staging_genre`**（BATCH-001 / BATCH-005） |
| 物理ER 関係 | `raw_product_metadata` → `staging_genre` : `transforms_to`（**LOGICAL** FK。Staging 系は物理 FK なし） |
| カーディナリティ | 1 Raw Metadata : **N** Staging Genre（1 レスポンス内の複数ジャンルノード） |
| 参照列 | `staging_genre.raw_metadata_id` → `raw_product_metadata.raw_metadata_id` |
| trace | `raw_metadata_id` / `staging_genre_id`（インターフェース一覧 IF-DB-BATCH-005） |
| `source` / `source_api` | **`source` は本テーブルに denormalize**（Upsert キー用）。`source_api` は **`raw_product_metadata.source_api`** 経由で trace（行に持たない） |
| 対象 Raw | `raw_product_metadata.source_api = 'genre_search'` のみ（`raw_product_metadata_テーブル定義書` §11） |

```mermaid
flowchart LR
    RPM[raw_product_metadata] --> SG[staging_genre]
    SG --> EG[external_genre]
```

### 5.3 `staging_genre` → `external_genre` 関係（upserts）

`external_genre_テーブル定義書` §5.2 に従う。

| 観点 | 方針 |
| ---- | ---- |
| 物理ER 関係 | `staging_genre` → `external_genre` : `upserts`（**LOGICAL**） |
| Upsert 自然キー | **`source` + `external_genre_id`**（`external_genre.uq_external_genre_source_id` と同一体系） |
| カーディナリティ | N Staging 行 : 1 External Genre（時系列で複数 Staging 行が同一正本行に収束） |
| 反映 Batch | BATCH-001（楽天ジャンル同期）および BATCH-005 反映フェーズ |
| 正本性 | **永続正本は `external_genre`**。Staging 行は一時中間 |

### 5.4 BATCH-001 / BATCH-005 書き込み経路

| Batch | 入力 | Staging 作成 | `external_genre` 反映 | 備考 |
| ----- | ---- | ------------ | --------------------- | ---- |
| BATCH-001 | 楽天ジャンル検索API | ○（`staging_genre` INSERT） | ○（同一 Batch 内 Upsert） | バッチ処理一覧。ジャンル専用同期 |
| BATCH-005 | `raw_product_metadata`（`genre_search`） | ○（Staging 変換後 INSERT） | ○（反映フェーズで Upsert） | 商品 Raw 連携と同一パイプライン |

> **方針**: いずれの経路も **Staging 行を経由** して `external_genre` へ反映する（`external_genre_テーブル定義書` §5.2）。BATCH-001 は Raw 保存と Staging 作成・正本 Upsert を **同一 Run 内** で完結させる。

### 5.5 楽天ジャンルAPI マッピング（Staging 列）

| 楽天ジャンルAPI（正規化後） | Staging 物理カラム | `external_genre` 列 | 備考 |
| --------------------------- | ------------------ | ------------------- | ---- |
| `genreId` | `external_genre_id` | `external_genre_id` | `0` は root 行（`external_genre_テーブル定義書` §17.1 No.4） |
| `jaName` / `genreName` | `genre_name` | `genre_name` | Adapter で `genre_name` に統一 |
| `level` / `genreLevel` | `genre_level` | `genre_level` | 0 以上 |
| `parentGenreId`（最直近親） | `parent_external_genre_id` | `parent_external_genre_id` | root は `NULL` |
| （子ジャンル有無） | `is_leaf` | `is_leaf` | API `children` 空、または Batch 判定 |
| — | `source` | `source` | `raw_product_metadata.source` から denormalize。MVP 固定 `rakuten` |
| — | `staged_at` | `fetched_at` | Staging 完了日時を正本反映時の `fetched_at` に渡す |

### 5.6 外部商品データ連携設計書 §12.1 との差分整理

| 外部商品データ連携設計書 §12.1 | 本テーブル（MVP 物理 DDL） | 扱い |
| ------------------------------ | -------------------------- | ---- |
| `parent_genre_id` | `parent_external_genre_id` | 論理ER §9.2・`external_genre` に合わせ物理名を統一 |
| `source_system` | `source` | `item.source` / `external_genre.source` と同一体系 |
| `is_active` | （列なし） | MVP **不採用**（`external_genre_テーブル定義書` §17.1 No.3 決定済み） |
| `fetched_at` | `staged_at` | Staging 層は **`staged_at`**。正本反映時に `external_genre.fetched_at` へ写像 |

### 5.7 論理ER §9.2 との差分整理

| 論理ER §9.2 主要属性 | 本テーブル | 扱い |
| -------------------- | ---------- | ---- |
| `staging_genre_id` | `staging_genre_id` | 一致 |
| `raw_metadata_id` | `raw_metadata_id` | 一致 |
| `external_genre_id` | `external_genre_id` | 一致 |
| `genre_name` | `genre_name` | 一致 |
| `parent_external_genre_id` | `parent_external_genre_id` | 一致 |
| `genre_level` | `genre_level` | 一致 |
| `staged_at` | `staged_at` | 一致 |
| （未列挙） | `source` | **採用**（`staging_item` と同型。Upsert キー整合のため §17.1 No.2 提案） |
| （未列挙） | `is_leaf` | **採用**（`external_genre` Upsert 更新列との整合のため §17.1 No.3 提案） |

### 5.8 関連 Staging（同一 Raw 由来・別 Task）

| テーブル | 紐づけ | 備考 |
| -------- | ------ | ---- |
| `staging_item` | `raw_metadata_id`（商品 API 由来時） | 商品 Staging 正本（#517） |
| `staging_item_image` | `raw_metadata_id` + `external_item_code` | 画像 Staging（別 Task） |
| `staging_ranking_signal` | `raw_metadata_id` + `external_item_code` | ランキング Staging（別 Task） |

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `staging_genre_id` | Staging Genre ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK。trace キー（IF-DB-BATCH-005） |
| 2 | `raw_metadata_id` | Raw Metadata ID | `uuid` | `yes` | — | LOGICAL | — | — | 生成元 Raw Metadata。`raw_product_metadata.raw_metadata_id` 参照 |
| 3 | `source` | Data Source | `text` | `yes` | — | — | — | `'rakuten'` | 外部 EC ソース。Upsert キー（`external_genre.source` と同一）。`raw_product_metadata.source` から denormalize |
| 4 | `external_genre_id` | External Genre ID | `bigint` | `yes` | — | LOGICAL | — | — | 楽天 `genreId`。`external_genre.external_genre_id` 論理参照。`0` は root |
| 5 | `genre_name` | Genre Name | `varchar(255)` | `yes` | — | — | — | — | ジャンル表示名。楽天 `jaName` / `genreName` |
| 6 | `parent_external_genre_id` | Parent External Genre ID | `bigint` | `no` | — | LOGICAL | — | `NULL` | 最直近の親ジャンルID。root（`external_genre_id = 0`）は `NULL` |
| 7 | `genre_level` | Genre Level | `smallint` | `yes` | — | — | — | — | 階層レベル。楽天 `level` / `genreLevel` |
| 8 | `is_leaf` | Leaf Flag | `boolean` | `yes` | — | — | — | `false` | 末端ジャンル（子ジャンルなし）か |
| 9 | `staged_at` | Staged At | `timestamptz` | `yes` | — | — | — | — | Staging 変換完了日時（UTC） |
| 10 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | 行作成日時 |
| 11 | `updated_at` | Updated At | `timestamptz` | `yes` | — | — | — | `now()` | 行最終更新日時 |

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `staging_genre_id` | サロゲート UUID | trace キー |
| UNIQUE | `raw_metadata_id`, `external_genre_id` | Raw 1 件あたり同一ジャンルIDは 1 Staging 行 | §17.1 No.1 **提案**。BATCH-001 / BATCH-005 冪等 |

---

## 8. 外部キー・参照関係

### 8.1 参照先（論理）

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `raw_metadata_id` | `raw_product_metadata.raw_metadata_id` | `LOGICAL` | Batch で存在確認 | transforms_to 親 |
| `external_genre_id` | `external_genre.external_genre_id` | `LOGICAL` | Upsert 先。Staging 時点では未存在可 | 反映後に正本化 |
| `parent_external_genre_id` | `external_genre.external_genre_id` | `LOGICAL` | Batch で親行存在確認（root は NULL） | 物理 FK は Staging 系なし |

### 8.2 被参照（論理）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `external_genre` | `source`, `external_genre_id` | upserts（間接） | `LOGICAL` | Upsert キー対応 |

### 8.3 関連 Staging（`staging_item` との関係）

`staging_item_テーブル定義書` §8.3 に従う。

| テーブル | 紐づけ | 備考 |
| -------- | ------ | ---- |
| `staging_item` | 同一 `raw_metadata_id`（商品 API 由来 Raw の場合のみ並存） | ジャンル API Raw では `staging_item` 行は通常 **0 件** |
| `staging_item.external_genre_id` | 商品行が参照するジャンルID | 本テーブルで Upsert された `external_genre` を間接参照 |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `staging_genre_pkey` | `staging_genre_id` | btree（PK） | 主キー | 自動生成 |
| `uq_staging_genre_raw_metadata_genre` | `raw_metadata_id`, `external_genre_id` | unique btree | BATCH-001 / BATCH-005 冪等 | §7 |
| `idx_staging_genre_raw_metadata` | `raw_metadata_id` | btree | Raw 単位一覧・Retention DELETE 補助 | transforms_to 親 |
| `idx_staging_genre_source_id` | `source`, `external_genre_id` | btree | `external_genre` 反映フェーズの突合 | Upsert キー |

> 物理ER §10 への Index 行追記は DDL Task または別 docs Task で整合する。

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `staging_genre_pkey` | PRIMARY KEY | `staging_genre_id` | 主キー | — |
| `uq_staging_genre_raw_metadata_genre` | UNIQUE | `raw_metadata_id`, `external_genre_id` | BATCH 冪等 | §7 |
| `chk_staging_genre_source_mvp` | CHECK | `source` | `source = 'rakuten'` | MVP 固定 |
| `chk_staging_genre_level_range` | CHECK | `genre_level` | `genre_level >= 0 AND genre_level <= 5` | `external_genre` と同一上限（§17.1 No.4 提案） |
| `chk_staging_genre_name_length` | CHECK | `genre_name` | `char_length(genre_name) BETWEEN 1 AND 255` | — |
| `chk_staging_genre_parent_not_self` | CHECK | `parent_external_genre_id` | `parent_external_genre_id IS NULL OR parent_external_genre_id <> external_genre_id` | 自己参照禁止 |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `source` | （code 未定義） | `item.source` / `external_genre.source` 慣行 | MVP: `rakuten` | CHECK で MVP 固定 |
| — | — | — | — | 状態カラムなし（ジャンルは hash 差分判定対象外） |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| INSERT | batch | BATCH-001 / BATCH-005 Staging 変換成功 | 全業務列 + `staged_at` | `(raw_metadata_id, external_genre_id)` UNIQUE | IF-DB-BATCH-005 |
| SELECT | batch | `external_genre` 反映フェーズ | — | — | Staging 行を読み Upsert |
| DELETE | batch | Batch 成功完了後 Retention | — | `raw_metadata_id` 単位等 | 物理ER §13 |
| INSERT / UPDATE / DELETE | api / reco / web | — | — | **禁止** | Staging は Batch 専用 |

### 12.1 Staging 保存フロー（ジャンル API）

```text
1. raw_product_metadata（source_api = genre_search, import_status = raw_saved）を読み取り
2. Object Storage から Raw JSON 取得
3. Staging Transformer（MOD-BATCH-020）でジャンルノード（genre / ancestors / siblings / children）を展開
4. Staging Validator（MOD-BATCH-021）で必須項目検証
5. staging_genre INSERT（1 ノード = 1 行）
6. external_genre UPSERT（反映フェーズ）
7. raw_product_metadata.import_status → staged（必要に応じて imported）
```

### 12.2 INSERT 疑似コード

```sql
INSERT INTO staging_genre (
  raw_metadata_id,
  source,
  external_genre_id,
  genre_name,
  parent_external_genre_id,
  genre_level,
  is_leaf,
  staged_at
) VALUES (
  :raw_metadata_id,
  :source,
  :external_genre_id,
  :genre_name,
  :parent_external_genre_id,
  :genre_level,
  :is_leaf,
  :staged_at
)
ON CONFLICT (raw_metadata_id, external_genre_id) DO UPDATE SET
  source = EXCLUDED.source,
  genre_name = EXCLUDED.genre_name,
  parent_external_genre_id = EXCLUDED.parent_external_genre_id,
  genre_level = EXCLUDED.genre_level,
  is_leaf = EXCLUDED.is_leaf,
  staged_at = EXCLUDED.staged_at,
  updated_at = now();
```

### 12.3 `staging_genre` → `external_genre` 列マッピング

| staging_genre 列 | external_genre 列 | 備考 |
| ---------------- | ----------------- | ---- |
| `source` | `source` | Upsert キー |
| `external_genre_id` | `external_genre_id` | Upsert キー |
| `genre_name` | `genre_name` | |
| `parent_external_genre_id` | `parent_external_genre_id` | |
| `genre_level` | `genre_level` | |
| `is_leaf` | `is_leaf` | |
| `staged_at` | `fetched_at` | Staging 完了日時を正本の最終反映日時とする |

### 12.4 `external_genre` Upsert 疑似コード（反映フェーズ）

```sql
INSERT INTO external_genre (
  external_genre_id, source, genre_name,
  parent_external_genre_id, genre_level, is_leaf, fetched_at
)
SELECT
  sg.external_genre_id,
  sg.source,
  sg.genre_name,
  sg.parent_external_genre_id,
  sg.genre_level,
  sg.is_leaf,
  sg.staged_at
FROM staging_genre sg
WHERE sg.raw_metadata_id = :raw_metadata_id
ON CONFLICT (source, external_genre_id) DO UPDATE SET
  genre_name = EXCLUDED.genre_name,
  parent_external_genre_id = EXCLUDED.parent_external_genre_id,
  genre_level = EXCLUDED.genre_level,
  is_leaf = EXCLUDED.is_leaf,
  fetched_at = EXCLUDED.fetched_at;
```

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | **成功 Batch 完了後即 DELETE** / 失敗・部分成功時 **7〜14 日**（物理ER §13・`staging_item_テーブル定義書` §13 と同型） |
| 削除方式 | 物理 DELETE |
| 削除条件 | 原則 **`raw_metadata_id` 単位**（Raw Metadata Retention と連動） |
| 論理削除 | 列なし |
| 履歴 | **保持しない**（Staging 中間のため） |
| アーカイブ | MVP 対象外 |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `staging_genre` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 外部商品データ連携系。**`raw_product_metadata` 作成後**、**`external_genre` より前または並行** 可（LOGICAL FK）。`staging_item` と並行可 |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | batch（service role 経由）のみ |
| 書き込み権限 | batch のみ。Online / reco / web からの DML 禁止 |
| service role利用 | Staging Repository に限定 |
| 個人情報・機微情報 | 含まない（ジャンル名のみ） |
| ログ出力制限 | 大量ジャンル名を application log に過剰出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / CHECK / UNIQUE が定義どおり | migration |
| 2 | 冪等 Upsert | 同一 `(raw_metadata_id, external_genre_id)` 再 INSERT が UPDATE になる | migration |
| 3 | transforms_to | `raw_metadata_id` 不存在時 Batch が拒否（アプリ validation） | integration |
| 4 | 反映連携 | Staging 行から `external_genre` Upsert が `source` + `external_genre_id` で成功する | integration |
| 5 | 多行展開 | 1 ジャンル API レスポンスから ancestors / children 等が複数行になる | integration |
| 6 | Retention | 成功 Batch 後 DELETE が `raw_metadata_id` 単位で実行可能 | integration |
| 7 | 権限 | web client から Direct DB アクセス不可 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | UNIQUE `(raw_metadata_id, external_genre_id)` | 1 Raw 内の複数ジャンルノード展開との整合 | Human | HR #525 | §17.1 No.1 提案 |
| 2 | `source` 列の Staging 明示保持 | Upsert キー整合 | Human | HR #525 | §17.1 No.2 提案 |
| 3 | `is_leaf` 列の Staging 保持 | `external_genre` Upsert 列との整合 | Human | HR #525 | §17.1 No.3 提案 |
| 4 | `genre_level` CHECK 上限 5 | `external_genre` と同一にするか | Human | HR #525 | §17.1 No.4 提案 |
| 5 | BATCH-001 内 `external_genre` 直接 Upsert の詳細順序 | Run 内フェーズ分割 | Human | HR #525 | 実装 Task へ引き継ぎ可 |

### 17.1 Human Review 提案（Issue #525）

| No | 論点 | 提案内容 | 根拠 |
| --: | ---- | -------- | ---- |
| 1 | UNIQUE キー | **`(raw_metadata_id, external_genre_id)`** を MVP 必須とする | 1 ジャンル API レスポンス内の複数ノード（genre / ancestors / siblings / children）を 1 Raw あたり 1 行ずつ保持。`staging_item` の `(raw_metadata_id, external_item_code)` と同型 |
| 2 | `source` 列 | **採用**。`raw_product_metadata.source` を Staging INSERT 時にコピー | `staging_item` Human Review #517 No.2 と同型。`external_genre` Upsert キー整合 |
| 3 | `is_leaf` 列 | **採用** | `external_genre_テーブル定義書` §5.2 更新列に含まれる。論理ER §9.2 未列挙だが物理 DDL で補完 |
| 4 | `genre_level` CHECK | **0〜5**（`external_genre.chk_external_genre_level_range` と同一） | Human Review #494 No.2 決定済み方針の Staging 側踏襲 |
| 5 | Retention | **物理ER §13 方針**（成功 Batch 後即 DELETE） | `staging_item_テーブル定義書` §13 と同一 |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | §9 transforms_to / upserts / §13 Retention |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §9.2 属性 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §6 No.23 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | `source_api` 等 |
| 外部商品連携 | `docs/05_アプリケーション設計/アプリ/外部商品データ連携設計書.md` | §4.4 / §12 ジャンルデータ |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-DB-BATCH-005 |
| バッチ設計方針書 | `docs/05_アプリケーション設計/アプリ/batch/バッチ設計方針書.md` | BATCH-001 / BATCH-005 |
| バッチ処理一覧 | `docs/05_アプリケーション設計/アプリ/batch/バッチ処理一覧.md` | 入出力 |
| 処理構成定義書 | `docs/05_アプリケーション設計/アプリ/処理構成定義書.md` | MOD-BATCH-020〜022 |
| raw_product_metadata 定義書 | `docs/06_実装設計/database/raw_product_metadata_テーブル定義書.md` | §5.5 transforms_to 親 |
| external_genre 定義書 | `docs/06_実装設計/database/external_genre_テーブル定義書.md` | §5.2 Upsert 先 |
| staging_item 定義書 | `docs/06_実装設計/database/staging_item_テーブル定義書.md` | Staging 系方針参考 |
| source_api enum | `packages/code-definitions/batch/source_api.yaml` | `genre_search` 識別 |

---

## 19. レビュー観点

- 論理ER §9.2・テーブル一覧 §6 No.23 と矛盾していない（差分は §5.7 で明示）
- 物理ER §9 transforms_to / upserts と整合している
- `raw_product_metadata` → `staging_genre` → `external_genre` 昇格関係が §5.2 / §5.3 / §12.3 / §12.4 で明記されている
- 外部商品データ連携設計書 §12.1 との列差分が §5.6 で整理されている
- `external_genre_テーブル定義書` §5.2 Upsert キー・更新列と整合している
- Staging 系 **物理 FK なし** 方針が §8 で明記されている
- Retention（物理ER §13）が §13 に反映されている
- `staging_item` / `staging_item_image` / `staging_ranking_signal` 本体定義が out_of_scope であることが §5.1 / §5.8 で明示されている
- apps/** / OpenAPI / generated 変更が含まれていない
- secret や `.env` 実値が含まれていない
- Human Review #525 提案事項（§17.1 No.1〜5）が本文に反映されている
