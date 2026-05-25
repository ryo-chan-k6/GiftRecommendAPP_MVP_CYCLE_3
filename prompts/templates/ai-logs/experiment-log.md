# Intake Log

## 1. 概要

| 項目          | 内容                  |
| ------------- | --------------------- |
| Log ID        | `{{log.id}}`          |
| Log種別       | `intake`              |
| 件名          | {{log.title}}         |
| 発生日時      | `{{log.occurred_at}}` |
| 記録日時      | `{{log.recorded_at}}` |
| 発生元        | `{{source.channel}}`  |
| 発生元Command | `{{command.name}}`    |
| 発生元Agent   | `{{agent.primary}}`   |
| 関連Issue     | `{{issue.number}}`    |
| 関連PR        | `{{pr.number}}`       |
| Definition    | `{{definition.path}}` |
| 重要度        | `{{log.severity}}`    |
| 状態          | `{{log.status}}`      |

---

## 2. 結論

{{log.summary}}

---

## 3. intake log として記録する理由

{{log.reason}}

### 3.1 intake対象理由

{{#each log.intake_reasons}}

- {{this}}
  {{/each}}

{{#unless log.intake_reasons}}

- Issue化前の相談、要望、フィードバック、または作業候補を整理する必要があるため
  {{/unless}}

### 3.2 通常作業ログではない理由

通常作業ログをすべて `ai-logs/` に保存しない。  
このログは、Issue化前の入力、未整理の要望、作業候補、判断材料を一時的に整理するために記録する。

---

## 4. 入力内容

### 4.1 元入力の概要

{{intake.original_summary}}

### 4.2 元入力

```text
{{intake.original_text}}
```

### 4.3 入力種別

| 項目                  | 内容                                   |
| --------------------- | -------------------------------------- |
| 入力種別              | `{{intake.type}}`                      |
| 発生元                | `{{source.discovered_from}}`           |
| 入力者                | `{{source.requester}}`                 |
| 関連Task              | `{{source.related_task}}`              |
| 関連Task Definition   | `{{source.related_task_definition}}`   |
| 関連Review Definition | `{{source.related_review_definition}}` |
| 関連Command           | `{{source.related_command}}`           |

---

## 5. 確認した事実

AI Agent が確認できた事実。

{{#each facts}}

- {{this}}
  {{/each}}

{{#unless facts}}

- なし
  {{/unless}}

---

## 6. 推論

確認した事実から推論した内容。

{{#each inferences}}

- {{this}}
  {{/each}}

{{#unless inferences}}

- なし
  {{/unless}}

> 推論は確定事実ではない。  
> 後続判断では、正本docs、Issue、PR、Definition、ユーザー確認結果を優先する。

---

## 7. 未確認事項

AI Agent では確認できなかった事項。

{{#each unconfirmed}}

- {{this}}
  {{/each}}

{{#unless unconfirmed}}

- なし
  {{/unless}}

---

## 8. 分類

| 項目                | 内容                                         |
| ------------------- | -------------------------------------------- |
| 分類                | `{{classification.category}}`                |
| サブ分類            | `{{classification.sub_category}}`            |
| 作業種別            | `{{classification.work_type}}`               |
| 対象領域            | `{{classification.area}}`                    |
| Phase               | `{{classification.phase}}`                   |
| 優先度              | `{{classification.priority}}`                |
| 緊急度              | `{{classification.urgency}}`                 |
| Issue化要否         | `{{classification.issue_required}}`          |
| Contract Task化要否 | `{{classification.contract_task_required}}`  |
| Human Decision要否  | `{{classification.human_decision_required}}` |

---

## 9. Issue化判断

| 項目           | 内容                                  |
| -------------- | ------------------------------------- |
| Issue化要否    | `{{issue_candidate.required}}`        |
| 判断理由       | {{issue_candidate.reason}}            |
| 推奨Issue種別  | `{{issue_candidate.issue_type}}`      |
| 推奨Task種別   | `{{issue_candidate.task_type}}`       |
| 推奨Priority   | `{{issue_candidate.priority}}`        |
| 推奨Phase      | `{{issue_candidate.phase}}`           |
| 推奨Issue unit | `{{issue_candidate.issue.unit}}`      |
| 推奨Issue type | `{{issue_candidate.issue.type}}`      |
| 推奨Issue area | `{{issue_candidate.issue.area}}`      |
| 推奨Definition | `{{issue_candidate.definition_path}}` |
| 推奨Template   | `{{issue_candidate.template_path}}`   |

### 9.1 Issue化が必要な理由

{{#each issue_candidate.required_reasons}}

- {{this}}
  {{/each}}

{{#unless issue_candidate.required_reasons}}

- なし
  {{/unless}}

### 9.2 Issue化しない理由

{{#each issue_candidate.not_required_reasons}}

- {{this}}
  {{/each}}

{{#unless issue_candidate.not_required_reasons}}

- なし
  {{/unless}}

---

## 10. 推奨Issue案

{{#each proposed_issues}}

### 10.{{@index}} {{title}}

| 項目               | 内容                     |
| ------------------ | ------------------------ |
| Issue種別          | `{{issue_type}}`         |
| Task種別           | `{{task_type}}`          |
| Priority           | `{{priority}}`           |
| Phase              | `{{phase}}`              |
| 推奨Issue unit     | `{{issue.unit}}`         |
| 推奨Issue type     | `{{issue.type}}`         |
| 推奨Issue area     | `{{issue.area}}`         |
| 推奨Definition     | `{{definition_path}}`    |
| 推奨Template       | `{{template_path}}`      |
| no-branch          | `{{branch.no_branch}}`   |
| no-branch          | `{{branch.no_branch}}`   |
| Parent Epic Issue  | `{{parent.epic_issue}}`  |
| Parent Epic Branch | `{{parent.epic_branch}}` |

#### 概要

{{summary}}

#### scope

{{#each scope}}

- {{this}}
  {{/each}}

{{#unless scope}}

- なし
  {{/unless}}

#### out_of_scope

{{#each out_of_scope}}

- {{this}}
  {{/each}}

{{#unless out_of_scope}}

- なし
  {{/unless}}

#### acceptance criteria

{{#each acceptance_criteria}}

- {{this}}
  {{/each}}

{{#unless acceptance_criteria}}

- なし
  {{/unless}}

#### Human Reviewで確認してほしいこと

{{#each human_decision_points}}

- {{this}}
  {{/each}}

{{#unless human_decision_points}}

- なし
  {{/unless}}

{{/each}}

{{#unless proposed_issues}}

- なし
  {{/unless}}

---

## 11. Contract Task化判断

| 項目                | 内容                                |
| ------------------- | ----------------------------------- |
| Contract Task化要否 | `{{contract_task.required}}`        |
| 判断理由            | {{contract_task.reason}}            |
| 推奨Definition      | `{{contract_task.definition_path}}` |
| 推奨Issue種別       | `{{contract_task.issue_type}}`      |
| 推奨Issue unit      | `{{contract_task.issue.unit}}`      |
| 推奨Issue type      | `{{contract_task.issue.type}}`      |
| 推奨Issue area      | `{{contract_task.issue.area}}`      |

### 11.1 Contract Task化が必要な理由

{{#each contract_task.required_reasons}}

- {{this}}
  {{/each}}

{{#unless contract_task.required_reasons}}

- なし
  {{/unless}}

### 11.2 Contract Task化しない理由

{{#each contract_task.not_required_reasons}}

- {{this}}
  {{/each}}

{{#unless contract_task.not_required_reasons}}

- なし
  {{/unless}}

---

## 12. 影響範囲

| 観点        | 影響有無                               | 影響度                              | 補足                             |
| ----------- | -------------------------------------- | ----------------------------------- | -------------------------------- |
| docs        | `{{impact.docs.affected}}`             | `{{impact.docs.level}}`             | {{impact.docs.note}}             |
| source code | `{{impact.source.affected}}`           | `{{impact.source.level}}`           | {{impact.source.note}}           |
| tests       | `{{impact.tests.affected}}`            | `{{impact.tests.level}}`            | {{impact.tests.note}}            |
| API仕様     | `{{impact.api_spec.affected}}`         | `{{impact.api_spec.level}}`         | {{impact.api_spec.note}}         |
| OpenAPI     | `{{impact.openapi.affected}}`          | `{{impact.openapi.level}}`          | {{impact.openapi.note}}          |
| Orval       | `{{impact.orval.affected}}`            | `{{impact.orval.level}}`            | {{impact.orval.note}}            |
| generated   | `{{impact.generated.affected}}`        | `{{impact.generated.level}}`        | {{impact.generated.note}}        |
| DB schema   | `{{impact.db_schema.affected}}`        | `{{impact.db_schema.level}}`        | {{impact.db_schema.note}}        |
| CI/CD       | `{{impact.cicd.affected}}`             | `{{impact.cicd.level}}`             | {{impact.cicd.note}}             |
| security    | `{{impact.security.affected}}`         | `{{impact.security.level}}`         | {{impact.security.note}}         |
| GitHub運用  | `{{impact.github_operation.affected}}` | `{{impact.github_operation.level}}` | {{impact.github_operation.note}} |
| Project運用 | `{{impact.project.affected}}`          | `{{impact.project.level}}`          | {{impact.project.note}}          |

---

## 13. 参照すべき入力資料

### 13.1 input docs

{{#each input.docs}}

- `{{path}}`
  - 必須: `{{required}}`
  - 参照目的: {{purpose}}
    {{/each}}

{{#unless input.docs}}

- なし
  {{/unless}}

### 13.2 input templates

{{#each input.templates}}

- `{{path}}`
  - 必須: `{{required}}`
  - 参照目的: {{purpose}}
  - 適用先:
    {{#each applies_to}} - `{{this}}`
    {{/each}}
    {{/each}}

{{#unless input.templates}}

- なし
  {{/unless}}

### 13.3 input files

{{#each input.files}}

- `{{path}}`
  - 必須: `{{required}}`
  - 参照目的: {{purpose}}
    {{/each}}

{{#unless input.files}}

- なし
  {{/unless}}

---

## 14. リスク

{{#each risks}}

- {{this}}
  {{/each}}

{{#unless risks}}

- なし
  {{/unless}}

---

## 15. 人間判断が必要な事項

{{#each human_decision_points}}

- {{this}}
  {{/each}}

{{#unless human_decision_points}}

- なし
  {{/unless}}

---

## 16. 推奨対応

### 16.1 即時対応

{{#each recommended_actions.immediate}}

- {{this}}
  {{/each}}

{{#unless recommended_actions.immediate}}

- なし
  {{/unless}}

### 16.2 後続対応

{{#each recommended_actions.follow_up}}

- {{this}}
  {{/each}}

{{#unless recommended_actions.follow_up}}

- なし
  {{/unless}}

### 16.3 別Issue化候補

{{#each follow_up.items}}

- 内容: {{description}}
  - 種別: `{{type}}`
  - 推奨対応: {{recommended_action}}
  - 別Issue化要否: `{{issue_required}}`
    {{/each}}

{{#unless follow_up.items}}

- なし
  {{/unless}}

---

## 17. 次Action

### 17.1 Issue化する場合

```text
{{next_action.on_create_issue}}
```

### 17.2 Contract Task化する場合

```text
{{next_action.on_create_contract_task}}
```

### 17.3 追加確認する場合

```text
{{next_action.on_human_decision}}
```

### 17.4 Issue化しない場合

```text
{{next_action.on_no_issue}}
```

---

## 18. 停止条件

以下に該当する場合、AI Agent は作業を停止し、人間確認へ回す。

{{#each stop_conditions}}

- {{this}}
  {{/each}}

{{#unless stop_conditions}}

- 入力内容の意図が不明な場合
- scope / out_of_scope を定義できない場合
- 参照すべき正本docsが不明な場合
- Issue化要否を判断できない場合
- API contract変更、DB schema変更、security影響が疑われる場合
- secret、APIキー、`.env` 実値を扱う必要がある場合
- Human Reviewを省略する必要があるように見える場合
  {{/unless}}

---

## 19. Status更新意図

| 項目       | 内容                               |
| ---------- | ---------------------------------- |
| 現在Status | `{{project.current_status}}`       |
| 推奨Status | `{{project.recommended_status}}`   |
| 更新意図   | `{{project.status_update_intent}}` |

Status更新は、GitHub Actions または運用スクリプトで実施する。  
このログではStatus更新の意図のみを記録する。

---

## 20. 正本参照

| 種別           | 参照先                |
| -------------- | --------------------- |
| 関連Issue      | `{{issue.url}}`       |
| 関連PR         | `{{pr.url}}`          |
| 関連Definition | `{{definition.path}}` |
| 関連docs       | `{{docs.url}}`        |
| 関連レビュー   | `{{review.url}}`      |
| 関連ai-log     | `{{related_log.url}}` |

Issue作成後は、作業計画はIssueを正本とする。  
PR作成後は、作業結果とレビュー結果はPRを正本とする。  
成果物はdocsを正本とする。

---

## 21. 記録先

| 項目      | 内容                                   |
| --------- | -------------------------------------- |
| 保存要否  | `{{operation_logging.ai_logs.intake}}` |
| 保存先    | `{{operation_logging.path}}`           |
| log level | `{{operation_logging.level}}`          |
| 保存理由  | {{operation_logging.reason}}           |

このログはIssue化前の入力整理を目的とする補助ログである。  
Issue化後は、作業計画の正本をGitHub Issueへ移す。

---

## 22. 備考

{{#each notes}}

- {{this}}
  {{/each}}

{{#unless notes}}

- なし
  {{/unless}}
