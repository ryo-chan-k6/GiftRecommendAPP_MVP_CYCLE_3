# Docs Review Result

## 1. レビュー結果

| 項目 | 内容 |
| ---- | ---- |
| Review Result | `{{review.result}}` |
| 対象PR | `{{pr.number}}` |
| 対象Issue | `{{issue.number}}` |
| Task ID | `{{task.id}}` |
| Definition | `{{definition.path}}` |
| Reviewer | `{{agent.primary}}` |
| Review日時 | `{{review.reviewed_at}}` |

### Review Result の分類

| 分類 | 意味 | 次Action |
| ---- | ---- | -------- |
| `approve_for_human_review` | docs Review上は大きな問題なし。Human Reviewへ進めてよい | Human Review |
| `request_changes` | 同一Branchで修正が必要 | `/fix-review-comments` |
| `needs_human_decision` | docs正本・用語・scope判断に人間判断が必要 | Human判断待ち |
| `split_required` | 別Issue化が必要 | Issue分割 |
| `blocked` | 前提不足でレビュー不可 | 前提解消 |

---

## 2. 結論

{{review.summary}}

---

## 3. 確認した成果物

{{#each deliverables}}

- `{{this}}`
  {{/each}}

---

## 4. docs必須確認

| 観点 | 判定 | 補足 |
| ---- | ---- | ---- |
| 正本docsと整合 | `{{docs_check.canonical_consistency}}` | {{docs_check.canonical_consistency_note}} |
| 指定テンプレート準拠 | `{{docs_check.template_conformity}}` | {{docs_check.template_conformity_note}} |
| 配置先が適切 | `{{docs_check.path_consistency}}` | {{docs_check.path_consistency_note}} |
| 章構成が適切 | `{{docs_check.structure}}` | {{docs_check.structure_note}} |
| 粒度が適切 | `{{docs_check.granularity}}` | {{docs_check.granularity_note}} |
| 用語揺れなし | `{{docs_check.terminology}}` | {{docs_check.terminology_note}} |
| Markdown表が崩れていない | `{{docs_check.markdown_tables}}` | {{docs_check.markdown_tables_note}} |
| Mermaid構文が妥当 | `{{docs_check.mermaid}}` | {{docs_check.mermaid_note}} |
| secret混入なし | `{{docs_check.no_secret}}` | {{docs_check.no_secret_note}} |

---

## 5. scope / out_of_scope 確認

| 項目 | 内容 |
| ---- | ---- |
| scope内に収まっているか | `{{scope_check.in_scope}}` |
| scope外変更の有無 | `{{scope_check.scope_out_changes}}` |
| 補足 | {{scope_check.notes}} |

---

## 6. 修正必須事項

{{#each review.required_fixes}}

### 6.{{@index}} {{this.title}}

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

## 7. 任意改善事項

{{#each review.optional_improvements}}

### 7.{{@index}} {{this.title}}

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

## 8. Human Review観点

{{#each human_review_points}}

- {{this}}
  {{/each}}

{{#unless human_review_points}}

- 成果物の粒度が後続実装Taskの入力として十分か
- 未決事項が人間判断事項として適切に分離されているか
- MVP範囲と対象外範囲が妥当か
  {{/unless}}

---

## 9. 未確認事項

{{#each review.unconfirmed}}

- {{this}}
  {{/each}}

{{#unless review.unconfirmed}}

- なし
  {{/unless}}
