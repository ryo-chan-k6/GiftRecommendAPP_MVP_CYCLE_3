# Incident Detected

## 1. 結論

[error] AI作業が停止しました。

| 項目 | 内容 |
| ---- | ---- |
| Issue | `{{issue.number}}` |
| PR | `{{pr.number}}` |
| Branch | `{{branch.name}}` |
| Agent | `{{agent.name}}` |
| ai-log | `{{ai_log.path}}` |

## 2. 発生内容

{{incident.summary}}

## 3. 停止理由

{{incident.stop_reason}}

## 4. 人間に確認してほしいこと

{{human_action}}

## 5. 再開条件

{{restart_condition}}

## 6. 正本

Slack通知は正本ではない。incidentの詳細は必要に応じて `ai-logs/incidents/`、Issue、PRに記録する。

