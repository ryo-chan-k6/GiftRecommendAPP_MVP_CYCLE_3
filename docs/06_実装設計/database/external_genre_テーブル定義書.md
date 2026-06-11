# External Genre テーブル定義書

## 1. ドキュメント情報

| 項目           | 内容                             |
| -------------- | -------------------------------- |
| ドキュメントID | `DB-TBL-MVP-external_genre`      |
| ドキュメント名 | External Genre テーブル定義書    |
| 対象システム   | Gift Recommendation Service MVP  |
| MVP対象        | `yes`                            |
| 作成日         | 2026-06-12                       |
| 更新日         | 2026-06-12（Human Review #494 反映） |

---

## 2. 概要

`external_genre` は、楽天ジャンル検索API（BATCH-001）由来の **外部ジャンル階層** を内部正本として保持する Item系テーブルである。

`item.external_genre_id` / `item_popularity_signal.external_genre_id` / `fetch_cursor.target_external_genre_id` 等の参照先となり、Batch による商品取得・ランキング取得の対象ジャンル解決に利用する。

**Public API では返却しない**（内部参照マスタ。Web / API 公開対象外）。

---

## 3. 目的

- 楽天ジャンルID・ジャンル名・階層（parent / level / is_leaf）を DB 上で一意に管理する
- BATCH-001 / BATCH-005 による Upsert 正本として、後続 Batch（BATCH-002 / BATCH-003 等）のジャンル解決を可能にする
- 後続 DDL Task が migration を作成できる粒度まで設計を確定する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `external_genre` |
| 論理テーブル名 | External Genre |
| 分類 | Item系 |
| 正本区分 | 外部参照 / 内部正本 |
| 主な更新主体 | batch（BATCH-001 / BATCH-005 経由） |
| 主な参照主体 | batch（取得計画・Upsert）、reco（間接：item 経由） |
| MVP対象 | `yes` |
| 関連物理ER | `docs/06_実装設計/database/物理ER.md` §8–§11 |

---

## 5. 用途・責務

- 楽天ジャンル検索APIレスポンスを Adapter で正規化した **ジャンル参照データ** を保持する
- テーブル一覧 §5 補足どおり、**差分反映（Upsert）対象** の外部参照マスタである（ランキング Snapshot とは異なり、時系列全件反映ではない）
- `staging_genre` 経由または BATCH-001 直接反映で Upsert する（§5.2）
- ジャンル階層探索（親子・末端判定）と取得対象ジャンル管理の正本とする
- **履歴管理は行わない**。Batch Upsert により外部 API から取得した **最新のジャンル状態** を行単位で上書き保持し、アプリ内でも当該行を **現在値の正本** として参照する（§5.4）

### 5.1 対象外

- 商品正本（`item` の責務）
- Staging 中間データ（`staging_genre` の責務）
- ランキング観測（`ranking_snapshot` / `item_popularity_signal` の責務）
- 楽天属性（`external_attribute` の責務。MVP 任意）
- Public API 公開

### 5.2 `staging_genre` → `external_genre` Upsert 関係

| 観点 | 方針 |
| ---- | ---- |
| データフロー | `raw_product_metadata` → `staging_genre`（BATCH-005 Staging 変換）→ `external_genre`（Item 関連反映） |
| 物理ER 関係 | `staging_genre` → `external_genre` : `upserts`（LOGICAL。Staging 系は物理 FK なし） |
| Upsert キー | `source` + `external_genre_id` |
| 更新列 | `genre_name`, `parent_external_genre_id`, `genre_level`, `is_leaf`, `fetched_at` |
| 冪等性 | 同一キーで INSERT ... ON CONFLICT UPDATE。Batch 再実行で同一結果 |
| BATCH-001 | 楽天ジャンル同期 Batch が `staging_genre` / `external_genre` を更新（バッチ処理一覧） |
| BATCH-005 | Raw 取込・Staging 変換後、ジャンル行を `staging_genre` へ載せ、反映フェーズで `external_genre` へ Upsert |

### 5.3 楽天API マッピング

