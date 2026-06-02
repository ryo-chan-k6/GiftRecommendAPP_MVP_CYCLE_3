# Incident Log

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-06-02-pr-created-review-definition-not-found-pr333` |
| Log種別 | `incident` |
| 件名 | PR #333 `pr-created` が `review_definition_not_found` で失敗 |
| 発生日時 | 2026-06-02 |
| 関連 Issue | #336（恒久対応） |
| 関連 PR | #333 |
| 状態 | `mitigated`（#336 で対応中） |

## 2. 事象

Fixer E2E 検証 PR #333 作成時、`PR Created Status Sync` は Status を `AI Review` に更新したが、続く `dispatch-review-pr-harness.cjs` が `review_definition_not_found` で **job failure**（Run [26795208665](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/26795208665)）。

## 3. 根本原因

| # | 原因 | 詳細 |
| --- | ---- | ---- |
| 1 | Branch summary ≠ Task ファイル名 | summary `fixer-e2e-ai`、Task `fixer-e2e-verify.yaml` |
| 2 | `pr-review.yaml` 未作成 | PR diff に Review Definition なし |
| 3 | `ai_review_required: false` でも fail | Review 未解決時に Task gate 未到達。仕様 §5「AI Review 省略」と乖離 |

## 4. 影響

- `pr-created` workflow が赤（Fixer E2E では Status 更新は成功し、Fixer dispatch 検証は別経路で実施可能だった）
- 同型の Task PR（summary 不一致・AI Review 不要）で再発しうる

## 5. 恒久対応（Issue #336）

- Task Definition を PR changed files から解決
- `ai_review_required: false` なら Review 未解決でも skip（job success）
- workstream review 慣例パス `reviews/{workstream}/pr-review.yaml` 追加
- filename summary による Task 候補補強
