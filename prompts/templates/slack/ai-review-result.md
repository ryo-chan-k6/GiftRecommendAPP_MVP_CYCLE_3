# AI Review Result

## 1. 結論

{{review.summary}}

| 項目          | 内容                     |
| ------------- | ------------------------ |
| Review Result | `{{review.result}}`      |
| 対象PR        | `{{pr.number}}`          |
| 対象Issue     | `{{issue.number}}`       |
| Task ID       | `{{task.id}}`            |
| Definition    | `{{definition.path}}`    |
| Reviewer      | `{{agent.primary}}`      |
| Review日時    | `{{review.reviewed_at}}` |

---

## 2. 判定

{{#if review.result_message}}
{{review.result_message}}
{{else}}

- `approve_for_human_review`: AI Review上は大きな問題なし。Human Reviewへ進めてよい
- `request_changes`: 同一Branchで修正が必要
- `needs_human_decision`: 人間判断が必要
- `split_required`: 別Issue化が必要
- `blocked`: 前提不足でレビュー不可
  {{/if}}

---

## 3. 主な確認内容

{{#each review.checked_points}}

- {{this}}
  {{/each}}

---

## 4. 良い点

{{#each review.good_points}}

- {{this}}
  {{/each}}

{{#unless review.good_points}}

- なし
  {{/unless}}

---

## 5. 修正必須事項

{{#each review.required_fixes}}

- `{{severity}}` {{title}}
  - 対象: `{{target}}`
  - 理由: {{reason}}
  - 推奨対応: {{recommended_action}}
    {{/each}}

{{#unless review.required_fixes}}

- なし
  {{/unless}}

---

## 6. 任意改善事項

{{#each review.optional_improvements}}

- {{title}}
  - 対象: `{{target}}`
  - 改善案: {{suggested_fix}}
    {{/each}}

{{#unless review.optional_improvements}}

- なし
  {{/unless}}

---

## 7. Human Reviewで確認してほしいこと

{{#each human_decision_points}}

- {{this}}
  {{/each}}

{{#unless human_decision_points}}

- なし
  {{/unless}}

---

## 8. テスト・CI確認結果

### 実施済み

{{#each test_results.executed}}

- {{name}}: `{{result}}`
  {{/each}}

{{#unless test_results.executed}}

- なし
  {{/unless}}

### 未実施

{{#each test_results.not_executed}}

- {{name}}
  - 未実施理由: {{reason}}
  - 残リスク: {{risk}}
    {{/each}}

{{#unless test_results.not_executed}}

- なし
  {{/unless}}

### CI

| 項目       | 内容                 |
| ---------- | -------------------- |
| CI実行有無 | `{{ci.executed}}`    |
| CI結果     | `{{ci.result}}`      |
| 失敗Job    | `{{ci.failed_jobs}}` |
| 補足       | {{ci.notes}}         |

---

## 9. 影響確認

| 観点                 | 判定                                  | 補足                                  |
| -------------------- | ------------------------------------- | ------------------------------------- |
| scope / out_of_scope | `{{review.scope_check.result}}`       | {{review.scope_check.notes}}          |
| acceptance criteria  | `{{review.acceptance_result}}`        | {{review.acceptance_notes}}           |
| generated            | `{{review.generated.no_manual_edit}}` | {{review.generated.manual_edit_note}} |
| API / DB / Contract  | `{{review.impact.overall_result}}`    | {{review.impact.notes}}               |
| security             | `{{review.security.overall_result}}`  | {{review.security.notes}}             |
| Branch / PR運用      | `{{review.branch.overall_result}}`    | {{review.branch.notes}}               |

---

## 10. follow-up候補

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

## 11. Status更新意図

| 項目       | 内容                               |
| ---------- | ---------------------------------- |
| 現在Status | `{{project.current_status}}`       |
| 次Status   | `{{project.next_status}}`          |
| 更新意図   | `{{project.status_update_intent}}` |

---

## 12. 次Action

```text
{{review.next_action}}
```

---

## 13. 正本

| 種別          | 参照先                      |
| ------------- | --------------------------- |
| 作業計画      | `{{issue.url}}`             |
| 作業結果      | `{{pr.url}}`                |
| AI Review結果 | `{{pr.review_comment_url}}` |
| 成果物        | `{{docs.url}}`              |

Slack通知は正本ではない。  
作業計画はIssue、作業結果とレビュー結果はPR、成果物はdocsを正本とする。
