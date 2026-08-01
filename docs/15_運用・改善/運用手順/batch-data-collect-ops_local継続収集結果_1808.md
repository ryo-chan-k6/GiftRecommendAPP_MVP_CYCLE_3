# batch-data-collect-ops local継続収集結果（#1808）

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 関連Issue | #1808（親Epic #1798。先行 #1801 / PR #1807） |
| 前提 | [本格収集運用枠](../../../ai-logs/human-decisions/2026-07-31-batch-data-collect-ops-plan.md) / [段階1結果](./batch-data-collect-ops_local継続収集結果_1801.md) |
| 記録日 | 2026-08-01 |
| 実行主体 | **Human**（`--live-rakuten`）。AI は手順・記録同期・阻害時最小修正・PR/Review |
| 段階 | 段階2 **充足** → 段階3着手（`100003` weekly 途中失敗 → existing 連鎖 ID 修正） |

secret・token・APIキー・egress IP・接続文字列実値は記載しない。

---

## 2. 段階2（Human報告）

| 項目 | 内容 |
| ---- | ---- |
| ノブ | `pages_per_run=60` / `cursors_per_run=1`（既定） / `genre_ids=100005` / `max_qps=1` |
| コマンド | `./scripts/batch/local_daily_orchestrator.sh --live-rakuten --genre-ids 100005 --pages-per-run=60 --max-qps 1` |
| 結果 | **10回以上連続成功** |
| 429 | **なし** |
| 進行条件（運用枠: 3 Run以上・429なし） | **充足** |
| 個別 `pipeline_batch_run_id` | Human 環境ログに保持。本docsへは一覧未転記（必要時に追記） |

Human により段階2実行は停止済み（これ以上同ノブを回さない）。

---

## 3. 親シェル修正（段階3準備）

| 項目 | 内容 |
| ---- | ---- |
| 背景 | daily/weekly が同一 `--genre-ids` を BATCH-002 と BATCH-003 に渡すと、拡大ジャンル（`100000`/`100003`/`100004`）で Ranking が HTTP 400 |
| 対応 | `--ranking-genre-ids`（BATCH-002）と `--genre-ids`（BATCH-003 / weekly BATCH-001）を分離。Ranking 既定は `100005` のまま |
| 対象 | `scripts/batch/lib/local_orchestrator_common.sh` / `local_daily_orchestrator.sh` / `local_weekly_orchestrator.sh` / README |

---

## 4. 段階3（Human実行手順）

**1ジャンルずつ。同時 live 禁止。** 推奨順の一例: `100003` → `100004` → `100000`（Ranking は常に `100005`）。

### 4.1 初回（ジャンル未同期のとき）— weekly

```bash
cd /home/ryo-c/GitHub/GiftRecommendAPP_MVP_CYCLE_3_worktrees/chore-task-1808-stage2-to4-threshold-review
set -a && source .env && set +a
./scripts/batch/local_weekly_orchestrator.sh --live-rakuten \
  --genre-ids 100003 --ranking-genre-ids 100005 \
  --pages-per-run=60 --max-qps 1
```

### 4.2 日次継続 — daily

```bash
./scripts/batch/local_daily_orchestrator.sh --live-rakuten \
  --genre-ids 100003 --ranking-genre-ids 100005 \
  --pages-per-run=60 --max-qps 1
```

各ジャンルで安定したら次ジャンルへ。成功/失敗・429・`pipeline_batch_run_id` を AI へ共有すると本docsへ追記する。

---

## 5. 段階3 Run 記録

### 5.1 `100003` weekly（失敗・既存連鎖）

| 項目 | 内容 |
| ---- | ---- |
| コマンド | `local_weekly_orchestrator.sh --live-rakuten --genre-ids 100003 --ranking-genre-ids 100005 --pages-per-run=60 --max-qps 1` |
| `pipeline_batch_run_id`（シナリオ） | `acb725c7-87ac-4890-871f-2bfdcafef370` |
| BATCH-001 / 002 | succeeded |
| BATCH-003 | succeeded（`pages=1` `budget_stopped=True`） |
| import 連鎖（003後 005〜017） | succeeded |
| BATCH-004 | partially_succeeded（succeeded=15 failed=3）。429なし |
| 004後 raw_staging（BATCH-005） | **failed** `GRS-BAT-001` / `empty staging_plan` |
| シナリオ結果 | FAILED（subsequent steps not started） |

#### 原因（事実）

