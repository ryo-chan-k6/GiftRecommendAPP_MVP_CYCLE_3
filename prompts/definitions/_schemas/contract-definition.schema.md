# Contract Definition Schema

## 1. 目的

本ドキュメントは、`prompts/definitions/cross-cutting/` 配下に配置する Contract Definition の標準構造を定義する。

Contract Definition は、AI Agent に対して以下を明確に伝えるための契約変更定義である。

- どのAPI契約を変更するか
- なぜ契約変更が必要か
- OpenAPI / Orval / generated / API client に影響があるか
- provider / consumer のどちらに影響するか
- 通常Taskから分離すべき横断影響があるか
- 破壊的変更か、後方互換性を維持できるか
- どの成果物・実装・テストを更新する必要があるか
- どの条件で人間判断へ回すか

Contract Definition は、通常Taskに API contract / OpenAPI / Orval / generated などの横断影響を混在させないために利用する。

正本は Task Definition設計書 **§9.5（Contract Definition）**・**§10.2（contract 必須項目）**・**§12 `definition_type`**（Contract では `contract` 固定）とする。task 型と共通の骨格は **§9.1** を参照する。ルートキー `contract:` に加え、契約変更固有の `source` / `change` / `impact` / `generation_policy` 等を置く。記入例は `_examples/contract-definition.example.yaml`。

---

## 2. 対象ファイル

本Schemaは、以下に配置するContract Definitionを対象とする。

```text
prompts/definitions/cross-cutting/<theme>/<name>.yaml
```

例：

```text
prompts/definitions/cross-cutting/api-contract-orval/contract-task.yaml
prompts/definitions/cross-cutting/recommendation-api-contract/contract-task.yaml
prompts/definitions/cross-cutting/generated-api-client/contract-task.yaml
```

---

## 3. 対応Command

Contract Definition は、主に以下のCommandで利用する。

| Command                 | 利用目的                                    |
| ----------------------- | ------------------------------------------- |
| `/create-contract-task` | 契約変更Task Issueを作成する                |
| `/work-issue`           | 作成済みContract Task Issue上で実作業を行う |
| `/create-pr`            | 契約変更の作業結果をPR化する                |
| `/review-pr`            | Contract変更PRをレビューする                |
| `/summarize-work`       | 契約変更・影響分析・判断依頼を要約する      |

---

## 4. 基本形式

Contract Definition は YAML 形式で記述する。

```yaml
schema_version: "1.0"
definition_type: "contract"

contract:
  id:
  title:
  summary:
  type:
  priority:
  status:

work_mode: "ai-agent"

source:
  discovered_from:
  related_issue:
  related_pr:
  related_task_definition:
  related_review:
  reason:

commands:
  primary:
  allowed:
  next:

agent:
  primary:
  support:
  review:

change:
  api_name:
  api_kind:
  endpoint:
  method:
  change_type:
  breaking_change:
  backward_compatibility:
  reason:

scope:
out_of_scope:

input:
  docs:
  templates:
  files:
  issues:
  prs:
  openapi:
  orval:
  generated:

output:
  docs:
  files:
  openapi:
  orval:
  generated:
  tests:
  logs:

impact:
  api_design:
  api_list:
  api_spec:
  openapi:
  orval:
  generated:
  provider:
  consumer:
  tests:
  docs:
  db:
  cicd:
  security:

provider_consumer:
  providers:
  consumers:
  compatibility_notes:
  rollout_order:

generation_policy:
  generated_expected:
  manual_edit_allowed:
  source_files:
  regenerate_commands:
  output_paths:
  verification_commands:

deliverables:
acceptance_criteria:

branch:
  no_branch:
  name:
  base:
  target:
  worktree_required:

project:
  project_name:
  fields:
    phase:
    status:
    priority:
    planned_start:
    due_date:

issue:
  unit:
  type:
  area:

dependencies:
  epics:
  issues:
  prs:
  tasks:
  blocking:

parallel_control:
  depends_on:
  blocks:
  exclusive_files:
  conflict_risk:
  generated_impact:
  contract_impact:
  db_impact:

test_policy:
  required:
  commands:
  manual_checks:
  not_required:
  skip_reason:

review:
  human_review_required:
  ai_review_required:
  review_points:
  specialist_reviews:

operation_logging:
  level:
  ai_logs:
  reason:

risk_points:
human_decision_points:
stop_conditions:
notes:
```

---

## 5. 必須項目一覧

