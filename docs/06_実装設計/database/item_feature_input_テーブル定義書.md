# Item Feature Input テーブル定義書

## 1. ドキュメント情報

| 項目 | 内容 |
| ---- | ---- |
| ドキュメントID | `DB-TBL-MVP-item_feature_input` |
| ドキュメント名 | Item Feature Input テーブル定義書 |
| 対象システム | Gift Recommendation Service MVP |
| MVP対象 | `yes` |
| 作成日 | 2026-07-22 |
| 更新日 | 2026-07-22 |
| 関連 Issue | [#1568](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1568) / Epic [#1561](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1561) |

---

## 2. 概要

`item_feature_input` は、BATCH-011 が算出した **Feature 入力 hash / payload** を、複合 workflow（`workflow_call`）跨ぎでも参照できるよう永続化する **中間結果テーブル** である。

`item_feature.feature_input_hash`（最終派生行）への物理列書込は引き続き **BATCH-012** が行う。本テーブルは IF-DB-BATCH-012 の **中間永続正本** であり、`item_generation_queue` に hash 列は持たない（Queue 定義書 / #507 継承）。

---

## 3. 目的

- BATCH-011 → BATCH-012 の job 分離時に in-process handoff へ依存しない
- `feature_input_hash` / `feature_input_payload` の冪等 Upsert を可能にする
- `item_feature` 最終行とは責務を分離する（raw Feature 生成前の入力確定）

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `item_feature_input` |
| 論理テーブル名 | Item Feature Input |
| 分類 | Item派生データ系（中間） |
| 主な更新主体 | batch（BATCH-011） |
| 主な参照主体 | batch（BATCH-012） |
| MVP対象 | `yes` |
| IF | **IF-DB-BATCH-012** |
| migration | `supabase/migrations/20260722120000_item_feature_embedding_input.sql` |
| DDL 分割 | `db/ddl/d17_item_feature_embedding_input.sql` |

---

## 5. 用途・責務

| 観点 | 方針 |
| ---- | ---- |
| 書込 | BATCH-011 が hash / payload 算出成功時に Upsert（skip 時は省略可） |
| 読取 | BATCH-012 が `item_id` + `semantic_config_version_id` + `feature_input_hash` で検証・消費 |
| Queue | hash 列は持たない。任意で `item_generation_queue_id` を LOGICAL 記録 |
| 最終派生 | `item_feature` への hash 列書込は BATCH-012（本テーブルとは別） |

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `item_feature_input_id` | Item Feature Input ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK |
| 2 | `item_id` | Item ID | `uuid` | `yes` | — | `ON` | — | — | `item.item_id` |
| 3 | `semantic_config_version_id` | Semantic Config Version ID | `uuid` | `yes` | — | `ON` | — | — | 意味定義 version |
| 4 | `feature_input_hash` | Feature Input Hash | `varchar(64)` | `yes` | — | — | — | — | SHA-256 小文字 hex 64 |
| 5 | `feature_input_payload` | Feature Input Payload | `jsonb` | `yes` | — | — | — | — | canonicalize 前/後の構造化入力（object） |
| 6 | `batch_run_id` | Batch Run ID | `uuid` | `no` | — | `LOGICAL` | — | — | 算出 Batch Run（BATCH-011） |
| 7 | `item_generation_queue_id` | Item Generation Queue ID | `uuid` | `no` | — | `LOGICAL` | — | — | 対象 Queue 行（任意） |
| 8 | `computed_at` | Computed At | `timestamptz` | `yes` | — | — | — | — | hash 算出確定日時（UTC） |
| 9 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | 行作成 |
| 10 | `updated_at` | Updated At | `timestamptz` | `yes` | — | — | — | `now()` | Upsert 時更新 |

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | Index 名 |
| ---- | ---------- | -------- |
| PRIMARY KEY | `item_feature_input_id` | — |
| UNIQUE | `item_id`, `semantic_config_version_id`, `feature_input_hash` | `uq_item_feature_input_idempotent` |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK | 備考 |
| ------ | ------ | -- | ---- |
| `item_id` | `item.item_id` | `ON` / `RESTRICT` | |
| `semantic_config_version_id` | `semantic_config_version` | `ON` / `RESTRICT` | |
| `batch_run_id` | `batch_run_log` | `LOGICAL` | |
| `item_generation_queue_id` | `item_generation_queue` | `LOGICAL` | |

---

## 9. CHECK / Index

| 制約 | 内容 |
| ---- | ---- |
| `chk_item_feature_input_hash_format` | 64 hex |
| `chk_item_feature_input_payload_object` | `jsonb` object |
| Indexes | lookup / hash / batch_run / queue |

---

## 10. Upsert 方針

同一冪等キーでの再実行は Upsert（`feature_input_payload` / `computed_at` / `updated_at` / 任意 trace 列を更新）。

---

## 11. セキュリティ・ログ

- `feature_input_payload` に secret / 認証情報を載せない
- ログには `feature_input_hash` 全文を出さず、先頭数文字 + 省略可
- Public API 非公開

---

## 12. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-22 | 初版（E2 T2 / #1568。Human 確定: IF-DB-BATCH-012 永続化） |
