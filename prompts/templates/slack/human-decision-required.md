# Human Decision Required

## 1. 結論

[action_required] 人間判断が必要です。

| 項目 | 内容 |
| ---- | ---- |
| 判断事項 | {{decision.title}} |
| Issue | `{{issue.number}}` |
| PR | `{{pr.number}}` |
| ai-log | `{{ai_log.path}}` |

## 2. 背景

{{decision.background}}

## 3. 選択肢

{{decision.options}}

## 4. AIの推奨

{{decision.recommendation}}

## 5. 人間に決めてほしいこと

{{decision.request}}

## 6. 正本

Slack通知だけで判断を完結させない。判断内容はIssue、PR、またはai-logsに記録する。