| 項目                           | 必須 | 内容                       |
| ------------------------------ | ---- | -------------------------- |
| `schema_version`               | 必須 | Schema version             |
| `definition_type`              | 必須 | `contract` 固定            |
| `work_mode`                    | 必須 | `human-led` または `ai-agent`（§16.1・§16.2） |
| `contract.id`                  | 必須 | Contract Definition識別子  |
| `contract.title`               | 必須 | 契約変更Task名             |
| `contract.type`                | 必須 | 契約変更種別               |
| `source.reason`                | 必須 | 契約変更が必要になった理由 |
| `commands.primary`             | 必須 | 主に実行するCommand        |
| `agent.primary`                | 必須 | 主担当Agent                |
| `change.api_name`              | 必須 | 対象API名                  |
| `change.api_kind`              | 必須 | API種別                    |
| `change.change_type`           | 必須 | 変更種別                   |
| `change.breaking_change`       | 必須 | 破壊的変更有無             |
| `scope`                        | 必須 | 今回実施すること           |
| `out_of_scope`                 | 必須 | 今回実施しないこと         |
| `input`                        | 必須 | 入力資料                   |
| `output`                       | 必須 | 出力先                     |
| `impact`                       | 必須 | 影響範囲                   |
| `provider_consumer`            | 必須 | provider / consumer 影響   |
| `generation_policy`            | 必須 | generatedファイルの扱い    |
| `deliverables`                 | 必須 | 成果物                     |
| `acceptance_criteria`          | 必須 | 完了条件                   |
| `branch`                       | 必須 | Branch方針                 |
| `project`                      | 必須 | Project同期項目            |
| `issue.unit`                   | 必須 | 作業管理分類（issue同期項目） |
| `issue.type`                   | 必須 | 作業種別（issue同期項目）  |
| `issue.area`                   | 必須 | 作業対象領域（issue同期項目） |
| `dependencies.epics`           | 必須 | 依存Epic Issue番号配列（空配列可） |
| `parallel_control`             | 必須 | 並列作業制御               |
| `test_policy`                  | 必須 | テスト・検証方針           |
| `review.human_review_required` | 必須 | Human Review要否           |
| `operation_logging.level`      | 必須 | AIログ運用レベル           |
| `human_decision_points`        | 必須 | 人間判断事項               |
| `stop_conditions`              | 必須 | 停止条件                   |

---

## 6. 項目定義

### 6.1 `schema_version`

Schema versionを記載する。

```yaml
schema_version: "1.0"
```

---

### 6.2 `definition_type`

Definition種別を記載する。正本は Task Definition設計書 **§12 `definition_type`**。

Contract Definitionでは `contract` 固定とする。

```yaml
definition_type: "contract"
```

---

### 6.3 `work_mode`

人主導 / AI主導の判定キー。正本は Task Definition設計書 **§16.1**。

```yaml
work_mode: "ai-agent"
```

| 項目   | 内容                            |
| ------ | ------------------------------- |
| 型     | string                          |
| 必須   | yes                             |
| 配置   | `contract` ブロック直後（推奨） |
| 許容値 | `human-led`, `ai-agent`         |

| `work_mode`   | `branch.no_branch` 標準値 | 説明（Issue運用ルール §7 / §8）                          |
| ------------- | ------------------------- | -------------------------------------------------------- |
| `human-led`   | `true`                    | 未来着手Issue。着手まで Branch 作成を遅延                |
| `ai-agent`    | `false`                   | Issue 作成後に Branch 作成まで進める（Contract Task 標準） |

`branch.no_branch` は上記標準値と **一致必須** とする。意図的にずらす場合は `human_decision_points` に理由を明記する。

`/create-contract-task` では、`work_mode` と `branch.no_branch` の整合を確認する。

---

## 7. `contract`

Contract Definition自体の基本情報を定義する。

```yaml
contract:
  id: "contract-recommendation-api-orval"
  title: "レコメンドAPI契約変更Task"
  summary: "レコメンドAPIのOpenAPI定義変更とOrval再生成を行う"
  type: "api_contract"
  priority: "medium"
  status: "ready"
```

### 7.1 `contract.id`

Contract Definitionを識別するID。

| 項目 | 内容                                |
| ---- | ----------------------------------- |
| 型   | string                              |
| 必須 | yes                                 |
| 命名 | kebab-case推奨                      |
| 例   | `contract-recommendation-api-orval` |

---

### 7.2 `contract.title`

契約変更Task名。

---

### 7.3 `contract.summary`

契約変更の概要。

---

### 7.4 `contract.type`

契約変更種別。

| 許容値              | 内容                                   |
| ------------------- | -------------------------------------- |
| `api_contract`      | API契約変更                            |
| `openapi`           | OpenAPI定義変更                        |
| `orval`             | Orval設定・生成変更                    |
| `generated_client`  | generated API client変更               |
| `provider_consumer` | provider / consumer 双方に影響する変更 |
| `contract_test`     | contract test追加・修正                |
| `cross_cutting`     | 複数領域にまたがる横断変更             |

---

### 7.5 `contract.priority`

優先度。

| 許容値   | 内容     |
| -------- | -------- |
| `high`   | 優先度高 |
| `medium` | 通常     |
| `low`    | 優先度低 |

---

### 7.6 `contract.status`

Definition自体の状態。

| 許容値       | 内容     |
| ------------ | -------- |
| `draft`      | 作成中   |
| `ready`      | 実行可能 |
| `blocked`    | 前提不足 |
| `deprecated` | 廃止     |

---

## 8. `source`

契約変更が必要になった経緯を定義する。

```yaml
source:
  discovered_from: "review"
  related_issue: "#102"
  related_pr: "#203"
  related_task_definition: "prompts/definitions/tasks/recommendation-result/implementation.yaml"
  related_review: "prompts/definitions/reviews/recommendation-result/pr-review.yaml"
  reason: "通常Taskの実装中に、response schemaの追加が必要になったため"
```

| 項目                      | 必須     | 内容                   |
| ------------------------- | -------- | ---------------------- |
| `discovered_from`         | 必須     | 契約変更が発生した入口 |
| `related_issue`           | 条件付き | 関連Issue              |
| `related_pr`              | 条件付き | 関連PR                 |
| `related_task_definition` | 条件付き | 関連Task Definition    |
| `related_review`          | 条件付き | 関連Review Definition  |
| `reason`                  | 必須     | 契約変更が必要な理由   |

`discovered_from` の許容値例：

| 値               | 内容                       |
| ---------------- | -------------------------- |
| `planning`       | 計画段階で判明             |
| `implementation` | 実装中に判明               |
| `review`         | レビュー中に判明           |
| `ci`             | CIで判明                   |
| `human_decision` | 人間判断で発生             |
| `incident`       | 作業不可・障害・例外で判明 |

