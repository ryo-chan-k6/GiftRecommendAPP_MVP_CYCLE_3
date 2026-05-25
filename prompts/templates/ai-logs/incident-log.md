# Incident Log

## 1. 概要

| 項目          | 内容                  |
| ------------- | --------------------- |
| Log ID        | `{{log.id}}`          |
| Log種別       | `incident`            |
| 件名          | {{log.title}}         |
| 発生日時      | {{log.occurred_at}}   |
| 記録日時      | {{log.recorded_at}}   |
| 発生元Command | `{{command.name}}`    |
| 発生元Agent   | `{{agent.primary}}`   |
| 関連Issue     | `{{issue.number}}`    |
| 関連PR        | `{{pr.number}}`       |
| Definition    | `{{definition.path}}` |
| 重要度        | `{{log.severity}}`    |
| 状態          | `{{log.status}}`      |

---

## 2. 結論

{{log.summary}}

---

## 3. incident として記録する理由

{{log.reason}}

### 3.1 incident 対象理由

{{#each log.incident_reasons}}

- {{this}}
  {{/each}}

{{#unless log.incident_reasons}}

- 作業継続に影響するエラー、前提不足、判断不能、または人間確認が必要な事象のため
  {{/unless}}

### 3.2 通常作業ログではない理由

通常作業ログをすべて `ai-logs/` に保存しない。  
このログは、作業停止、エラー、判断不能、再発防止、後続対応のために記録する。

---

## 4. 発生経緯

| 項目                  | 内容                                   |
| --------------------- | -------------------------------------- |
| 発生元                | `{{source.discovered_from}}`           |
| 関連Task              | `{{source.related_task}}`              |
| 関連Task Definition   | `{{source.related_task_definition}}`   |
| 関連Review Definition | `{{source.related_review_definition}}` |
| 関連Command           | `{{source.related_command}}`           |

### 4.1 詳細

{{source.detail}}

---

## 5. 事象内容

| 項目          | 内容                           |
| ------------- | ------------------------------ |
| incident type | `{{incident.type}}`            |
| 発生箇所      | `{{incident.location}}`        |
| 発生条件      | {{incident.condition}}         |
| 影響範囲      | {{incident.scope}}             |
| 再現性        | `{{incident.reproducibility}}` |
| 作業継続可否  | `{{incident.can_continue}}`    |
| block状態     | `{{incident.blocked}}`         |

### 5.1 エラーメッセージ / 出力

```text
{{incident.error_message}}
```

### 5.2 関連ログ / コマンド出力

```text
{{incident.command_output}}
```

---

## 6. 確認した事実

AI Agent が確認できた事実。

{{#each facts}}

- {{this}}
  {{/each}}

{{#unless facts}}

- なし
  {{/unless}}

---

## 7. 推論

確認した事実から推論した内容。

{{#each inferences}}

- {{this}}
  {{/each}}

{{#unless inferences}}

- なし
  {{/unless}}

> 推論は確定事実ではない。  
> 後続判断では、Issue本文、PR差分、Definition、正本docs、実行ログを確認すること。

---

## 8. 未確認事項

{{#each unconfirmed}}

- {{this}}
  {{/each}}

{{#unless unconfirmed}}

- なし
  {{/unless}}

---

## 9. 影響範囲

| 観点        | 影響有無                               | 影響度                              | 補足                             |
| ----------- | -------------------------------------- | ----------------------------------- | -------------------------------- |
| docs        | `{{impact.docs.affected}}`             | `{{impact.docs.level}}`             | {{impact.docs.note}}             |
| source code | `{{impact.source.affected}}`           | `{{impact.source.level}}`           | {{impact.source.note}}           |
| tests       | `{{impact.tests.affected}}`            | `{{impact.tests.level}}`            | {{impact.tests.note}}            |
| API仕様     | `{{impact.api_spec.affected}}`         | `{{impact.api_spec.level}}`         | {{impact.api_spec.note}}         |
| OpenAPI     | `{{impact.openapi.affected}}`          | `{{impact.openapi.level}}`          | {{impact.openapi.note}}          |
| Orval       | `{{impact.orval.affected}}`            | `{{impact.orval.level}}`            | {{impact.orval.note}}            |
| generated   | `{{impact.generated.affected}}`        | `{{impact.generated.level}}`        | {{impact.generated.note}}        |
| DB schema   | `{{impact.db_schema.affected}}`        | `{{impact.db_schema.level}}`        | {{impact.db_schema.note}}        |
| migration   | `{{impact.migration.affected}}`        | `{{impact.migration.level}}`        | {{impact.migration.note}}        |
| CI/CD       | `{{impact.cicd.affected}}`             | `{{impact.cicd.level}}`             | {{impact.cicd.note}}             |
| security    | `{{impact.security.affected}}`         | `{{impact.security.level}}`         | {{impact.security.note}}         |
| GitHub運用  | `{{impact.github_operation.affected}}` | `{{impact.github_operation.level}}` | {{impact.github_operation.note}} |
| Project運用 | `{{impact.project.affected}}`          | `{{impact.project.level}}`          | {{impact.project.note}}          |

---

## 10. 影響対象ファイル / 成果物

### 10.1 docs

{{#each affected.docs}}

- `{{path}}`
  - 影響内容: {{impact}}
  - 対応要否: `{{required}}`
    {{/each}}

{{#unless affected.docs}}

- なし
  {{/unless}}

### 10.2 source code / config

{{#each affected.files}}

- `{{path}}`
  - 影響内容: {{impact}}
  - 対応要否: `{{required}}`
    {{/each}}

{{#unless affected.files}}

- なし
  {{/unless}}

### 10.3 tests / CI

{{#each affected.tests}}

- `{{path}}`
  - 影響内容: {{impact}}
  - 対応要否: `{{required}}`
    {{/each}}

{{#unless affected.tests}}

- なし
  {{/unless}}

### 10.4 generated / contract files

{{#each affected.contract_files}}

- `{{path}}`
  - 種別: `{{type}}`
  - 影響内容: {{impact}}
  - 対応要否: `{{required}}`
    {{/each}}

{{#unless affected.contract_files}}

- なし
  {{/unless}}

---

## 11. 原因分析

### 11.1 直接原因

{{incident.direct_cause}}

### 11.2 根本原因候補

{{#each incident.root_cause_candidates}}

- {{this}}
  {{/each}}

{{#unless incident.root_cause_candidates}}

- 未特定
  {{/unless}}

### 11.3 原因分類

| 分類             | 該当                               | 補足                            |
| ---------------- | ---------------------------------- | ------------------------------- |
| Definition不備   | `{{cause.definition_issue}}`       | {{cause.definition_note}}       |
| 入力資料不足     | `{{cause.input_missing}}`          | {{cause.input_note}}            |
| docs不整合       | `{{cause.docs_inconsistency}}`     | {{cause.docs_note}}             |
| 実装不整合       | `{{cause.implementation_issue}}`   | {{cause.implementation_note}}   |
| テスト不備       | `{{cause.test_issue}}`             | {{cause.test_note}}             |
| CI/CD不備        | `{{cause.cicd_issue}}`             | {{cause.cicd_note}}             |
| GitHub運用不備   | `{{cause.github_operation_issue}}` | {{cause.github_operation_note}} |
| 権限・認証問題   | `{{cause.permission_issue}}`       | {{cause.permission_note}}       |
| 外部サービス要因 | `{{cause.external_service_issue}}` | {{cause.external_service_note}} |
| AI判断限界       | `{{cause.ai_limitation}}`          | {{cause.ai_limitation_note}}    |

---

## 12. 暫定対応

{{#each mitigation.temporary_actions}}

- {{this}}
  {{/each}}

{{#unless mitigation.temporary_actions}}

- なし
  {{/unless}}

---

## 13. 恒久対応案

{{#each mitigation.permanent_actions}}

- {{this}}
  {{/each}}

{{#unless mitigation.permanent_actions}}

- 未定
  {{/unless}}

---

## 14. 人間判断が必要な事項

{{#each human_decision_points}}

- {{this}}
  {{/each}}

{{#unless human_decision_points}}

- なし
  {{/unless}}

---

## 15. 推奨対応

### 15.1 即時対応

{{#each recommended_actions.immediate}}

- {{this}}
  {{/each}}

{{#unless recommended_actions.immediate}}

- なし
  {{/unless}}

### 15.2 後続対応

{{#each recommended_actions.follow_up}}

- {{this}}
  {{/each}}

{{#unless recommended_actions.follow_up}}

- なし
  {{/unless}}

### 15.3 別Issue化候補

{{#each follow_up.items}}

- 内容: {{description}}
  - 種別: `{{type}}`
  - 推奨対応: {{recommended_action}}
  - 別Issue化要否: `{{issue_required}}`
    {{/each}}

{{#unless follow_up.items}}

- なし
  {{/unless}}

---

## 16. 作業再開条件

以下を満たしたら作業再開可能とする。

{{#each resume_conditions}}

- {{this}}
  {{/each}}

{{#unless resume_conditions}}

- incident の原因または暫定対応が明確になっている
- 人間判断が必要な事項について回答を得ている
- scope / out_of_scope が再確認されている
- secret、`.env` 実値、APIキーなどの混入がないことを確認している
  {{/unless}}

---

## 17. 停止条件

以下に該当する場合、AI Agent は作業を停止し、人間確認へ回す。

{{#each stop_conditions}}

- {{this}}
  {{/each}}

{{#unless stop_conditions}}

- 原因が特定できない場合
- 作業継続によりscope外変更が発生する場合
- secret、APIキー、`.env` 実値を扱う必要がある場合
- security上の懸念がある場合
- DB schema変更やAPI contract変更が必要になった場合
- generatedファイルの手動編集が必要に見える場合
- Human Reviewを省略する必要があるように見える場合
- AIがPR merge判断を行う必要がある場合
  {{/unless}}

---

## 18. 再発防止策

{{#each prevention.actions}}

- {{this}}
  {{/each}}

{{#unless prevention.actions}}

- 未定
  {{/unless}}

### 18.1 更新候補

| 対象                       | 更新要否                                | 補足                                |
| -------------------------- | --------------------------------------- | ----------------------------------- |
| Task Definition Schema     | `{{prevention.update_task_schema}}`     | {{prevention.task_schema_note}}     |
| Review Definition Schema   | `{{prevention.update_review_schema}}`   | {{prevention.review_schema_note}}   |
| Contract Definition Schema | `{{prevention.update_contract_schema}}` | {{prevention.contract_schema_note}} |
| Commands設計書             | `{{prevention.update_commands_design}}` | {{prevention.commands_design_note}} |
| Rules / Agents             | `{{prevention.update_rules_agents}}`    | {{prevention.rules_agents_note}}    |
| docs                       | `{{prevention.update_docs}}`            | {{prevention.docs_note}}            |
| CI/CD                      | `{{prevention.update_cicd}}`            | {{prevention.cicd_note}}            |

---

## 19. Status更新意図

| 項目       | 内容                               |
| ---------- | ---------------------------------- |
| 現在Status | `{{project.current_status}}`       |
| 推奨Status | `{{project.recommended_status}}`   |
| 更新意図   | `{{project.status_update_intent}}` |

Status更新は、GitHub Actions または運用スクリプトで実施する。  
このログではStatus更新の意図のみを記録する。

---

## 20. 正本参照

| 種別              | 参照先                       |
| ----------------- | ---------------------------- |
| 作業計画          | `{{issue.url}}`              |
| 作業結果          | `{{pr.url}}`                 |
| Definition        | `{{definition.path}}`        |
| Review Definition | `{{review_definition.path}}` |
| 関連docs          | `{{docs.url}}`               |
| 関連レビュー      | `{{review.url}}`             |
| 関連ログ          | `{{related_log.url}}`        |

---

## 21. 記録先

| 項目      | 内容                                      |
| --------- | ----------------------------------------- |
| 保存要否  | `{{operation_logging.ai_logs.incidents}}` |
| 保存先    | `{{operation_logging.path}}`              |
| log level | `{{operation_logging.level}}`             |
| 保存理由  | {{operation_logging.reason}}              |

このログは incident を記録するための補助ログである。  
作業計画はIssue、作業結果とレビュー結果はPR、成果物はdocsを正本とする。

---

## 22. 備考

{{#each notes}}

- {{this}}
  {{/each}}

{{#unless notes}}

- なし
  {{/unless}}
