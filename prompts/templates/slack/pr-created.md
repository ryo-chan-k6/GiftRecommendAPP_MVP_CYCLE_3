# PR Created

## 1. 結論

PRを作成しました。  
AI Reviewへ進めます。

| 項目          | 内容                  |
| ------------- | --------------------- |
| PR            | `{{pr.number}}`       |
| PR URL        | `{{pr.url}}`          |
| 対象Issue     | `{{issue.number}}`    |
| Issue URL     | `{{issue.url}}`       |
| Task ID       | `{{task.id}}`         |
| Definition    | `{{definition.path}}` |
| Source Branch | `{{branch.name}}`     |
| Target Branch | `{{branch.target}}`   |
| 作成者        | `{{agent.primary}}`   |

---

## 2. PR概要

{{task.summary}}

---

## 3. 対応内容

{{#each work_summary.completed}}

- {{this}}
  {{/each}}

{{#unless work_summary.completed}}

- なし
  {{/unless}}

---

## 4. 主な変更ファイル

### docs

{{#each changed_files.docs}}

- `{{this}}`
  {{/each}}

{{#unless changed_files.docs}}

- なし
  {{/unless}}

### source code

{{#each changed_files.source}}

- `{{this}}`
  {{/each}}

{{#unless changed_files.source}}

- なし
  {{/unless}}

### tests

{{#each changed_files.tests}}

- `{{this}}`
  {{/each}}

{{#unless changed_files.tests}}

- なし
  {{/unless}}

### generated

{{#each changed_files.generated}}

- `{{this}}`
  {{/each}}

{{#unless changed_files.generated}}

- なし
  {{/unless}}

---

## 5. テスト・検証結果

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

| 項目       | 内容              |
| ---------- | ----------------- |
| CI実行有無 | `{{ci.executed}}` |
| CI結果     | `{{ci.result}}`   |
| 補足       | {{ci.notes}}      |

---

## 6. 影響確認

| 観点              | 内容                                 |
| ----------------- | ------------------------------------ |
| scope外変更       | `{{work_summary.scope_out_changes}}` |
| generated差分     | `{{generated.diff_exists}}`          |
| generated手動編集 | `{{generated.manual_edit}}`          |
| API仕様影響       | `{{impact.api_spec}}`                |
| OpenAPI影響       | `{{impact.openapi}}`                 |
| Orval影響         | `{{impact.orval}}`                   |
| DB schema影響     | `{{impact.db_schema}}`               |
| security影響      | `{{security.impact}}`                |

---

## 7. Human Reviewで確認してほしいこと

{{#each human_decision_points}}

- {{this}}
  {{/each}}

{{#unless human_decision_points}}

- なし
  {{/unless}}

---

## 8. 残課題 / follow-up候補

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

## 9. PR運用メモ

- Task PRでは原則として `Closes {{issue.number}}` を使用しない
- Task PRでは `Related to {{issue.number}}` を使用する
- Task Issue の Done / close は、PR merge時の workflow で制御する
- Task Branch から `develop` へ直接PRを作成しない
- PR target は原則として Parent Epic Branch とする
- AI Review後に Human Review へ進める

---

## 10. Status更新意図

| 項目       | 内容                               |
| ---------- | ---------------------------------- |
| 現在Status | `{{project.current_status}}`       |
| 次Status   | `AI Review`                        |
| 更新意図   | `{{project.status_update_intent}}` |

---

## 11. 次Action

```text
/review-pr @{{review_definition.path}} {{pr.number}}
```

---

## 12. 正本

| 種別       | 参照先                |
| ---------- | --------------------- |
| 作業計画   | `{{issue.url}}`       |
| 作業結果   | `{{pr.url}}`          |
| Definition | `{{definition.path}}` |
| 成果物     | `{{docs.url}}`        |

Slack通知は正本ではない。  
作業計画はIssue、作業結果はPR、成果物はdocsを正本とする。