---

## 9. `commands`

このDefinitionが対応するCommandを定義する。

```yaml
commands:
  primary: "/create-contract-task"
  allowed:
    - "/create-contract-task"
    - "/work-issue"
    - "/create-pr"
    - "/review-pr"
    - "/summarize-work"
  next:
    success: "/work-issue"
    pr: "/create-pr"
    review: "/review-pr"
    blocked: null
```

---

## 10. `agent`

担当Agentを定義する。

```yaml
agent:
  primary: "contract-ai"
  support:
    - "orchestrator-ai"
    - "support-ai"
    - "test-ai"
  review:
    - "reviewer-ai"
    - "contract-ai"
```

| 項目      | 必須 | 内容          |
| --------- | ---- | ------------- |
| `primary` | 必須 | 主担当Agent   |
| `support` | 任意 | 補助Agent     |
| `review`  | 任意 | レビューAgent |

---

## 11. `change`

契約変更の中身を定義する。

```yaml
change:
  api_name: "Recommendation API"
  api_kind: "public"
  endpoint: "POST /api/v1/recommendations"
  method: "POST"
  change_type: "modify_response"
  breaking_change: false
  backward_compatibility: "compatible"
  reason: "レコメンド理由表示に必要なreason fieldsをresponseへ追加するため"
```

| 項目                     | 必須     | 内容           |
| ------------------------ | -------- | -------------- |
| `api_name`               | 必須     | API名          |
| `api_kind`               | 必須     | API種別        |
| `endpoint`               | 条件付き | endpoint       |
| `method`                 | 条件付き | HTTP method    |
| `change_type`            | 必須     | 変更種別       |
| `breaking_change`        | 必須     | 破壊的変更有無 |
| `backward_compatibility` | 必須     | 後方互換性     |
| `reason`                 | 必須     | 変更理由       |

### 11.1 `api_kind`

| 許容値     | 内容         |
| ---------- | ------------ |
| `public`   | Public API   |
| `internal` | Internal API |
| `batch`    | Batch連携API |
| `reco`     | Reco連携API  |
| `admin`    | 管理系API    |
| `unknown`  | 未確定       |

---

### 11.2 `change_type`

| 許容値                  | 内容               |
| ----------------------- | ------------------ |
| `add_endpoint`          | endpoint追加       |
| `modify_endpoint`       | endpoint変更       |
| `remove_endpoint`       | endpoint削除       |
| `add_request_field`     | request field追加  |
| `modify_request_field`  | request field変更  |
| `remove_request_field`  | request field削除  |
| `add_response_field`    | response field追加 |
| `modify_response_field` | response field変更 |
| `remove_response_field` | response field削除 |
| `modify_error_response` | error response変更 |
| `modify_auth`           | 認証認可仕様変更   |
| `modify_operation_id`   | operationId変更    |
| `modify_schema`         | schema変更         |
| `modify_orval_config`   | Orval設定変更      |
| `regenerate_client`     | client再生成       |
| `other`                 | その他             |

---

### 11.3 `backward_compatibility`

| 許容値                     | 内容                 |
| -------------------------- | -------------------- |
| `compatible`               | 後方互換性あり       |
| `conditionally_compatible` | 条件付きで互換性あり |
| `breaking`                 | 破壊的変更           |
| `unknown`                  | 未確定               |

Public APIで `breaking` または `unknown` の場合は、人間判断へ回す。

---

## 12. `scope`

今回実施することを定義する。

```yaml
scope:
  - "API仕様書の対象response schemaを更新する"
  - "OpenAPI定義を更新する"
  - "OrvalでAPI clientを再生成する"
  - "provider / consumer の影響範囲を確認する"
```

---

## 13. `out_of_scope`

今回実施しないことを定義する。

```yaml
out_of_scope:
  - "UI仕様変更"
  - "DB schema変更"
  - "レコメンドアルゴリズム変更"
  - " unrelated endpoint の修正"
```

scope外変更をContract Taskに混在させない。

---

## 14. `input`

参照する入力資料を定義する。

```yaml
input:
  docs:
    - path: "docs/04_論理設計/API設計方針書.md"
      required: true
      purpose: "API設計方針を確認するため"
    - path: "docs/05_実装設計/API仕様書.md"
      required: true
      purpose: "対象API仕様を確認するため"
  templates:
    - path: "prompts/templates/docs/api-spec.md"
      required: true
      purpose: "API仕様書を標準フォーマットで更新するため"
      applies_to:
        - "docs/05_実装設計/API仕様書.md"
  files:
    - path: "apps/api/src/routes/recommendations.ts"
      required: false
      purpose: "provider実装の影響確認"
  issues:
    - "#102"
  prs:
    - "#203"
  openapi:
    path: "packages/contracts/openapi/public-api.yaml"
    required: true
  orval:
    path: "orval.config.ts"
    required: true
  generated:
    paths:
      - "apps/web/src/generated/api/"
    required: true
```

---

### 14.1 `input.templates`

成果物docsの作成・更新時に利用する文書テンプレートを定義する。

| 項目         | 必須 | 内容                                 |
| ------------ | ---- | ------------------------------------ |
| `path`       | yes  | 利用するテンプレートファイルのパス   |
| `required`   | yes  | 必須テンプレートか                   |
| `purpose`    | yes  | テンプレートの利用目的               |
| `applies_to` | 推奨 | このテンプレートを適用する出力先docs |

例：