| 楽天ジャンルAPI（正規化後） | 物理カラム | 備考 |
| --------------------------- | ---------- | ---- |
| `genreId` | `external_genre_id` | 楽天ジャンルID。`0` は root 行として DB 保持（§17.1 No.4） |
| `jaName` / `genreName` | `genre_name` | Adapter で `genre_name` に統一 |
| `level` / `genreLevel` | `genre_level` | 階層レベル |
| `parentGenreId`（祖先チェーン末端） | `parent_external_genre_id` | 最直近の親。root は `NULL` |
| （子ジャンル有無） | `is_leaf` | API `children` 空、または Batch 判定 |
| — | `source` | MVP 固定 `rakuten` |
| — | `fetched_at` | 当該行の最終取得反映日時 |

> **外部商品データ連携設計書 §12.1 との差分**: 設計書は `parent_genre_id` / `source_system` / `is_active` を列挙するが、論理ER §8.2 は `parent_external_genre_id` / `source` を採用し `is_active` は持たない。本テーブル定義書は **論理ER §8.2 を正** とし、`source_system` → `source`、`parent_genre_id` → `parent_external_genre_id` に物理名を揃える。`is_active` は MVP 物理 DDL では **採用しない**（§17.1 No.3 決定済み）。

### 5.4 正本モデル（履歴なし・最新状態 Upsert）

| 観点 | 方針 |
| ---- | ---- |
| 履歴管理 | **行わない**。ジャンル名・階層・末端フラグの過去版を別行・別テーブルで保持しない |
| 更新方式 | Batch が `source` + `external_genre_id` 単位で Upsert し、取得結果で既存行を **上書き** |
| 正本性 | アプリ内（batch / reco）では、常に **最新の Upsert 結果** をジャンル参照の正本として扱う |
| 論理削除 | `is_active` 列は持たない。無効化・非参照は Batch 側の取得対象制御で行い、行自体は原則残す |
| ランキングとの違い | ランキングは Snapshot（時系列観測）。ジャンルは **参照マスタ** であり Snapshot 化しない |

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `external_genre_id` | External Genre ID | `bigint` | `yes` | `yes` | — | `yes` | — | 楽天ジャンルID（外部自然キー）。MVP では `source='rakuten'` 前提で PK とする |
| 2 | `source` | Data Source | `text` | `yes` | — | — | — | `'rakuten'` | 外部商品データ元。MVP は `rakuten` 固定。`item.source` と同一コード体系 |
| 3 | `genre_name` | Genre Name | `varchar(255)` | `yes` | — | — | — | — | ジャンル表示名。楽天 `jaName` / `genreName` の正本 |
| 4 | `parent_external_genre_id` | Parent External Genre ID | `bigint` | `no` | — | self | — | `NULL` | 親ジャンルID。`external_genre_id = 0`（root）の行は `NULL`。それ以外の最上位は親行を参照 |
| 5 | `genre_level` | Genre Level | `smallint` | `yes` | — | — | — | — | 階層レベル。楽天 `level` / `genreLevel`。0 以上 |
| 6 | `is_leaf` | Leaf Flag | `boolean` | `yes` | — | — | — | `false` | 末端ジャンル（子ジャンルなし）か。取得計画・ランキング対象判定に利用 |
| 7 | `fetched_at` | Fetched At | `timestamptz` | `yes` | — | — | — | — | 当該ジャンル行の最終取得・反映日時（UTC） |

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
| PRIMARY KEY | `external_genre_id` | 楽天ジャンルIDを自然キーとして採用 | 論理ER §8.2 整合。MVP は `source='rakuten'` のみ |
| UNIQUE | `source`, `external_genre_id` | Upsert キー | `item.uq_item_source_external_code` と同型。将来マルチソース時の拡張用 |

> **将来拡張**: 複数 `source` 共存時は PK を `(source, external_genre_id)` へ変更する可能性あり（Human Review / 別 Task）。

---

## 8. 外部キー・参照関係

