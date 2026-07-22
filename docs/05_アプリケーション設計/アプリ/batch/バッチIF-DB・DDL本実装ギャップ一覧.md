# バッチIF-DB・DDL本実装ギャップ一覧

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | E2 棚卸し正本（docs） |
| 対象 | IF-DB-BATCH-001〜017 / 020 / 021 / IF-VEC-BATCH-001（001〜017 中心） |
| 作成日 | 2026-07-22 |
| 更新日 | 2026-07-22（Human 確定反映） |
| 関連 Epic | [#1561](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1561) |
| 関連 Task | [#1562](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1562) |
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
| 物理テーブル / migrations | initial + 増分 **4 本**。主要テーブルは概ね存在 |
| `apps/batch` DB 書込 | **ScaffoldDbWriter / in-memory repositories のみ**（実クライアント未配線） |
| CLI | 多くが `--scaffold-demo` 以外で未完了経路 |
| 019 出力物理 | migration に CREATE なし（**E2 除外**） |
| 旧 OPEN #102/#133 | **本 Epic（#1561）へ寄せ、not planned でクローズ**（Human 確定・2026-07-22） |
| #109 / #136 | E0 で **E2取込**。T2（列差分棚卸し必須）と突合 |

**§4 との対応（要約根拠）:** マトリクス上、専用テーブル欠落は **012 / 015 / 019** のみ。それ以外の主対象テーブルは migration 上に存在感あり。

---

## 3. migration 概観（事実）

| ファイル | 概要 |
| -------- | ---- |
| `20260617120000_initial_schema.sql` | 初期スキーマ（主要 batch テーブル含む） |
| `20260702120000_matching_config.sql` | `matching_config` |
| `20260708120000_metric_log.sql` | `metric_log` |
| `20260715120000_item_active_status_candidate.sql` | `item_active_status_candidate` |

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
| IF-DB-BATCH-012 | feature_input_hash / queue | **専用テーブルなし**（現状） | in-memory handoff | **Human 確定: 永続テーブル/列を追加**（T2） |
| IF-DB-BATCH-013 | `item_feature` | initial にあり | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-014 | normalized / `item_meaning` | initial（列・テーブル） | ScaffoldDbWriter / in-memory | |
| IF-DB-BATCH-015 | embedding_input_hash / context | **専用テーブルなし**（現状） | in-memory handoff | **Human 確定: 永続テーブル/列を追加**（T2） |
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
| C. Handoff-only IF（現状） | 012 / 015 | 専用物理なし。**Human 確定で永続化へ移行**（T2 で DDL） |
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
| T2 | DDL 不足分（001〜017） | **列差分の追加棚卸しを必須**。定義あり・migration なし／列差分に加え、**012 / 015 の永続テーブル・列追加**を含む。**019 除外** | 破壊的変更は承認必須 |
| T3 | DB 接続基盤 | `DbWriter` 実実装 + Scaffold 切替 | secret は env 名のみ |
| T4a | IF stub 解除 Wave A | 001〜008 + 020/021（取込・Item） | 範囲確認 |
| T4b | IF stub 解除 Wave B | 009〜017 + VEC | 012/015 は T2 永続化後に解除 |
| T5 | UT / 境界 | Protocol 互換・scaffold 回帰。実 DB は local/CI 限定 | — |

**推奨着手順（Human 確定）:** T1（完了後）→ **T2（列差分棚卸し必須）** → T3 → T4a → T4b → T5。

---

## 8. Human 確定事項（2026-07-22）

| No | 確認事項 | 確定内容 |
| -- | -------- | -------- |
| 1 | IF-DB-BATCH-012 / 015 | **永続テーブル/列を追加する**（handoff のままにしない） |
| 2 | stub 解除順 | **Wave A → B** でよい |
| 3 | #102 / #133 の重複整理 | **本 Epic（#1561）へ寄せ、旧 Issue を not planned** |
| 4 | T2（DDL 不足分） | **列差分の追加棚卸しを必須**とする（「現状ほぼ不要」とはしない） |

---

## 9. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-22 | 初版（E2 inventory / #1562） |
| 2026-07-22 | AI Review 対応: §4 stub 列の明示化、§2 要約根拠・§4 列差分注記を追加 |
| 2026-07-22 | Human 確定反映（012/015 永続化、Wave A→B、#102/#133 not planned、T2 列差分棚卸し必須） |
