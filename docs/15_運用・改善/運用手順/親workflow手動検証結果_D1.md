# 親workflow手動検証結果（D1）

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 関連 Epic | [#1637](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1637) |
| 関連 Task | [#1715](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1715) |
| 方針 | 案 **A** / **D1**（schedule 無効・低 `max_items` dispatch） |
| 手順 | [親workflow手動検証手順_D1](./親workflow手動検証手順_D1.md) |
| 実施日 | 2026-07-28 |
| 実施者 | `okuri-ai-bot`（machine account） |

secret / token / 接続文字列実値は本結果に含めない。

---

## 2. 実施サマリ

| 項目 | 内容 |
| ---- | ---- |
| Workflow | Batch Daily Orchestrator（`batch-daily-orchestrator.yml`） |
| ref | `develop` |
| inputs | `max_items=1`, `run_retry_after=false` |
| Run URL | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30358450150 |
| 親 status | `completed` |
| 親 conclusion | `failure` |
| 判定 | **PARTIAL** |

weekly / manual は Wave 1 では未実施（daily 必須を優先。コスト抑制）。

---

## 3. Job 結果（事実）

| Job | conclusion |
| --- | ---------- |
| `ranking_snapshot / ranking-snapshot` | success |
| `item_import / resolve-run-id` | success |
| `item_import / item_pseudo_diff / item-pseudo-diff` | success |
| `item_import / raw_staging / raw-staging` | success |
| `item_import / product_diff / product-diff` | success |
| `item_import / item_apply / item-apply` | success |
| `item_import / item_active_status / item-active-status` | success |
| `item_import / import_summary / import-summary` | **failure** |
| `item_meaning_generation` | skipped（上流 failure のため） |
| `distribution_metrics` | skipped |
| `retry_failed_items` | skipped（`run_retry_after=false` かつ上流 failure） |

失敗 step（名前のみ）: `Run BATCH-017 scaffold demo`

---

## 4. 所見

### 4.1 確認できたこと（事実）

- 親 `workflow_dispatch` は machine account から起動可能
- `jobs.needs` 連鎖は設計どおり（ranking → item_import 内ジョブ順 → 失敗後の後段 skip）
- `run_retry_after=false` 時に retry が走らないことと整合

### 4.2 失敗の位置づけ（事実 + 推論）

- **事実:** 失敗は複合子 `item_import` 内の BATCH-017（import_summary）step。親 YAML の schedule / concurrency 自体の不具合ではない
- **推論:** 017 が scaffold demo 経路で動いている、または集計対象 `batch_run_id` 前提不足の可能性。葉ジョブ修正は #1637 の schedule 有効化とは分離してよい

### 4.3 案 A との関係

schedule は無効のまま（案 A）。本結果をもって **案 B（daily cron 有効化）へ自動移行しない**。017 失敗の扱いと案 B 再判断は Human。

---

## 5. 次アクション（推奨・未確定）

| 優先 | 内容 | 担当案 |
| ---- | ---- | ------ |
| high | BATCH-017 GHA step（scaffold demo vs live / `job_run_id`・`batch_run_id`）の切り分け | 別 Task または既存 batch Issue |
| medium | 後続 Wave `notify / cron-docs`（Slack 失敗通知・cron JST 00:30 コメント同期）。schedule は無効のまま可 | #1637 |
| low | weekly の D1 手動検証（任意） | #1637 |
| Human | 案 B 移行の再判断（本 PARTIAL を見て） | Human |

---

## 6. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-28 | 初版。daily D1 実施・PARTIAL 記録（run 30358450150） |