````yaml
templates:
  - path: "prompts/templates/docs/api-spec.md"
    required: true
    purpose: "API仕様書を標準フォーマットで更新するため"
    applies_to:
      - "docs/05_実装設計/API仕様書.md"

---

## 15. `output`

作成・更新する出力先を定義する。

```yaml
output:
  docs:
    - path: "docs/05_実装設計/API仕様書.md"
      action: "update"
      required: true
      template: "prompts/templates/docs/api-spec.md"
  files:
    - path: "apps/api/src/routes/recommendations.ts"
      action: "update"
      required: false
  openapi:
    - path: "packages/contracts/openapi/public-api.yaml"
      action: "update"
      required: true
  orval:
    - path: "orval.config.ts"
      action: "update"
      required: false
  generated:
    - path: "apps/web/src/generated/api/"
      action: "regenerate"
      required: true
  tests:
    - path: "apps/api/tests/contract/recommendations.test.ts"
      action: "update"
      required: true
  logs:
    ai_logs_required: true
    path: "ai-logs/cross-cutting/"
````

### 15.1 `output.docs`

作成・更新するdocsを定義する。

| 項目       | 必須     | 内容                           |
| ---------- | -------- | ------------------------------ |
| `path`     | yes      | 出力先docs                     |
| `action`   | yes      | `create` / `update` / `delete` |
| `required` | yes      | 必須成果物か                   |
| `template` | 条件付き | 利用する文書テンプレート       |

例：

```yaml
docs:
  - path: "docs/05_実装設計/API仕様書.md"
    action: "update"
    required: true
    template: "prompts/templates/docs/api-spec.md"
```

### 15.2 `output.generated`

generatedファイルは、原則として再生成によって更新する。  
手動編集してはならない。

---

## 16. `impact`

影響範囲を定義する。

```yaml
impact:
  api_design:
    affected: true
    note: "API仕様書のresponse schemaを更新する"
  api_list:
    affected: false
    note: "既存endpointのresponse追加のみ"
  api_spec:
    affected: true
    note: "response項目追加"
  openapi:
    affected: true
    note: "components schema更新"
  orval:
    affected: true
    note: "client再生成が必要"
  generated:
    affected: true
    note: "generated API client差分あり"
  provider:
    affected: true
    note: "apps/api のresponse生成処理に影響"
  consumer:
    affected: true
    note: "apps/web の型利用箇所に影響"
  tests:
    affected: true
    note: "contract test更新が必要"
  docs:
    affected: true
    note: "API仕様書更新"
  db:
    affected: false
    note: "DB schema変更なし"
  cicd:
    affected: false
    note: "CI定義変更なし"
  security:
    affected: false
    note: "認証認可仕様変更なし"
```

| 項目       | 内容     |
| ---------- | -------- |
| `affected` | 影響有無 |
| `note`     | 影響内容 |

影響有無が不明な場合は `unknown` 相当として扱い、人間確認へ回す。

---

## 17. `provider_consumer`

provider / consumer の影響を定義する。

```yaml
provider_consumer:
  providers:
    - name: "apps/api"
      affected: true
      responsibility: "Public API provider"
      required_changes:
        - "response schemaにreason fieldsを追加"
  consumers:
    - name: "apps/web"
      affected: true
      responsibility: "Public API consumer"
      required_changes:
        - "generated clientの型差分を確認"
  compatibility_notes:
    - "response field追加のため、既存consumerへの破壊的影響は低い"
  rollout_order:
    - "OpenAPI更新"
    - "provider実装更新"
    - "Orval再生成"
    - "consumer型確認"
    - "contract test実行"
```

---

## 18. `generation_policy`

generatedファイルの扱いを定義する。

```yaml
generation_policy:
  generated_expected: true
  manual_edit_allowed: false
  source_files:
    - "packages/contracts/openapi/public-api.yaml"
  regenerate_commands:
    - "pnpm orval"
  output_paths:
    - "apps/web/src/generated/api/"
  verification_commands:
    - "pnpm typecheck"
    - "pnpm test"
```

| 項目                    | 必須     | 内容                    |
| ----------------------- | -------- | ----------------------- |
| `generated_expected`    | 必須     | generated差分想定       |
| `manual_edit_allowed`   | 必須     | 手動編集可否。原則false |
| `source_files`          | 条件付き | 生成元                  |
| `regenerate_commands`   | 条件付き | 再生成コマンド          |
| `output_paths`          | 条件付き | 生成先                  |
| `verification_commands` | 推奨     | 再生成後の検証コマンド  |

`manual_edit_allowed: true` は原則禁止する。  
必要に見える場合は停止し、人間確認へ回す。

---

## 19. `deliverables`

成果物を定義する。

```yaml
deliverables:
  - "Contract Task Issue"
  - "契約変更影響分析"
  - "更新済みAPI仕様書"
  - "更新済みOpenAPI定義"
  - "再生成済みAPI client"
  - "更新済みcontract test"
```

---

## 20. `acceptance_criteria`

完了条件を定義する。

```yaml
acceptance_criteria:
  - "契約変更の目的がIssue本文に記載されている"
  - "影響範囲がAPI設計書、OpenAPI、Orval、generated、provider、consumer、testに分けて整理されている"
  - "OpenAPI定義が更新されている"
  - "generatedファイルが手動編集ではなく再生成で更新されている"
  - "provider / consumer の影響確認が完了している"
  - "必要なcontract testが実行または未実施理由付きで整理されている"
  - "破壊的変更有無と後方互換性が明記されている"
  - "Human Review観点が明記されている"
