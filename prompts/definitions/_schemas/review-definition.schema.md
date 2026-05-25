# Review Definition Schema

## 1. 目的

本ドキュメントは、`prompts/definitions/reviews/` 配下に配置する Review Definition の標準構造を定義する。

Review Definition は、AI Agent に対して以下を明確に伝えるためのレビュー定義である。

- どのPRをレビュー対象にするか
- どのIssue / Task Definitionを基準にレビューするか
- どの観点で差分を確認するか
- docs / code / test / API contract / DB / generated / security のどこまで確認するか
- 何をもって Human Review へ進めてよいと判断するか
- 何をもって修正要求・停止・人間判断とするか
- レビュー結果をどの形式でPRに記録するか

Review Definition は、作業そのものを実行するための定義ではない。

正本は Task Definition設計書 **§9.4（Review Definition）**・**§10.1（全種別共通）**・**§12 `definition_type`**（Review では `review` 固定）、AIレビュー運用設計書、および `prompts/definitions/_examples/review-definition.example.yaml` を参照する。  
task 型と共通の骨格は設計書 **§9.1** を参照する。レビュー対象の作業条件は Task Definition を正本とし、Review Definition はレビュー観点・判定基準（`target` / `review_scope` / `review_points` / `result_policy` 等）を補足する。

---

## 2. 対象ファイル

本Schemaは、以下に配置する Review Definition を対象とする。

```text
prompts/definitions/reviews/<workstream_key>/pr-review.yaml
```

例：

```text
prompts/definitions/_examples/review-definition.example.yaml
prompts/definitions/reviews/api-contract-orval/pr-review.yaml
```

---

## 3. 対応Command

Review Definition は、主に以下のCommandで利用する。

| Command                | 利用目的                                        |
| ---------------------- | ----------------------------------------------- |
| `/review-pr`           | PRのAI Reviewを実施する                         |
| `/summarize-work`      | AI Review結果をSlack / PR / Issue向けに要約する |
| `/fix-review-comments` | 修正後の再レビュー観点を確認する                |

`/review-pr` では、Review Definition と Task Definition の両方を参照する。  
Task Definition は「何を完了すべきか」、Review Definition は「どの観点でレビューするか」を定義する。

---

## 4. 基本形式

Review Definition は YAML 形式で記述する。

```yaml
schema_version: "1.0"
definition_type: "review"

review:
  id:
  title:
  summary:
  type:
  status:

work_mode: "ai-agent"

target:
  pr:
  issue:
  task_definition:
  source_branch:
  target_branch:
  parent_epic_issue:
  parent_epic_branch:

commands:
  primary:
  allowed:
  next:

agent:
  primary:
  support:
  specialist:
  next:

review_scope:
  docs:
  source:
  tests:
  api_contract:
  db:
  generated:
  cicd:
  security:
  project_operation:

input:
  task_definition:
  issue:
  pr:
  diff:
  docs:
  files:
  test_results:
  ci_results:
  templates:

review_points:
  common:
  docs:
  source:
  tests:
  api_contract:
  db:
  generated:
  cicd:
  security:
  branch:
  project:

acceptance_check:
  use_task_acceptance_criteria:
  additional_criteria:

result_policy:
  approve_for_human_review:
  request_changes:
  needs_human_decision:
  split_required:
  blocked:

status_policy:
  current_status:
  on_approve:
  on_request_changes:
  on_needs_human_decision:
  on_split_required:
  on_blocked:

outputs:
  pr_comment_template:
  slack_template:
  update_pr_body:
  create_follow_up_issue:
  ai_logs:

operation_logging:
  level:
  ai_logs:
  reason:

human_decision_points:
stop_conditions:
notes:
```

---

## 5. 必須項目一覧

以下は原則必須とする。

| 項目                          | 必須     | 内容                      |
| ----------------------------- | -------- | ------------------------- |
| `schema_version`              | 必須     | Schema version            |
| `definition_type`             | 必須     | `review` 固定             |
| `work_mode`                   | 必須     | `human-led` または `ai-agent`（§16.1・§16.2） |
| `review.id`                   | 必須     | Review Definition識別子   |
| `review.title`                | 必須     | レビュー名                |
| `review.type`                 | 必須     | レビュー種別              |
| `target.pr`                   | 条件付き | 対象PR。実行時指定でも可  |
| `target.issue`                | 必須     | 対象Issue                 |
| `target.task_definition`      | 必須     | 基準となるTask Definition |
| `target.source_branch`        | 条件付き | PR source branch          |
| `target.target_branch`        | 条件付き | PR target branch          |
| `commands.primary`            | 必須     | 主に実行するCommand       |
| `agent.primary`               | 必須     | 主担当Agent               |
| `review_scope`                | 必須     | レビュー対象領域          |
| `input.task_definition`       | 必須     | Task Definition参照       |
| `input.pr`                    | 必須     | PR参照                    |
| `input.diff`                  | 必須     | diff確認要否              |
| `review_points.common`        | 必須     | 共通レビュー観点          |
| `acceptance_check`            | 必須     | 完了条件確認方針          |
| `result_policy`               | 必須     | レビュー結果分類          |
| `status_policy`               | 必須     | Status更新意図            |
| `outputs.pr_comment_template` | 必須     | PRコメントテンプレート    |
| `operation_logging.level`     | 必須     | AIログ運用レベル          |
| `human_decision_points`       | 必須     | 人間判断事項              |
| `stop_conditions`             | 必須     | 停止条件                  |