| 項目 | 内容 |
| ---- | ---- |
| BATCH-004 | Raw `object_key` に葉の `job_run_id` を埋める（`--batch-run-id` なし） |
| 当時の親シェル | 004 に葉 UUID、続く 005 にシナリオ `pipeline_batch_run_id` を渡していた |
| 結果 | 005 が 004 の Raw を選定できず empty plan |

#### 対応

| 項目 | 内容 |
| ---- | ---- |
| 修正 | `lor_run_existing_item_chain` で GHA existing-item の `resolve-run-id` 相当を別発行し、004〜017 で同一 business ID を使う（シナリオ pipeline とは分離） |
| 段階3の収集本体 | 001〜003〜import は本 Run で成功済み。ジャンル拡大の主線は継続可 |

#### 再開手順（Human）

修正取り込み後、次のいずれか:

1. **weekly 再実行**（001〜004連鎖を通しで確認したいとき）— 同上コマンド
2. **daily 継続**（`100003` の BATCH-003 収集を進めるとき）— 004連鎖は weekly のみ

```bash
./scripts/batch/local_daily_orchestrator.sh --live-rakuten \
  --genre-ids 100003 --ranking-genre-ids 100005 \
  --pages-per-run=60 --max-qps 1
```

### 5.2 `100003` weekly（成功・existing ID 修正後）

| 項目 | 内容 |
| ---- | ---- |
| `pipeline_batch_run_id`（シナリオ） | `d8d42811-f58e-443a-b3bc-12a5c1259460` |
| existing `business_run_id` | `68dd3f36-39f2-4ee5-8b3e-40923ea79765` |
| BATCH-001 / 002 / 003 | succeeded（003: `pages=1` `budget_stopped=True`） |
| 003後 import 連鎖 | succeeded |
| BATCH-004 | partially_succeeded（16/3）。429なし |
| 004後 BATCH-005 | partially_succeeded（15/1）。1件 `GRS-VAL-001`（空 Items）だがシナリオ継続 |
| 004後 006〜017 | succeeded（008 updated=1 applied=16） |
| シナリオ結果 | **SUCCEEDED**（existing business ID 分離の確認） |

### 5.3 `100003` weekly 2回目（失敗・空 Items のみ）

| 項目 | 内容 |
| ---- | ---- |
| `pipeline_batch_run_id` | `9d491128-d327-4b98-9e60-90302f003919` |
| BATCH-001 / 002 / 003 | succeeded（003: `pages=1`） |
| 003後 BATCH-005 | **failed** `GRS-VAL-001` / `GRS-BAT-001`。plan=1・空 Items（`first_item_keys=-`） |
| シナリオ結果 | FAILED（005 で停止。004 未到達） |

#### 原因（事実と推論）

| 区分 | 内容 |
| ---- | ---- |
| 事実 | 005 が `top_keys` に `Items` を含むが要素なしの Raw を処理し、staging 行 0 件で全体 failed |
| 事実 | 003 は空 Items を catalog exhausted として Raw 保存する（`allow_empty`） |
| 推論 | 直前 weekly で当該カーソルが枯渇し、2回目は空ページのみが予算内に入った |

#### 対応

| 項目 | 内容 |
| ---- | ---- |
| BATCH-005 | 空 Items（staging 行 0 件）を **skip + staged** とし、sole empty でも `succeeded`（シナリオを止めない） |
| 運用 | ジャンル同期済みの `100003` 収集継続は **daily** を主とする。weekly の連打は不要 |

```bash
./scripts/batch/local_daily_orchestrator.sh --live-rakuten \
  --genre-ids 100003 --ranking-genre-ids 100005 \
  --pages-per-run=60 --max-qps 1
```

---

## 6. §5.3.5 本見直し

| 項目 | 内容 |
| ---- | ---- |
| 見直し時点 | 段階2完了 **または** 開始から7日（どちらか早い方）→ **段階2完了で到達** |
| 現状 | 見直し実施待ち（Human 実測共有後、運用方針§5.3.5へ維持/改定案を反映） |
| 非記載 | secret 実値 |

---

## 7. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-08-01 | 初版。段階2充足（Human: 10回以上成功・429なし）。Ranking/取得ジャンル分離と段階3手順 |
| 2026-08-01 | 段階3 `100003` weekly 失敗を記録。existing 連鎖の business run ID 分離を親シェルへ反映 |
| 2026-08-01 | weekly 成功（5.2）と 2回目空 Items 失敗（5.3）を記録。BATCH-005 空 Items skip 化 |
