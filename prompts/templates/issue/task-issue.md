# {{task.title}}

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Task ID | `{{task.id}}` |
| Task種別 | `{{task.type}}` |
| Definition | `{{definition.path}}` |
| Parent Epic Issue | `{{parent.epic_issue}}` |
| Parent Epic Branch | `{{parent.epic_branch}}` |
| 作業主体 | `{{work_mode}}` |
| 主担当Agent | `{{agent.primary}}` |

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
{{parent.epic_issue}}

### Parent Epic Branch
{{parent.epic_branch}}

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

## 8.5 contract_gate（Implementation Task・該当時）

| 項目 | 内容 |
| ---- | ---- |
| required | `{{contract_gate.required}}` |
| gate_id | `{{contract_gate.gate_id}}` |

### prerequisite_contract_tasks

{{#each contract_gate.prerequisite_contract_tasks}}
- issue: `{{issue}}`
  - definition: `{{definition}}`
{{/each}}

### verify_at

{{#each contract_gate.verify_at}}
- {{this}}
{{/each}}

### blocked_message

{{contract_gate.blocked_message}}

`required: true` の場合、Gate未通過時は作業を開始しない。正本は `docs/00_共通/AIエージェント運用/Contract Gate運用設計書.md` §4。

---

## 9. 入力資料

### 9.1 input docs

{{#each input.docs}}
- `{{path}}`
  - required: `{{required}}`
  - purpose: {{purpose}}
{{/each}}

### 9.2 input templates

{{#each input.templates}}
- `{{path}}`
  - required: `{{required}}`
  - purpose: {{purpose}}
{{/each}}

### 9.3 input files

{{#each input.files}}
- `{{path}}`
  - required: `{{required}}`
  - purpose: {{purpose}}
{{/each}}

---

## 10. 出力先

### 10.1 output docs

{{#each output.docs}}
- `{{path}}`
  - action: `{{action}}`
  - required: `{{required}}`
  - template: `{{template}}`
{{/each}}

### 10.2 output files

{{#each output.files}}
- `{{path}}`
  - action: `{{action}}`
  - required: `{{required}}`
{{/each}}

### 10.3 output tests

{{#each output.tests}}
- `{{path}}`
  - action: `{{action}}`
  - required: `{{required}}`
{{/each}}

### 10.4 generated

| 項目 | 内容 |
| ---- | ---- |
| generated差分想定 | `{{output.generated.expected}}` |
| 対象path | `{{output.generated.paths}}` |
| 扱い | `{{output.generated.handling}}` |

generatedファイルは手動編集しない。

---

## 11. 完了条件

{{#each acceptance_criteria}}
- [ ] {{this}}
{{/each}}

---

## 12. テスト・検証方針

### 12.1 required

{{#each test_policy.required}}
- {{this}}
{{/each}}

### 12.2 commands

{{#each test_policy.commands}}
```bash
{{this}}
```
{{/each}}

### 12.3 not required / skip reason

{{#each test_policy.not_required}}
- {{this}}
{{/each}}

{{#each test_policy.skip_reason}}
- {{@key}}: {{this}}
{{/each}}

実施していないテストを、実施済みとして報告しない。

---

## 13. レビュー方針

| 項目 | 内容 |
| ---- | ---- |
| AI Review required | `{{review.ai_review_required}}` |
| Human Review required | `{{review.human_review_required}}` |
| Docs Review | `{{review.specialist_reviews.docs}}` |
| Test Review | `{{review.specialist_reviews.test}}` |
| Contract Review | `{{review.specialist_reviews.contract}}` |
| Security Review | `{{review.specialist_reviews.security}}` |

### 13.1 review points

{{#each review.review_points}}
- {{this}}
{{/each}}

### 13.2 Human Reviewで確認してほしいこと

{{#each human_decision_points}}
- {{this}}
{{/each}}

---

## 14. 停止条件

{{#each stop_conditions}}
- {{this}}
{{/each}}

---

## 15. operation_logging

| 項目 | 内容 |
| ---- | ---- |
| log level | `{{operation_logging.level}}` |
| intake log | `{{operation_logging.ai_logs.intake}}` |
| incident log | `{{operation_logging.ai_logs.incidents}}` |
| cross-cutting log | `{{operation_logging.ai_logs.cross_cutting}}` |
| experiment log | `{{operation_logging.ai_logs.experiments}}` |
| reason | {{operation_logging.reason}} |

通常作業ログをすべて `ai-logs/` に保存しない。
