# Split Required Feedback

## 1. 結論

このTask内では扱わず、別Issue化が必要です。  
以下の理由・分割案を確認してください。

| 項目          | 内容                         |
| ------------- | ---------------------------- |
| Split種別     | `{{split.type}}`             |
| 優先度        | `{{split.priority}}`         |
| 対象Issue     | `{{issue.number}}`           |
| 対象PR        | `{{pr.number}}`              |
| Task ID       | `{{task.id}}`                |
| Definition    | `{{definition.path}}`        |
| 発生元Command | `{{command.name}}`           |
| 担当Agent     | `{{agent.primary}}`          |
| 発生日時      | `{{split.occurred_at}}`      |
| 現在Status    | `{{project.current_status}}` |

---

## 2. 別Issue化が必要な理由

{{split.reason}}

### 2.1 該当理由

{{#each split.required_reasons}}

- {{this}}
  {{/each}}

{{#unless split.required_reasons}}

- scope外の変更が含まれているため
- 現在のTask責務を超える変更が必要なため
  {{/unless}}

---

## 3. 現在のTaskで扱わない理由

{{split.out_of_current_task_reason}}

### 3.1 scope / out_of_scope との関係

| 項目                | 内容                             |
| ------------------- | -------------------------------- |
| 現在Taskのscope内か | `{{split.within_current_scope}}` |
| out_of_scope該当    | `{{split.matches_out_of_scope}}` |
| 補足                | {{split.scope_note}}             |

### 3.2 現在Taskのscope

{{#each scope}}

- {{this}}
  {{/each}}

{{#unless scope}}

- なし
  {{/unless}}

### 3.3 現在Taskのout_of_scope

{{#each out_of_scope}}

- {{this}}
  {{/each}}

{{#unless out_of_scope}}

- なし
  {{/unless}}

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
> 別Issue化の最終判断は、人間確認結果を正とする。

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

## 7. 分割対象

### 7.1 分割すべき内容

{{#each split.items}}

- {{title}}
  - 種別: `{{type}}`
  - 理由: {{reason}}
  - 推奨Issue化: `{{issue_required}}`
  - 優先度: `{{priority}}`
    {{/each}}

{{#unless split.items}}

- なし
  {{/unless}}

### 7.2 現在Taskに残す内容

{{#each split.keep_in_current_task}}

- {{this}}
  {{/each}}

{{#unless split.keep_in_current_task}}

- なし
  {{/unless}}

### 7.3 現在Taskから除外する内容

{{#each split.exclude_from_current_task}}

- {{this}}
  {{/each}}

{{#unless split.exclude_from_current_task}}

- なし
  {{/unless}}

---

## 8. 推奨Issue分割案

{{#each proposed_issues}}

### 8.{{@index}} {{title}}

| 項目           | 内容                   |
| -------------- | ---------------------- |
| 推奨Issue種別  | `{{issue_type}}`       |
| 推奨Task種別   | `{{task_type}}`        |
| Priority       | `{{priority}}`         |
| Phase          | `{{phase}}`            |
| 推奨Issue unit | `{{issue.unit}}`       |
| 推奨Issue type | `{{issue.type}}`       |
| 推奨Issue area | `{{issue.area}}`       |
| 推奨Definition | `{{definition_path}}`  |
| 推奨Template   | `{{template_path}}`    |
| 依存元Issue    | `{{depends_on_issue}}` |
| 依存元PR       | `{{depends_on_pr}}`    |
| no-branch      | `{{branch.no_branch}}` |

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

## 9. 影響範囲

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

## 10. Contract Task化要否

| 項目                | 内容                                |
| ------------------- | ----------------------------------- |
| Contract Task化要否 | `{{contract_task.required}}`        |
| 判断理由            | {{contract_task.reason}}            |
| 推奨Definition      | `{{contract_task.definition_path}}` |
| 推奨Issue種別       | `{{contract_task.issue_type}}`      |
| 推奨Issue unit      | `{{contract_task.issue.unit}}`      |
| 推奨Issue type      | `{{contract_task.issue.type}}`      |
| 推奨Issue area      | `{{contract_task.issue.area}}`      |

### 10.1 Contract Task化が必要な理由

{{#each contract_task.required_reasons}}

- {{this}}
  {{/each}}

{{#unless contract_task.required_reasons}}

- なし
  {{/unless}}

### 10.2 Contract Task化しない理由

{{#each contract_task.not_required_reasons}}

- {{this}}
  {{/each}}

{{#unless contract_task.not_required_reasons}}

- なし
  {{/unless}}

---

## 11. 現在PRへの対応方針

| 項目           | 内容                              |
| -------------- | --------------------------------- |
| 現在PRに残す   | `{{current_pr.keep_changes}}`     |
| 現在PRから戻す | `{{current_pr.revert_changes}}`   |
| PR継続可否     | `{{current_pr.can_continue}}`     |
| 推奨対応       | {{current_pr.recommended_action}} |

### 11.1 現在PRに残す変更

{{#each current_pr.keep_items}}

- {{this}}
  {{/each}}

{{#unless current_pr.keep_items}}

- なし
  {{/unless}}

### 11.2 現在PRから除外する変更

{{#each current_pr.revert_items}}

- {{this}}
  {{/each}}

{{#unless current_pr.revert_items}}

- なし
  {{/unless}}

---

## 12. Branch / Project 方針

| 項目           | 内容                               |
| -------------- | ---------------------------------- |
| 現在Branch     | `{{branch.current}}`               |
| 現在PR target  | `{{branch.target}}`                |
| 推奨Status     | `{{project.recommended_status}}`   |
| Status更新意図 | `{{project.status_update_intent}}` |

### 12.1 新規IssueのBranch方針

{{#each proposed_issues}}

- {{title}}
  - no-branch: `{{branch.no_branch}}`
  - Branch名: `{{branch.name}}`
  - Branch base: `{{branch.base}}`
  - PR target: `{{branch.target}}`
    {{/each}}

{{#unless proposed_issues}}

- なし
  {{/unless}}

---

## 13. 人間に確認したいこと

{{#each human_decision_points}}

- {{this}}
  {{/each}}

{{#unless human_decision_points}}

- なし
  {{/unless}}

---

## 14. AI推奨案

| 項目     | 内容                            |
| -------- | ------------------------------- |
| 推奨案   | `{{recommendation.option_id}}`  |
| 推奨理由 | {{recommendation.reason}}       |
| 確信度   | `{{recommendation.confidence}}` |

### 14.1 補足

{{recommendation.note}}

---

## 15. 推奨次Action

### 15.1 別Issueを作成する場合

```text
{{next_action.on_create_issue}}
```

### 15.2 Contract Taskを作成する場合

```text
{{next_action.on_create_contract_task}}
```

### 15.3 現在PRを修正して継続する場合

```text
{{next_action.on_fix_current_pr}}
```

### 15.4 判断保留にする場合

```text
{{next_action.on_hold}}
```

---

## 16. ai-logs 記録要否

| 項目              | 内容                                          |
| ----------------- | --------------------------------------------- |
| incident log      | `{{operation_logging.ai_logs.incidents}}`     |
| cross-cutting log | `{{operation_logging.ai_logs.cross_cutting}}` |
| log level         | `{{operation_logging.level}}`                 |
| 保存先            | `{{operation_logging.path}}`                  |
| 理由              | {{operation_logging.reason}}                  |

通常作業ログをすべて `ai-logs/` に保存しない。  
別Issue化が横断影響、Contract Task化、判断不能、作業停止を伴う場合のみ、必要に応じて `ai-logs/` に記録する。

---

## 17. 回答してほしい形式

以下のいずれかで回答してください。

```text
別Issue化してください。分割案はA案で進めてください。
```

```text
Contract Taskとして分離してください。
```

```text
現在PRからscope外変更を除外して、元Taskを継続してください。
```

```text
判断保留です。追加で以下を確認してください。
-
```

```text
別Issue化せず、現在Task内で扱ってください。理由は以下です。
-
```

---

## 18. 正本

| 種別         | 参照先                |
| ------------ | --------------------- |
| 作業計画     | `{{issue.url}}`       |
| 作業結果     | `{{pr.url}}`          |
| Definition   | `{{definition.path}}` |
| 関連docs     | `{{docs.url}}`        |
| 関連レビュー | `{{review.url}}`      |
| 関連ai-log   | `{{ai_log.url}}`      |

このフィードバックは、別Issue化要否を判断するための確認依頼である。  
作業計画はIssue、作業結果とレビュー結果はPR、成果物はdocsを正本とする。

---

## 19. 備考

{{#each notes}}

- {{this}}
  {{/each}}

{{#unless notes}}

- なし
  {{/unless}}