---

## 6. 項目定義

## 6.1 `schema_version`

Schema versionを記載する。

```yaml
schema_version: "1.0"
```

| 項目   | 内容    |
| ------ | ------- |
| 型     | string  |
| 必須   | yes     |
| 記述例 | `"1.0"` |

---

## 6.2 `definition_type`

Definition種別を記載する。正本は Task Definition設計書 **§12 `definition_type`**。

Review Definitionでは `review` 固定とする。

```yaml
definition_type: "review"
```

| 項目   | 内容     |
| ------ | -------- |
| 型     | string   |
| 必須   | yes      |
| 許容値 | `review` |

---

### 6.3 `work_mode`

人主導 / AI主導の判定キー。正本は Task Definition設計書 **§16.1**。

```yaml
work_mode: "ai-agent"
```

| 項目   | 内容                           |
| ------ | ------------------------------ |
| 型     | string                         |
| 必須   | yes                            |
| 配置   | `review` ブロック直後（推奨）  |
| 許容値 | `human-led`, `ai-agent`        |

| `work_mode`   | `branch.no_branch` 標準値 | 説明                                                       |
| ------------- | ------------------------- | ---------------------------------------------------------- |
| `human-led`   | `true`                    | 未来着手Issue。着手まで Branch 作成を遅延                  |
| `ai-agent`    | `false`                   | Issue 作成後に Branch 作成まで進める（Task / Contract 標準） |

**Review Definition の補足:** `/review-pr` のみで利用し Issue を新規作成しない場合は `branch` ブロックを省略してよい。Issue 作成や `/start-task` 連携時は `branch` を記載し、PRレビューで新規 Branch を作らない場合は `ai-agent` + `no_branch: true` とし、`human_decision_points` に理由を明記する（§19.5）。

`/review-pr` では、記載がある `work_mode` と `branch.no_branch` の整合を確認する。

---

## 7. `review`

Review Definition 自体の基本情報を定義する。

```yaml
review:
  id: "review-scr-002-recommendation-input-pr"
  title: "SCR-002 レコメンド条件入力画面 PRレビュー"
  summary: "SCR-002 レコメンド条件入力画面に関するPRを、Task Definitionと差分に基づいてAI Reviewする"
  type: "task_pr_review"
  status: "ready"
```

### 7.1 `review.id`

Review Definitionを識別するID。

| 項目 | 内容                                    |
| ---- | --------------------------------------- |
| 型   | string                                  |
| 必須 | yes                                     |
| 命名 | kebab-case推奨                          |
| 例   | `review-scr-002-recommendation-input-pr` |

---

### 7.2 `review.title`

レビュー名。

| 項目 | 内容                                |
| ---- | ----------------------------------- |
| 型   | string                              |
| 必須 | yes                                 |
| 例   | `SCR-002 レコメンド条件入力画面 PRレビュー` |

---

### 7.3 `review.summary`

レビュー概要。

| 項目 | 内容                                        |
| ---- | ------------------------------------------- |
| 型   | string                                      |
| 必須 | 推奨                                        |
| 用途 | PRコメント、Slack通知、レビューサマリに利用 |

---

### 7.4 `review.type`

レビュー種別。

| 許容値                  | 内容                                         |
| ----------------------- | -------------------------------------------- |
| `task_pr_review`        | 通常Task PRレビュー                          |
| `docs_review`           | docs中心のレビュー                           |
| `implementation_review` | 実装中心のレビュー                           |
| `test_review`           | test中心のレビュー                           |
| `contract_review`       | API contract / OpenAPI / Orval中心のレビュー |
| `security_review`       | security観点中心のレビュー                   |
| `review_fix_review`     | レビュー指摘対応後の再レビュー               |

---

### 7.5 `review.status`

Review Definition自体の状態。

| 許容値       | 内容     |
| ------------ | -------- |
| `draft`      | 作成中   |
| `ready`      | 実行可能 |
| `blocked`    | 前提不足 |
| `deprecated` | 廃止     |

---

## 8. `target`

レビュー対象を定義する。

```yaml
target:
  pr: "#123"
  issue: "#102"
  task_definition: "prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml"
  source_branch: "feature/issue-102-scr-002-recommendation-input"
  target_branch: "epic/recommendation-ui"
  parent_epic_issue: "#101"
  parent_epic_branch: "epic/recommendation-ui"
```

| 項目                 | 必須     | 内容                                          |
| -------------------- | -------- | --------------------------------------------- |
| `pr`                 | 条件付き | 対象PR番号。Command実行時引数で指定してもよい |
| `issue`              | 必須     | 対象Task Issue                                |
| `task_definition`    | 必須     | 基準となるTask Definition                     |
| `source_branch`      | 条件付き | PR source branch                              |
| `target_branch`      | 条件付き | PR target branch                              |
| `parent_epic_issue`  | 条件付き | 親Epic Issue                                  |
| `parent_epic_branch` | 条件付き | 親Epic Branch                                 |

Task PRの場合、`target_branch` は原則として `parent_epic_branch` と一致する。

---

## 9. `commands`

このReview Definitionが対応するCommandを定義する。

```yaml
commands:
  primary: "/review-pr"
  allowed:
    - "/review-pr"
    - "/summarize-work"
  next:
    approve_for_human_review: "Human Review"
    request_changes: "/fix-review-comments"
    needs_human_decision: "Human Decision"
    split_required: "/start-task"
    blocked: null
```