```

完了条件は、検証可能な文にする。

---

## 21. `branch`

Branch方針を定義する。`no_branch` は §16.1 `work_mode` の標準値と一致必須とする。

```yaml
branch:
  no_branch: false
  name: "feature/task-<issue-number>-recommendation-api-orval"
  base: "feature/epic-<issue-number>-recommendation-api"
  target: "feature/epic-<issue-number>-recommendation-api"
  worktree_required: true
```

| 項目                | 必須     | 内容                                                          |
| ------------------- | -------- | ------------------------------------------------------------- |
| `no_branch`         | 必須     | Branchを作らない場合は `true`。`work_mode` 標準値と一致必須（§16.2） |
| `name`              | 条件付き | Branch名                                                      |
| `base`              | 条件付き | Branch base                                                   |
| `target`            | 条件付き | PR target                                                     |
| `worktree_required` | 推奨     | worktree 要否                                                 |

Task BranchのPR targetは、原則として親Epic Branchとする。  
Task Branchから `develop` へ直接PRを作成してはならない。

---

## 22. `project`

GitHub Projects同期項目を定義する。

```yaml
project:
  project_name: "Gift Recommendation Service MVP Cycle 3"
  fields:
    phase: "06_実装設計"
    status: "Todo"
    priority: "high"
    planned_start: null
    due_date: null
```

---

## 23. `issue`

Issueに同期する分類を定義する。正本は Task Definition設計書 §9.1・§14 とする。

```yaml
issue:
  unit: "task"
  type: "feature"
  area: "api"
```

`issue.type` は GitHub Label / Branch type に同期する通常の作業種別を記載する。契約変更種別は `contract.type` に記載し、`issue.type: "contract"` は使用しない。

---

## 24. `dependencies`

依存関係を定義する。

```yaml
dependencies:
  epics:
    - "#300"
  issues:
    - "#102"
  prs:
    - "#203"
  tasks:
    - "task-recommendation-result-implementation"
  blocking: true
```

契約変更に依存するEpic / 通常Taskがある場合、依存関係を明示する。`dependencies.epics` は空配列でも明示する。

---

## 25. `test_policy`

テスト・検証方針を定義する。

```yaml
test_policy:
  required:
    - "OpenAPI validation"
    - "Orval generation"
    - "typecheck"
    - "contract test"
  commands:
    - "pnpm openapi:validate"
    - "pnpm orval"
    - "pnpm typecheck"
    - "pnpm test"
  manual_checks:
    - "generated差分がOpenAPI変更と対応していることを確認する"
    - "provider / consumer の影響範囲を確認する"
  not_required:
    - "e2e test"
  skip_reason:
    e2e test: "契約変更Taskでは、まずcontract testとtypecheckを優先するため"
```

実施していないテストを実施済みとして報告してはならない。

---

## 26. `review`

レビュー方針を定義する。

```yaml
review:
  human_review_required: true
  ai_review_required: true
  review_points:
    - "通常Taskから契約変更が分離されているか"
    - "OpenAPI / Orval / generated の影響が整理されているか"
    - "generatedファイルを手動編集していないか"
    - "provider / consumer の影響が整理されているか"
    - "破壊的変更有無が明記されているか"
  specialist_reviews:
    docs: true
    test: true
    contract: true
    security: true
```

Contract Definitionでは、原則として `contract: true` とする。

---

## 27. `operation_logging`

AIログ運用を定義する。

```yaml
operation_logging:
  level: "standard"
  ai_logs:
    intake: false
    incidents: false
    cross_cutting: true
    experiments: false
  reason: "OpenAPI / Orval / generated への横断影響があるため、必要に応じてcross-cuttingログ候補とする"
```

通常作業ログをすべて `ai-logs/` に保存しない。  
ただし、Contract Taskでは横断影響が大きい場合、`ai-logs/cross-cutting/` への記録候補とする。

---

## 28. `risk_points`

リスク観点を記載する。

```yaml
risk_points:
  - "OpenAPIとprovider実装が不一致になる可能性"
  - "generated API client差分によりconsumer側で型エラーが発生する可能性"
  - "破壊的変更を互換変更として扱ってしまう可能性"
  - "通常Taskにcontract変更が混在する可能性"
```

---

## 29. `human_decision_points`

人間判断が必要な論点を記載する。

```yaml
human_decision_points:
  - "Public APIのresponse field追加をMVPで実施してよいか"
  - "後方互換性ありとして扱ってよいか"
  - "consumer側修正を同一Contract Taskに含めるか、別Taskに分けるか"
```

ない場合でも空配列 `[]` を明記する。

---

## 30. `stop_conditions`

作業停止条件を記載する。

```yaml
stop_conditions:
  - "契約変更の目的が不明な場合"
  - "対象APIが不明な場合"
  - "破壊的変更の可能性がある場合"
  - "Public APIの後方互換性判断が必要な場合"
  - "OpenAPI変更方針が不明な場合"
  - "Orval再生成方針が不明な場合"
  - "generatedファイルの手動編集が必要に見える場合"
  - "provider / consumer の影響範囲が不明な場合"
  - "secretや.env実値を扱う必要がある場合"
  - "security上の懸念がある場合"
```

---

## 31. `notes`

補足事項を記載する。

```yaml
notes:
  - "Contract Taskでは、OpenAPIを生成元、generated API clientを派生物として扱う"
  - "Slack通知は正本ではない。契約変更の正本はIssue、PR、docsとする"
```

---

## 32. 標準テンプレート

新しいContract Definitionは、原則として以下を雛形にする。

```yaml
schema_version: "1.0"
definition_type: "contract"

