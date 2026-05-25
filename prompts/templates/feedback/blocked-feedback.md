# Blocked Feedback

## 1. 結論

作業を継続できないため、現在 `blocked` として停止しています。  
以下の理由・確認事項を確認してください。

| 項目          | 内容                         |
| ------------- | ---------------------------- |
| Blocked種別   | `{{blocked.type}}`           |
| 優先度        | `{{blocked.priority}}`       |
| 対象Issue     | `{{issue.number}}`           |
| 対象PR        | `{{pr.number}}`              |
| Task ID       | `{{task.id}}`                |
| Definition    | `{{definition.path}}`        |
| 発生元Command | `{{command.name}}`           |
| 担当Agent     | `{{agent.primary}}`          |
| 発生日時      | `{{blocked.occurred_at}}`    |
| 現在Status    | `{{project.current_status}}` |

---

## 2. Blocked理由

{{blocked.reason}}

### 2.1 該当する停止条件

{{#each blocked.stop_conditions}}

- {{this}}
  {{/each}}

{{#unless blocked.stop_conditions}}

- なし
  {{/unless}}

---

## 3. 現在の状態

| 項目           | 内容                               |
| -------------- | ---------------------------------- |
| Branch         | `{{branch.name}}`                  |
| PR target      | `{{branch.target}}`                |
| 作業継続可否   | `{{blocked.can_continue}}`         |
| 停止中か       | `{{blocked.is_blocked}}`           |
| 推奨Status     | `{{project.recommended_status}}`   |
| Status更新意図 | `{{project.status_update_intent}}` |

---

## 4. 確認した事実

AI Agent が確認できた事実。

{{#each facts}}

- {{this}}
  {{/each}}

{{#unless facts}}

- なし
  {{/unless}}

---

## 5. 推論

確認した事実から推論した内容。

{{#each inferences}}

- {{this}}
  {{/each}}

{{#unless inferences}}

- なし
  {{/unless}}

> 推論は確定事実ではない。  
> 判断が必要な場合は、人間確認結果を正とする。

---

## 6. 未確認事項

AI Agent では確認できなかった事項。

{{#each unconfirmed}}

- {{this}}
  {{/each}}

{{#unless unconfirmed}}

- なし
  {{/unless}}

---

## 7. 影響範囲

| 観点        | 影響有無                               | 補足                             |
| ----------- | -------------------------------------- | -------------------------------- |
| docs        | `{{impact.docs.affected}}`             | {{impact.docs.note}}             |
| source code | `{{impact.source.affected}}`           | {{impact.source.note}}           |
| tests       | `{{impact.tests.affected}}`            | {{impact.tests.note}}            |
| API仕様     | `{{impact.api_spec.affected}}`         | {{impact.api_spec.note}}         |
| OpenAPI     | `{{impact.openapi.affected}}`          | {{impact.openapi.note}}          |
| Orval       | `{{impact.orval.affected}}`            | {{impact.orval.note}}            |
| generated   | `{{impact.generated.affected}}`        | {{impact.generated.note}}        |
| DB schema   | `{{impact.db_schema.affected}}`        | {{impact.db_schema.note}}        |
| CI/CD       | `{{impact.cicd.affected}}`             | {{impact.cicd.note}}             |
| security    | `{{impact.security.affected}}`         | {{impact.security.note}}         |
| GitHub運用  | `{{impact.github_operation.affected}}` | {{impact.github_operation.note}} |
| Project運用 | `{{impact.project.affected}}`          | {{impact.project.note}}          |

---

## 8. 作業継続できない理由

AI Agent が勝手に進めない理由。

{{blocked.stop_reason}}

### 8.1 主な理由

{{#each blocked.stop_reason_items}}

- {{this}}
  {{/each}}

{{#unless blocked.stop_reason_items}}

- なし
  {{/unless}}

---

## 9. 人間に確認したいこと

{{#each human_decision_points}}

- {{this}}
  {{/each}}

{{#unless human_decision_points}}

- なし
  {{/unless}}

---

## 10. 対応選択肢

{{#each options}}

### 10.{{@index}} {{title}}

| 項目     | 内容                       |
| -------- | -------------------------- |
| 選択肢ID | `{{id}}`                   |
| 推奨度   | `{{recommendation_level}}` |
| 影響度   | `{{impact_level}}`         |
| リスク   | `{{risk_level}}`           |

#### 内容

{{description}}

#### メリット

{{#each pros}}

- {{this}}
  {{/each}}

{{#unless pros}}

- なし
  {{/unless}}

#### デメリット / リスク

{{#each cons}}

- {{this}}
  {{/each}}

{{#unless cons}}

- なし
  {{/unless}}

#### 必要な後続対応

{{#each next_actions}}

- {{this}}
  {{/each}}

{{#unless next_actions}}

- なし
  {{/unless}}

{{/each}}

{{#unless options}}

- なし
  {{/unless}}

---

## 11. AI推奨案

| 項目       | 内容                            |
| ---------- | ------------------------------- |
| 推奨選択肢 | `{{recommendation.option_id}}`  |
| 推奨理由   | {{recommendation.reason}}       |
| 確信度     | `{{recommendation.confidence}}` |

### 11.1 補足

{{recommendation.note}}

---

## 12. 作業再開条件

以下を満たしたら作業を再開できる。

{{#each resume_conditions}}

- {{this}}
  {{/each}}

{{#unless resume_conditions}}

- Blocked理由が解消されている
- 人間判断が必要な事項について回答を得ている
- scope / out_of_scope が再確認されている
- secret、`.env` 実値、APIキーなどの混入がないことを確認している
  {{/unless}}

---

## 13. 推奨次Action

### 13.1 作業を再開する場合

```text
{{next_action.on_resume}}
```

### 13.2 修正して再実行する場合

```text
{{next_action.on_fix_and_retry}}
```

### 13.3 別Issue化する場合

```text
{{next_action.on_split_required}}
```

### 13.4 作業停止を継続する場合

```text
{{next_action.on_keep_blocked}}
```

---

## 14. ai-logs 記録要否

| 項目              | 内容                                          |
| ----------------- | --------------------------------------------- |
| incident log      | `{{operation_logging.ai_logs.incidents}}`     |
| cross-cutting log | `{{operation_logging.ai_logs.cross_cutting}}` |
| log level         | `{{operation_logging.level}}`                 |
| 保存先            | `{{operation_logging.path}}`                  |
| 理由              | {{operation_logging.reason}}                  |

通常作業ログをすべて `ai-logs/` に保存しない。  
blocked が作業停止・例外・判断不能に該当する場合のみ、必要に応じて `ai-logs/incidents/` に記録する。

---

## 15. 回答してほしい形式

以下のいずれかで回答してください。

```text
A案で進めてください
```

```text
作業を再開してください。条件は以下です。
-
```

```text
追加で以下を確認してください。
-
```

```text
このTaskでは扱わず、別Issue化してください。
```

```text
作業停止を継続してください。
```

---

## 16. 正本

| 種別         | 参照先                |
| ------------ | --------------------- |
| 作業計画     | `{{issue.url}}`       |
| 作業結果     | `{{pr.url}}`          |
| Definition   | `{{definition.path}}` |
| 関連docs     | `{{docs.url}}`        |
| 関連レビュー | `{{review.url}}`      |
| 関連ai-log   | `{{ai_log.url}}`      |

このフィードバックは、作業を再開するための確認依頼である。  
作業計画はIssue、作業結果とレビュー結果はPR、成果物はdocsを正本とする。

---

## 17. 備考

{{#each notes}}

- {{this}}
  {{/each}}

{{#unless notes}}

- なし
  {{/unless}}