| 項目      | 必須 | 内容                     |
| --------- | ---- | ------------------------ |
| `primary` | 必須 | 主に実行するCommand      |
| `allowed` | 推奨 | 利用可能なCommand        |
| `next`    | 推奨 | レビュー結果別の次Action |

`primary` の許容値は原則として以下。

```yaml
"/review-pr"
```

---

## 10. `agent`

担当Agentを定義する。

```yaml
agent:
  primary: "reviewer-ai"
  support:
    - "support-ai"
  specialist:
    docs: "docs-reviewer-ai"
    test: "test-ai"
    contract: "contract-ai"
    security: null
  next:
    fixer: "fixer-ai"
    human: "human-reviewer"
```

| 項目         | 必須 | 内容              |
| ------------ | ---- | ----------------- |
| `primary`    | 必須 | 主担当Agent       |
| `support`    | 任意 | 補助Agent         |
| `specialist` | 推奨 | 専門レビューAgent |
| `next`       | 推奨 | 後続対応者        |

許容値例：

```yaml
reviewer-ai
docs-reviewer-ai
test-ai
contract-ai
fixer-ai
support-ai
```

---

## 11. `review_scope`

レビュー対象領域を定義する。

```yaml
review_scope:
  docs: true
  source: true
  tests: true
  api_contract: false
  db: false
  generated: false
  cicd: false
  security: true
  project_operation: true
```

| 項目                | 内容                                              |
| ------------------- | ------------------------------------------------- |
| `docs`              | docs変更を確認する                                |
| `source`            | source code変更を確認する                         |
| `tests`             | test変更・test結果を確認する                      |
| `api_contract`      | API仕様、OpenAPI、Orval、API client影響を確認する |
| `db`                | DB schema、migration、seed影響を確認する          |
| `generated`         | generated差分を確認する                           |
| `cicd`              | CI/CD設定・実行結果を確認する                     |
| `security`          | secret、認証認可、権限、ログ安全性を確認する      |
| `project_operation` | Issue、Branch、PR target、Status運用を確認する    |

`false` の領域でも、PR diff上に変更が含まれている場合は確認対象にする。  
特に API contract / DB / generated / security への影響は、scope外でも見逃してはならない。

---

## 12. `input`

レビュー時に参照する入力情報を定義する。

```yaml
input:
  task_definition:
    path: "prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml"
    required: true
  issue:
    number: "#102"
    required: true
  pr:
    number: "#123"
    required: true
  diff:
    required: true
    compare_with: "epic/recommendation-ui"
  docs:
    - path: "docs/05_実装設計/画面仕様書/SCR-002 レコメンド条件入力画面仕様書.md"
      required: true
      purpose: "成果物の内容確認"
  files:
    - path: "apps/web/src/app/recommendations/page.tsx"
      required: false
      purpose: "実装差分確認"
  test_results:
    required: true
    source: "pr_body"
  ci_results:
    required: false
    source: "github_actions"
  templates:
    review_outputs:
      pr_comment: "prompts/templates/review/ai-review-comment.md"
      slack: "prompts/templates/slack/ai-review-result.md"
    deliverables:
      - path: "prompts/templates/docs/screen-spec.md"
        required: true
        purpose: "Task成果物が指定テンプレートに沿って作成されているか確認するため"
        applies_to:
          - "docs/05_実装設計/画面仕様書/SCR-002 レコメンド条件入力画面仕様書.md"
```

### 12.1 `input.task_definition`

基準となるTask Definitionを指定する。

| 項目       | 必須 | 内容                 |
| ---------- | ---- | -------------------- |
| `path`     | yes  | Task Definition path |
| `required` | yes  | 必須か               |

---

### 12.2 `input.issue`

対象Issueを指定する。

| 項目       | 必須 | 内容      |
| ---------- | ---- | --------- |
| `number`   | yes  | Issue番号 |
| `required` | yes  | 必須か    |

---

### 12.3 `input.pr`

対象PRを指定する。

| 項目       | 必須     | 内容   |
| ---------- | -------- | ------ |
| `number`   | 条件付き | PR番号 |
| `required` | yes      | 必須か |

PR番号は、Command実行時に `#123` のように渡してもよい。

---

### 12.4 `input.diff`

PR diffの確認方法を指定する。

| 項目           | 必須     | 内容           |
| -------------- | -------- | -------------- |
| `required`     | yes      | diff確認必須か |
| `compare_with` | 条件付き | 比較対象branch |

Task PRでは、`compare_with` は原則として親Epic Branchとする。

---

### 12.5 `input.docs`

レビュー対象または参照対象docsを指定する。

| 項目       | 必須 | 内容      |
| ---------- | ---- | --------- |
| `path`     | yes  | docs path |
| `required` | yes  | 必須か    |
| `purpose`  | yes  | 参照目的  |

---

### 12.6 `input.files`

レビュー対象または参照対象source code / config / test fileを指定する。

---

### 12.7 `input.test_results`

テスト結果の参照元を指定する。

| `source`  | 内容         |
| --------- | ------------ |
| `pr_body` | PR本文       |
| `ci`      | CI結果       |
| `manual`  | 手動確認結果 |
| `mixed`   | 複数参照     |

---

### 12.8 `input.ci_results`

CI結果の参照元を指定する。

| `source`         | 内容           |
| ---------------- | -------------- |
| `github_actions` | GitHub Actions |
| `manual`         | 手動記載       |
| `not_required`   | 今回対象外     |