### 8.1 自己参照

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
| `parent_external_genre_id` | `external_genre.external_genre_id` | `ON` | `ON DELETE RESTRICT` | 親削除時に子が残ることを防止。root（`external_genre_id = 0`）は `NULL` |

> 物理ER §8 FK 表には self-reference 行が未掲載。Human Review #494 により **物理 FK ON（RESTRICT）** を確定（§17.1 No.1）。

### 8.2 被参照（論理）

| 参照元 | 参照列 | 関係 | FK制約 | 備考 |
| ------ | ------ | ---- | ------ | ---- |
| `item` | `external_genre_id` | classifies | `LOGICAL` | 物理ER §8。商品 Upsert 時に設定 |
| `item_popularity_signal` | `external_genre_id` | ranking_genre | `LOGICAL` | ランキング対象ジャンル |
| `fetch_cursor` | `target_external_genre_id` | targets | `LOGICAL` | 疑似差分取得カーソル |
| `staging_genre` | `external_genre_id` | upserts | `LOGICAL` | Staging → 正本 Upsert キー |

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
| `external_genre_pkey` | `external_genre_id` | btree（PK） | 主キー | 自動生成 |
| `uq_external_genre_source_id` | `source`, `external_genre_id` | unique | Upsert キー | §7 と同一 |
| `idx_external_genre_parent` | `parent_external_genre_id` | btree | 階層 traversals / 子ジャンル一覧 | self-ref FK 補助 |
| `idx_external_genre_level_leaf` | `genre_level`, `is_leaf` | btree | 取得対象ジャンル抽出（末端・階層別） | BATCH-001 計画用 |

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
| `external_genre_pkey` | PRIMARY KEY | `external_genre_id` | 主キー | — |
| `uq_external_genre_source_id` | UNIQUE | `source`, `external_genre_id` | Upsert キー | — |
| `fk_external_genre_parent` | FOREIGN KEY | `parent_external_genre_id` | `external_genre(external_genre_id)` ON DELETE RESTRICT | §8.1。Human Review #494 確定 |
| `chk_external_genre_source_mvp` | CHECK | `source` | `source = 'rakuten'` | MVP 固定。enum Task 後に緩和可 |
| `chk_external_genre_level_range` | CHECK | `genre_level` | `genre_level >= 0 AND genre_level <= 5` | MVP 上限 5（§17.1 No.2 確定）。運用中に実測で変更する場合は migration で CHECK 更新 |
| `chk_external_genre_name_length` | CHECK | `genre_name` | `char_length(genre_name) BETWEEN 1 AND 255` | — |
| `chk_external_genre_parent_not_self` | CHECK | `parent_external_genre_id` | `parent_external_genre_id IS NULL OR parent_external_genre_id <> external_genre_id` | 自己参照禁止 |

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
| `source` | （code 未定義） | リソース一覧 / `item.source` 慣行 | MVP: `rakuten` | enum定義書には未 YAML 化。CHECK で MVP 固定 |
| — | — | — | — | 状態カラムなし |

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
| UPSERT | batch（BATCH-001 / BATCH-005） | `source` + `external_genre_id` 一致 | `genre_name`, `parent_external_genre_id`, `genre_level`, `is_leaf`, `fetched_at` | キー単位 Upsert | バッチ設計方針書 §8.2「ジャンル: upsert / 差分反映」 |
| SELECT | batch | 取得計画・ジャンル名解決 | — | — | BATCH-002 / BATCH-003 の対象ジャンル解決 |
| SELECT | batch / reco | `item` 結合時 | — | — | 間接参照 |
| DELETE | — | MVP では原則禁止 | — | — | 物理削除しない。未使用ジャンルは行を残し Batch 側で参照しない |

### 12.1 Upsert 疑似コード

