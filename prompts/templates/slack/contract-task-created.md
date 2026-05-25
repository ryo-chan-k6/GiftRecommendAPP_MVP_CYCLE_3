# Contract Task Created

## 1. 結論

Contract Task Issueを作成しました。  
通常Taskから分離し、API契約変更・OpenAPI・Orval・generated影響を専用Taskとして管理します。

| 項目                | 内容                    |
| ------------------- | ----------------------- |
| Contract Task Issue | `{{issue.number}}`      |
| Issue URL           | `{{issue.url}}`         |
| Contract ID         | `{{contract.id}}`       |
| Contract種別        | `{{contract.type}}`     |
| Priority            | `{{contract.priority}}` |
| Definition          | `{{definition.path}}`   |
| 発生元Command       | `{{command.name}}`      |
| 作成者              | `{{agent.primary}}`     |
| 作成日時            | `{{created_at}}`        |

---

## 2. Contract概要

{{contract.summary}}

| 項目                | 内容                                 |
| ------------------- | ------------------------------------ |
| タイトル            | {{contract.title}}                   |
| 発生元              | `{{source.discovered_from}}`         |
| 関連Issue           | `{{source.related_issue}}`           |
| 関連PR              | `{{source.related_pr}}`              |
| 関連Task Definition | `{{source.related_task_definition}}` |

---

## 3. Contract Task化した理由

{{source.reason}}

### 3.1 分離理由

{{#each contract_task.required_reasons}}

- {{this}}
  {{/each}}

{{#unless contract_task.required_reasons}}

- API contract / OpenAPI / Orval / generated など、通常Taskに混在させるべきでない横断影響があるため
  {{/unless}}

---

## 4. 契約変更内容

| 項目       | 内容                                |
| ---------- | ----------------------------------- |
| API名      | `{{change.api_name}}`               |
| API種別    | `{{change.api_kind}}`               |
| Method     | `{{change.method}}`                 |
| Endpoint   | `{{change.endpoint}}`               |
| 変更種別   | `{{change.change_type}}`            |
| 破壊的変更 | `{{change.breaking_change}}`        |
| 後方互換性 | `{{change.backward_compatibility}}` |
| 変更理由   | {{change.reason}}                   |

---

## 5. 作業範囲

### 5.1 scope

{{#each scope}}

- {{this}}
  {{/each}}

{{#unless scope}}

- なし
  {{/unless}}

### 5.2 out_of_scope

{{#each out_of_scope}}

- {{this}}
  {{/each}}

{{#unless out_of_scope}}

- なし
  {{/unless}}

---

## 6. 主な影響範囲

| 観点      | 影響有無                        | 補足                      |
| --------- | ------------------------------- | ------------------------- |
| API仕様   | `{{impact.api_spec.affected}}`  | {{impact.api_spec.note}}  |
| OpenAPI   | `{{impact.openapi.affected}}`   | {{impact.openapi.note}}   |
| Orval     | `{{impact.orval.affected}}`     | {{impact.orval.note}}     |
| generated | `{{impact.generated.affected}}` | {{impact.generated.note}} |
| provider  | `{{impact.provider.affected}}`  | {{impact.provider.note}}  |
| consumer  | `{{impact.consumer.affected}}`  | {{impact.consumer.note}}  |
| tests     | `{{impact.tests.affected}}`     | {{impact.tests.note}}     |
| docs      | `{{impact.docs.affected}}`      | {{impact.docs.note}}      |
| DB        | `{{impact.db.affected}}`        | {{impact.db.note}}        |
| security  | `{{impact.security.affected}}`  | {{impact.security.note}}  |

---

## 7. provider / consumer 影響

### 7.1 providers

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

### 7.2 consumers

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

---

## 8. 互換性メモ

{{#each provider_consumer.compatibility_notes}}

- {{this}}
  {{/each}}

{{#unless provider_consumer.compatibility_notes}}

- なし
  {{/unless}}

---

## 9. rollout order

{{#each provider_consumer.rollout_order}}

- {{this}}
  {{/each}}

{{#unless provider_consumer.rollout_order}}

- 未定
  {{/unless}}

---

## 10. OpenAPI / Orval / generated 方針

| 項目              | 内容                                        |
| ----------------- | ------------------------------------------- |
| generated差分想定 | `{{generation_policy.generated_expected}}`  |
| generated手動編集 | `{{generation_policy.manual_edit_allowed}}` |
| 生成元ファイル    | `{{generation_policy.source_files}}`        |
| 出力先            | `{{generation_policy.output_paths}}`        |

### 10.1 再生成コマンド

{{#each generation_policy.regenerate_commands}}

```bash
{{this}}
```

{{/each}}

{{#unless generation_policy.regenerate_commands}}

```text
なし
```

{{/unless}}

### 10.2 検証コマンド

{{#each generation_policy.verification_commands}}

```bash
{{this}}
```

{{/each}}

{{#unless generation_policy.verification_commands}}

```text
なし
```

{{/unless}}

---

## 11. Branch / Project

| 項目           | 内容                       |
| -------------- | -------------------------- |
| no-branch      | `{{branch.no_branch}}`     |
| no-branch      | `{{branch.no_branch}}`     |
| Branch         | `{{branch.name}}`          |
| Branch base    | `{{branch.base}}`          |
| PR target      | `{{branch.target}}`        |
| Project        | `{{project.project_name}}` |
| 現在Status     | `{{project.fields.status}}` |
| Phase          | `{{project.fields.phase}}` |

---

## 12. Issue同期項目

| 項目 | 内容 |
| ---- | ---- |
| unit | `{{issue.unit}}` |
| type | `{{issue.type}}` |
| area | `{{issue.area}}` |

---

## 13. Human Reviewで確認してほしいこと

{{#each human_decision_points}}

- {{this}}
  {{/each}}

{{#unless human_decision_points}}

- なし
  {{/unless}}

---

## 14. リスク

{{#each risk_points}}

- {{this}}
  {{/each}}

{{#unless risk_points}}

- なし
  {{/unless}}

---

## 15. ai-logs 記録要否

| 項目              | 内容                                          |
| ----------------- | --------------------------------------------- |
| cross-cutting log | `{{operation_logging.ai_logs.cross_cutting}}` |
| incident log      | `{{operation_logging.ai_logs.incidents}}`     |
| log level         | `{{operation_logging.level}}`                 |
| 理由              | {{operation_logging.reason}}                  |

通常作業ログをすべて `ai-logs/` に保存しない。  
OpenAPI / Orval / generated などの横断影響がある場合のみ、必要に応じて `ai-logs/cross-cutting/` に記録する。

---

## 16. 次Action

```text
/work-issue @{{definition.path}}
```

---

## 17. 正本

| 種別         | 参照先                     |
| ------------ | -------------------------- |
| 作業計画     | `{{issue.url}}`            |
| Definition   | `{{definition.path}}`      |
| 関連Issue    | `{{source.related_issue}}` |
| 関連PR       | `{{source.related_pr}}`    |
| 関連docs     | `{{docs.url}}`             |
| 横断影響ログ | `{{ai_log.url}}`           |

Slack通知は正本ではない。  
作業計画はIssue、作業結果とレビュー結果はPR、成果物はdocsを正本とする。