---

### 12.9 `input.templates`

レビュー時に参照するテンプレートを指定する。

`input.templates` は、以下の2種類に分けて扱う。

| 項目             | 内容                                                                 |
| ---------------- | -------------------------------------------------------------------- |
| `review_outputs` | AI Review結果を出力するためのテンプレート                            |
| `deliverables`   | Task成果物が指定テンプレートに沿っているか確認するためのテンプレート |

例：

````yaml
templates:
  review_outputs:
    pr_comment: "prompts/templates/review/ai-review-comment.md"
    slack: "prompts/templates/slack/ai-review-result.md"
  deliverables:
    - path: "prompts/templates/docs/screen-spec.md"
      required: true
      purpose: "Task成果物が指定テンプレートに沿って作成されているか確認するため"
      applies_to:
        - "docs/05_実装設計/画面仕様書/SCR-002 レコメンド条件入力画面仕様書.md"

---

## 13. `review_points`

レビュー観点を定義する。

```yaml
review_points:
  common:
    - "Task Definitionのscopeを満たしているか"
    - "out_of_scopeの変更が混在していないか"
    - "acceptance_criteriaを満たしているか"
  docs:
    - "正本docsと矛盾していないか"
    - "用語揺れがないか"
  source:
    - "既存アーキテクチャと整合しているか"
    - "責務分離が崩れていないか"
  tests:
    - "test_policyに従って必要なテストが実施されているか"
  api_contract:
    - "OpenAPI / Orval / API client影響がないか"
  db:
    - "DB schema / migration影響がないか"
  generated:
    - "generatedファイルを手動編集していないか"
  cicd:
    - "CI結果が確認されているか"
  security:
    - "secretや.env実値が含まれていないか"
  branch:
    - "Task Branchからdevelopへ直接PRしていないか"
  project:
    - "Status更新意図が明確か"
````

### 13.1 `common`

すべてのPR Reviewで確認する共通観点。

推奨項目：

- Task Definitionのscopeを満たしているか
- out_of_scopeの変更が混在していないか
- acceptance_criteriaを満たしているか
- PR本文に変更内容、テスト結果、未実施事項が記載されているか
- Human Review観点が明記されているか

---

### 13.2 `docs`

docs変更がある場合の確認観点。

推奨項目：

- 正本docsと矛盾していないか
- 用語揺れがないか
- 古い方針が残っていないか
- Markdown表やMermaidが崩れていないか
- Notion転記を想定した体裁になっているか
- Task Definitionで指定された文書テンプレートに沿って作成されているか
- `output.docs[].template` と成果物docsの章構成が対応しているか

---

### 13.3 `source`

source code変更がある場合の確認観点。

推奨項目：

- 既存アーキテクチャと整合しているか
- 責務分離が崩れていないか
- 命名が適切か
- 型安全性に問題がないか
- エラーハンドリングが適切か
- 過剰実装がないか

---

### 13.4 `tests`

test変更またはtest結果を確認する観点。

推奨項目：

- test_policyに従っているか
- 必要なテストが実施されているか
- 未実施テストに理由と残リスクがあるか
- 実施していないテストを実施済みとして扱っていないか
- fixture / mockの変更が妥当か

---

### 13.5 `api_contract`

API contract影響を確認する観点。

推奨項目：

- API仕様に影響がないか
- OpenAPIに影響がないか
- Orval設定や生成物に影響がないか
- provider / consumer の両方に影響しないか
- Contract Task化すべき変更が混在していないか

---

### 13.6 `db`

DB影響を確認する観点。

推奨項目：

- DB schema変更がないか
- migration変更がないか
- seed変更がないか
- ER / テーブル設計方針書との整合性があるか
- 専用Task化すべき変更が混在していないか

---

### 13.7 `generated`

generated差分を確認する観点。

推奨項目：

- generatedファイルを手動編集していないか
- 生成元と差分が対応しているか
- 再生成手順が明確か
- generated差分がTask scope内か
- Contract Task化が必要でないか

---

### 13.8 `security`

security観点。

推奨項目：

- secretを含んでいないか
- `.env` 実値を含んでいないか
- DB接続文字列の実値を含んでいないか
- API keyを含んでいないか
- ログに機密情報を出していないか
- 認証認可への影響が明確か

---

### 13.9 `branch`

Branch / PR運用観点。

推奨項目：

- Source Branchが正しいか
- Target Branchが正しいか
- Task Branchからdevelopへ直接PRしていないか
- Parent Epic Branchの最新状態を取り込んでいるか
- Task PRで `Related to #<Task Issue番号>` が使われているか
- Task PRで `Closes #<Task Issue番号>` を使っていないか

---

### 13.10 `project`

GitHub Projects運用観点。

推奨項目：

- 現在StatusがAI Reviewであるか
- レビュー結果に応じたStatus更新意図が明確か
- Issue close / DoneをPR本文の自動closeキーワードに依存していないか

---

## 14. `acceptance_check`

Task Definitionの完了条件をどのように確認するかを定義する。

```yaml
acceptance_check:
  use_task_acceptance_criteria: true
  additional_criteria:
    - "PR本文に実施済みテストと未実施テストが明記されている"
    - "Human Reviewで確認すべき事項が明記されている"
    - "PR本文に実施済みテストと未実施テストが明記されている"
    - "Human Reviewで確認すべき事項が明記されている"
    - "Task Definitionで文書テンプレートが指定されている場合、成果物がそのテンプレートに沿っている"
```

