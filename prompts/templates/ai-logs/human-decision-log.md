# Human Decision Log

## 1. 概要

| 項目          | 内容                  |
| ------------- | --------------------- |
| Log ID        | `{{log.id}}`          |
| Log種別       | `human-decision`      |
| 件名          | {{log.title}}         |
| 発生日時      | {{log.occurred_at}}   |
| 記録日時      | {{log.recorded_at}}   |
| 発生元Command | `{{command.name}}`    |
| 発生元Agent   | `{{agent.primary}}`   |
| workstream_key | `{{workstream_key}}` |
| 関連Issue     | `{{issue.number}}`    |
| 関連PR        | `{{pr.number}}`       |
| Definition    | `{{definition.path}}` |
| 重要度        | `{{log.severity}}`    |
| 状態          | `{{log.status}}`      |

---

## 2. 結論

{{log.summary}}

---

## 3. human-decision として記録する理由

{{log.reason}}

### 3.1 記録対象理由

{{#each log.human_decision_reasons}}

- {{this}}
  {{/each}}

{{#unless log.human_decision_reasons}}

- AIだけでは判断できない設計・仕様・運用判断があり、人間の最終判断が必要なため
  {{/unless}}

### 3.2 通常作業ログではない理由

通常作業ログをすべて `ai-logs/` に保存しない。  
このログは、人間へエスカレーションする判断論点と選択肢を整理するために記録する。正本は [AIログ運用ルール](../../../docs/00_共通/AIエージェント運用/AIログ運用ルール.md) §13 とする。

---

## 4. 発生経緯

| 項目                  | 内容                                   |
| --------------------- | -------------------------------------- |
| 発生元                | `{{source.discovered_from}}`           |
| 関連Task              | `{{source.related_task}}`              |
| 関連Task Definition   | `{{source.related_task_definition}}`   |
| 関連Review Definition | `{{source.related_review_definition}}` |
| 関連Command           | `{{source.related_command}}`           |

### 4.1 詳細

{{source.detail}}

---

## 5. 判断が必要な事項

Task Definition `human_decision_points` および作業中に発生した論点。

{{#each human_decision_points}}

- {{this}}
  {{/each}}

{{#unless human_decision_points}}

- （未記載）
  {{/unless}}

---

## 6. 背景

{{decision.background}}

---

## 7. 選択肢

| 案  | 内容 | メリット | デメリット |
| --- | ---- | -------- | ---------- |
| A   | {{decision.option_a.summary}} | {{decision.option_a.pros}} | {{decision.option_a.cons}} |
| B   | {{decision.option_b.summary}} | {{decision.option_b.pros}} | {{decision.option_b.cons}} |

{{#if decision.option_c.summary}}
| C   | {{decision.option_c.summary}} | {{decision.option_c.pros}} | {{decision.option_c.cons}} |
{{/if}}

---

## 8. AIの推奨

{{decision.ai_recommendation}}

---

## 9. 人間に決めてほしいこと

{{decision.human_request}}

---

## 10. 判断後に必要な対応

{{decision.follow_up}}

---

## 11. 確認した事実

{{#each facts}}

- {{this}}
  {{/each}}

{{#unless facts}}

- なし
  {{/unless}}

---

## 12. 推論

{{#each inferences}}

- {{this}}
  {{/each}}

{{#unless inferences}}

- なし
  {{/unless}}

---

## 13. 関連情報

| 種別           | 参照                |
| -------------- | ------------------- |
| 関連docs       | {{related.docs}}    |
| 関連Issue      | {{related.issues}}  |
| 関連PR         | {{related.prs}}     |
| 関連Branch     | {{related.branch}}  |

---

## 14. 人間判断結果（記録時）

| 項目       | 内容                 |
| ---------- | -------------------- |
| 判断者     | {{resolution.owner}} |
| 判断日時   | {{resolution.at}}    |
| 採用案     | {{resolution.choice}} |
| 判断理由   | {{resolution.reason}} |
| 後続Issue  | {{resolution.follow_up_issue}} |
| 後続Task   | {{resolution.follow_up_task}} |
