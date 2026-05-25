# {{contract.title}}

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Contract ID | `{{contract.id}}` |
| Contract種別 | `{{contract.type}}` |
| Definition | `{{definition.path}}` |
| 発生元 | `{{source.discovered_from}}` |
| 関連Issue | `{{source.related_issue}}` |
| 関連PR | `{{source.related_pr}}` |
| Parent Epic Issue | `{{parent.epic_issue}}` |
| Parent Epic Branch | `{{parent.epic_branch}}` |
| 作業主体 | `{{work_mode}}` |

---

## 2. 契約変更内容

| 項目 | 内容 |
| ---- | ---- |
| API名 | `{{change.api_name}}` |
| API種別 | `{{change.api_kind}}` |
| Endpoint | `{{change.endpoint}}` |
| Method | `{{change.method}}` |
| 変更種別 | `{{change.change_type}}` |
| 破壊的変更 | `{{change.breaking_change}}` |
| 後方互換性 | `{{change.backward_compatibility}}` |
| 変更理由 | {{change.reason}} |

破壊的変更、後方互換性不明、provider / consumer影響不明の場合は、人間確認へ回す。

---

## 3. Project同期項目

| 項目 | 内容 |
| ---- | ---- |
| Project | `{{project.project_name}}` |
| 初期Status | `{{project.fields.status}}` |
| Phase | `{{project.fields.phase}}` |
| Priority | `{{project.fields.priority}}` |
| Area | `{{project.fields.area}}` |
| Planned Start | `{{project.fields.planned_start}}` |
| Due Date | `{{project.fields.due_date}}` |
| Milestone | `{{milestone.name}}` |

---

## 4. Issue同期項目

GitHub Labelは本文に列挙しない。workflowが以下の値から `unit:*` / `type:*` / `area:*` / `priority:*` を導出する。

| 項目 | 内容 |
| ---- | ---- |
| unit | `{{issue.unit}}` |
| type | `{{issue.type}}` |
| area | `{{issue.area}}` |
| priority | `{{project.fields.priority}}` |
| Contract Task | `true` |

---

## 5. Branch / PR 方針

- [{{#if branch.no_branch}}x{{else}} {{/if}}] no-branch

| 項目 | 内容 |
| ---- | ---- |
| Branch名 | `{{branch.name}}` |
| Branch summary | `{{branch.summary}}` |
| Branch base | `{{branch.base}}` |
| PR target | `{{branch.target}}` |
| worktree要否 | `{{branch.worktree_required}}` |

- `no-branch` はIssue本文チェックのみを正本とする。GitHub Label `no-branch` は定義しない・付与しない。
- Contract Task PRはParent Epic Branchへ向ける。
- Contract Task PRでは `Related to #<Task Issue番号>` を使用し、原則として `Closes #<Task Issue番号>` は使用しない。
- OpenAPI / Orval / generated影響を通常Taskに混在させない。

---

## 6. scope

{{#each scope}}
- {{this}}
{{/each}}

---

## 7. out_of_scope

{{#each out_of_scope}}
- {{this}}
{{/each}}

---

## 8. 入力資料

### 8.1 input docs

{{#each input.docs}}
- `{{path}}`
  - required: `{{required}}`
  - purpose: {{purpose}}
{{/each}}

### 8.2 OpenAPI / Orval / generated

| 項目 | 内容 |
| ---- | ---- |
| OpenAPI | `{{input.openapi.path}}` |
| Orval | `{{input.orval.path}}` |
| generated | `{{input.generated.paths}}` |

---

## 9. 出力先

### 9.1 docs / files

{{#each output.docs}}
- `{{path}}`
  - action: `{{action}}`
  - required: `{{required}}`
  - template: `{{template}}`
{{/each}}

{{#each output.files}}
- `{{path}}`
  - action: `{{action}}`
  - required: `{{required}}`
{{/each}}

### 9.2 OpenAPI / Orval / generated / tests

{{#each output.openapi}}
- `{{path}}`
  - action: `{{action}}`
  - required: `{{required}}`
{{/each}}

{{#each output.orval}}
- `{{path}}`
  - action: `{{action}}`
  - required: `{{required}}`
{{/each}}

{{#each output.generated}}
- `{{path}}`
  - action: `{{action}}`
  - required: `{{required}}`
{{/each}}

{{#each output.tests}}
- `{{path}}`
  - action: `{{action}}`
  - required: `{{required}}`
{{/each}}

---

## 10. 影響範囲

| 観点 | 影響有無 | 補足 |
| ---- | -------- | ---- |
| API設計 | `{{impact.api_design.affected}}` | {{impact.api_design.note}} |
| API一覧 | `{{impact.api_list.affected}}` | {{impact.api_list.note}} |
| API仕様 | `{{impact.api_spec.affected}}` | {{impact.api_spec.note}} |
| OpenAPI | `{{impact.openapi.affected}}` | {{impact.openapi.note}} |
| Orval | `{{impact.orval.affected}}` | {{impact.orval.note}} |
| generated | `{{impact.generated.affected}}` | {{impact.generated.note}} |
| provider | `{{impact.provider.affected}}` | {{impact.provider.note}} |
| consumer | `{{impact.consumer.affected}}` | {{impact.consumer.note}} |
| DB | `{{impact.db.affected}}` | {{impact.db.note}} |
| CI/CD | `{{impact.cicd.affected}}` | {{impact.cicd.note}} |
| security | `{{impact.security.affected}}` | {{impact.security.note}} |

---

## 11. generated / 再生成方針

| 項目 | 内容 |
| ---- | ---- |
| generated差分想定 | `{{generation_policy.generated_expected}}` |
| 手動編集許可 | `{{generation_policy.manual_edit_allowed}}` |
| 生成元ファイル | `{{generation_policy.source_files}}` |
| 出力先 | `{{generation_policy.output_paths}}` |

{{#each generation_policy.regenerate_commands}}
```bash
{{this}}
```
{{/each}}

generatedファイルは手動編集しない。再生成方針が不明な場合は作業を停止する。

---

## 12. 完了条件

{{#each acceptance_criteria}}
- [ ] {{this}}
{{/each}}

---

## 13. テスト・検証方針

{{#each test_policy.required}}
- {{this}}
{{/each}}

{{#each test_policy.commands}}
```bash
{{this}}
```
{{/each}}

---

## 14. レビュー方針

| 項目 | 内容 |
| ---- | ---- |
| AI Review required | `{{review.ai_review_required}}` |
| Human Review required | `{{review.human_review_required}}` |
| Contract Review | `{{review.specialist_reviews.contract}}` |
| Security Review | `{{review.specialist_reviews.security}}` |

### 14.1 review points

{{#each review.review_points}}
- {{this}}
{{/each}}

### 14.2 Human Reviewで確認してほしいこと

{{#each human_decision_points}}
- {{this}}
{{/each}}

---

## 15. operation_logging

| 項目 | 内容 |
| ---- | ---- |
| log level | `{{operation_logging.level}}` |
| cross-cutting log | `{{operation_logging.ai_logs.cross_cutting}}` |
| incident log | `{{operation_logging.ai_logs.incidents}}` |
| reason | {{operation_logging.reason}} |