contract:
  id: ""
  title: ""
  summary: ""
  type: "api_contract"
  priority: "medium"
  status: "draft"

work_mode: "ai-agent"

source:
  discovered_from: null
  related_issue: null
  related_pr: null
  related_task_definition: null
  related_review: null
  reason: ""

commands:
  primary: "/create-contract-task"
  allowed:
    - "/create-contract-task"
    - "/work-issue"
    - "/create-pr"
    - "/review-pr"
    - "/summarize-work"
  next:
    success: "/work-issue"
    pr: "/create-pr"
    review: "/review-pr"
    blocked: null

agent:
  primary: "contract-ai"
  support:
    - "orchestrator-ai"
    - "support-ai"
    - "test-ai"
  review:
    - "reviewer-ai"
    - "contract-ai"

change:
  api_name: ""
  api_kind: "unknown"
  endpoint: null
  method: null
  change_type: ""
  breaking_change: null
  backward_compatibility: "unknown"
  reason: ""

scope: []

out_of_scope: []

input:
  docs: []
  templates: []
  files: []
  issues: []
  prs: []
  openapi:
    path: null
    required: false
  orval:
    path: null
    required: false
  generated:
    paths: []
    required: false

output:
  docs: []
  files: []
  openapi: []
  orval: []
  generated: []
  tests: []
  logs:
    ai_logs_required: false
    path: null

impact:
  api_design:
    affected: false
    note: ""
  api_list:
    affected: false
    note: ""
  api_spec:
    affected: false
    note: ""
  openapi:
    affected: false
    note: ""
  orval:
    affected: false
    note: ""
  generated:
    affected: false
    note: ""
  provider:
    affected: false
    note: ""
  consumer:
    affected: false
    note: ""
  tests:
    affected: false
    note: ""
  docs:
    affected: false
    note: ""
  db:
    affected: false
    note: ""
  cicd:
    affected: false
    note: ""
  security:
    affected: false
    note: ""

provider_consumer:
  providers: []
  consumers: []
  compatibility_notes: []
  rollout_order: []

generation_policy:
  generated_expected: false
  manual_edit_allowed: false
  source_files: []
  regenerate_commands: []
  output_paths: []
  verification_commands: []

deliverables: []

acceptance_criteria: []

branch:
  no_branch: false
  name: null
  base: null
  target: null
  worktree_required: false

project:
  project_name: ""
  fields:
    phase: ""
    status: "Todo"
    priority: "medium"
    planned_start: null
    due_date: null

issue:
  unit: ""
  type: ""
  area: ""

dependencies:
  epics: []
  issues: []
  prs: []
  tasks: []
  blocking: false

parallel_control:
  depends_on: []
  blocks: []
  exclusive_files: []
  conflict_risk: "low"
  generated_impact: false
  contract_impact: true
  db_impact: false

test_policy:
  required: []
  commands: []
  manual_checks: []
  not_required: []
  skip_reason: {}

review:
  human_review_required: true
  ai_review_required: true
  review_points: []
  specialist_reviews:
    docs: true
    test: true
    contract: true
    security: true

operation_logging:
  level: "standard"
  ai_logs:
    intake: false
    incidents: false
    cross_cutting: false
    experiments: false
  reason: ""

risk_points: []

human_decision_points: []

stop_conditions: []

notes: []
```

---

## 33. 記入例

```yaml
schema_version: "1.0"
definition_type: "contract"

contract:
  id: "contract-recommendation-api-response-reason"
  title: "レコメンドAPI response reason項目追加"
  summary: "レコメンド結果表示に必要なreason項目をresponse schemaへ追加し、OpenAPIとgenerated clientを更新する"
  type: "api_contract"
  priority: "high"
  status: "ready"

work_mode: "ai-agent"

source:
  discovered_from: "implementation"
  related_issue: "#102"
  related_pr: null
  related_task_definition: "prompts/definitions/tasks/recommendation-result/implementation.yaml"
  related_review: null
  reason: "画面実装Taskで、レコメンド理由表示に必要なresponse項目がAPI仕様に不足していることが判明したため"

commands:
  primary: "/create-contract-task"
  allowed:
    - "/create-contract-task"
    - "/work-issue"
    - "/create-pr"
    - "/review-pr"
    - "/summarize-work"
  next:
    success: "/work-issue"
    pr: "/create-pr"
    review: "/review-pr"
    blocked: null

agent:
  primary: "contract-ai"
  support:
    - "orchestrator-ai"
    - "support-ai"
    - "test-ai"
  review:
    - "reviewer-ai"
    - "contract-ai"

change:
  api_name: "Recommendation API"
  api_kind: "public"
  endpoint: "POST /api/v1/recommendations"
  method: "POST"
  change_type: "add_response_field"
  breaking_change: false
  backward_compatibility: "compatible"
  reason: "レコメンド理由表示に必要なreason項目をresponseへ追加するため"

scope:
  - "API仕様書のRecommendation API response schemaを更新する"
  - "OpenAPI components schemaを更新する"
  - "Orvalでgenerated API clientを再生成する"
  - "provider / consumer 影響を確認する"
  - "contract testを更新する"

out_of_scope:
  - "レコメンドアルゴリズム変更"
  - "DB schema変更"
  - "画面UIデザイン変更"
  - " unrelated endpoint の修正"

