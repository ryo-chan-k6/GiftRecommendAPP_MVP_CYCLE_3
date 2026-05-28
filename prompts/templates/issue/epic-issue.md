# {{epic.title}}

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Epic ID | `{{epic.id}}` |
| Epic名 | `{{epic.title}}` |
| Definition | `{{definition.path}}` |
| 成果物識別子 | `{{epic_scope.artifact_id}}` |
| workstream_key | `{{epic.workstream_key}}` |
| 親Issue | {{parent.issue}} |
| 作業主体 | `{{work_mode}}` |

---

## 2. Issue運用メタデータ

Issue同期・Project同期・Branch作成に使う機械可読ブロック。`###` 見出し名を変更しない。

### 作業単位
{{issue.unit}}

### 作業種別
{{issue.type}}

### 作業主体
{{work_mode}}

### 初期Status
{{project.fields.status}}

### プロジェクト工程
{{project.fields.phase}}

### 優先度
{{project.fields.priority}}

### 対象領域
{{issue.area}}

### Planned Start
{{project.fields.planned_start}}

### Due Date
{{project.fields.due_date}}

### Milestone
{{milestone.name}}

### 親Issue
{{parent.issue}}

### Branch summary
{{branch.summary}}

### Branch作成制御
- [{{#if branch.no_branch}}x{{else}} {{/if}}] no-branch

### Branch base
{{branch.base}}

### PR target
{{branch.target}}

---

## 5. 背景

{{background}}

---

## 6. 目的

{{objective}}

---

## 7. scope

{{#each scope}}
- {{this}}
{{/each}}

---

## 8. out_of_scope

{{#each out_of_scope}}
- {{this}}
{{/each}}

---

## 9. epic_scope

| 項目 | 内容 |
| ---- | ---- |
| artifact_id | `{{epic_scope.artifact_id}}` |

### 9.1 allowed_paths

{{#each epic_scope.allowed_paths}}
- `{{this}}`
{{/each}}

### 9.2 forbidden_paths

{{#each epic_scope.forbidden_paths}}
- `{{this}}`
{{/each}}

### 9.3 child_task_areas

{{#each epic_scope.child_task_areas}}
- `{{this}}`
{{/each}}

---

## 10. 依存Epic

{{#each dependencies.epics}}
- {{this}}
{{/each}}

---

## 11. 子Task候補

{{#each child_tasks}}
- {{this}}
{{/each}}

---

## 12. 入力資料

### 12.1 input docs

{{#each input.docs}}
- `{{path}}`
  - required: `{{required}}`
  - purpose: {{purpose}}
{{/each}}

### 12.2 input files

{{#each input.files}}
- `{{path}}`
  - required: `{{required}}`
  - purpose: {{purpose}}
{{/each}}

---

## 13. 管理対象成果物

### 13.1 docs

{{#each output.docs}}
- `{{path}}`
  - action: `{{action}}`
  - required: `{{required}}`
  - template: `{{template}}`
{{/each}}

### 13.2 files

{{#each output.files}}
- `{{path}}`
  - action: `{{action}}`
  - required: `{{required}}`
{{/each}}

### 13.3 tests

{{#each output.tests}}
- `{{path}}`
  - action: `{{action}}`
  - required: `{{required}}`
{{/each}}

---

## 14. 完了条件

{{#each acceptance_criteria}}
- [ ] {{this}}
{{/each}}

---

## 15. レビュー方針

| 項目 | 内容 |
| ---- | ---- |
| AI Review required | `{{review.ai_review_required}}` |
| Human Review required | `{{review.human_review_required}}` |
| Docs Review | `{{review.specialist_reviews.docs}}` |
| Test Review | `{{review.specialist_reviews.test}}` |
| Contract Review | `{{review.specialist_reviews.contract}}` |
| Security Review | `{{review.specialist_reviews.security}}` |

### 15.1 review points

{{#each review.review_points}}
- {{this}}
{{/each}}

### 15.2 Human Reviewで確認してほしいこと

{{#each human_decision_points}}
- {{this}}
{{/each}}

---

## 16. 停止条件

{{#each stop_conditions}}
- {{this}}
{{/each}}

---

## 17. operation_logging

| 項目 | 内容 |
| ---- | ---- |
| log level | `{{operation_logging.level}}` |
| intake log | `{{operation_logging.ai_logs.intake}}` |
| incident log | `{{operation_logging.ai_logs.incidents}}` |
| cross-cutting log | `{{operation_logging.ai_logs.cross_cutting}}` |
| experiment log | `{{operation_logging.ai_logs.experiments}}` |
| reason | {{operation_logging.reason}} |

通常作業ログをすべて `ai-logs/` に保存しない。
