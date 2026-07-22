# Item Embedding Input テーブル定義書

## 1. ドキュメント情報

| 項目 | 内容 |
| ---- | ---- |
| ドキュメントID | `DB-TBL-MVP-item_embedding_input` |
| ドキュメント名 | Item Embedding Input テーブル定義書 |
| 対象システム | Gift Recommendation Service MVP |
| MVP対象 | `yes` |
| 作成日 | 2026-07-22 |
| 更新日 | 2026-07-22 |
| 関連 Issue | [#1568](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1568) / Epic [#1561](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1561) |

---

## 2. 概要

`item_embedding_input` は、BATCH-014 が算出した **`embedding_input_hash` / `item_text_context`** を、複合 workflow 跨ぎでも参照できるよう永続化する **中間結果テーブル** である。

`item_embedding.embedding_input_hash`（最終派生行）への物理列書込は引き続き **BATCH-015**（IF-VEC-BATCH-001）が行う。本テーブルは IF-DB-BATCH-015 の **中間永続正本** であり、`item_generation_queue` に hash 列は持たない。

---

## 3. 目的

- BATCH-014 → BATCH-015 の job 分離時に in-process handoff へ依存しない
- Embedding API 入力に必要な `item_text_context` を再構築せず消費できる
- `item_embedding` 最終行とは責務を分離する

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `item_embedding_input` |
| 論理テーブル名 | Item Embedding Input |
| 分類 | Item派生データ系（中間） |
| 主な更新主体 | batch（BATCH-014） |
| 主な参照主体 | batch（BATCH-015） |
| MVP対象 | `yes` |
| IF | **IF-DB-BATCH-015** |
| migration | `supabase/migrations/20260722120000_item_feature_embedding_input.sql` |
| DDL 分割 | `db/ddl/d17_item_feature_embedding_input.sql` |

---

## 5. 用途・責務

| 観点 | 方針 |
| ---- | ---- |
| 書込 | BATCH-014 が hash / context 算出成功時に Upsert（skip 時は省略可） |
| 読取 | BATCH-015 が `item_id` + `model_version_id` + `embedding_input_hash` で検証・消費 |
| `item_text_context` | **canonicalize 済みテキスト全文を永続化**（Embedding 入力に必須。digest のみでは不足） |
| Queue | hash 列は持たない。任意で `item_generation_queue_id` を LOGICAL 記録 |
| 最終派生 | `item_embedding` への hash 列書込は BATCH-015 |

### 5.1 Human 判断メモ（採用案）

| 論点 | 本定義の採用 | 備考 |
| ---- | ------------ | ---- |
| テーブル名 | `item_embedding_input` | Human Review で確認 |
| context 保存粒度 | **全文（canonical text）** | digest のみは 015 再構築が必要になるため非採用（推奨） |
| TTL / パージ | **未確定** | 運用ポリシーは別 Task。MVP は永続保持 |

---

## 6. カラム定義

| No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
| 1 | `item_embedding_input_id` | Item Embedding Input ID | `uuid` | `yes` | `yes` | — | `yes` | `gen_random_uuid()` | サロゲート PK |
| 2 | `item_id` | Item ID | `uuid` | `yes` | — | `ON` | — | — | `item.item_id` |
| 3 | `model_version_id` | Model Version ID | `uuid` | `yes` | — | `ON` | — | — | Embedding `model_version` |
| 4 | `embedding_source_type` | Embedding Source Type | `text` | `yes` | — | — | — | `'item_text_context'` | MVP 固定 |
| 5 | `embedding_input_hash` | Embedding Input Hash | `varchar(64)` | `yes` | — | — | — | — | SHA-256 小文字 hex 64 |
| 6 | `item_text_context` | Item Text Context | `text` | `yes` | — | — | — | — | canonicalize 済み Embedding 入力テキスト |
| 7 | `batch_run_id` | Batch Run ID | `uuid` | `no` | — | `LOGICAL` | — | — | 算出 Batch Run（BATCH-014） |
| 8 | `item_generation_queue_id` | Item Generation Queue ID | `uuid` | `no` | — | `LOGICAL` | — | — | 対象 Queue 行（任意） |
| 9 | `computed_at` | Computed At | `timestamptz` | `yes` | — | — | — | — | hash 算出確定日時（UTC） |
| 10 | `created_at` | Created At | `timestamptz` | `yes` | — | — | — | `now()` | 行作成 |
| 11 | `updated_at` | Updated At | `timestamptz` | `yes` | — | — | — | `now()` | Upsert 時更新 |

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | Index 名 |
| ---- | ---------- | -------- |
| PRIMARY KEY | `item_embedding_input_id` | — |
| UNIQUE | `item_id`, `model_version_id`, `embedding_input_hash` | `uq_item_embedding_input_idempotent` |

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK | 備考 |
| ------ | ------ | -- | ---- |
| `item_id` | `item.item_id` | `ON` / `RESTRICT` | |
| `model_version_id` | `model_version.model_version_id` | `ON` / `RESTRICT` | Embedding モデル |
| `batch_run_id` | `batch_run_log` | `LOGICAL` | |
| `item_generation_queue_id` | `item_generation_queue` | `LOGICAL` | |

---

## 9. CHECK / Index

| 制約 | 内容 |
| ---- | ---- |
| `chk_item_embedding_input_source_type` | `item_text_context` 固定 |
| `chk_item_embedding_input_hash_format` | 64 hex |
| `chk_item_embedding_input_context_nonempty` | trim 後長さ > 0 |
| Indexes | lookup / hash / batch_run / queue |

---

## 10. Upsert 方針

同一冪等キーでの再実行は Upsert（`item_text_context` / `computed_at` / `updated_at` / 任意 trace 列を更新）。

---

## 11. セキュリティ・ログ

- ログに `item_text_context` の商品全文ダンプを出さない
- ログに `embedding_input_hash` 全文を出さず、先頭数文字 + 省略可
- Public API 非公開
- retention / 個人情報観点のパージ方針は Human 判断待ち（§5.1）

---

## 12. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-22 | 初版（E2 T2 / #1568。Human 確定: IF-DB-BATCH-015 永続化） |
