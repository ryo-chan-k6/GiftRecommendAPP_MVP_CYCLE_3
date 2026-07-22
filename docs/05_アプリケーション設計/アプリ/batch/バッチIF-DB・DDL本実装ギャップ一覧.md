# バッチIF-DB・DDL本実装ギャップ一覧

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | E2 棚卸し正本（docs） |
| 対象 | IF-DB-BATCH-001〜017 / 020 / 021 / IF-VEC-BATCH-001（001〜017 中心） |
| 作成日 | 2026-07-22 |
| 更新日 | 2026-07-22（T2 列差分棚卸し・012/015 永続 DDL 反映） |
| 関連 Epic | [#1561](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1561) |
| 関連 Task | [#1562](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1562)（T1） / [#1568](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1568)（T2） |
| 先行 | E0 ギャップ一覧 / E1 親 workflow（#1560 MERGED） |

### 1.1 目的

IF-DB × テーブル定義 × migrations × `apps/batch` stub の現状を突合し、E2 後続（DDL 不足分・接続基盤・stub 解除・UT）の Human 判断材料を正本化する。

### 1.2 本ドキュメントでやらないこと

| out of scope | 理由 |
| ------------ | ---- |
| DDL / migration の新規適用・破壊的変更 | 後続 Task + Human 承認 |
| `ScaffoldDbWriter` 実接続実装 | 後続 Task |
| repositories stub 解除コード | 後続 Task |
| 親 / 複合 workflow 改修 | E1 完了・本 Epic 外 |
| 外部 API 本接続 | E3 |
| BATCH-018/019 出力物理 DDL 本格整備 | Human 確定どおり後回し |

### 1.3 区分

| 区分 | 意味 |
| ---- | ---- |
| 事実 | 正本 docs・実ファイル・Issue 状態から確認 |
| 推論 | 事実からの影響・推奨 |
| 決定事項 | Human が明示採用した方針 |
| Human 判断待ち | 本ドキュメントでは断定しない（残があれば） |

---

## 2. 30秒サマリ（事実）

| 項目 | 状態 |
| ---- | ---- |
| IF-DB（001〜017,+020/021,+VEC） | インターフェース一覧に定義あり |
| 物理テーブル / migrations | initial + 増分 **5 本**（D17: `item_feature_input` / `item_embedding_input` 追加）。主要テーブルは概ね存在 |
| `apps/batch` DB 書込 | **ScaffoldDbWriter / in-memory repositories のみ**（実クライアント未配線） |
| CLI | 多くが `--scaffold-demo` 以外で未完了経路 |
| 019 出力物理 | migration に CREATE なし（**E2 除外**） |
| 旧 OPEN #102/#133 | **本 Epic（#1561）へ寄せ、not planned でクローズ**（Human 確定・2026-07-22） |
| #109 / #136 | E0 で **E2取込**。T2（列差分棚卸し必須）と突合 |

**§4 との対応（要約根拠）:** マトリクス上、専用テーブル欠落は **019** のみ（E2 除外）。012 / 015 は T2 で中間永続テーブルを追加。

---

## 3. migration 概観（事実）

| ファイル | 概要 |
| -------- | ---- |
| `20260617120000_initial_schema.sql` | 初期スキーマ（主要 batch テーブル含む） |
| `20260702120000_matching_config.sql` | `matching_config` |
| `20260708120000_metric_log.sql` | `metric_log` |
| `20260715120000_item_active_status_candidate.sql` | `item_active_status_candidate` |
| `20260722120000_item_feature_embedding_input.sql` | **D17** `item_feature_input` / `item_embedding_input`（#1568） |

**補足:** `db/ddl/` に分割 SQL がある。適用正本は `supabase/migrations/` と DDL バッチ分割表を優先。

---

## 4. IF × テーブル × migration × stub マトリクス（事実）

本節は **テーブル有無（migration 上の存在感）中心**である。列差分の追加棚卸しは §8 Human 確定どおり **T2 で必須**とする。

| IF ID | 主対象（一覧） | migration 上の存在感 | apps/batch stub | 備考 |
| ----- | -------------- | -------------------- | --------------- | ---- |
| IF-DB-BATCH-001 | `batch_run_log` | initial にあり | ScaffoldDbWriter / in-memory | Obs 共通 |
| IF-DB-BATCH-002 | `api_call_log` | initial にあり | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-003 | `fetch_cursor` | initial にあり | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-004 | `raw_product_metadata` | initial にあり | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-005 | staging_* | initial にあり | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-006 | `product_diff_result` | initial にあり | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-007 | `item` / image / review | initial にあり | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-008 | `ranking_snapshot` / popularity | initial にあり | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-009 | `item.active_status` | initial（列） | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-010 | `item_generation_queue` | initial にあり | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-011 | `item_semantic` | initial にあり | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-012 | `item_feature_input`（中間） | D17 migration あり | in-memory（読取未配線） | T2 で CREATE。最終列は `item_feature`（BATCH-012） |
| IF-DB-BATCH-013 | `item_feature` | initial にあり | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-014 | normalized / `item_meaning` | initial（列・テーブル） | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-015 | `item_embedding_input`（中間） | D17 migration あり | in-memory（読取未配線） | T2 で CREATE。最終列は `item_embedding`（BATCH-015） |
| IF-VEC-BATCH-001 | `item_embedding` | initial にあり | ScaffoldDbWriter / in-memory | Embedding API は E3 |
| IF-DB-BATCH-016 | distribution metric 3 種 | initial にあり | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-017 | `item_import_summary` | initial にあり | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-020/021 | `item_active_status_candidate` | 増分 migration あり | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-018 | evaluation_* | initial にあり | scaffold（参考） | **E2 本格化除外** |
| IF-DB-BATCH-019 | feedback_analysis_* | **CREATE なし** | 明示 stub | **E2 除外** |

---

## 5. stub 種別（事実）

| 種別 | 代表 | 意味 |
| ---- | ---- | ---- |
| A. ScaffoldDbWriter | `infrastructure/db/writer.py` | 書込をメモリ記録のみ |
| B. In-memory repositories | 各 `application/*/repositories.py` | テーブル相当を dict/list |
| C. Handoff-only IF（旧） | 012 / 015 | **T2 で中間永続テーブル化済み**。アプリ stub 解除は T4b |
| D. 論理契約 stub | 019 | 物理未整備（E2 外） |
| E. 外部/生成 Scaffold | Rakuten / Embedding / LLM adapter | E3 領域 |

**横断事実:** `psycopg` / SQLAlchemy / asyncpg 等の本番書込クライアントは `apps/batch` に未配線（調査時点）。

---

## 6. OPEN Issue 突合（事実 + Human 確定）

調査日: 2026-07-22（再確認・確定反映）

| Issue | 状態 | タイトル | E0 Human 確定 | E2 での扱い（決定事項） |
| ----- | ---- | -------- | ------------- | ---------------------- |
| #102 | **CLOSED (not planned)** | [Epic]: アプリ機能実装設計（db） | E2取込 | **本 Epic（#1561）へ寄せて not planned** |
| #109 | OPEN | [Task]: DDL作成 | E2取込 | 後続 T2（列差分棚卸し必須）と突合。不足が無ければクローズ案 |
| #133 | **CLOSED (not planned)** | [Epic]: DB構築 | E2取込 | **本 Epic（#1561）へ寄せて not planned** |
| #136 | OPEN | [Task]: マイグレーションファイル作成 | E2取込 | T2 の列差分棚卸し結果で不足分のみ後続 Task |

**補足:** #102 / #133 は本ドキュメント §8 Human 確定に基づき **not planned クローズ済み**（2026-07-22）。Projects Status の手動更新が必要な場合は Human が確認する（bot token に `project` scope なし）。

---

## 7. 後続 Task 分割案（推論 + Human 確定反映）

| 順 | 推奨 Task | 内容 | Human 関与 |
| -- | --------- | ---- | ---------- |
| T1 | **本 Task（棚卸し）** | 本 docs | Review |
| T2 | DDL 不足分（001〜017） | **完了（#1568）**: 列差分棚卸し + 012/015 永続 DDL | Review |
| T3 | DB 接続基盤 | `DbWriter` 実実装 + Scaffold 切替 | secret は env 名のみ |
| T4a | IF stub 解除 Wave A | 001〜008 + 020/021（取込・Item） | 範囲確認 |
| T4b | IF stub 解除 Wave B | 009〜017 + VEC | 012/015 は T2 永続化後に解除 |
| T5 | UT / 境界 | Protocol 互換・scaffold 回帰。実 DB は local/CI 限定 | — |

**推奨着手順（Human 確定）:** T1（完了）→ **T2（完了・本 PR）** → T3 → T4a → T4b → T5。

---

## 8. Human 確定事項（2026-07-22）

| No | 確認事項 | 確定内容 |
| -- | -------- | -------- |
| 1 | IF-DB-BATCH-012 / 015 | **永続テーブル/列を追加する**（handoff のままにしない）→ T2 で `item_feature_input` / `item_embedding_input` を追加 |
| 2 | stub 解除順 | **Wave A → B** でよい |
| 3 | #102 / #133 の重複整理 | **本 Epic（#1561）へ寄せ、旧 Issue を not planned** |
| 4 | T2（DDL 不足分） | **列差分の追加棚卸しを必須**とする（「現状ほぼ不要」とはしない）→ §10 に実施結果 |

---

## 9. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-22 | 初版（E2 inventory / #1562） |
| 2026-07-22 | AI Review 対応: §4 stub 列の明示化、§2 要約根拠・§4 列差分注記を追加 |
| 2026-07-22 | Human 確定反映（012/015 永続化、Wave A→B、#102/#133 not planned、T2 列差分棚卸し必須） |
| 2026-07-22 | T2（#1568）: 列差分棚卸し結果・D17 migration・定義書・仕様追記を反映 |

---

## 10. T2 列差分棚卸し結果（事実・2026-07-22 / #1568）

調査方法: 各テーブル定義書 §6 カラム定義 vs `supabase/migrations/**` の `CREATE TABLE` 列名突合。

### 10.1 サマリ

| 判定 | 件数（テーブル単位） | 扱い |
| ---- | -------------------: | ---- |
| match（列一致） | 25 | 追加 DDL 不要 |
| dedicated_missing → **CREATE 済み（本 Task）** | 2（012/015） | D17 |
| migration_missing（意図的除外） | 1（`staging_attribute`） | MVP DDL 不含（物理ER §17 No.7）。**本 Task で CREATE しない** |
| 019 | 除外 | E2 外 |

### 10.2 IF 別詳細

| IF ID | テーブル | 判定 | 詳細 |
| ----- | -------- | ---- | ---- |
| IF-DB-BATCH-001 | `batch_run_log` | match | 14 cols |
| IF-DB-BATCH-002 | `api_call_log` | match | 18 cols |
| IF-DB-BATCH-003 | `fetch_cursor` | match | 11 cols |
| IF-DB-BATCH-004 | `raw_product_metadata` | match | 15 cols |
| IF-DB-BATCH-005 | `staging_item` / `staging_item_image` / `staging_ranking_signal` / `staging_genre` | match | 各列一致 |
| （参考） | `staging_attribute` | migration_missing（意図的） | 定義書のみ。DDL 分割表 D05 △ |
| IF-DB-BATCH-006 | `product_diff_result` | match | 10 cols |
| IF-DB-BATCH-007 | `item` / `item_image` / `item_review_summary` | match | |
| IF-DB-BATCH-008 | `ranking_snapshot` / `item_popularity_signal` | match | |
| IF-DB-BATCH-009 | `item`（`active_status` 含む） | match | |
| IF-DB-BATCH-010 | `item_generation_queue` | match | 9 cols。hash 列なし（継承） |
| IF-DB-BATCH-011 | `item_semantic` | match | 5 cols |
| IF-DB-BATCH-012 | `item_feature_input` | **T2 CREATE** | D17 / 定義書追加 |
| IF-DB-BATCH-013 | `item_feature` | match | 9 cols（`feature_input_hash` 含む） |
| IF-DB-BATCH-014 | `item_meaning` | match | 9 cols |
| IF-DB-BATCH-015 | `item_embedding_input` | **T2 CREATE** | D17 / 定義書追加 |
| IF-VEC-BATCH-001 | `item_embedding` | match | 7 cols（`embedding_input_hash` 含む） |
| IF-DB-BATCH-016 | distribution metric 3 種 | match | |
| IF-DB-BATCH-017 | `item_import_summary` | match | 15 cols |
| IF-DB-BATCH-020/021 | `item_active_status_candidate` | match | 15 cols |

### 10.3 T2 成果物（事実）

| 成果物 | パス |
| ------ | ---- |
| migration | `supabase/migrations/20260722120000_item_feature_embedding_input.sql` |
| DDL 分割 | `db/ddl/d17_item_feature_embedding_input.sql` |
| 定義書 | `item_feature_input_テーブル定義書.md` / `item_embedding_input_テーブル定義書.md` |
| 仕様追記 | BATCH-011/012/014/015 §2.2 等 |
| IF 一覧 | IF-DB-BATCH-012 / 015 対象更新 |

### 10.4 Human Review 観点（T2）

| No | 観点 | 推奨案 |
| -- | ---- | ------ |
| 1 | テーブル名 | `item_feature_input` / `item_embedding_input` |
| 2 | `item_text_context` 保存粒度 | **canonical 全文**（digest のみは非推奨） |
| 3 | retention / パージ | **未確定**（別 Task） |
| 4 | `staging_attribute` CREATE | **しない**（既存 MVP 除外を維持） |
| 5 | DROP | **なし**（本 Task は加算のみ） |