| 項目                           | 必須 | 内容                                             |
| ------------------------------ | ---- | ------------------------------------------------ |
| `use_task_acceptance_criteria` | 必須 | Task Definitionのacceptance_criteriaを利用するか |
| `additional_criteria`          | 推奨 | Review固有の追加完了条件                         |

Review Definitionは、Task Definitionの完了条件を上書きしない。  
追加観点として扱う。

---

## 15. `result_policy`

レビュー結果分類ごとの判定基準を定義する。

```yaml
result_policy:
  approve_for_human_review:
    conditions:
      - "acceptance_criteriaを満たしている"
      - "修正必須事項がない"
      - "Human Reviewで確認すべき事項が整理されている"
  request_changes:
    conditions:
      - "同一Branchで修正可能な不備がある"
      - "テスト不足がある"
      - "PR本文の必要情報が不足している"
  needs_human_decision:
    conditions:
      - "仕様判断が必要"
      - "scope外変更の扱い判断が必要"
  split_required:
    conditions:
      - "別Issue化すべき変更が混在している"
      - "Contract Task化すべき変更がある"
  blocked:
    conditions:
      - "PR diffを確認できない"
      - "Task Definitionが存在しない"
      - "IssueとPRの対応が不明"
```

### 15.1 `approve_for_human_review`

Human Reviewへ進めてよい状態。

主な条件：

- PRが対象Issue / Task Definitionと対応している
- scope内の変更である
- acceptance_criteriaを満たしている
- 必要なテスト・検証結果が記載されている
- 修正必須事項がない
- Human Review観点が明確である

---

### 15.2 `request_changes`

同一Branchで修正が必要な状態。

主な条件：

- acceptance_criteriaを一部満たしていない
- 同一Branchで直せる不備がある
- テスト不足がある
- PR本文に必要情報が不足している
- docs / code / testの軽微〜中程度の修正が必要

---

### 15.3 `needs_human_decision`

人間判断が必要な状態。

主な条件：

- 仕様判断が必要
- scope外変更を含めるべきか判断が必要
- テスト未実施を許容してよいか判断が必要
- security上の許容判断が必要
- AIレビュー観点と人間指示が衝突している

---

### 15.4 `split_required`

別Issue化が必要な状態。

主な条件：

- 現在Taskのscope外変更が混在している
- 前段成果物の大きな修正が必要
- API contract / DB / generated など横断影響がある
- Contract Taskまたは専用Task化すべき変更がある

---

### 15.5 `blocked`

前提不足でレビュー不能な状態。

主な条件：

- PRが存在しない
- diffを確認できない
- Task Definitionが存在しない
- IssueとPRの対応が不明
- PR targetが不明
- `input.docs` / `output.docs` が確認できない
- secret混入など重大懸念がある

---

## 16. `status_policy`

レビュー結果ごとのStatus更新意図を定義する。

```yaml
status_policy:
  current_status: "AI Review"
  on_approve: "Human Review"
  on_request_changes: "In Progress"
  on_needs_human_decision: "Human Review"
  on_split_required: "In Progress"
  on_blocked: "In Progress"
```

| 項目                      | 内容                                 |
| ------------------------- | ------------------------------------ |
| `current_status`          | レビュー実行時の想定Status           |
| `on_approve`              | approve_for_human_review時の次Status |
| `on_request_changes`      | request_changes時の次Status          |
| `on_needs_human_decision` | needs_human_decision時の次Status     |
| `on_split_required`       | split_required時の次Status           |
| `on_blocked`              | blocked時の次Status                  |

Status更新は、Commandが直接確定するのではなく、GitHub Actions で実施する。実装の正本は [PRレビュー完了時Status更新ワークフロー仕様書](../../../docs/06_実装設計/github_actions/PRレビュー完了時Status更新ワークフロー仕様書.md) とする。  
Review Definitionでは、更新意図のみを定義する。`needs_human_decision` の自動化既定は `Human Review`（PR コメントで `次Status: In Progress` を明示した場合のみ In Progress）。

---

## 17. `outputs`

レビュー結果の出力先・テンプレートを定義する。

```yaml
outputs:
  pr_comment_template: "prompts/templates/review/ai-review-comment.md"
  slack_template: "prompts/templates/slack/ai-review-result.md"
  update_pr_body: false
  create_follow_up_issue: false
  ai_logs:
    required: false
    path: null
```

| 項目                     | 必須 | 内容                          |
| ------------------------ | ---- | ----------------------------- |
| `pr_comment_template`    | 必須 | AI Reviewコメントテンプレート |
| `slack_template`         | 任意 | Slack通知テンプレート         |
| `update_pr_body`         | 推奨 | PR本文更新要否                |
| `create_follow_up_issue` | 推奨 | follow-up Issue作成要否       |
| `ai_logs`                | 推奨 | ai-logs記録要否               |

通常のAI Review結果はPRコメントを正本とする。  
Slack通知は正本ではない。

---

## 18. `operation_logging`

AIログ運用を定義する。

```yaml
operation_logging:
  level: "standard"
  ai_logs:
    intake: false
    incidents: false
    cross_cutting: false
    experiments: false
  reason: "通常PRレビューのため、レビュー結果はPRコメントを正本とする"
```

### 18.1 `level`

| 値         | 内容   |
| ---------- | ------ |
| `minimal`  | 最小限 |
| `standard` | 標準   |
| `detailed` | 詳細   |

原則は `standard` とする。

