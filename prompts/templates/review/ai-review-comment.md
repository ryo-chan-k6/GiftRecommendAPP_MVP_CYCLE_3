# AI Review Result

## 1. レビュー結果

| 項目          | 内容                     |
| ------------- | ------------------------ |
| Review Result | `{{review.result}}`      |
| 対象PR        | `{{pr.number}}`          |
| 対象Issue     | `{{issue.number}}`       |
| Task ID       | `{{task.id}}`            |
| Definition    | `{{definition.path}}`    |
| Reviewer      | `{{agent.primary}}`      |
| Review日時    | `{{review.reviewed_at}}` |

### Review Result の分類

| 分類                       | 意味                                                  | 次Action               |
| -------------------------- | ----------------------------------------------------- | ---------------------- |
| `approve_for_human_review` | AI Review上は大きな問題なし。Human Reviewへ進めてよい | Human Review           |
| `request_changes`          | 同一Branchで修正が必要                                | `/fix-review-comments` |
| `needs_human_decision`     | 人間判断が必要                                        | Human判断待ち          |
| `split_required`           | 別Issue化が必要                                       | Issue分割              |
| `blocked`                  | 前提不足でレビュー不可                                | 前提解消               |

---

## 2. 結論

{{review.summary}}

---

## 3. 確認した事実

AI Reviewで確認できた事実。

