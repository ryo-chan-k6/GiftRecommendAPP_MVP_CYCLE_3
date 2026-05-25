# AI Review Completed

## 1. 結論

[review] AIレビューが完了しました。

| 項目 | 内容 |
| ---- | ---- |
| Review Result | `{{review.result}}` |
| PR | `{{pr.number}}` |
| PR URL | `{{pr.url}}` |
| Issue | `{{issue.number}}` |
| Issue URL | `{{issue.url}}` |
| Next Status | `{{project.next_status}}` |

## 2. サマリ

{{review.summary}}

## 3. 指摘

| 種別 | 件数 |
| ---- | ---- |
| must | `{{review.must_count}}` |
| should | `{{review.should_count}}` |
| nit | `{{review.nit_count}}` |
| question | `{{review.question_count}}` |

## 4. 人間に必要な対応

{{human_action}}

## 5. 正本

Slack通知は正本ではない。AI Review結果はPRコメントを正本とする。