### 18.2 `ai_logs`

| 項目            | 内容                                     |
| --------------- | ---------------------------------------- |
| `intake`        | Issue化前フィードバック                  |
| `incidents`     | レビュー不可・例外                       |
| `cross_cutting` | OpenAPI / Orval / generated 等の横断影響 |
| `experiments`   | AI運用検証・比較実験                     |

通常レビュー結果をすべて `ai-logs/` に保存しない。

---

## 19. `human_decision_points`

人間判断が必要な論点を記載する。

```yaml
human_decision_points:
  - "未実施テストを許容してHuman Reviewへ進めてよいか"
  - "scope外の軽微なdocs補足を同一PRに含めてよいか"
```

| 項目     | 内容                   |
| -------- | ---------------------- |
| 型       | list[string]           |
| 必須     | yes                    |
| ない場合 | 空配列 `[]` を明記する |

AIが独断で判断してはいけない論点を明示する。

---

## 19.5 `branch`（任意）

Issue 作成・`/start-task` 連携時のみ記載する。`/review-pr` のみの Review Definition では省略可。

```yaml
branch:
  no_branch: true
  name: null
  base: null
  target: null
```

| 項目        | 必須     | 内容                                                        |
| ----------- | -------- | ----------------------------------------------------------- |
| `no_branch` | 条件付き | `branch` 記載時は必須。`work_mode` 標準値と一致必須（§16.2） |

`review_points.branch` は PR の Branch 運用確認観点であり、本ブロックとは別物とする。

---

## 20. `stop_conditions`

レビュー停止条件を記載する。

```yaml
stop_conditions:
  - "PRが存在しない場合"
  - "Task Definitionが存在しない場合"
  - "IssueとPRの対応が不明な場合"
  - "diffを確認できない場合"
  - "secretや.env実値の混入が疑われる場合"
```

| 項目 | 内容         |
| ---- | ------------ |
| 型   | list[string] |
| 必須 | yes          |

---

## 21. `notes`

補足事項を記載する。

```yaml
notes:
  - "レビューCommand内では修正作業を行わない"
```

| 項目 | 内容         |
| ---- | ------------ |
| 型   | list[string] |
| 必須 | no           |

---

## 22. 標準テンプレート

新しい Review Definition は、原則として以下を雛形にする。

```yaml
schema_version: "1.0"
definition_type: "review"

review:
  id: ""
  title: ""
  summary: ""
  type: "task_pr_review"
  status: "draft"

work_mode: "ai-agent"

target:
  pr: null
  issue: null
  task_definition: ""
  source_branch: null
  target_branch: null
  parent_epic_issue: null
  parent_epic_branch: null

commands:
  primary: "/review-pr"
  allowed:
    - "/review-pr"
    - "/summarize-work"
  next:
    approve_for_human_review: "Human Review"
    request_changes: "/fix-review-comments"
    needs_human_decision: "Human Decision"
    split_required: "/start-task"
    blocked: null

agent:
  primary: "reviewer-ai"
  support:
    - "support-ai"
  specialist:
    docs: null
    test: null
    contract: null
    security: null
  next:
    fixer: "fixer-ai"
    human: "human-reviewer"

review_scope:
  docs: true
  source: true
  tests: true
  api_contract: true
  db: true
  generated: true
  cicd: true
  security: true
  project_operation: true

input:
  task_definition:
    path: ""
    required: true
  issue:
    number: null
    required: true
  pr:
    number: null
    required: true
  diff:
    required: true
    compare_with: null
  docs: []
  files: []
  test_results:
    required: true
    source: "pr_body"
  ci_results:
    required: false
    source: "github_actions"
  templates:
    pr_comment: "prompts/templates/review/ai-review-comment.md"
    slack: null

review_points:
  common:
    - "Task Definitionのscopeを満たしているか"
    - "out_of_scopeの変更が混在していないか"
    - "acceptance_criteriaを満たしているか"
    - "PR本文に変更内容、テスト結果、未実施事項が記載されているか"
    - "Human Review観点が明記されているか"
  docs: []
  source: []
  tests: []
  api_contract: []
  db: []
  generated: []
  cicd: []
  security: []
  branch:
    - "Task Branchからdevelopへ直接PRしていないか"
    - "Task PRでRelated to #<Task Issue番号>が使われているか"
    - "Task PRでCloses #<Task Issue番号>を使っていないか"
  project:
    - "レビュー結果に応じたStatus更新意図が明確か"

acceptance_check:
  use_task_acceptance_criteria: true
  additional_criteria: []

result_policy:
  approve_for_human_review:
    conditions:
      - "acceptance_criteriaを満たしている"
      - "修正必須事項がない"
      - "Human Reviewで確認すべき事項が整理されている"
  request_changes:
    conditions:
      - "同一Branchで修正可能な不備がある"
      - "テスト不足がある"
      - "PR本文の必要情報が不足している"
  needs_human_decision:
    conditions:
      - "仕様判断が必要"
      - "scope外変更の扱い判断が必要"
  split_required:
    conditions:
      - "別Issue化すべき変更が混在している"
      - "Contract Task化すべき変更がある"
  blocked:
    conditions:
      - "PR diffを確認できない"
      - "Task Definitionが存在しない"
      - "IssueとPRの対応が不明"

status_policy:
  current_status: "AI Review"
  on_approve: "Human Review"
  on_request_changes: "In Progress"
  on_needs_human_decision: "Human Review"
  on_split_required: "In Progress"
  on_blocked: "In Progress"

outputs:
  pr_comment_template: "prompts/templates/review/ai-review-comment.md"
  slack_template: null
  update_pr_body: false
  create_follow_up_issue: false
  ai_logs:
    required: false
    path: null

operation_logging:
  level: "standard"
  ai_logs:
    intake: false
    incidents: false
    cross_cutting: false
    experiments: false
  reason: "通常PRレビューのため、レビュー結果はPRコメントを正本とする"

human_decision_points: []

stop_conditions:
  - "PRが存在しない場合"
  - "Task Definitionが存在しない場合"
  - "IssueとPRの対応が不明な場合"
  - "diffを確認できない場合"
  - "secretや.env実値の混入が疑われる場合"
  - "generatedファイルの手動編集が疑われる場合"
  - "Human Reviewを省略する前提になっている場合"
  - "AIがmerge判断を行う必要がある場合"

notes:
  - "レビューCommand内では修正作業を行わない"
```

