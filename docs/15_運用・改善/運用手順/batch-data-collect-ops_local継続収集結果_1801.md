# batch-data-collect-ops local継続収集結果（#1801）

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 関連Issue | #1801（親Epic #1798 / 統括 #1745） |
| 関連PR | #1807 |
| 前提Decision | [本格収集運用枠](../../../ai-logs/human-decisions/2026-07-31-batch-data-collect-ops-plan.md) / [オーケストレータ導入ゲート](../../../ai-logs/human-decisions/2026-08-01-local-batch-orchestrator-gate.md) / [fetch_plan](../../../ai-logs/human-decisions/2026-07-31-rakuten-fetch-mvp-fetch-plan.md) |
| 記録日 | 2026-08-01 |
| 実行経路 | `scripts/batch/local_daily_orchestrator.sh --live-rakuten`（個別CLI本線化なし） |
| 段階 | 段階1（進行条件充足・継続中）。Human方針: **継続**（途中完了例外は採らない）。Planned Start 前の早期着手を承認 |

secret・token・APIキー・egress IP・`DATABASE_URL`・Object Storage 実値は本ドキュメントに含めない。

---

## 2. 着手ゲート

| ゲート | 結果 |
| ------ | ---- |
| 運用枠 Decision decided | 充足 |
| local-orchestrator-impl（#1804 / PR #1806）親Epic反映 | 充足 |
| egress IP 照合 | MATCH（値は非記載） |
| worktree `.env` | メイン `.env` への symlink（gitignore） |
| 早期 live 開始 | Human 承認（2026-08-01） |
| Object Storage live | Human が endpoint 実値投入後、`object_storage_live_verify` **Go**（2026-08-01） |

---

## 3. 親シェル最小修正（収集阻害解消）

| 項目 | 内容 |
| ---- | ---- |
| genre 伝播 | `--genre-ids`（既定 `100005`）・`--no-update-sort`・`--max-qps` を追加。#1765 Ranking実測に整合 |
| job_run_id | 葉ごとに UUID 発行。`pipeline_batch_run_id` を複数葉の `batch_run_log` PK に共用しない（007/008 UniqueViolation 解消） |
| live OS | daily/weekly の 001/002 にも `--live-object-storage` を付与 |

---

## 4. Run記録

### 4.1 失敗 Run（genre未指定）

| 項目 | 内容 |
| ---- | ---- |
| 時刻 | 2026-08-01 14:25 JST 付近 |
| `pipeline_batch_run_id` | `fa67f2b8-406a-40dc-bdc5-07435f2cf122` |
| 結果 | FAILED at `ranking_snapshot` |
| 原因 | Ranking 対象ジャンル不正（親シェルが genre 未伝播） |

### 4.2 失敗 Run（Object Storage プレースホルダ）

| 項目 | 内容 |
| ---- | ---- |
| 時刻 | 2026-08-01 14:41 JST 付近 |
| `pipeline_batch_run_id` | `64676aae-be0a-4409-b948-7cda1de1dfbe` |
| BATCH-002 | succeeded（`100005`） |
| BATCH-003 | failed（`GRS-RAW-001` / HTTP 400 / `Project not specified.`） |
| 原因 | `OBJECT_STORAGE_ENDPOINT` が `.env.example` 系プレースホルダのまま（#1765 §4.6 と同症状） |

### 4.3 段階1 Run（OS復旧後・途中 UniqueViolation → 再開成功）

| 項目 | 内容 |
| ---- | ---- |
| 時刻 | 2026-08-01 14:50〜14:51 JST |
| `pipeline_batch_run_id` | `531b6cbc-41e7-4052-a2e0-61ac1e60167a` |
| ノブ | `pages_per_run=10` / `cursors_per_run=1` / `genre_ids=100005` / `max_qps=1` / `no_update_sort` |
| BATCH-002〜006 | succeeded（002 `storage_backend=http`、003 `pages=1 budget_stopped=True`） |
| BATCH-007 初回 | failed（`batch_run_log_pkey` UniqueViolation。pipeline ID 共用が原因） |
| 修正後再開 | `--from-step item_apply` で 007/008/017 **succeeded**。scenario **SUCCEEDED** |
| 429 | なし |