```sql
INSERT INTO external_genre (
  external_genre_id, source, genre_name,
  parent_external_genre_id, genre_level, is_leaf, fetched_at
) VALUES (...)
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
| 保持期間 | 長期（外部参照マスタ） |
| 削除方式 | 物理 DELETE 原則禁止 |
| 削除条件 | — |
| 論理削除 | `is_active` 列なし。最新状態 Upsert 正本モデル（§5.4） |
| 履歴 | 保持しない。過去版は Raw / Staging / Log 側で必要に応じて追跡 |
| アーカイブ | MVP 対象外 |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `external_genre` |
| migration単位 | 1 テーブル = 1 migration（DDL Task） |
| 適用順序 | 物理ER §15: Item 群。`item` より **前**（`item.external_genre_id` LOGICAL 参照のため先行作成が望ましい） |
| rollback方針 | forward migration 主体。DROP は Human Review 必須 |
| 破壊的変更有無 | `no`（初回 CREATE） |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | batch（service role 経由） |
| 書き込み権限 | batch のみ。Online / reco 実行中の DML 更新なし |
| service role利用 | BATCH-001 / BATCH-005 の Upsert に限定 |
| 個人情報・機微情報 | 含まない |
| ログ出力制限 | ジャンル名を error ログに過剰出力しない |

---

## 16. テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | DDL適用 | CREATE TABLE / Index / FK / CHECK が定義どおり | migration |
| 2 | Upsert 冪等 | 同一 `source` + `external_genre_id` で再実行しても 1 行 | integration |
| 3 | 階層整合 | `parent_external_genre_id` が存在する親を指す（FK） | integration |
| 4 | CHECK | `genre_level` 範囲外・自己親参照が拒否される | migration |
| 5 | Batch 連携 | BATCH-001 後に BATCH-002 が対象ジャンルを解決できる | manual |
| 6 | 権限 | web client から Direct DB アクセス不可 | manual |

---

## 17. 未決事項

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| — | — | — | — | — | Human Review #494 にて No.1〜4 を決定済み（下記参照） |

### 17.1 Human Review 決定事項（Issue #494）

| No | 論点 | 決定内容 | 決定者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | `parent_external_genre_id` 物理 FK 採否 | **物理 FK ON（`ON DELETE RESTRICT`）** を採用 | Human | 物理ER §8 FK 表への追記は DDL Task または別 docs Task で整合 |
| 2 | `genre_level` MVP 上限 | **0〜5**（`chk_external_genre_level_range`）を採用 | Human | 運用中に楽天階層の実測で上限変更が必要になった場合は migration で CHECK を更新する |
| 3 | `is_active` 列の採否 | **不採用**。Upsert により **最新の外部ジャンル状態を正本として上書き保持** する（履歴管理しない） | Human | §5.4 正本モデル参照。batch / reco は常に最新行を参照 |
| 4 | root ジャンル（`genreId=0`）の保持 | **`external_genre_id = 0` の行を DB に保持** し、Batch 探索起点とする | Human | `parent_external_genre_id` は `NULL` |

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 物理ER | `docs/06_実装設計/database/物理ER.md` | Item系・FK・Index 方針 |
| 論理ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | §8.2 属性・§14.3 関係 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | §5 No.13・§5 補足 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | `source` code 将来 YAML 化 |
| 外部商品データ連携 | `docs/05_アプリケーション設計/アプリ/外部商品データ連携設計書.md` | §12 ジャンルデータ |
| バッチ設計方針書 | `docs/05_アプリケーション設計/アプリ/batch/バッチ設計方針書.md` | §8.2 / §8.6 Upsert 方針 |
| バッチ処理一覧 | `docs/05_アプリケーション設計/アプリ/batch/バッチ処理一覧.md` | BATCH-001 / BATCH-005 |

---

## 19. レビュー観点

- 論理ER §8.2・物理ER Item系・テーブル一覧 §5 と矛盾していない
- ジャンル階層（`parent_external_genre_id` / `genre_level` / `is_leaf`）と Batch Upsert 方針が明記されている
- `staging_genre` → `external_genre` Upsert 関係が §5.2 に整理されている
- `item.external_genre_id` / `item_popularity_signal.external_genre_id` との LOGICAL 参照が §8.2 に明記されている
- 外部商品データ連携設計書 §12.1 との列名差分が §5.3 で解消されている
- DDL Task が CREATE TABLE を起こせる粒度である
- secret や `.env` 実値が含まれていない
