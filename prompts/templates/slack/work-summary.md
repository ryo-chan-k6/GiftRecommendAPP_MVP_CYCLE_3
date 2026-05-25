# Work Summary

## 1. 結論

{{work_summary.summary}}

| 項目          | 内容                     |
| ------------- | ------------------------ |
| Summary種別   | `{{summary.type}}`       |
| 発生元Command | `{{command.name}}`       |
| 対象Issue     | `{{issue.number}}`       |
| 対象PR        | `{{pr.number}}`          |
| Task ID       | `{{task.id}}`            |
| Definition    | `{{definition.path}}`    |
| 担当Agent     | `{{agent.primary}}`      |
| 作成日時      | `{{summary.created_at}}` |

---

## 2. 現在の状態

| 項目           | 内容                               |
| -------------- | ---------------------------------- |
| 現在Status     | `{{project.current_status}}`       |
| 次Status       | `{{project.next_status}}`          |
| Status更新意図 | `{{project.status_update_intent}}` |
| Branch         | `{{branch.name}}`                  |
| PR target      | `{{branch.target}}`                |
| 作業継続可否   | `{{work_summary.can_continue}}`    |
| block状態      | `{{work_summary.blocked}}`         |

---

## 3. 対応内容

今回対応した内容。

{{#each work_summary.completed}}

- {{this}}
  {{/each}}

{{#unless work_summary.completed}}

- なし
  {{/unless}}

---

## 4. 未対応事項

今回対応していない事項。

{{#each work_summary.not_done}}

- {{this}}
  {{/each}}

{{#unless work_summary.not_done}}

- なし
  {{/unless}}

---

## 5. 主な変更ファイル

### 5.1 docs

{{#each changed_files.docs}}

- `{{this}}`
  {{/each}}

{{#unless changed_files.docs}}

- なし
  {{/unless}}

### 5.2 source code

{{#each changed_files.source}}

- `{{this}}`
  {{/each}}

{{#unless changed_files.source}}

- なし
  {{/unless}}

### 5.3 tests

{{#each changed_files.tests}}

- `{{this}}`
  {{/each}}

{{#unless changed_files.tests}}

- なし
  {{/unless}}

### 5.4 config / scripts

{{#each changed_files.config}}

- `{{this}}`
  {{/each}}

{{#unless changed_files.config}}

- なし
  {{/unless}}

### 5.5 generated

{{#each changed_files.generated}}

- `{{this}}`
  {{/each}}

{{#unless changed_files.generated}}

- なし
  {{/unless}}

---

## 6. 成果物

{{#each deliverables}}

- {{this}}
  {{/each}}

{{#unless deliverables}}

- なし
  {{/unless}}

---

## 7. scope / out_of_scope 確認

| 項目                    | 内容                                 |
| ----------------------- | ------------------------------------ |
| scope内に収まっているか | `{{work_summary.scope_satisfied}}`   |
| scope外変更             | `{{work_summary.scope_out_changes}}` |
| 補足                    | {{work_summary.scope_out_notes}}     |

### 7.1 scope

{{#each scope}}

- {{this}}
  {{/each}}

{{#unless scope}}

- なし
  {{/unless}}

### 7.2 out_of_scope

{{#each out_of_scope}}

- {{this}}
  {{/each}}

{{#unless out_of_scope}}

- なし
  {{/unless}}

---

## 8. テスト・検証結果

### 8.1 実施済み

{{#each test_results.executed}}

- {{name}}: `{{result}}`
  - 補足: {{note}}
    {{/each}}

{{#unless test_results.executed}}

- なし
  {{/unless}}

### 8.2 実行コマンド

{{#each test_results.commands}}

```bash
{{this}}
```

{{/each}}

{{#unless test_results.commands}}

```text
なし
```

{{/unless}}

### 8.3 manual checks

{{#each test_results.manual_checks}}

- {{this}}
  {{/each}}

{{#unless test_results.manual_checks}}

- なし
  {{/unless}}

### 8.4 未実施

{{#each test_results.not_executed}}

- {{name}}
  - 未実施理由: {{reason}}
  - 代替確認: {{alternative_check}}
  - 残リスク: {{risk}}
    {{/each}}

{{#unless test_results.not_executed}}

- なし
  {{/unless}}

> 実施していないテストを、実施済みとして扱わない。

---

## 9. CI結果

| 項目       | 内容                 |
| ---------- | -------------------- |
| CI実行有無 | `{{ci.executed}}`    |
| CI結果     | `{{ci.result}}`      |
| 失敗Job    | `{{ci.failed_jobs}}` |
| 補足       | {{ci.notes}}         |

---

## 10. Review状況

| 項目              | 内容                               |
| ----------------- | ---------------------------------- |
| AI Review実施有無 | `{{review.ai_review_executed}}`    |
| AI Review結果     | `{{review.result}}`                |
| Human Review要否  | `{{review.human_review_required}}` |
| Human Review状況  | `{{review.human_review_status}}`   |
| Reviewコメント    | `{{review.url}}`                   |

### 10.1 AI Review要約

{{review.summary}}

### 10.2 修正必須事項

{{#each review.required_fixes}}

- `{{severity}}` {{title}}
  - 対象: `{{target}}`
  - 推奨対応: {{recommended_action}}
    {{/each}}

{{#unless review.required_fixes}}

- なし
  {{/unless}}

---

## 11. 影響確認

| 観点        | 影響有無               | 補足                      |
| ----------- | ---------------------- | ------------------------- |
| docs        | `{{impact.docs}}`      | {{impact.docs_note}}      |
| source code | `{{impact.source}}`    | {{impact.source_note}}    |
| tests       | `{{impact.tests}}`     | {{impact.tests_note}}     |
| API仕様     | `{{impact.api_spec}}`  | {{impact.api_spec_note}}  |
| OpenAPI     | `{{impact.openapi}}`   | {{impact.openapi_note}}   |
| Orval       | `{{impact.orval}}`     | {{impact.orval_note}}     |
| generated   | `{{impact.generated}}` | {{impact.generated_note}} |
| DB schema   | `{{impact.db_schema}}` | {{impact.db_schema_note}} |
| CI/CD       | `{{impact.cicd}}`      | {{impact.cicd_note}}      |
| security    | `{{impact.security}}`  | {{impact.security_note}}  |

---

## 12. generated確認

| 項目              | 内容                                   |
| ----------------- | -------------------------------------- |
| generated差分     | `{{generated.diff_exists}}`            |
| 手動編集有無      | `{{generated.manual_edit}}`            |
| 生成元            | `{{generated.source}}`                 |
| 再生成コマンド    | `{{generated.command}}`                |
| Contract Task要否 | `{{generated.contract_task_required}}` |

### 12.1 generated補足

{{generated.notes}}

---

## 13. Human Reviewで確認してほしいこと

{{#each human_decision_points}}

- {{this}}
  {{/each}}

{{#unless human_decision_points}}

- なし
  {{/unless}}

---

## 14. 残課題 / follow-up候補

{{#each follow_up.items}}

- {{description}}
  - 種別: `{{type}}`
  - 推奨対応: {{recommended_action}}
  - 別Issue化要否: `{{issue_required}}`
    {{/each}}

{{#unless follow_up.items}}

- なし
  {{/unless}}

---

## 15. ai-logs 記録要否

| 項目          | 内容                                          |
| ------------- | --------------------------------------------- |
| intake        | `{{operation_logging.ai_logs.intake}}`        |
| incidents     | `{{operation_logging.ai_logs.incidents}}`     |
| cross-cutting | `{{operation_logging.ai_logs.cross_cutting}}` |
| experiments   | `{{operation_logging.ai_logs.experiments}}`   |
| log level     | `{{operation_logging.level}}`                 |
| 理由          | {{operation_logging.reason}}                  |

通常作業ログをすべて `ai-logs/` に保存しない。

---

## 16. 次Action

```text
{{next_action.command}}
```

### 16.1 補足

{{next_action.note}}

---

## 17. 正本

| 種別       | 参照先                |
| ---------- | --------------------- |
| 作業計画   | `{{issue.url}}`       |
| 作業結果   | `{{pr.url}}`          |
| Definition | `{{definition.path}}` |
| Review結果 | `{{review.url}}`      |
| 成果物     | `{{docs.url}}`        |

Slack通知は正本ではない。  
作業計画はIssue、作業結果とレビュー結果はPR、成果物はdocsを正本とする。

---

## 18. 備考

{{#each notes}}

- {{this}}
  {{/each}}

{{#unless notes}}

- なし
  {{/unless}}
