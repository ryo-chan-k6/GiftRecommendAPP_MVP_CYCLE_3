# 親workflow daily 再検証結果（D1）

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 関連 Epic | [#1732](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1732) |
| 関連 Task | [#1742](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1742) |
| 初回検証 | [親workflow手動検証結果_D1](./親workflow手動検証結果_D1.md)（#1715 / PARTIAL） |
| 方針 | 案 A / D1（schedule 無効・低 `max_items` dispatch） |
| 実施日 | 2026-07-30 |
| 実施者 | `okuri-ai-bot`（machine account） |

secret / token / 接続文字列 / channel ID 実値は本結果に含めない。

---

## 2. 目的

初回 D1（Run 30358450150）は `item_import / import_summary`（BATCH-017）で失敗し、
親 conclusion が `failure`、判定が `PARTIAL` だった。

#1717 / #1726 の修正後、同等の低コスト条件で daily 親全体を再実行し、以下を確認する。

- BATCH-017 の PARTIAL 解消
- `item_import → item_meaning_generation → distribution_metrics` の後段連鎖
- `run_retry_after=false` 時の retry skip
- schedule 無効維持

---

## 3. 実施サマリ（事実）

| 項目 | 内容 |
| ---- | ---- |
| Workflow | Batch Daily Orchestrator（`batch-daily-orchestrator.yml`） |
| ref | `test/task-1742-batch-daily-rerun-d1` |
| SHA | `3f709974` |
| event | `workflow_dispatch` |
| inputs | `max_items=1`, `run_retry_after=false` |
| Run URL | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30509052971 |
| 親 status | `completed` |
| 親 conclusion | **`success`** |
| Environment 承認 | 本 Run では Human の承認操作なしに全 job が進行 |
| 判定 | **PASS** |

---

## 4. Job 結果（事実）

### 4.1 ranking / item import

| Job | conclusion |
| --- | ---------- |
| `ranking_snapshot / ranking-snapshot` | success |
| `item_import / resolve-run-id` | success |
| `item_import / item_pseudo_diff / item-pseudo-diff` | success |
| `item_import / raw_staging / raw-staging` | success |
| `item_import / product_diff / product-diff` | success |
| `item_import / item_apply / item-apply` | success |
| `item_import / item_active_status / item-active-status` | success |
| `item_import / import_summary / import-summary` | **success** |

### 4.2 item meaning generation / metrics

| Job | conclusion |
| --- | ---------- |
| `item_meaning_generation / resolve-run-id` | success |
| `item_meaning_generation / item_generation_queue / item-generation-queue` | success |
| `item_meaning_generation / item_semantic / item-semantic` | success |
| `item_meaning_generation / feature_input_hash / feature-input-hash` | success |
| `item_meaning_generation / item_feature / item-feature` | success |
| `item_meaning_generation / feature_normalization / feature-normalization` | success |
| `item_meaning_generation / embedding_input_hash / embedding-input-hash` | success |
| `item_meaning_generation / item_embedding / item-embedding` | success |
| `item_meaning_generation / import_summary / import-summary` | success |
| `distribution_metrics / distribution-metrics` | success |

### 4.3 条件付き job

| Job | conclusion | 理由 |
| --- | ---------- | ---- |
| `retry_failed_items` | skipped | `run_retry_after=false` |
| `notify_failure` | skipped | 上流 failure なし |

---

## 5. 初回 D1 との差分（事実）

| 観点 | 初回 D1（Run 30358450150） | 再検証（Run 30509052971） |
| ---- | -------------------------- | ------------------------- |
| 親 conclusion | failure | **success** |
| 判定 | PARTIAL | **PASS** |
| item import BATCH-017 | failure | **success** |
| item meaning generation | skipped | **全 job success** |
| distribution metrics | skipped | **success** |
| retry | skipped | skipped（入力どおり） |

**事実:** 初回 D1 の blocker だった BATCH-017 failure は、daily 親全体の再検証で再現せず、
後段を含む親本線が完走した。

---

## 6. 判定と含意

### 6.1 判定（事実）

- daily 親 D1 再検証: **PASS**
- BATCH-017 PARTIAL: **解消確認**
- 親 `jobs.needs` 連鎖: **完走**
- schedule: **無効のまま**

### 6.2 含意（推論）

- 案 B 再判断前の high 技術検証「daily 親 D1 再実行」は充足した。
- 本 Run は Task Branch の `workflow_dispatch` であり、cron 定期運用の無人性・長期安定性を保証するものではない。
- 現行 GHA の楽天取得は Scaffold 前提であり、#1607 完了後の live 取込を保証しない。
- 案 B の採否は、Scaffold 定期取込・監視・rollback・コストを含め Human が判断する。

---

## 7. 残リスク・未確認

| 項目 | 状態 |
| ---- | ---- |
| weekly / manual 親 D1 | 未実施 |
| cron schedule 起動 | 未実施（Human 承認前の有効化禁止） |
| 長期連続運転 | 未実施 |
| #1607 楽天 API 本番 egress | 未完了 |
| Scaffold データの定期蓄積上限 | 未評価 |
| 監視・rollback 手順 | 明文化未完了 |

---

## 8. Human 判断ゲート

本結果により high 技術検証は完了したが、案 B（daily schedule 有効化）を自動採用しない。
以下を Human が判断する。

1. Scaffold 前提の daily 定期実行を許容するか
2. システムエラー通知チャンネルと incident メンション運用で監視要件を満たすか
3. rollback（`on.schedule` 再無効化）と障害対応体制が十分か
4. daily schedule 有効化 Task を開始するか、B-0 を継続するか

---

## 9. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-30 | 初版。Run 30509052971。daily 親全体 success、BATCH-017 PARTIAL 解消確認 |
