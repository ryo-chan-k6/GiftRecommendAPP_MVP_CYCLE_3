# Human Decision Request

## 1. 結論

人間判断が必要です。  
以下の判断事項について確認してください。

| 項目          | 内容                        |
| ------------- | --------------------------- |
| 判断種別      | `{{decision.type}}`         |
| 優先度        | `{{decision.priority}}`     |
| 対象Issue     | `{{issue.number}}`          |
| 対象PR        | `{{pr.number}}`             |
| Task ID       | `{{task.id}}`               |
| Definition    | `{{definition.path}}`       |
| 発生元Command | `{{command.name}}`          |
| 依頼元Agent   | `{{agent.primary}}`         |
| 発生日時      | `{{decision.requested_at}}` |

---

## 2. 判断が必要な理由

{{decision.reason}}

---

## 3. 判断してほしいこと

{{#each decision.questions}}

- {{this}}
  {{/each}}

{{#unless decision.questions}}

- なし
  {{/unless}}

---

## 4. 確認した事実

AI Agent が確認できた事実。

{{#each facts}}

- {{this}}
  {{/each}}

{{#unless facts}}

- なし
  {{/unless}}

---

## 5. 推論

確認した事実から推論した内容。

{{#each inferences}}

- {{this}}
  {{/each}}

{{#unless inferences}}

- なし
  {{/unless}}

> 推論は確定事実ではない。  
> 判断が必要な場合は、人間確認結果を正とする。

---

## 6. 未確認事項

AI Agent では確認できなかった事項。

{{#each unconfirmed}}

- {{this}}
  {{/each}}

{{#unless unconfirmed}}

- なし
  {{/unless}}

---

## 7. 選択肢

{{#each decision.options}}

## 7.{{@index}} {{title}}

| 項目     | 内容                       |
| -------- | -------------------------- |
| 選択肢ID | `{{id}}`                   |
| 推奨度   | `{{recommendation_level}}` |
| 影響度   | `{{impact_level}}`         |
| リスク   | `{{risk_level}}`           |

### 内容

{{description}}

### メリット

{{#each pros}}

- {{this}}
  {{/each}}

{{#unless pros}}

- なし
  {{/unless}}

### デメリット / リスク

{{#each cons}}

- {{this}}
  {{/each}}

{{#unless cons}}

- なし
  {{/unless}}

### 必要な後続対応

{{#each next_actions}}

- {{this}}
  {{/each}}

{{#unless next_actions}}

- なし
  {{/unless}}

{{/each}}

---

## 8. AI推奨案

| 項目       | 内容                               |
| ---------- | ---------------------------------- |
| 推奨選択肢 | `{{decision.recommended_option}}`  |
| 推奨理由   | {{decision.recommendation_reason}} |
| 確信度     | `{{decision.confidence}}`          |

### 補足

{{decision.recommendation_note}}

---

## 9. 影響範囲

| 観点        | 影響有無                        | 補足                      |
| ----------- | ------------------------------- | ------------------------- |
| docs        | `{{impact.docs.affected}}`      | {{impact.docs.note}}      |
| source code | `{{impact.source.affected}}`    | {{impact.source.note}}    |
| tests       | `{{impact.tests.affected}}`     | {{impact.tests.note}}     |
| API仕様     | `{{impact.api_spec.affected}}`  | {{impact.api_spec.note}}  |
| OpenAPI     | `{{impact.openapi.affected}}`   | {{impact.openapi.note}}   |
| Orval       | `{{impact.orval.affected}}`     | {{impact.orval.note}}     |
| generated   | `{{impact.generated.affected}}` | {{impact.generated.note}} |
| DB schema   | `{{impact.db_schema.affected}}` | {{impact.db_schema.note}} |
| CI/CD       | `{{impact.cicd.affected}}`      | {{impact.cicd.note}}      |
| security    | `{{impact.security.affected}}`  | {{impact.security.note}}  |
| Project運用 | `{{impact.project.affected}}`   | {{impact.project.note}}   |

---

## 10. 現在の状態

| 項目         | 内容                             |
| ------------ | -------------------------------- |
| 現在Status   | `{{project.current_status}}`     |
| 推奨Status   | `{{project.recommended_status}}` |
| Branch       | `{{branch.name}}`                |
| PR target    | `{{branch.target}}`              |
| 作業継続可否 | `{{decision.can_continue}}`      |
| 停止中か     | `{{decision.blocked}}`           |

---

## 11. AIが勝手に進めない理由

{{decision.stop_reason}}

該当する理由。

{{#each decision.stop_reason_items}}

- {{this}}
  {{/each}}

{{#unless decision.stop_reason_items}}

- なし
  {{/unless}}

---

## 12. 判断後の次Action

### 12.1 承認する場合

```text
{{next_action.on_approve}}
```

### 12.2 修正する場合

```text
{{next_action.on_request_changes}}
```

### 12.3 別Issue化する場合

```text
{{next_action.on_split_required}}
```

### 12.4 作業停止を継続する場合

```text
{{next_action.on_blocked}}
```

---

## 13. 回答してほしい形式

以下のいずれかで回答してください。

```text
A案で進めてください
```

```text
B案で進めてください。補足条件は以下です。
-
```

```text
判断保留です。追加で以下を確認してください。
-
```

```text
このTaskでは扱わず、別Issue化してください。
```

---

## 14. 正本

| 種別         | 参照先                |
| ------------ | --------------------- |
| 作業計画     | `{{issue.url}}`       |
| 作業結果     | `{{pr.url}}`          |
| Definition   | `{{definition.path}}` |
| 関連docs     | `{{docs.url}}`        |
| 関連レビュー | `{{review.url}}`      |

この判断依頼は、作業を進めるための確認依頼である。  
作業計画はIssue、作業結果とレビュー結果はPR、成果物はdocsを正本とする。

---

## 15. 備考

{{#each notes}}

- {{this}}
  {{/each}}

{{#unless notes}}

- なし
  {{/unless}}