### 4.4 段階1 Run（通し成功）

| 項目 | 内容 |
| ---- | ---- |
| 時刻 | 2026-08-01 14:51 JST |
| `pipeline_batch_run_id` | `7b6c491e-db87-4d6b-b060-40f72b40a716` |
| ノブ | 同上 |
| 結果 | local-daily **SUCCEEDED**（002→003→005→006→007→008→017 すべて succeeded） |
| BATCH-003 | `pages=1 budget_stopped=True`（予算10に対し1ページで停止。cursor/route 側の進行量） |
| 429 | なし |

### 4.5 段階1 Run（追加・通し成功）

| 項目 | 内容 |
| ---- | ---- |
| 時刻 | 2026-08-01 15:17 JST |
| `pipeline_batch_run_id` | `3174f140-b994-45ea-808d-cedfd1d224b5` |
| ノブ | 同上 |
| 結果 | local-daily **SUCCEEDED**（002→003→005→006→007→008→017） |
| BATCH-003 | `pages=1 budget_stopped=True` / 429 なし |
| 備考 | AI Review must 対応（段階1追加1 Run）＋Human継続方針の明示後に実施 |

---

## 5. §5.3.5 見直し

| 項目 | 内容 |
| ---- | ---- |
| 見直し時点（運用枠） | 段階2完了、または本格収集開始から7日のどちらか早い方 |
| 現状 | 段階1進行条件は充足。段階2未着手のため見直し時点未達 |
| 暫定 | 閾値変更なし（**維持**） |

---

## 6. 停止 / 再開

| 項目 | 内容 |
| ---- | ---- |
| Object Storage ブロッカー | **解消**（Human endpoint 実値投入） |
| Human方針 | **方針 B**（2026-08-01）: #1801 は段階1までで区切り、**reopen しない**。段階2〜4＋§5.3.5本見直しは新 Task **#1808** で継続 |
| 現在 | 段階1進行条件充足。段階2以降は #1808（Human が live 実行。AI は記録同期・最小修正・PR/Review） |
| 段階2以降の実行主体 | **Human**（`--live-rakuten`）。AI は実行しない |
| 再開コマンド例（段階2・Human） | `./scripts/batch/local_daily_orchestrator.sh --live-rakuten --genre-ids 100005 --pages-per-run=60 --max-qps 1` |

段階2以降の収集・§5.3.5本見直しの作業計画・Branch・PR は **#1808**（`chore/task-1808-stage2-to4-threshold-review`）を正とする。本結果docsへの Run 追記は #1808 側で継続してよい。

---

## 7. 累計カウンタ（キャンペーン）

| 指標 | 値 |
| ---- | ---- |
| 本格収集開始日 | 2026-08-01 |
| 期間上限 | 開始から最大7日、または BATCH-003 累計 Run 20回 |
| BATCH-003 成功 Run 累計 | **3**（`531b6cbc-…` / `7b6c491e-…` / `3174f140-…`） |
| 段階1 進行条件 | 2〜3 Run・429なし・失敗なし・ログ追跡可能 → **充足** |
| 段階2移行 | 新 Task **#1808** で着手（通常継続ノブ `pages_per_run=60`。Human live 実行） |
| キャンペーン完了 | **未完了**（段階2〜4・§5.3.5本見直しは #1808） |

---

## 8. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-08-01 | 初版。ゲート確認・genre伝播・OSプレースホルダ停止を記録 |
| 2026-08-01 | OS復旧後の段階1成功・job_run_id UniqueViolation修正・通し SUCCEEDED を追記 |
| 2026-08-01 | Human継続方針・段階1追加Run（累計3）・進行条件充足を追記 |
| 2026-08-01 | 方針B反映。段階2以降は新 Task #1808 / Human live 実行へ引き継ぎ |
