# {{epic.title}}

## 1. 概要

{{epic.summary}}

| 項目 | 内容 |
| ---- | ---- |
| Epic ID | `{{epic.id}}` |
| 対象Epic Issue | `{{issue.number}}` |
| Definition | `{{definition.path}}` |
| Source Branch | `{{branch.name}}` |
| Target Branch | `{{branch.target}}` |

---

## 2. 対象Issue

Closes #{{issue.number}}

Epic PRのtargetは原則として `develop` とする。merge判断はHuman Reviewで行う。

---

## 3. Epic Scope

| 項目 | 内容 |
| ---- | ---- |
| 対象識別子 | `{{epic_scope.artifact_id}}` |
| allowed_paths | {{epic_scope.allowed_paths}} |
| forbidden_paths | {{epic_scope.forbidden_paths}} |

---

## 4. 統合したTask

| Task Issue | Task名 | PR | 状態 | 備考 |
| ---------- | ------ | -- | ---- | ---- |
{{#each child_tasks}}
| `{{issue}}` | {{title}} | `{{pr}}` | {{status}} | {{note}} |
{{/each}}

---

## 5. 対応内容

{{#each work_summary.completed}}
- {{this}}
{{/each}}

---

## 6. 変更ファイル

| 区分 | ファイル |
| ---- | -------- |
| docs | {{changed_files.docs}} |
| source | {{changed_files.source}} |
| tests | {{changed_files.tests}} |
| config / generated | {{changed_files.config_generated}} |

---

## 7. Epic完了条件

{{#each acceptance_criteria}}
- [{{#if satisfied}}x{{else}} {{/if}}] {{description}}
  - 確認結果: {{result_note}}
{{/each}}

---

## 8. テスト・検証結果

### 8.1 実施済み

{{#each test_results.executed}}
- [x] {{this.name}}
  - 結果: `{{this.result}}`
  - 補足: {{this.note}}
{{/each}}

### 8.2 実行コマンド

{{#each test_results.commands}}
```bash
{{this}}
```
{{/each}}

### 8.3 未実施

{{#each test_results.not_executed}}
- [ ] {{this.name}}
  - 未実施理由: {{this.reason}}
  - 代替確認: {{this.alternative_check}}
  - 残リスク: {{this.risk}}
{{/each}}

---

## 9. 横断影響

| 対象 | 影響有無 | 内容 |
| ---- | -------- | ---- |
| API contract | `{{impact.api_contract.affected}}` | {{impact.api_contract.note}} |
| DB | `{{impact.db.affected}}` | {{impact.db.note}} |
| generated | `{{impact.generated.affected}}` | {{impact.generated.note}} |
| CI/CD | `{{impact.cicd.affected}}` | {{impact.cicd.note}} |
| security | `{{impact.security.affected}}` | {{impact.security.note}} |

---

## 10. AI Review結果

| 項目 | 内容 |
| ---- | ---- |
| AI Review実施 | `{{ai_review.executed}}` |
| Review Result | `{{ai_review.result}}` |
| 指摘残 | `{{ai_review.remaining_findings}}` |
| 補足 | {{ai_review.note}} |

---

## 11. Human Review観点

{{#each human_review_points}}
- {{this}}
{{/each}}

---

## 12. 残課題

{{#each remaining_issues}}
- {{this}}
{{/each}}

---

## 13. Status更新意図

| 項目 | 内容 |
| ---- | ---- |
| 現在Status | `{{project.current_status}}` |
| 次Status | `AI Review` |
| 更新意図 | `In Progress → AI Review` |
