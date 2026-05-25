# Cross-Cutting Impact Log

## 1. 概要

| 項目          | 内容                  |
| ------------- | --------------------- |
| Log ID        | `{{log.id}}`          |
| Log種別       | `cross-cutting`       |
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

## 3. このログを記録する理由

{{log.reason}}

### 3.1 cross-cutting log 対象理由

{{#each log.cross_cutting_reasons}}

- {{this}}
  {{/each}}

{{#unless log.cross_cutting_reasons}}

- OpenAPI / Orval / generated / API contract / DB / CI/CD など、複数領域に影響する可能性があるため
  {{/unless}}

### 3.2 通常作業ログではない理由

通常作業ログをすべて `ai-logs/` に保存しない。  
このログは、横断影響の把握、後続Task分離、Contract Task化、人間判断のために記録する。

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

## 5. 確認した事実

AI Agent が確認できた事実。

{{#each facts}}

- {{this}}
  {{/each}}

{{#unless facts}}

- なし
  {{/unless}}

---

## 6. 推論

確認した事実から推論した内容。

{{#each inferences}}

- {{this}}
  {{/each}}

{{#unless inferences}}

- なし
  {{/unless}}

> 推論は確定事実ではない。  
> 後続判断では、PR差分、Issue本文、Definition、正本docsを確認すること。

---

## 7. 未確認事項

{{#each unconfirmed}}

- {{this}}
  {{/each}}

{{#unless unconfirmed}}

- なし
  {{/unless}}

---

## 8. 横断影響範囲

| 観点        | 影響有無                        | 影響度                       | 補足                      |
| ----------- | ------------------------------- | ---------------------------- | ------------------------- |
| docs        | `{{impact.docs.affected}}`      | `{{impact.docs.level}}`      | {{impact.docs.note}}      |
| API仕様     | `{{impact.api_spec.affected}}`  | `{{impact.api_spec.level}}`  | {{impact.api_spec.note}}  |
| OpenAPI     | `{{impact.openapi.affected}}`   | `{{impact.openapi.level}}`   | {{impact.openapi.note}}   |
| Orval       | `{{impact.orval.affected}}`     | `{{impact.orval.level}}`     | {{impact.orval.note}}     |
| generated   | `{{impact.generated.affected}}` | `{{impact.generated.level}}` | {{impact.generated.note}} |
| provider    | `{{impact.provider.affected}}`  | `{{impact.provider.level}}`  | {{impact.provider.note}}  |
| consumer    | `{{impact.consumer.affected}}`  | `{{impact.consumer.level}}`  | {{impact.consumer.note}}  |
| DB schema   | `{{impact.db_schema.affected}}` | `{{impact.db_schema.level}}` | {{impact.db_schema.note}} |
| migration   | `{{impact.migration.affected}}` | `{{impact.migration.level}}` | {{impact.migration.note}} |
| tests       | `{{impact.tests.affected}}`     | `{{impact.tests.level}}`     | {{impact.tests.note}}     |
| CI/CD       | `{{impact.cicd.affected}}`      | `{{impact.cicd.level}}`      | {{impact.cicd.note}}      |
| security    | `{{impact.security.affected}}`  | `{{impact.security.level}}`  | {{impact.security.note}}  |
| Project運用 | `{{impact.project.affected}}`   | `{{impact.project.level}}`   | {{impact.project.note}}   |

---

## 9. 影響対象ファイル / 成果物

### 9.1 docs

{{#each affected.docs}}

- `{{path}}`
  - 影響内容: {{impact}}
  - 対応要否: `{{required}}`
    {{/each}}

{{#unless affected.docs}}

- なし
  {{/unless}}

### 9.2 source code

{{#each affected.files}}

- `{{path}}`
  - 影響内容: {{impact}}
  - 対応要否: `{{required}}`
    {{/each}}

{{#unless affected.files}}

- なし
  {{/unless}}

### 9.3 OpenAPI / Orval / generated

{{#each affected.contract_files}}

- `{{path}}`
  - 種別: `{{type}}`
  - 影響内容: {{impact}}
  - 対応要否: `{{required}}`
    {{/each}}

{{#unless affected.contract_files}}

- なし
  {{/unless}}

### 9.4 tests / CI

{{#each affected.tests}}

- `{{path}}`
  - 影響内容: {{impact}}
  - 対応要否: `{{required}}`
    {{/each}}

{{#unless affected.tests}}

- なし
  {{/unless}}

---

## 10. provider / consumer 影響

### 10.1 providers

{{#each provider_consumer.providers}}

- `{{name}}`
  - affected: `{{affected}}`
  - responsibility: {{responsibility}}
  - required changes:
    {{#each required_changes}} - {{this}}
    {{/each}}
    {{/each}}

{{#unless provider_consumer.providers}}

- なし
  {{/unless}}

### 10.2 consumers

{{#each provider_consumer.consumers}}

- `{{name}}`
  - affected: `{{affected}}`
  - responsibility: {{responsibility}}
  - required changes:
    {{#each required_changes}} - {{this}}
    {{/each}}
    {{/each}}

{{#unless provider_consumer.consumers}}

- なし
  {{/unless}}

### 10.3 compatibility notes

{{#each provider_consumer.compatibility_notes}}

- {{this}}
  {{/each}}

{{#unless provider_consumer.compatibility_notes}}

- なし
  {{/unless}}

### 10.4 rollout order

{{#each provider_consumer.rollout_order}}

- {{this}}
  {{/each}}

{{#unless provider_consumer.rollout_order}}

- 未定
  {{/unless}}

---

## 11. generated / 再生成影響

| 項目              | 内容                                  |
| ----------------- | ------------------------------------- |
| generated差分想定 | `{{generated.expected}}`              |
| 手動編集有無      | `{{generated.manual_edit}}`           |
| 生成元            | `{{generated.source_files}}`          |
| 出力先            | `{{generated.output_paths}}`          |
| 再生成コマンド    | `{{generated.regenerate_commands}}`   |
| 検証コマンド      | `{{generated.verification_commands}}` |

### 11.1 generated確認メモ

{{generated.notes}}

### 11.2 注意

- generatedファイルは手動編集しない
- generated差分がある場合は、生成元と再生成手順を明確にする
- 再生成コマンドが不明な場合は、推測で進めない
- OpenAPI / Orval / generated に影響がある場合は、Contract Task化を検討する

---

## 12. Contract Task化判断

| 項目                | 内容                                |
| ------------------- | ----------------------------------- |
| Contract Task化要否 | `{{contract_task.required}}`        |
| 判断理由            | {{contract_task.reason}}            |
| 推奨Definition      | `{{contract_task.definition_path}}` |
| 推奨Issue種別       | `{{contract_task.issue_type}}`      |
| 推奨Issue unit      | `{{contract_task.issue.unit}}`      |
| 推奨Issue type      | `{{contract_task.issue.type}}`      |
| 推奨Issue area      | `{{contract_task.issue.area}}`      |

### 12.1 Contract Task化が必要な理由

{{#each contract_task.required_reasons}}

- {{this}}
  {{/each}}

{{#unless contract_task.required_reasons}}

- なし
  {{/unless}}

### 12.2 Contract Task化しない理由

{{#each contract_task.not_required_reasons}}

- {{this}}
  {{/each}}

{{#unless contract_task.not_required_reasons}}

- なし
  {{/unless}}

---

## 13. リスク

{{#each risks}}

- {{this}}
  {{/each}}

{{#unless risks}}

- なし
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

## 16. 停止条件

以下に該当する場合、AI Agent は作業を停止し、人間確認へ回す。

{{#each stop_conditions}}

- {{this}}
  {{/each}}

{{#unless stop_conditions}}

- OpenAPI / Orval / generated の変更方針が不明な場合
- generatedファイルの手動編集が必要に見える場合
- provider / consumer の影響範囲が不明な場合
- 破壊的変更の可能性がある場合
- DB schema変更が必要になった場合
- security上の懸念がある場合
- secret、APIキー、`.env` 実値を扱う必要がある場合
  {{/unless}}

---

## 17. Status更新意図

| 項目       | 内容                               |
| ---------- | ---------------------------------- |
| 現在Status | `{{project.current_status}}`       |
| 推奨Status | `{{project.recommended_status}}`   |
| 更新意図   | `{{project.status_update_intent}}` |

Status更新は、GitHub Actions または運用スクリプトで実施する。  
このログではStatus更新の意図のみを記録する。

---

## 18. 正本参照

| 種別              | 参照先                       |
| ----------------- | ---------------------------- |
| 作業計画          | `{{issue.url}}`              |
| 作業結果          | `{{pr.url}}`                 |
| Definition        | `{{definition.path}}`        |
| Review Definition | `{{review_definition.path}}` |
| 関連docs          | `{{docs.url}}`               |
| 関連レビュー      | `{{review.url}}`             |

---

## 19. 記録先

| 項目      | 内容                                          |
| --------- | --------------------------------------------- |
| 保存要否  | `{{operation_logging.ai_logs.cross_cutting}}` |
| 保存先    | `{{operation_logging.path}}`                  |
| log level | `{{operation_logging.level}}`                 |
| 保存理由  | {{operation_logging.reason}}                  |

このログは横断影響を記録するための補助ログである。  
作業計画はIssue、作業結果とレビュー結果はPR、成果物はdocsを正本とする。

---

## 20. 備考

{{#each notes}}

- {{this}}
  {{/each}}

{{#unless notes}}

- なし
  {{/unless}}
