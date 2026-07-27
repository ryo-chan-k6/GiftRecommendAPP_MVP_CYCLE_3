# バッチIF-DB・DDL本実装ギャップ一覧

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | E2 棚卸し正本（docs） |
| 対象 | IF-DB-BATCH-001〜017 / 020 / 021 / IF-VEC-BATCH-001（001〜017 中心） |
| 作成日 | 2026-07-22 |
| 更新日 | 2026-07-27（#1635 Wave 1 / #1684: IF-013 + 011/012 claim/status） |
| 関連 Epic | [#1561](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1561) / 読取後続 [#1623](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1623) / 書込後続 [#1632](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1632) / [#1633](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1633) / [#1635](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1635) |
| 関連 Task | [#1562](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1562)（T1） / [#1568](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1568)（T2） / [#1576](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1576)（T3） / [#1579](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1579)（T4a） / [#1583](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1583)（T4b） / [#1588](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1588)（T5） |
| 先行 | E0 ギャップ一覧 / E1 親 workflow（#1560 MERGED） |

### 1.1 目的

IF-DB × テーブル定義 × migrations × `apps/batch` stub の現状を突合し、E2 後続（DDL 不足分・接続基盤・stub 解除・UT）の Human 判断材料を正本化する。

### 1.2 本ドキュメントでやらないこと

| out of scope | 理由 |
| ------------ | ---- |
| DDL / migration の新規適用・破壊的変更 | 後続 Task + Human 承認（T2 は加算 CREATE 済） |
| 親 / 複合 workflow 改修 | E1 完了・本 Epic 外 |
| 外部 API 本接続 | E3 |
| BATCH-018/019 出力物理 DDL 本格整備 | Human 確定どおり後回し |
| 代表以外の IF フル UPSERT・読取 SELECT | 読取 SELECT は [#1623](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1623) / [バッチDB読取・SELECT本実装ギャップ一覧](./バッチDB読取・SELECT本実装ギャップ一覧.md) |

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
| `apps/batch` DB 書込 | **T3: `PostgresDbWriter` + `create_db_writer`**。未設定 / `scaffold://` は `ScaffoldDbWriter`。**代表 IF は UPSERT 済**（T4a: 006/020、T4b: 012/015）。他 IF の repositories は in-memory のまま |
| CLI | **Wave A / Wave B は非 `--scaffold-demo` で `create_db_writer` 配線済**。読取 SELECT 本実装は [#1623](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1623)。IF-005 は [#1632](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1632) Wave 1+2 Epic Branch MERGED。**IF-007 item 系は [#1633](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1633) Wave 1（#1669）本配線**。**IF-009 / IF-021（BATCH-008）は #1633 Wave 2（#1671/#1672）Epic Branch MERGED**。**IF-013 + 011/012 claim/status は [#1635](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1635) Wave 1（#1684）本配線**。他 IF フル UPSERT は後続 |
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
| IF-DB-BATCH-005 | staging_* | initial にあり | **#1632 Wave 1+2 Epic Branch MERGED**: Wave 1（#1660/#1663）`staging_item` / `staging_item_image` UPSERT + `raw_product_metadata` UPDATE。Wave 2（#1666/#1667）`staging_ranking_signal` / `staging_genre` UPSERT + transform stub 解除。`external_genre` 非書込維持。develop 反映は Epic PR | |
| IF-DB-BATCH-006 | `product_diff_result` | initial にあり | **T4a**: `upsert_rows`（ON CONFLICT） | Wave A CLI 配線済み。読取 SELECT は未 |
| IF-DB-BATCH-007 | `item` / image / review | initial にあり | **#1633 Wave 1（#1669）**: `item` UPSERT `(source, external_item_code)`（`active_status`/`is_active`/`first_fetched_at`/`item_id` は DO UPDATE 対象外）+ `unchanged` は `update_rows`。`item_image` UPSERT `(item_id, image_url)` + 集合外 `delete_rows`。`item_review_summary` UPSERT `(item_id)`。偽 `sync_replace` write 廃止。`active_status` 本更新は Wave 2（IF-009） | 読取 SELECT は #1623 Wave C 済 |
| IF-DB-BATCH-008 | `ranking_snapshot` / popularity | initial にあり | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-009 | `item.active_status` | initial（列） | **#1633 Wave 2（#1671）**: BATCH-008 `update_rows`（`active_status` / `is_active`、equals `(source, external_item_code)`）。`write_rows` 禁止 | Wave 1 の item UPSERT とは分離 |
| IF-DB-BATCH-010 | `item_generation_queue` | initial にあり | **#1634 Wave 1（#1677）**: BATCH-009 `write_rows` INSERT（UUID PK）+ active `queued` の `queued_at` のみ `update_rows`。偽 `op=touch_queued_at` 廃止。claim / status / `item_semantic` は Wave 2（IF-011） | |
| IF-DB-BATCH-011 | `item_semantic` | initial にあり | **#1634 Wave 2（#1679）**: BATCH-010 claim `update_rows`（queued+semantic→processing）+ 終端 status `update_rows` + `item_semantic` UPSERT conflict `(item_id, semantic_config_version_id)`。成功時 processing 維持は DB no-op。偽 `op` 廃止。Rule-first 維持 | |
| IF-DB-BATCH-012 | `item_feature_input`（中間） | D17 migration あり | **T4b**: `upsert_rows`（E2 済。#1684 非対象） | T2 CREATE + Wave B UPSERT。読取 SELECT は後続 |
| IF-DB-BATCH-013 | `item_feature` | initial にあり | **#1635 Wave 1（#1684）**: BATCH-012 `upsert_rows` conflict `(item_id, semantic_config_version_id, feature_code, feature_input_hash, feature_normalization_version_id)` / update `(raw_feature_value, generated_at)`。claim/status は BATCH-011/012 共通（continue / keep_processing は DB no-op、feature claim・終端は `update_rows`）。偽 `op` 廃止 | IF-012 input は非変更 |
| IF-DB-BATCH-014 | normalized / `item_meaning` | initial（列・テーブル） | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-015 | `item_embedding_input`（中間） | D17 migration あり | **T4b**: `upsert_rows` | T2 CREATE + Wave B UPSERT。読取 SELECT は未 |
| IF-VEC-BATCH-001 | `item_embedding` | initial にあり | ScaffoldDbWriter / in-memory | Embedding API は E3 |
| IF-DB-BATCH-016 | distribution metric 3 種 | initial にあり | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-017 | `item_import_summary` | initial にあり | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-020/021 | `item_active_status_candidate` | 増分 migration あり | **T4a**: candidate UPSERT（IF-020 / BATCH-004）。**#1633 Wave 2（#1671）**: IF-021 相当 — applied/superseded/discarded は `update_rows`、Retention は `delete_rows`（detected 削除禁止、偽 `op=delete` write 廃止） | Wave A CLI 配線済み。IF-020 INSERT は本 Wave 非対象 |
| IF-DB-BATCH-018 | evaluation_* | initial にあり | scaffold（参考） | **E2 本格化除外** |
| IF-DB-BATCH-019 | feedback_analysis_* | **CREATE なし** | 明示 stub | **E2 除外** |

---

## 5. stub 種別（事実）

| 種別 | 代表 | 意味 |
| ---- | ---- | ---- |
| A. ScaffoldDbWriter | `infrastructure/db/writer.py` | 書込をメモリ記録のみ。`create_db_writer` の fallback |
| B. In-memory repositories | 各 `application/*/repositories.py` | テーブル相当を dict/list。**代表 IF（006/020/012/015）は T4a/T4b で UPSERT 解除**。他 IF は残存 |
| C. Handoff-only IF（旧） | 012 / 015 | **T2 で中間永続テーブル化**。**T4b で UPSERT 解除済**（読取 SELECT は後続） |
| D. 論理契約 stub | 019 | 物理未整備（E2 外） |
| E. 外部/生成 Scaffold | Rakuten / Embedding / LLM adapter | E3 領域 |
| F. PostgresDbWriter（T3） | `infrastructure/db/writer.py` | `DATABASE_URL` 実 URL 時。汎用 INSERT + **`upsert_rows`（T4a）** + **`update_rows` / `delete_rows`（#1632 Wave 1）**。代表 IF 配線は T4a/T4b。IF-005 staging は #1632 Wave 1+2 本配線済（Epic Branch）。**IF-007 item 系は #1633 Wave 1（#1669）本配線**。**IF-009 / IF-021（BATCH-008）は #1633 Wave 2 Epic Branch MERGED**。**IF-010 queue（BATCH-009）は #1634 Wave 1（#1677）本配線**。**IF-011 semantic（BATCH-010）は #1634 Wave 2（#1679）本配線（Epic Branch）**。**IF-013 item_feature + BATCH-011/012 claim/status は #1635 Wave 1（#1684）本配線（Epic Branch）** |

**横断事実:** `create_db_writer(database_url)` で Scaffold / Postgres を切替可能（reco `create_database_session` と同型）。Wave A/B CLI 配線済。**本番 SQL は代表 IF（006/020/012/015）配線済**。**IF-005 staging は #1632 Wave 1+2 Epic Branch MERGED**（item/image/import_status + ranking/genre）。**IF-007 item / item_image / item_review_summary は #1633 Wave 1（#1669）本配線**。**IF-009 / IF-021（BATCH-008）は #1633 Wave 1+2 Epic Branch MERGED**（develop は Epic PR）。**IF-010 queue（BATCH-009）は #1634 Wave 1（#1677）本配線**。**IF-011 semantic（BATCH-010）は #1634 Wave 2（#1679）本配線（Epic Branch）**。**IF-013 item_feature + BATCH-011/012 claim/status は #1635 Wave 1（#1684）本配線（Epic Branch）**。残 IF（014/016/017/VEC）は [#1635](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1635) Wave 2+。読取 SELECT は #1623。

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
| T3 | DB 接続基盤 | **完了（#1576）**: `PostgresDbWriter` + `create_db_writer`（Scaffold 切替）。repositories stub は T4 | Review |
| T4a | IF stub 解除 Wave A | **完了（#1579）**: `upsert_rows` + Wave A CLI 配線 + IF-006/020 UPSERT | Review |
| T4b | IF stub 解除 Wave B | **完了（#1583）**: Wave B CLI 配線 + IF-012/015 UPSERT | Review |
| T5 | UT / 境界 | **完了（#1588）**: Protocol / CLI 配線 / 代表 IF UPSERT / scaffold-demo 回帰。production DB 結合なし | Review |

**推奨着手順（Human 確定）:** T1〜T5 完了 → **Epic PR → develop（本作業）**。

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
| 2026-07-22 | T3（#1576）: `PostgresDbWriter` / `create_db_writer` 接続基盤を反映 |
| 2026-07-23 | T4a（#1579）: `upsert_rows`・Wave A CLI 配線・IF-006/020 UPSERT を反映 |
| 2026-07-23 | T4b（#1583）: Wave B CLI 配線・IF-012/015 UPSERT を反映 |
| 2026-07-23 | T4b（#1583）: §1.2 / §2 / §5 要約を T4a/T4b 後の実態に追随（Wave A/DDL 本体変更なし） |
| 2026-07-23 | T5（#1588）: UT 境界・CLI 配線・代表 IF・scaffold 回帰を反映 |
| 2026-07-24 | T5 完了反映。Epic PR → develop 準備 |
| 2026-07-27 | #1632 Wave 1（#1660）: IF-005 staging_item / image / import_status UPSERT 本配線 |
| 2026-07-27 | #1632 Wave 2（#1666）: IF-005 staging_ranking_signal / staging_genre UPSERT + transform stub 解除 |
| 2026-07-27 | #1633 Wave 2（#1671）: IF-009 / IF-021（BATCH-008）active_status `update_rows` + candidate `update_rows` / Retention `delete_rows` |
| 2026-07-27 | #1635 Wave 1（#1684）: IF-013 item_feature UPSERT + BATCH-011/012 claim/status `update_rows`（IF-012 非変更） |

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


---

## 11. T4a Wave A stub 解除進捗（事実・2026-07-23 / #1579）

| 項目 | 状態 |
| ---- | ---- |
| `DbWriter.upsert_rows` | Scaffold 記録 + Postgres `ON CONFLICT DO UPDATE` |
| `resolve_job_db_writer` | `--scaffold-demo` → Scaffold / それ以外 → `create_db_writer` |
| Wave A CLI 配線 | genre_sync / ranking_snapshot / item_pseudo_diff / raw_staging / product_diff / item_apply / item_active_status / item_recheck で `create_db_writer` |
| IF-006 | `product_diff_result` UPSERT（`(batch_run_id, external_item_code)`） |
| IF-020 | `item_active_status_candidate` UPSERT（`(batch_run_id, source, external_item_code)`） |
| 未実施（後続） | 003/008 フル UPSERT。**007 item 系は #1633 Wave 1（#1669）本配線済**（Epic Branch）。**009 / 021（BATCH-008）は #1633 Wave 1+2 Epic Branch MERGED**。**005 staging は #1632 Wave 1+2 Epic Branch MERGED**（develop は Epic PR） |

---

## 12. T4b Wave B stub 解除進捗（事実・2026-07-23 / #1583）

| 項目 | 状態 |
| ---- | ---- |
| Wave B CLI 配線 | item_generation_queue / item_semantic / item_feature / feature_normalization / feature_input_hash / item_embedding / embedding_input_hash / distribution_metrics / import_summary |
| IF-012 | `item_feature_input` UPSERT（`(item_id, semantic_config_version_id, feature_input_hash)`） |
| IF-015 | `item_embedding_input` UPSERT（`(item_id, model_version_id, embedding_input_hash)`）。`item_text_context` は canonical JSON 全文 |
| 未実施（後続） | **009 は #1633 Wave 2 Epic Branch MERGED（update_rows）**。**013 + 011/012 claim/status は #1635 Wave 1（#1684）本配線**。014/016/017/VEC フル UPSERT、読取 SELECT |

---

## 13. T5 UT / 境界進捗（事実・2026-07-23 / #1588）

| 項目 | 状態 |
| ---- | ---- |
| Protocol / factory | Scaffold / Postgres が `DbWriter` 構造を満たす UT |
| Wave A/B CLI 配線 | `__main__.py` が `create_db_writer` を呼ぶ AST 回帰 |
| 代表 IF UPSERT キー | 006/020/012/015 の conflict 形状を Scaffold upsert で固定 |
| scaffold-demo | product_diff / feature_input_hash / embedding_input_hash |
| production DB 結合 | **未実施**（方針どおり除外） |
| 次 | **Epic PR → develop**（#1561） |

---

## 14. #1632 Wave 2 IF-005 ranking/genre UPSERT 進捗（事実・2026-07-27 / #1666）

| 項目 | 状態 |
| ---- | ---- |
| `staging_ranking_signal` UPSERT | `upsert_rows` / conflict `(raw_metadata_id, rank)` |
| `staging_genre` UPSERT | `upsert_rows` / conflict `(raw_metadata_id, external_genre_id)` |
| transform stub 解除 | `item_ranking` / `genre_search` → Staging 候補生成 |
| validate | items 空でも ranking/genre があれば受理 |
| `external_genre` | **非書込維持**（BATCH-001 責務） |
| UT | `test_raw_staging.py` ranking/genre 成功書込 |
| 残 | develop 反映は Epic PR（#1632）の Human Review / merge |

---

## 15. #1633 Wave 2 IF-009 / IF-021（BATCH-008）進捗（事実・2026-07-27 / #1671/#1672 MERGED）

| 項目 | 状態 |
| ---- | ---- |
| IF-009 `item.active_status` | `update_rows`（set: `active_status` / `is_active`、equals: `(source, external_item_code)`） |
| IF-021 candidate applied | `update_rows`（set: `candidate_status` / `applied_at` / `updated_at`、datetime オブジェクト） |
| IF-021 candidate superseded/discarded | `update_rows`（set: `candidate_status` / `updated_at`） |
| IF-021 Retention DELETE | `delete_rows`（equals: `item_active_status_candidate_id`）。detected は削除禁止 |
| 偽 `op=delete` write | **廃止** |
| IF-020 candidate INSERT UPSERT | **非変更**（T4a / BATCH-004 維持） |
| UT | `test_item_active_status.py` / `test_item_active_status_retention.py`（update_calls / delete_calls） |
| 実 DB 疎通 | local postgres（127.0.0.1）で disposable item/candidate の update → select → delete cleanup 成功（secret 非出力）。Task Issue / PR 記録は後続 |
| Issue / PR | Wave 1 #1669/#1670 MERGED。Wave 2 #1671/#1672 MERGED。develop 反映は Epic PR（#1633） |
| 残 | develop 反映は Epic PR（#1633）の Human Review / merge |

---

## 16. #1635 Wave 1 IF-013 + BATCH-011/012 claim/status 進捗（事実・2026-07-27 / #1684）

| 項目 | 状態 |
| ---- | ---- |
| BATCH-011 claim continue | semantic+processing → **DB no-op**（偽 `op=continue_processing` 廃止） |
| BATCH-011 / 012 feature claim | `update_rows`（set: `queue_status=processing` / `started_at`、equals: id + `queued` + `generation_type=feature`）。`rows_affected==0` → None |
| BATCH-011 / 012 keep_processing | **DB no-op**（偽 `op=*_keep_processing` 廃止） |
| BATCH-011 / 012 終端 status | `update_rows`（偽 `op=update_status` 廃止） |
| IF-013 `item_feature` UPSERT | `upsert_rows` / conflict 5列 / update `(raw_feature_value, generated_at)`。payload に `op` / `normalized_feature_value` / `item_feature_id` なし |
| IF-012 `item_feature_input` | **非変更**（E2 T4b 維持。再実装しない） |
| UT | `test_feature_input_hash.py` / `test_item_feature.py`（upsert_calls / update_calls） |
| 実 DB 疎通 | Task 実装時に local/dev で disposable queue claim →（FK 充足時）item_feature upsert → cleanup（secret 非出力） |
| Issue / PR | Wave 1 #1684。develop 反映は Epic PR（#1635） |
| 残 | Wave 2+（IF-014 / VEC / metrics / summary）。Epic Branch 統合 |

