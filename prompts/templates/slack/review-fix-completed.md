# Review Fix Completed

## 1. 結論

レビュー指摘対応が完了しました。  
再度AI Reviewへ進めます。

| 項目          | 内容                  |
| ------------- | --------------------- |
| 対象PR        | `{{pr.number}}`       |
| PR URL        | `{{pr.url}}`          |
| 対象Issue     | `{{issue.number}}`    |
| Issue URL     | `{{issue.url}}`       |
| Task ID       | `{{task.id}}`         |
| Definition    | `{{definition.path}}` |
| 発生元Command | `{{command.name}}`    |
| 担当Agent     | `{{agent.primary}}`   |
| 対応完了日時  | `{{completed_at}}`    |

---

## 2. 対応概要

{{fix_summary.summary}}

---

## 3. 対応対象レビュー

| 項目              | 内容                                    |
| ----------------- | --------------------------------------- |
| Review種別        | `{{review.type}}`                       |
| Review結果        | `{{review.result}}`                     |
| ReviewコメントURL | `{{review.comment_url}}`                |
| 指摘件数          | `{{review.comment_count}}`              |
| 修正必須件数      | `{{review.required_fix_count}}`         |
| 任意改善件数      | `{{review.optional_improvement_count}}` |

---

## 4. 対応した指摘

{{#each fixed_comments}}

- `{{severity}}` {{title}}
  - 対象: `{{target}}`
  - 指摘内容: {{comment}}
  - 対応内容: {{fix}}
  - 対応状態: `{{status}}`
    {{/each}}

{{#unless fixed_comments}}

- なし
  {{/unless}}

---

## 5. 対応しなかった指摘

{{#each not_fixed_comments}}

- `{{severity}}` {{title}}
  - 対象: `{{target}}`
  - 指摘内容: {{comment}}
  - 未対応理由: {{reason}}
  - 後続対応: {{next_action}}
    {{/each}}

{{#unless not_fixed_comments}}

- なし
  {{/unless}}

---

## 6. 主な変更ファイル

### 6.1 docs

{{#each changed_files.docs}}

- `{{this}}`
  {{/each}}

{{#unless changed_files.docs}}

- なし
  {{/unless}}

### 6.2 source code

{{#each changed_files.source}}

- `{{this}}`
  {{/each}}

{{#unless changed_files.source}}

- なし
  {{/unless}}

### 6.3 tests

{{#each changed_files.tests}}

- `{{this}}`
  {{/each}}

{{#unless changed_files.tests}}

- なし
  {{/unless}}

### 6.4 config / scripts

{{#each changed_files.config}}

- `{{this}}`
  {{/each}}

{{#unless changed_files.config}}

- なし
  {{/unless}}

### 6.5 generated

{{#each changed_files.generated}}

- `{{this}}`
  {{/each}}

{{#unless changed_files.generated}}

- なし
  {{/unless}}

---

## 7. scope / out_of_scope 確認

| 項目                    | 内容                                |
| ----------------------- | ----------------------------------- |
| scope内に収まっているか | `{{fix_summary.scope_satisfied}}`   |
| scope外変更             | `{{fix_summary.scope_out_changes}}` |
| 補足                    | {{fix_summary.scope_out_notes}}     |

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

## 10. 影響確認

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

## 11. generated確認

| 項目              | 内容                                   |
| ----------------- | -------------------------------------- |
| generated差分     | `{{generated.diff_exists}}`            |
| 手動編集有無      | `{{generated.manual_edit}}`            |
| 生成元            | `{{generated.source}}`                 |
| 再生成コマンド    | `{{generated.command}}`                |
| Contract Task要否 | `{{generated.contract_task_required}}` |

### 11.1 generated補足

{{generated.notes}}

---

## 12. Human Reviewで確認してほしいこと

{{#each human_decision_points}}

- {{this}}
  {{/each}}

{{#unless human_decision_points}}

- なし
  {{/unless}}

---

## 13. 残課題 / follow-up候補

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

## 14. Status更新意図

| 項目       | 内容                               |
| ---------- | ---------------------------------- |
| 現在Status | `{{project.current_status}}`       |
| 次Status   | `AI Review`                        |
| 更新意図   | `{{project.status_update_intent}}` |

---

## 15. 次Action

```text
/review-pr @{{review_definition.path}} {{pr.number}}
```

---

## 16. ai-logs 記録要否

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

## 17. 正本

| 種別       | 参照先                   |
| ---------- | ------------------------ |
| 作業計画   | `{{issue.url}}`          |
| 作業結果   | `{{pr.url}}`             |
| Review結果 | `{{review.comment_url}}` |
| Definition | `{{definition.path}}`    |
| 成果物     | `{{docs.url}}`           |

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
