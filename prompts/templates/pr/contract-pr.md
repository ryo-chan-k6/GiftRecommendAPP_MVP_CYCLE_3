# {{contract.title}}

## 1. 概要

{{contract.summary}}

| 項目 | 内容 |
| ---- | ---- |
| Contract ID | `{{contract.id}}` |
| Contract種別 | `{{contract.type}}` |
| Definition | `{{definition.path}}` |
| 対象Issue | `{{issue.number}}` |
| Parent Epic Issue | `{{parent.epic_issue}}` |
| Source Branch | `{{branch.name}}` |
| Target Branch | `{{branch.target}}` |

---

## 2. 対象Issue

Related to #{{issue.number}}

Contract Task PRでは原則として `Closes #{{issue.number}}` を使用しない。Task IssueのDone / closeはPR merge時workflowで制御する。

---

## 3. 契約変更内容

| 項目 | 内容 |
| ---- | ---- |
| API ID | `{{change.api_id}}` |
| API名 | {{change.api_name}} |
| API種別 | `{{change.api_kind}}` |
| Method | `{{change.method}}` |
| Endpoint | `{{change.endpoint}}` |
| 変更種別 | `{{change.change_type}}` |
| 破壊的変更 | `{{change.breaking_change}}` |
| 後方互換性 | {{change.backward_compatibility}} |

---

## 4. 対応内容

{{#each work_summary.completed}}
- {{this}}
{{/each}}

---

## 5. scope / out_of_scope 確認

### 5.1 scope

{{#each scope}}
- {{this}}
{{/each}}

### 5.2 out_of_scope

{{#each out_of_scope}}
- {{this}}
{{/each}}

### 5.3 scope外変更

| 項目 | 内容 |
| ---- | ---- |
| scope外変更 | `{{work_summary.scope_out_changes}}` |
| 補足 | {{work_summary.scope_out_notes}} |

---

## 6. 変更ファイル

| 区分 | ファイル |
| ---- | -------- |
| docs | {{changed_files.docs}} |
| OpenAPI | {{changed_files.openapi}} |
| Orval | {{changed_files.orval}} |
| generated | {{changed_files.generated}} |
| provider / consumer | {{changed_files.provider_consumer}} |
| tests | {{changed_files.tests}} |

---

## 7. 影響範囲

| 対象 | 影響有無 | 内容 |
| ---- | -------- | ---- |
| API設計書 | `{{impact.api_design.affected}}` | {{impact.api_design.note}} |
| API一覧 | `{{impact.api_list.affected}}` | {{impact.api_list.note}} |
| API仕様書 | `{{impact.api_spec.affected}}` | {{impact.api_spec.note}} |
| OpenAPI | `{{impact.openapi.affected}}` | {{impact.openapi.note}} |
| Orval | `{{impact.orval.affected}}` | {{impact.orval.note}} |
| generated | `{{impact.generated.affected}}` | {{impact.generated.note}} |
| provider | `{{impact.provider.affected}}` | {{impact.provider.note}} |
| consumer | `{{impact.consumer.affected}}` | {{impact.consumer.note}} |
| DB | `{{impact.db.affected}}` | {{impact.db.note}} |
| security | `{{impact.security.affected}}` | {{impact.security.note}} |

---

## 8. generated 方針

| 項目 | 内容 |
| ---- | ---- |
| generated発生 | `{{generation_policy.generated_expected}}` |
| 手動編集 | `{{generation_policy.manual_edit_allowed}}` |
| 生成元 | {{generation_policy.source_files}} |
| 再生成コマンド | {{generation_policy.regenerate_commands}} |
| 出力先 | {{generation_policy.output_paths}} |
| 検証コマンド | {{generation_policy.verification_commands}} |

generatedファイルは手動編集しない。

---

## 9. テスト・検証結果

### 9.1 実施済み

{{#each test_results.executed}}
- [x] {{this.name}}
  - 結果: `{{this.result}}`
  - 補足: {{this.note}}
{{/each}}

### 9.2 実行コマンド

{{#each test_results.commands}}
```bash
{{this}}
```
{{/each}}

### 9.3 未実施

{{#each test_results.not_executed}}
- [ ] {{this.name}}
  - 未実施理由: {{this.reason}}
  - 代替確認: {{this.alternative_check}}
  - 残リスク: {{this.risk}}
{{/each}}

---

## 10. 互換性・rollout

| 項目 | 内容 |
| ---- | ---- |
| 破壊的変更 | `{{compatibility.breaking_change}}` |
| 後方互換性 | {{compatibility.backward_compatibility}} |
| rollout順 | {{compatibility.rollout_order}} |
| 補足 | {{compatibility.notes}} |

---

## 11. security確認

- [ ] secret、APIキー、access token、password、private keyを含んでいない
- [ ] `.env` 実値を含んでいない
- [ ] DB接続文字列の実値を含んでいない
- [ ] 認証・認可への影響がある場合、影響範囲を明記している

---

## 12. Human Review観点

{{#each human_review_points}}
- {{this}}
{{/each}}

---

## 13. 残課題

{{#each remaining_issues}}
- {{this}}
{{/each}}

---

## 13.5 implementation_gate / Gate 解放

| 項目 | 内容 |
| ---- | ---- |
| gate_id | `{{implementation_gate.gate_id}}` |
| enabled | `{{implementation_gate.enabled}}` |

### prerequisite_checks（マージ前確認）

{{#each implementation_gate.prerequisite_checks}}
- [ ] {{this}}
{{/each}}

### 解放対象 Implementation Task

{{implementation_gate.releases_implementation_for}}

本 Contract PR マージ後、上記 Implementation Task は Contract Gate §4 を満たせば開始可能。

---

## 14. Status更新意図

| 項目 | 内容 |
| ---- | ---- |
| 現在Status | `{{project.current_status}}` |
| 次Status | `AI Review` |
| 更新意図 | `In Progress → AI Review` |
