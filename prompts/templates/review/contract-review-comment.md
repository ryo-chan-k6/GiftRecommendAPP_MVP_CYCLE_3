# Contract Review Result

## 1. レビュー結果

| 項目 | 内容 |
| ---- | ---- |
| Review Result | `{{review.result}}` |
| 対象PR | `{{pr.number}}` |
| 対象Issue | `{{issue.number}}` |
| Contract ID | `{{contract.id}}` |
| Definition | `{{definition.path}}` |
| Reviewer | `{{agent.primary}}` |
| Review日時 | `{{review.reviewed_at}}` |

### Review Result の分類

| 分類 | 意味 | 次Action |
| ---- | ---- | -------- |
| `approve_for_human_review` | Contract Review上は大きな問題なし。Human Reviewへ進めてよい | Human Review |
| `request_changes` | 同一Branchで修正が必要 | `/fix-review-comments` |
| `needs_human_decision` | 契約変更方針に人間判断が必要 | Human判断待ち |
| `split_required` | 別Contract Taskまたは別Task化が必要 | Issue分割 |
| `blocked` | 前提不足でレビュー不可 | 前提解消 |

---

## 2. 結論

{{review.summary}}

---

## 3. 確認した事実

{{#each review.facts}}

- {{this}}
  {{/each}}

---

## 4. 必須確認

| 観点 | 判定 | 補足 |
| ---- | ---- | ---- |
| API仕様書とOpenAPIが一致 | `{{contract_check.api_spec_openapi}}` | {{contract_check.api_spec_openapi_note}} |
| OpenAPIとgeneratedが一致 | `{{contract_check.openapi_generated}}` | {{contract_check.openapi_generated_note}} |
| Orval設定が妥当 | `{{contract_check.orval}}` | {{contract_check.orval_note}} |
| provider変更が反映済み | `{{contract_check.provider}}` | {{contract_check.provider_note}} |
| consumer影響が確認済み | `{{contract_check.consumer}}` | {{contract_check.consumer_note}} |
| contract testが妥当 | `{{contract_check.tests}}` | {{contract_check.tests_note}} |
| generated手動編集なし | `{{contract_check.no_manual_generated_edit}}` | {{contract_check.no_manual_generated_edit_note}} |
| secret混入なし | `{{contract_check.no_secret}}` | {{contract_check.no_secret_note}} |

---

## 5. 互換性確認

| 項目 | 内容 |
| ---- | ---- |
| 破壊的変更 | `{{compatibility.breaking_change}}` |
| 後方互換性 | {{compatibility.backward_compatibility}} |
| 影響範囲 | {{compatibility.impact_scope}} |
| rollout順 | {{compatibility.rollout_order}} |
| Human判断要否 | `{{compatibility.human_decision_required}}` |

---

## 6. provider / consumer 確認

### 6.1 provider

{{#each provider_consumer.providers}}

- `{{name}}`
  - 影響有無: `{{affected}}`
  - 確認結果: {{review_result}}
  - 補足: {{note}}
    {{/each}}

### 6.2 consumer

{{#each provider_consumer.consumers}}

- `{{name}}`
  - 影響有無: `{{affected}}`
  - 確認結果: {{review_result}}
  - 補足: {{note}}
    {{/each}}

---

## 7. 修正必須事項

{{#each review.required_fixes}}

### 7.{{@index}} {{this.title}}

| 項目 | 内容 |
| ---- | ---- |
| 重要度 | `{{this.severity}}` |
| 対象 | `{{this.target}}` |
| 分類 | `{{this.category}}` |
| 対応方針 | `{{this.recommended_action}}` |

#### 指摘内容

{{this.description}}

#### 理由

{{this.reason}}

#### 修正案

{{this.suggested_fix}}

{{/each}}

修正必須事項がない場合は `なし` と記載する。

---

## 8. 任意改善事項

{{#each review.optional_improvements}}

### 8.{{@index}} {{this.title}}

| 項目 | 内容 |
| ---- | ---- |
| 重要度 | `{{this.severity}}` |
| 対象 | `{{this.target}}` |
| 分類 | `{{this.category}}` |

#### 内容

{{this.description}}

#### 改善案

{{this.suggested_fix}}

{{/each}}

任意改善事項がない場合は `なし` と記載する。

---

## 9. テスト・CI確認

| 項目 | 判定 | 補足 |
| ---- | ---- | ---- |
| OpenAPI lint | `{{test_check.openapi_lint}}` | {{test_check.openapi_lint_note}} |
| Orval生成 | `{{test_check.orval_generation}}` | {{test_check.orval_generation_note}} |
| typecheck | `{{test_check.typecheck}}` | {{test_check.typecheck_note}} |
| contract test | `{{test_check.contract_test}}` | {{test_check.contract_test_note}} |
| CI | `{{test_check.ci}}` | {{test_check.ci_note}} |

---

## 10. Human Review観点

{{#each human_review_points}}

- {{this}}
  {{/each}}

{{#unless human_review_points}}

- 破壊的変更または互換性影響の判断
- provider / consumer 影響範囲の妥当性
- OpenAPI / generated 差分を同一Contract Taskで扱う範囲の妥当性
  {{/unless}}

---

## 11. 未確認事項

{{#each review.unconfirmed}}

- {{this}}
  {{/each}}

{{#unless review.unconfirmed}}

- なし
  {{/unless}}
