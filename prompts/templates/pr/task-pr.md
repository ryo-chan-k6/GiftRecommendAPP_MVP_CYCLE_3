# {{task.title}}

## 1. 概要

{{task.summary}}

| 項目 | 内容 |
| ---- | ---- |
| Task ID | `{{task.id}}` |
| Definition | `{{definition.path}}` |
| 対象Issue | `{{issue.number}}` |
| Parent Epic Issue | `{{parent.epic_issue}}` |
| Source Branch | `{{branch.name}}` |
| Target Branch | `{{branch.target}}` |

---

## 2. 対象Issue

Related to #{{issue.number}}

Task PRでは原則として `Closes #{{issue.number}}` を使用しない。Task IssueのDone / closeはPR merge時workflowで制御する。

---

## 3. 対応内容

{{#each work_summary.completed}}
- {{this}}
{{/each}}

---

## 4. scope / out_of_scope 確認

### 4.1 scope

{{#each scope}}
- {{this}}
{{/each}}

### 4.2 out_of_scope

{{#each out_of_scope}}
- {{this}}
{{/each}}

### 4.3 scope外変更

| 項目 | 内容 |
| ---- | ---- |
| scope外変更 | `{{work_summary.scope_out_changes}}` |
| 補足 | {{work_summary.scope_out_notes}} |

---

## 5. 変更ファイル

| 区分 | ファイル |
| ---- | -------- |
| docs | {{changed_files.docs}} |
| source | {{changed_files.source}} |
| tests | {{changed_files.tests}} |
| config / scripts | {{changed_files.config}} |
| generated | {{changed_files.generated}} |

---

## 6. テスト・検証結果

### 6.1 実施済み

{{#each test_results.executed}}
- [x] {{this.name}}
  - 結果: `{{this.result}}`
  - 補足: {{this.note}}
{{/each}}

### 6.2 実行コマンド

{{#each test_results.commands}}
```bash
{{this}}
```
{{/each}}

### 6.3 未実施

{{#each test_results.not_executed}}
- [ ] {{this.name}}
  - 未実施理由: {{this.reason}}
  - 代替確認: {{this.alternative_check}}
  - 残リスク: {{this.risk}}
{{/each}}

実施していないテストを、実施済みとして記載しない。

---

## 7. CI結果

| 項目 | 内容 |
| ---- | ---- |
| CI実行有無 | `{{ci.executed}}` |
| CI結果 | `{{ci.result}}` |
| 失敗Job | `{{ci.failed_jobs}}` |
| 補足 | {{ci.notes}} |

---

## 8. generated確認

| 項目 | 内容 |
| ---- | ---- |
| generated差分 | `{{generated.diff_exists}}` |
| 手動編集有無 | `{{generated.manual_edit}}` |
| 生成元 | `{{generated.source}}` |
| 再生成コマンド | `{{generated.command}}` |
| Contract Task要否 | `{{generated.contract_task_required}}` |

generatedファイルは手動編集しない。

---

## 8.5 Contract Gate 確認（該当時）

| 項目 | 内容 |
| ---- | ---- |
| Gate必須 | `{{contract_gate.required}}` |
| gate_id | `{{contract_gate.gate_id}}` |

### 通過確認

- [ ] 先行 Contract Task の PR が親 Epic Branch にマージ済み
- [ ] OpenAPI 正本（`packages/contracts/openapi/`）が Contract PR と整合
- [ ] generated 影響時は Orval 再生成済み（手動編集なし）
- [ ] 契約 docs は `api-contract-spec.md` / `openapi-spec.md` を正本とする（`api-spec.md` は使用しない）
- [ ] 破壊的変更時は Contract PR の Human Review 完了

Gate未通過のまま Implementation を進めていないこと。

### docs テンプレ使い分け

| 種別 | テンプレート |
| ---- | ------------ |
| 契約面 | `prompts/templates/docs/**/api-contract-spec.md` |
| 実装面 | `prompts/templates/docs/**/api-implementation-spec.md` |

---

## 9. API / DB / Contract / security 影響

| 観点 | 影響有無 | 補足 |
| ---- | -------- | ---- |
| API仕様 | `{{impact.api_spec}}` | {{impact.api_spec_note}} |
| OpenAPI | `{{impact.openapi}}` | {{impact.openapi_note}} |
| Orval | `{{impact.orval}}` | {{impact.orval_note}} |
| API client | `{{impact.api_client}}` | {{impact.api_client_note}} |
| DB schema | `{{impact.db_schema}}` | {{impact.db_schema_note}} |
| migration | `{{impact.migration}}` | {{impact.migration_note}} |
| CI/CD | `{{impact.cicd}}` | {{impact.cicd_note}} |
| security | `{{impact.security}}` | {{impact.security_note}} |

---

## 10. security確認

- [ ] secret、APIキー、access token、password、private keyを含んでいない
- [ ] `.env` 実値を含んでいない
- [ ] DB接続文字列の実値を含んでいない
- [ ] ログ出力に機密情報を含めていない

---

## 11. 完了条件チェック

{{#each acceptance_criteria}}
- [{{#if satisfied}}x{{else}} {{/if}}] {{description}}
  - 確認結果: {{result_note}}
{{/each}}

---

## 12. Review観点

{{#each review.review_points}}
- {{this}}
{{/each}}

---

## 13. Human Reviewで確認してほしいこと

{{#each human_decision_points}}
- {{this}}
{{/each}}

人間判断が不要な場合は `なし` と記載する。

---

## 14. 未実施事項 / 残課題

{{#each work_summary.not_done}}
- {{this}}
{{/each}}

{{#each follow_up.items}}
- 内容: {{this.description}}
  - 種別: `{{this.type}}`
  - 推奨対応: {{this.recommended_action}}
  - 別Issue化要否: `{{this.issue_required}}`
{{/each}}

---

## 15. Status更新意図

| 項目 | 内容 |
| ---- | ---- |
| 現在Status | `{{project.current_status}}` |
| 次Status | `AI Review` |
| 更新意図 | `In Progress → AI Review` |