---

## 23. 記入例

```yaml
schema_version: "1.0"
definition_type: "review"

review:
  id: "review-scr-002-recommendation-input-pr"
  title: "SCR-002 レコメンド条件入力画面 PRレビュー"
  summary: "SCR-002 レコメンド条件入力画面仕様書作成TaskのPRをAI Reviewする"
  type: "task_pr_review"
  status: "ready"

work_mode: "ai-agent"

branch:
  no_branch: true
  name: null
  base: null
  target: null

target:
  pr: null
  issue: "#102"
  task_definition: "prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml"
  source_branch: "docs/issue-102-scr-002-recommendation-input-screen-spec"
  target_branch: "epic/recommendation-ui"
  parent_epic_issue: "#101"
  parent_epic_branch: "epic/recommendation-ui"

commands:
  primary: "/review-pr"
  allowed:
    - "/review-pr"
    - "/summarize-work"
  next:
    approve_for_human_review: "Human Review"
    request_changes: "/fix-review-comments"
    needs_human_decision: "Human Decision"
    split_required: "/start-task"
    blocked: null

agent:
  primary: "reviewer-ai"
  support:
    - "support-ai"
  specialist:
    docs: "docs-reviewer-ai"
    test: null
    contract: null
    security: null
  next:
    fixer: "fixer-ai"
    human: "human-reviewer"

review_scope:
  docs: true
  source: false
  tests: false
  api_contract: true
  db: true
  generated: true
  cicd: false
  security: true
  project_operation: true

input:
  task_definition:
    path: "prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml"
    required: true
  issue:
    number: "#102"
    required: true
  pr:
    number: null
    required: true
  diff:
    required: true
    compare_with: "epic/recommendation-ui"
  docs:
    - path: "docs/05_実装設計/画面仕様書/SCR-002 レコメンド条件入力画面仕様書.md"
      required: true
      purpose: "作成成果物の内容確認"
  files: []
  test_results:
    required: true
    source: "pr_body"
  ci_results:
    required: false
    source: "not_required"
  templates:
    pr_comment: "prompts/templates/review/ai-review-comment.md"
    slack: "prompts/templates/slack/ai-review-result.md"

review_points:
  common:
    - "Task Definitionのscopeを満たしているか"
    - "out_of_scopeの変更が混在していないか"
    - "acceptance_criteriaを満たしているか"
    - "PR本文に変更内容、検証結果、未実施事項が記載されているか"
    - "Human Review観点が明記されているか"
  docs:
    - "画面仕様書が指定パスに作成されているか"
    - "表示項目、表示条件、空状態、エラー状態が記載されているか"
    - "関連APIとの接続点が記載されているか"
    - "用語揺れがないか"
  source: []
  tests:
    - "docs作成Taskとして必要なmanual checkが記載されているか"
  api_contract:
    - "OpenAPI変更が混在していないか"
  db:
    - "DB schema変更が混在していないか"
  generated:
    - "generatedファイルを手動編集していないか"
  cicd: []
  security:
    - "secretや.env実値が含まれていないか"
  branch:
    - "Task Branchからdevelopへ直接PRしていないか"
    - "Task PRでRelated to #102が使われているか"
    - "Task PRでCloses #102を使っていないか"
  project:
    - "Status更新意図がAI ReviewからHuman ReviewまたはIn Progressとして整理されているか"

acceptance_check:
  use_task_acceptance_criteria: true
  additional_criteria:
    - "PR本文に未実施テストの理由が記載されている"
    - "Human Reviewで確認してほしい事項が明記されている"

result_policy:
  approve_for_human_review:
    conditions:
      - "acceptance_criteriaを満たしている"
      - "修正必須事項がない"
      - "Human Reviewで確認すべき事項が整理されている"
  request_changes:
    conditions:
      - "同一Branchで修正可能なdocs不備がある"
      - "PR本文に必要情報が不足している"
  needs_human_decision:
    conditions:
      - "画面仕様のMVP範囲判断が必要"
  split_required:
    conditions:
      - "OpenAPI変更やDB schema変更が混在している"
  blocked:
    conditions:
      - "PR diffを確認できない"
      - "Task Definitionが存在しない"
      - "IssueとPRの対応が不明"

status_policy:
  current_status: "AI Review"
  on_approve: "Human Review"
  on_request_changes: "In Progress"
  on_needs_human_decision: "Human Review"
  on_split_required: "In Progress"
  on_blocked: "In Progress"

outputs:
  pr_comment_template: "prompts/templates/review/ai-review-comment.md"
  slack_template: "prompts/templates/slack/ai-review-result.md"
  update_pr_body: false
  create_follow_up_issue: false
  ai_logs:
    required: false
    path: null

operation_logging:
  level: "standard"
  ai_logs:
    intake: false
    incidents: false
    cross_cutting: false
    experiments: false
  reason: "通常PRレビューのため、レビュー結果はPRコメントを正本とする"

human_decision_points:
  - "画面仕様がMVP範囲として妥当か"

stop_conditions:
  - "PRが存在しない場合"
  - "Task Definitionが存在しない場合"
  - "IssueとPRの対応が不明な場合"
  - "diffを確認できない場合"
  - "OpenAPI変更が混在している場合"
  - "DB schema変更が混在している場合"
  - "generatedファイルの手動編集が疑われる場合"
  - "secretや.env実値の混入が疑われる場合"
  - "Human Reviewを省略する前提になっている場合"
  - "AIがmerge判断を行う必要がある場合"

notes:
  - "docs作成Taskのため、source code変更は原則scope外とする"
```