input:
  docs:
    - path: "docs/04_論理設計/API設計方針書.md"
      required: true
      purpose: "API設計方針を確認するため"
    - path: "docs/05_実装設計/API仕様書.md"
      required: true
      purpose: "対象API仕様を確認するため"
  files:
    - path: "apps/api/src/routes/recommendations.ts"
      required: true
      purpose: "provider実装の影響確認"
  issues:
    - "#102"
  prs: []
  openapi:
    path: "packages/contracts/openapi/public-api.yaml"
    required: true
  orval:
    path: "orval.config.ts"
    required: true
  generated:
    paths:
      - "apps/web/src/generated/api/"
    required: true

output:
  docs:
    - path: "docs/05_実装設計/API仕様書.md"
      action: "update"
      required: true
      template: "prompts/templates/docs/api-spec.md"
  files:
    - path: "apps/api/src/routes/recommendations.ts"
      action: "update"
      required: true
  openapi:
    - path: "packages/contracts/openapi/public-api.yaml"
      action: "update"
      required: true
  orval: []
  generated:
    - path: "apps/web/src/generated/api/"
      action: "regenerate"
      required: true
  tests:
    - path: "apps/api/tests/contract/recommendations.test.ts"
      action: "update"
      required: true
  logs:
    ai_logs_required: true
    path: "ai-logs/cross-cutting/"

impact:
  api_design:
    affected: true
    note: "API仕様書のresponse項目を追加する"
  api_list:
    affected: false
    note: "既存endpointのschema追加のみ"
  api_spec:
    affected: true
    note: "Recommendation API response schema更新"
  openapi:
    affected: true
    note: "components schema更新"
  orval:
    affected: true
    note: "client再生成が必要"
  generated:
    affected: true
    note: "generated API clientに型差分が出る"
  provider:
    affected: true
    note: "apps/api のresponse生成処理に影響"
  consumer:
    affected: true
    note: "apps/web の型利用箇所に影響"
  tests:
    affected: true
    note: "contract test更新が必要"
  docs:
    affected: true
    note: "API仕様書更新"
  db:
    affected: false
    note: "DB schema変更なし"
  cicd:
    affected: false
    note: "CI定義変更なし"
  security:
    affected: false
    note: "認証認可仕様変更なし"

provider_consumer:
  providers:
    - name: "apps/api"
      affected: true
      responsibility: "Recommendation API provider"
      required_changes:
        - "responseにreason項目を追加する"
  consumers:
    - name: "apps/web"
      affected: true
      responsibility: "Recommendation API consumer"
      required_changes:
        - "generated clientの型差分を確認する"
  compatibility_notes:
    - "response field追加のため、既存consumerへの破壊的影響は低い"
  rollout_order:
    - "API仕様書更新"
    - "OpenAPI更新"
    - "provider実装更新"
    - "Orval再生成"
    - "consumer型確認"
    - "contract test実行"

generation_policy:
  generated_expected: true
  manual_edit_allowed: false
  source_files:
    - "packages/contracts/openapi/public-api.yaml"
  regenerate_commands:
    - "pnpm orval"
  output_paths:
    - "apps/web/src/generated/api/"
  verification_commands:
    - "pnpm typecheck"
    - "pnpm test"

deliverables:
  - "Contract Task Issue"
  - "契約変更影響分析"
  - "更新済みAPI仕様書"
  - "更新済みOpenAPI定義"
  - "再生成済みAPI client"
  - "更新済みcontract test"

acceptance_criteria:
  - "契約変更の目的がIssue本文に記載されている"
  - "API仕様書が更新されている"
  - "OpenAPI定義が更新されている"
  - "generated API clientが再生成されている"
  - "generatedファイルを手動編集していない"
  - "provider / consumer の影響確認が完了している"
  - "contract testが実行または未実施理由付きで整理されている"
  - "破壊的変更有無と後方互換性が明記されている"

branch:
  no_branch: false
  name: "feature/task-<issue-number>-recommendation-api-response-reason"
  base: "feature/epic-<issue-number>-recommendation-api"
  target: "feature/epic-<issue-number>-recommendation-api"
  worktree_required: true

project:
  project_name: "Gift Recommendation Service MVP Cycle 3"
  fields:
    phase: "06_実装設計"
    status: "Todo"
    priority: "high"
    planned_start: null
    due_date: null

issue:
  unit: "task"
  type: "feature"
  area: "api"

dependencies:
  epics:
    - "#300"
  issues:
    - "#102"
  prs: []
  tasks:
    - "task-recommendation-result-implementation"
  blocking: true

parallel_control:
  depends_on: []
  blocks: []
  exclusive_files:
    - "packages/contracts/openapi/public-api.yaml"
    - "apps/web/src/generated/api/"
  conflict_risk: "medium"
  generated_impact: true
  contract_impact: true
  db_impact: false

test_policy:
  required:
    - "OpenAPI validation"
    - "Orval generation"
    - "typecheck"
    - "contract test"
  commands:
    - "pnpm openapi:validate"
    - "pnpm orval"
    - "pnpm typecheck"
    - "pnpm test"
  manual_checks:
    - "generated差分がOpenAPI変更と対応していることを確認する"
    - "provider / consumer の影響範囲を確認する"
  not_required:
    - "e2e test"
  skip_reason:
    e2e test: "契約変更Taskでは、まずcontract testとtypecheckを優先するため"

review:
  human_review_required: true
  ai_review_required: true
  review_points:
    - "通常Taskから契約変更が分離されているか"
    - "OpenAPI / Orval / generated の影響が整理されているか"
    - "generatedファイルを手動編集していないか"
    - "provider / consumer の影響が整理されているか"
    - "破壊的変更有無が明記されているか"
  specialist_reviews:
    docs: true
    test: true
    contract: true
    security: true

