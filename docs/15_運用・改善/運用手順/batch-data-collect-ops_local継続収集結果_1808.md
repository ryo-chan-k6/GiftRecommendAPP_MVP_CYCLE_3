# batch-data-collect-ops local継続収集結果（#1808）

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 関連Issue | #1808（親Epic #1798。先行 #1801 / PR #1807） |
| 前提 | [本格収集運用枠](../../../ai-logs/human-decisions/2026-07-31-batch-data-collect-ops-plan.md) / [段階1結果](./batch-data-collect-ops_local継続収集結果_1801.md) |
| 記録日 | 2026-08-01 |
| 実行主体 | **Human**（`--live-rakuten`）。AI は手順・記録同期・阻害時最小修正・PR/Review |
| 段階 | 段階2 **充足** → 段階3準備（Ranking/取得ジャンル分離） |

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

## 5. §5.3.5 本見直し

| 項目 | 内容 |
| ---- | ---- |
| 見直し時点 | 段階2完了 **または** 開始から7日（どちらか早い方）→ **段階2完了で到達** |
| 現状 | 見直し実施待ち（Human 実測共有後、運用方針§5.3.5へ維持/改定案を反映） |
| 非記載 | secret 実値 |

---

## 6. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-08-01 | 初版。段階2充足（Human: 10回以上成功・429なし）。Ranking/取得ジャンル分離と段階3手順 |