{{#each review.facts}}

- {{this}}
  {{/each}}

---

## 4. 推論

確認した事実から推論した内容。

{{#each review.inferences}}

- {{this}}
  {{/each}}

推論は確定事実ではない。  
判断が必要な場合は Human Review で確認する。

---

## 5. 未確認事項

AI Reviewでは確認できなかった事項。

{{#each review.unconfirmed}}

- {{this}}
  {{/each}}

未確認事項がない場合は `なし` と記載する。

---

## 6. 良い点

{{#each review.good_points}}

- {{this}}
  {{/each}}

---

## 7. 修正必須事項

同一Branchで修正が必要な事項。

{{#each review.required_fixes}}

### 7.{{@index}} {{this.title}}

| 項目     | 内容                          |
| -------- | ----------------------------- |
| 重要度   | `{{this.severity}}`           |
| 対象     | `{{this.target}}`             |
| 分類     | `{{this.category}}`           |
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

必須ではないが、改善するとよい事項。

{{#each review.optional_improvements}}

### 8.{{@index}} {{this.title}}

| 項目   | 内容                |
| ------ | ------------------- |
| 重要度 | `{{this.severity}}` |
| 対象   | `{{this.target}}`   |
| 分類   | `{{this.category}}` |

#### 内容

{{this.description}}

#### 改善案

{{this.suggested_fix}}

{{/each}}

任意改善事項がない場合は `なし` と記載する。

---

## 9. scope / out_of_scope 確認

### 9.1 scope確認

{{#each review.scope_check.in_scope}}

- [{{#if this.ok}}x{{else}} {{/if}}] {{this.item}}
  - 確認結果: {{this.note}}
    {{/each}}

### 9.2 out_of_scope確認

{{#each review.scope_check.out_of_scope}}

- [{{#if this.violated}}x{{else}} {{/if}}] {{this.item}}
  - 確認結果: {{this.note}}
    {{/each}}

### 9.3 判定

| 項目                    | 内容                                       |
| ----------------------- | ------------------------------------------ |
| scope内に収まっているか | `{{review.scope_check.result}}`            |
| scope外変更の有無       | `{{review.scope_check.scope_out_changes}}` |
| 補足                    | {{review.scope_check.notes}}               |

---

## 10. 完了条件チェック

Task Definition の acceptance_criteria に対する確認結果。

{{#each acceptance_criteria}}

- [{{#if this.satisfied}}x{{else}} {{/if}}] {{this.description}}
  - 確認結果: {{this.result_note}}
    {{/each}}

### 判定

| 項目         | 内容                           |
| ------------ | ------------------------------ |
| 完了条件判定 | `{{review.acceptance_result}}` |
| 補足         | {{review.acceptance_notes}}    |

---

## 11. 変更ファイル確認

### 11.1 docs

{{#each changed_files.docs}}

- `{{this}}`
  {{/each}}

### 11.2 source code

{{#each changed_files.source}}

- `{{this}}`
  {{/each}}

### 11.3 tests

{{#each changed_files.tests}}

- `{{this}}`
  {{/each}}

### 11.4 config / scripts

{{#each changed_files.config}}

- `{{this}}`
  {{/each}}

### 11.5 generated

{{#each changed_files.generated}}

- `{{this}}`
  {{/each}}

### 11.6 変更ファイル判定

| 項目             | 内容                                          |
| ---------------- | --------------------------------------------- |
| 意図しない変更   | `{{review.changed_files.unexpected_changes}}` |
| 不足している変更 | `{{review.changed_files.missing_changes}}`    |
| 補足             | {{review.changed_files.notes}}                |

---

## 12. docs確認

docs変更がある場合に確認する。

| 項目                    | 判定                                             | 補足                                   |
| ----------------------- | ------------------------------------------------ | -------------------------------------- |
| 正本docsと整合している  | `{{review.docs.consistent_with_canonical_docs}}` | {{review.docs.canonical_docs_note}}    |
| 用語揺れがない          | `{{review.docs.terminology_ok}}`                 | {{review.docs.terminology_note}}       |
| 章構成・粒度が適切      | `{{review.docs.structure_ok}}`                   | {{review.docs.structure_note}}         |
| Mermaid構文に問題がない | `{{review.docs.mermaid_ok}}`                     | {{review.docs.mermaid_note}}           |
| 古い方針が残っていない  | `{{review.docs.no_deprecated_policy}}`           | {{review.docs.deprecated_policy_note}} |

### docs指摘

{{#each review.docs.comments}}

- {{this}}
  {{/each}}

---

## 13. code確認

source code変更がある場合に確認する。

| 項目                             | 判定                                 | 補足                                 |
| -------------------------------- | ------------------------------------ | ------------------------------------ |
| 既存アーキテクチャと整合している | `{{review.code.architecture_ok}}`    | {{review.code.architecture_note}}    |
| 責務分離が崩れていない           | `{{review.code.responsibility_ok}}`  | {{review.code.responsibility_note}}  |
| 命名が適切                       | `{{review.code.naming_ok}}`          | {{review.code.naming_note}}          |
| 型安全性に問題がない             | `{{review.code.type_safety_ok}}`     | {{review.code.type_safety_note}}     |
| 過剰実装がない                   | `{{review.code.no_overengineering}}` | {{review.code.overengineering_note}} |
| エラーハンドリングが適切         | `{{review.code.error_handling_ok}}`  | {{review.code.error_handling_note}}  |

### code指摘

{{#each review.code.comments}}

- {{this}}
  {{/each}}

---

## 14. test / CI確認

### 14.1 テスト結果

{{#each test_results.executed}}

- [x] {{this.name}}
  - 結果: `{{this.result}}`
  - 補足: {{this.note}}
    {{/each}}

### 14.2 未実施テスト

{{#each test_results.not_executed}}

- [ ] {{this.name}}
  - 未実施理由: {{this.reason}}
  - 代替確認: {{this.alternative_check}}
  - 残リスク: {{this.risk}}
    {{/each}}

### 14.3 CI結果

| 項目       | 内容                 |
| ---------- | -------------------- |
| CI実行有無 | `{{ci.executed}}`    |
| CI結果     | `{{ci.result}}`      |
| 失敗Job    | `{{ci.failed_jobs}}` |
| 補足       | {{ci.notes}}         |

### 14.4 判定

| 項目                        | 内容                                 |
| --------------------------- | ------------------------------------ |
| test_policyを満たしているか | `{{review.test.policy_satisfied}}`   |
| 未実施テストの説明が十分か  | `{{review.test.skip_reason_ok}}`     |
| CI失敗の扱いが明確か        | `{{review.test.ci_failure_handled}}` |

> 実施していないテストを、実施済みとして扱わないこと。

---

## 15. generated確認

| 項目              | 内容                                   |
| ----------------- | -------------------------------------- |
| generated差分     | `{{generated.diff_exists}}`            |
| 手動編集有無      | `{{generated.manual_edit}}`            |
| 生成元            | `{{generated.source}}`                 |
| 再生成コマンド    | `{{generated.command}}`                |
| Contract Task要否 | `{{generated.contract_task_required}}` |

### generated判定

| 項目                          | 判定                                        | 補足                                    |
| ----------------------------- | ------------------------------------------- | --------------------------------------- |
| generated手動編集なし         | `{{review.generated.no_manual_edit}}`       | {{review.generated.manual_edit_note}}   |
| 生成元と差分が対応している    | `{{review.generated.source_matches_diff}}`  | {{review.generated.source_match_note}}  |
| 再生成手順が明確              | `{{review.generated.regeneration_clear}}`   | {{review.generated.regeneration_note}}  |
| Contract Task化要否が判断済み | `{{review.generated.contract_task_judged}}` | {{review.generated.contract_task_note}} |

---

## 16. API / DB / Contract 影響確認

| 観点       | 影響有無                | 判定                                  | 補足                       |
| ---------- | ----------------------- | ------------------------------------- | -------------------------- |
| API仕様    | `{{impact.api_spec}}`   | `{{review.impact.api_spec_result}}`   | {{impact.api_spec_note}}   |
| OpenAPI    | `{{impact.openapi}}`    | `{{review.impact.openapi_result}}`    | {{impact.openapi_note}}    |
| Orval      | `{{impact.orval}}`      | `{{review.impact.orval_result}}`      | {{impact.orval_note}}      |
| API client | `{{impact.api_client}}` | `{{review.impact.api_client_result}}` | {{impact.api_client_note}} |
| DB schema  | `{{impact.db_schema}}`  | `{{review.impact.db_schema_result}}`  | {{impact.db_schema_note}}  |
| migration  | `{{impact.migration}}`  | `{{review.impact.migration_result}}`  | {{impact.migration_note}}  |
| CI/CD      | `{{impact.cicd}}`       | `{{review.impact.cicd_result}}`       | {{impact.cicd_note}}       |

API contract / DB schema / generated への影響がある場合は、通常Taskに混在させず、必要に応じて Contract Task または専用Taskとして分離する。

---

## 17. security確認

| 項目                             | 判定                                          | 補足                                             |
| -------------------------------- | --------------------------------------------- | ------------------------------------------------ |
| secretを含んでいない             | `{{review.security.no_secret}}`               | {{review.security.no_secret_note}}               |
| `.env` 実値を含んでいない        | `{{review.security.no_env_values}}`           | {{review.security.no_env_values_note}}           |
| DB接続文字列の実値を含んでいない | `{{review.security.no_db_connection_string}}` | {{review.security.no_db_connection_string_note}} |
| API keyを含んでいない            | `{{review.security.no_api_key}}`              | {{review.security.no_api_key_note}}              |
| ログに機密情報を出していない     | `{{review.security.logging_safe}}`            | {{review.security.logging_note}}                 |
| 認証認可影響が明確               | `{{review.security.auth_impact_clear}}`       | {{review.security.auth_note}}                    |

security上の懸念がある場合は、Human Reviewへ回す。

---

## 18. Branch / PR運用確認

| 項目                                         | 判定                                         | 補足                                     |
| -------------------------------------------- | -------------------------------------------- | ---------------------------------------- |
| Source Branchが正しい                        | `{{review.branch.source_ok}}`                | {{review.branch.source_note}}            |
| Target Branchが正しい                        | `{{review.branch.target_ok}}`                | {{review.branch.target_note}}            |
| Task Branchからdevelopへ直接PRしていない     | `{{review.branch.not_direct_to_develop}}`    | {{review.branch.direct_to_develop_note}} |
| Parent Epic Branchの最新状態を取り込んでいる | `{{review.branch.up_to_date_with_epic}}`     | {{review.branch.up_to_date_note}}        |
| `Related to {{issue.number}}` がある         | `{{review.branch.related_to_issue_ok}}`      | {{review.branch.related_to_issue_note}}  |
| `Closes {{issue.number}}` を使っていない     | `{{review.branch.no_closes_for_task_issue}}` | {{review.branch.closes_note}}            |

Task Issue の Done / close は、PR merge時の workflow で制御する。

---

## 19. Human Reviewで確認してほしいこと

{{#each human_decision_points}}

- {{this}}
  {{/each}}

人間判断が不要な場合は `なし` と記載する。

---

## 20. follow-up Issue候補

{{#each follow_up.items}}

- 内容: {{this.description}}
  - 種別: `{{this.type}}`
  - 推奨対応: {{this.recommended_action}}
  - 別Issue化要否: `{{this.issue_required}}`
    {{/each}}

follow-up候補がない場合は `なし` と記載する。

---

## 21. AI Reviewコメント

### 21.1 総合コメント

{{review.comment}}

### 21.2 修正が必要な場合

`request_changes` の場合、次のCommandで修正する。

```text
/fix-review-comments @{{definition.path}} {{pr.number}}
```

### 21.3 Human Reviewへ進める場合

`approve_for_human_review` の場合、Human Reviewへ進める。

---

## 22. Status更新意図

| Review Result              | Status更新意図                                  |
| -------------------------- | ----------------------------------------------- |
| `approve_for_human_review` | `AI Review → Human Review`                      |
| `request_changes`          | `AI Review → In Progress`                       |
| `needs_human_decision`     | `AI Review → Human Review` または `In Progress` |
| `split_required`           | `AI Review → In Progress`                       |
| `blocked`                  | `AI Review → In Progress`                       |

### 今回のStatus更新意図

| 項目       | 内容                               |
| ---------- | ---------------------------------- |
| 現在Status | `{{project.current_status}}`       |
| 次Status   | `{{project.next_status}}`          |
| 更新意図   | `{{project.status_update_intent}}` |

Status更新は、GitHub Actions または運用スクリプトで実施する。  
CommandはStatus更新の意図を明確に出力する。

---

## 23. 次Action

```text
{{review.next_action}}
```

例：

```text
/fix-review-comments @{{definition.path}} {{pr.number}}
```

```text
Human Reviewへ進める
```

---

## 24. AI Reviewチェックリスト

- [ ] PRを確認した
- [ ] 対象Issueを確認した
- [ ] Task Definition / Review Definitionを確認した
- [ ] PR targetを確認した
- [ ] Task BranchがParent Epic Branchの最新状態を取り込んでいるか確認した
- [ ] diffを確認した
- [ ] scope / out_of_scope を確認した
- [ ] acceptance_criteria を確認した
- [ ] docs変更を確認した
- [ ] source code変更を確認した
- [ ] test / CI結果を確認した
- [ ] generated差分を確認した
- [ ] API / DB / Contract 影響を確認した
- [ ] security観点を確認した
- [ ] Human Review観点を整理した
- [ ] 修正要否を判定した
- [ ] Status更新意図を整理した
- [ ] 次Actionを明記した

---

## 25. 注意事項

- AI Reviewはmerge判断ではない
- Human Reviewを省略しない
- 修正が必要な場合は、レビューCommand内で修正しない
- 修正は `/fix-review-comments` に引き継ぐ
- Task PRでは原則として `Closes {{issue.number}}` を使用しない
- Task PRでは `Related to {{issue.number}}` を確認する
- generatedファイルの手動編集を許容しない
- secret、APIキー、`.env` 実値の混入を見逃さない
- 実施していないテストを実施済みとして扱わない
- Slack通知だけでレビュー記録を完結させない