operation_logging:
  level: "standard"
  ai_logs:
    intake: false
    incidents: false
    cross_cutting: true
    experiments: false
  reason: "OpenAPI / Orval / generated への横断影響があるため、必要に応じてcross-cuttingログ候補とする"

risk_points:
  - "OpenAPIとprovider実装が不一致になる可能性"
  - "generated API client差分によりconsumer側で型エラーが発生する可能性"
  - "通常Taskにcontract変更が混在する可能性"

human_decision_points:
  - "response field追加を後方互換性ありとして扱ってよいか"
  - "consumer側修正を同一Contract Taskに含めるか"

stop_conditions:
  - "契約変更の目的が不明な場合"
  - "対象APIが不明な場合"
  - "破壊的変更の可能性がある場合"
  - "OpenAPI変更方針が不明な場合"
  - "Orval再生成方針が不明な場合"
  - "generatedファイルの手動編集が必要に見える場合"
  - "provider / consumer の影響範囲が不明な場合"
  - "secretや.env実値を扱う必要がある場合"
  - "security上の懸念がある場合"

notes:
  - "Contract Taskでは、OpenAPIを生成元、generated API clientを派生物として扱う"
  - "Slack通知は正本ではない。契約変更の正本はIssue、PR、docsとする"
```

---

## 34. バリデーション観点

Contract Definition作成・修正時は、以下を確認する。

### 34.1 必須項目

- `schema_version` がある
- `definition_type: contract` である
- `work_mode` がある（`human-led` または `ai-agent`）
- `work_mode` と `branch.no_branch` が §16.2 の標準値と一致している
- `contract.id` がある
- `contract.title` がある
- `contract.type` がある
- `source.reason` がある
- `change.api_name` がある
- `change.api_kind` がある
- `change.change_type` がある
- `change.breaking_change` が明記されている
- `change.backward_compatibility` が明記されている
- `scope` が空でない
- `out_of_scope` が空でない
- `impact` が定義されている
- `provider_consumer` が定義されている
- `generation_policy` が定義されている
- `acceptance_criteria` がある
- `issue.type` が通常の作業種別（`feature` / `docs` / `test` 等）であり、契約変更種別を `issue.type` に入れていない
- `dependencies.epics` がある（空配列可）
- `test_policy` がある
- `review.human_review_required` がある
- `operation_logging.level` がある
- `stop_conditions` がある
- docs成果物を作成・更新する場合、利用する文書テンプレートが明確である
- `input.templates` に指定されたテンプレートが存在する
- `output.docs[].template` が指定されている場合、`input.templates[].path` と対応している
- 指定テンプレートと作成・更新対象docsの目的が矛盾していない
- 文書テンプレートの章構成に従って成果物を作成・更新する方針になっている

---

### 34.2 contract分離確認

- 通常Taskから契約変更が分離されている
- API contract変更が通常Taskに混在していない
- DB schema変更が混在していない
- generated差分の扱いが明確である
- provider / consumer の影響が整理されている

---

### 34.3 OpenAPI / Orval / generated確認

- OpenAPI変更有無が明確である
- Orval設定変更有無が明確である
- generated API client差分有無が明確である
- generatedファイルを手動編集する前提になっていない
- 再生成コマンドが明確である
- 再生成後の検証コマンドが明確である

---

### 34.4 互換性確認

- breaking change有無が明記されている
- backward compatibilityが明記されている
- Public APIの破壊的変更は人間判断へ回す構造になっている
- provider / consumer の対応順序が整理されている

---

### 34.5 test確認

- OpenAPI validation要否が明確である
- Orval generation要否が明確である
- typecheck要否が明確である
- contract test要否が明確である
- 未実施テストの理由を書く構造になっている

---

### 34.6 security確認

以下が含まれていないこと。

- APIキー
- access token
- refresh token
- password
- private key
- `.env` 実値
- DB接続文字列の実値
- Supabase service role key
- OpenAI API key
- その他secret相当の値

環境変数は、名称のみ記載する。

---

## 35. 禁止事項

以下は禁止する。

- Contract DefinitionなしでAPI contract変更を通常Taskに混在させること
- OpenAPI変更を未整理のまま実装だけ変更すること
- generatedファイルを手動編集する前提にすること
- Orval再生成方針を書かずにgenerated差分を出すこと
- provider / consumer の影響を整理しないこと
- breaking changeを人間判断なしに進めること
- Public APIの後方互換性をAIだけで確定すること
- secretや`.env` 実値を記載すること
- 実施していないテストを実施済みとして扱うこと
- Slack通知だけで契約変更記録を完結させること
- 通常作業ログをすべて `ai-logs/` に保存する前提にすること
- docs作成・更新Taskで、指定された文書テンプレートを無視して成果物を作成すること
- 存在しないテンプレートを指定したままContract Taskを開始すること
- `input.templates` と `output.docs[].template` が矛盾した状態で作業を開始すること

---

## 36. 一言まとめ

Contract Definition は、API contract / OpenAPI / Orval / generated / provider / consumer などの横断影響を安全に扱うための作業条件の正本である。

Task Definition が通常Taskの作業条件を定義するのに対し、Contract Definition は契約変更の目的、影響範囲、互換性、生成物の扱い、provider / consumer の対応、検証方針を定義する。

AI Agentは、Contract Definitionの `scope`、`out_of_scope`、`impact`、`provider_consumer`、`generation_policy`、`acceptance_criteria`、`test_policy`、`human_decision_points`、`stop_conditions` に従って作業し、破壊的変更や後方互換性判断が必要な場合は人間判断へ回す。
