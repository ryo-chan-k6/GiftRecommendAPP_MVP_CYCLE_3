# 親workflow Slack失敗通知 E2E結果

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| 関連 Epic | [#1732](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1732) |
| 関連 Task | [#1735](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1735) / [#1739](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1739) |
| 先行配線 | [#1730](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1730) / [#1729](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1729) |
| 対象 | `batch-daily-orchestrator.yml` の `notify_failure` → Slack 実送信、およびシステムエラー通知チャンネルへの分離 |
| 実施日 | 2026-07-30 |
| 実施者 | `okuri-ai-bot`（machine account） |

secret / token / channel ID 実値は本結果に含めない。

---

## 2. 実施方針（事実）

低コスト・低破壊のため、Task Branch 上で一時的に `e2e_force_fail` job（secret / stg 不要の `exit 1`）を追加し、後段葉 job を起動せずに `notify_failure` を発火させた。

| 項目 | 内容 |
| ---- | ---- |
| Workflow | Batch Daily Orchestrator |
| ref | `test/task-1735-batch-schedule-slack-e2e` |
| SHA（実行時） | `058b5cfd` |
| inputs | `max_items=1`, `run_retry_after=false` |
| Run URL | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30506470095 |
| 親 conclusion | `failure`（意図的） |
| 一時変更の扱い | 検証後に YAML を親 Epic tip 相当へ復元。**最終差分に意図的失敗 job を残さない** |

---

## 3. Job 結果（事実）

| Job | conclusion |
| --- | ---------- |
| `e2e_force_fail` | **failure**（意図的） |
| `ranking_snapshot` | skipped |
| `item_import` | skipped |
| `item_meaning_generation` | skipped |
| `distribution_metrics` | skipped |
| `retry_failed_items` | skipped |
| `notify_failure` | **success** |

### 3.1 Slack step（事実）

| 項目 | 内容 |
| ---- | ---- |
| Step 名 | `Notify Slack on daily orchestrator failure` |
| Step conclusion | `success` |
| `Slack notification failed` warning | **ログ上なし**（`postSlackMessage` の `!result.ok` 分岐は未発火と解釈） |
| Job summary | `Batch failure notification` 見出しを書く実装（本文に Run URL / 失敗 job 名を含む） |

### 3.2 システムエラー通知チャンネル分離後の E2E（#1739、事実）

| 項目 | 内容 |
| ---- | ---- |
| ref | `chore/task-1739-batch-slack-channel-separation` |
| SHA（実行時） | `c9e102a2` |
| Run URL | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/30508264881 |
| 親 conclusion | `failure`（意図的） |
| `e2e_force_fail` | `failure`（意図的） |
| 後段葉 job | skipped（stg / DB を起動しない） |
| `notify_failure` | **success** |
| Slack step | **success** |
| 通知先変数 | `SLACK_CHANNEL_ID_SYSTEM_ALERTS`（実値は記録しない） |
| 一時変更の扱い | 検証後に `e2e_force_fail` を除去。最終差分には残さない |

---

## 4. 判定

| 項目 | 内容 | 区分 |
| ---- | ---- | ---- |
| #1735 `notify_failure` 発火 | **PASS**（意図的失敗で発火） | 事実 |
| #1735 開発運用チャンネル UI 到達 | **Human 確認済み**（2026-07-30） | Human確認 |
| #1739 新通知先での Slack API 呼び出し | **PASS**（`notify_failure` / Slack step success） | 事実 |
| #1739 システムエラー通知チャンネル UI 到達 | **Human 確認済み**（2026-07-30） | Human確認 |
| 最終差分から意図的失敗除去 | 本 Task の完了条件（PR で確認） | 事実（手順） |

**総合（事実 + 推論）:** GHA 経路とシステムエラー通知チャンネル UI の両方で通知先分離を確認済み。通知先分離は完了扱いにできる。

---

## 5. 残リスク・注意（推論 / 未確認）

| 項目 | 内容 |
| ---- | ---- |
| UI 到達 | 開発運用チャンネル・システムエラー通知チャンネルともに Human 確認済み |
| incident メンション | `SLACK_MENTION_INCIDENT` が設定されている場合、実運用でもメンションが付く。運用可否は Human |
| weekly | weekly 親の `notify_failure` は配線済みだが本 E2E 未実施（別 Task 可） |
| 本線失敗時 | 葉 job 失敗（stg 承認・DB 等）でも同経路。本 E2E は意図的早期失敗のみ |

---

## 6. 案B再判断への影響（推論）

- §9 high「Slack 失敗通知 E2E」は **GHA / UI ともに完了**
- daily 親 D1 再実行は #1742 で **PASS**（Run 30509052971）
- 本結果をもって schedule 有効化を自動承認しない（#1732 gate 継承）

---

## 7. 変更履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-30 | 初版。Run 30506470095。notify_failure success / Slack warning なし |
| 2026-07-30 | #1739 通知先分離 E2E（Run 30508264881）を追記。GHA PASS / 新チャンネル UI は Human 確認待ち |
| 2026-07-30 | Human確認: システムエラー通知チャンネル UI 到達済み。#1742 daily親D1 PASSを反映 |