---

## 24. バリデーション観点

Review Definition作成・修正時は、以下を確認する。

### 24.1 必須項目

- `schema_version` がある
- `definition_type: review` である
- `work_mode` がある（`human-led` または `ai-agent`）
- `branch` を記載している場合、`work_mode` と `branch.no_branch` が §16.2 の標準値と一致している（例外時は `human_decision_points` に理由必須）
- `review.id` がある
- `review.title` がある
- `review.type` がある
- `target.issue` がある
- `target.task_definition` がある
- `commands.primary: /review-pr` である
- `agent.primary` がある
- `review_scope` がある
- `input.task_definition` がある
- `input.pr` がある
- `input.diff` がある
- `review_points.common` がある
- `acceptance_check` がある
- `result_policy` がある
- `status_policy` がある
- `outputs.pr_comment_template` がある
- `operation_logging.level` がある
- `stop_conditions` がある

---

### 24.2 target確認

- 対象Issueが明確である
- 対象PRが明確である、またはCommand実行時に指定する前提である
- Task Definition pathが明確である
- Task PRの場合、target branchが親Epic Branchである
- Task Branchからdevelopへ直接PRする前提になっていない

---

### 24.3 review_scope確認

- docs / source / tests / api_contract / db / generated / cicd / security / project_operation の確認要否が明確である
- `false` の領域でも、diffに含まれる場合は確認対象とする方針になっている
- API contract / DB / generated / security 影響を見逃さない構造になっている

---

### 24.4 review_points確認

- common観点が空でない
- Task Definitionのscope / out_of_scopeを確認する観点がある
- acceptance_criteriaを確認する観点がある
- PR本文・テスト結果・未実施事項を確認する観点がある
- Branch / PR target / Related to / Closes の確認観点がある
- generated手動編集を検知する観点がある
- secret / `.env` 実値混入を検知する観点がある
- Task Definitionで `output.docs[].template` が指定されている場合、テンプレート準拠を確認する観点がある
- Review Definitionの `input.templates.deliverables` が、Task Definitionの `output.docs[].template` と対応している
- 成果物docsが指定テンプレートの章構成に沿っているか確認する観点がある

---

### 24.5 result_policy確認

- `approve_for_human_review` の条件が明確である
- `request_changes` の条件が明確である
- `needs_human_decision` の条件が明確である
- `split_required` の条件が明確である
- `blocked` の条件が明確である
- AIがmerge可否を判断する構造になっていない

---

### 24.6 status_policy確認

- 初期StatusがAI Reviewである
- `approve_for_human_review` 時の次StatusがHuman Reviewである
- `request_changes` 時の次StatusがIn Progressである
- Status更新をCommandが直接確定する前提になっていない
- Status更新意図として扱う方針になっている

---

### 24.7 security確認

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

---

## 25. 禁止事項

以下は禁止する。

- Review Definitionで作業実施内容を定義すること
- Review DefinitionでTask Definitionのscopeを上書きすること
- Review Command内で修正作業を行う前提にすること
- Human Reviewを省略する前提にすること
- AIがPRをmerge判断する前提にすること
- Task Branchからdevelopへ直接PRする前提にすること
- Task PRで `Closes #<Task Issue番号>` を使う前提にすること
- generatedファイルの手動編集を許容すること
- secretや`.env` 実値を記載すること
- 実施していないテストを実施済みとして扱うこと
- Slack通知だけでレビュー記録を完結させること
- 通常レビュー結果をすべて `ai-logs/` に保存する前提にすること
- Task Definitionで指定された文書テンプレートへの準拠確認を省略すること
- `output.docs[].template` が指定されているにもかかわらず、Review Definition側でテンプレート確認観点を持たないこと
- 指定テンプレートが存在しない状態で、成果物レビューを完了扱いにすること

---

## 26. 一言まとめ

Review Definition は、PRをどの観点でAI Reviewするかを定義するレビュー条件の正本である。

Task Definition が「何を作業すべきか」を定義するのに対し、Review Definition は「何を確認し、どの結果分類にするか」を定義する。

AI Agentは、Review Definitionの `review_scope`、`review_points`、`acceptance_check`、`result_policy`、`status_policy`、`human_decision_points`、`stop_conditions` に従ってPRをレビューし、修正が必要な場合は `/fix-review-comments`、問題がなければ Human Review へ引き継ぐ。
