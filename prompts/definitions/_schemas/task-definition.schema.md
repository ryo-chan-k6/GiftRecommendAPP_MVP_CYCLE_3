# Task Definition Schema

## 1. 目的

本ドキュメントは、`prompts/definitions/tasks/` 配下に配置する Task Definition の標準構造を定義する。

Task Definition は、AI Agent に対して以下を明確に伝えるための作業定義である。

- 何を作業対象にするか
- 何を入力資料として参照するか
- 何を作成・修正するか
- どこまでを scope とするか
- どこからを out_of_scope とするか
- 何をもって完了とするか
- どのテスト・検証を行うか
- どの条件で人間判断へ回すか

AI Agent は、Task Definition に従って作業し、Definition に書かれていない scope 外作業を勝手に実施してはならない。

**標準構造の正本**は `docs/00_共通/AIエージェント運用/Task Definition設計書.md` **§9.1（実運用YAML）** とする。本Schemaは実運用形式の検証・補足定義である。記入例は `_examples/task-definition.example.yaml`、実運用例は `tasks/api-int-002-reco-recommendation-run/api-spec.yaml` を参照する。

---

## 2. 対象ファイル

本Schemaは、以下に配置するTask Definitionを対象とする。

```text
prompts/definitions/tasks/<workstream_key>/<task-role>.yaml
```

例：

```text
prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml
prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml
prompts/definitions/tasks/scr-002-recommendation-input/test.yaml
prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml
```

---

## 3. 対応Command

Task Definition は、主に以下のCommandで利用する。

| Command                | 利用目的                                     |
| ---------------------- | -------------------------------------------- |
| `/start-task`          | Issue作成、Project同期、Branch作成、作業開始 |
| `/work-issue`          | 既存Issue / Branch上での実作業               |
| `/create-pr`           | 作業結果をPR化                               |
| `/fix-review-comments` | レビュー指摘対応                             |
| `/summarize-work`      | 作業結果・判断依頼・完了報告の要約           |

`/review-pr` は原則として `prompts/definitions/reviews/` 配下の Review Definition を利用する。  
ただし、レビュー時にも Task Definition の `scope`、`acceptance_criteria`、`test_policy` は参照される。

---

## 4. 基本形式

Task Definition は YAML 形式で記述する。構造の正本は Task Definition設計書 **§9.1 実運用YAML**・**§12 `definition_type`** とする。

```yaml
schema_version: "1.0"
definition_type: "task"

task:
  id: ""
  title: ""
  summary: ""

work_mode: "ai-agent"

parent:
  epic_issue: null
  epic_issue_number: null
  epic_branch: null
  related_issues: []
  related_prs: []

commands:
  primary: ""
  allowed: []
  next:
    success: null
    review_fix: null
    blocked: null

agent:
  primary: ""
  support: []
  review: []

background: ""

objective: ""

scope: []

out_of_scope: []

input:
  docs: []
  templates: []
  files: []
  issues: []
  prs: []

output:
  docs: []
  files: []
  tests: []
  generated:
    expected: false
    paths: []
    handling: "none"
  logs:
    ai_logs_required: false
    path: null

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
  contract_impact: false
  db_impact: false

contract_gate:
  required: false
  gate_id: null
  prerequisite_contract_tasks: []
  verify_at:
    - "/start-task"
    - "/work-issue"
  checks: []
  blocked_message: null

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
    docs: false
    test: false
    contract: false
    security: false

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

## 5. 必須項目一覧

Task Definition設計書 **§10 必須項目** に準拠する。

| 項目                           | 必須           | 内容                              |
| ------------------------------ | -------------- | --------------------------------- |
| `schema_version`               | 必須           | Schema version                    |
| `definition_type`              | 必須           | `task` 固定（設計書 §12）        |
| `task.id`                      | 必須           | Task識別子                        |
| `task.title`                   | 必須           | Task名                            |
| `work_mode`                    | 必須           | `human-led` または `ai-agent`（§17.1・§17.2） |
| `commands.primary`             | 必須           | 主に実行するCommand               |
| `agent.primary`                | 必須           | 主担当Agent                       |
| `background`                   | 必須           | 背景                              |
| `objective`                    | 必須           | 目的                              |
| `scope`                        | 必須           | 今回実施すること                  |
| `out_of_scope`                 | 必須           | 今回実施しないこと                |
| `input.docs`                   | 必須           | 参照する正本docs                  |
| `input.templates`              | 必要時必須     | 出力docsの生成に使うテンプレート  |
| `output.docs`                  | docs作成時必須 | 作成・更新するdocs                |
| `output.docs[].template`       | docs作成時必須 | 使用テンプレート                  |
| `deliverables`                 | 必須           | 成果物                            |
| `acceptance_criteria`          | 必須           | 完了条件                          |
| `branch`                       | 必須           | Branch方針                        |
| `project.project_name`         | 必須           | Project名（§9.1 実運用YAML）          |
| `project.fields.phase`         | 必須           | 作業工程（Project同期項目）       |
| `project.fields.status`        | 必須           | 作業遷移状態（Project同期項目）   |
| `project.fields.priority`      | 必須           | 作業優先度（Project同期項目）     |
| `project.fields.planned_start` | 必須           | 作業開始予定日（Project同期項目） |
| `project.fields.due_date`      | 必須           | 作業完了予定日（Project同期項目） |
| `issue.unit`                   | 必須           | 作業管理分類（issue同期項目）     |
| `issue.type`                   | 必須           | 作業種別（issue同期項目）         |
| `issue.area`                   | 必須           | 作業対象領域（issue同期項目）     |
| `parent.epic_issue_number`     | 識別子付きTaskでは必須 | 親 Epic Issue 番号。識別子 prefix が `task.title` と一致すること（Task Definition設計書 §15.0） |
| `dependencies`                 | 必須           | 依存関係                          |
| `dependencies.epics`           | 識別子付きTaskでは必須 | 依存 Epic Issue 番号配列（成果物化方針書 §3.5.3） |
| `parallel_control`             | 必須           | 並列作業制御                      |
| `parallel_control.exclusive_files` | 識別子付きTaskでは推奨 | 親 Epic の `epic_scope.allowed_paths` 内に収まること |
| `contract_gate`                | 条件付き       | Implementation Task で契約前提が必要な場合（§23.5） |
| `test_policy`                  | 必須           | テスト・検証方針                  |
| `review.human_review_required` | 必須           | Human Review要否                  |
| `review.ai_review_required`    | 必須           | AI Review要否                     |
| `operation_logging.level`      | 必須           | AIログ運用レベル                  |
| `human_decision_points`        | 必須           | 人間判断事項                      |
| `stop_conditions`              | 必須           | 停止条件                          |


---

## 6. 項目定義

### 6.1 `schema_version`

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

### 6.2 `definition_type`

Definition種別を記載する。正本は Task Definition設計書 **§12 `definition_type`**。

Task Definitionでは `task` 固定とする。

```yaml
definition_type: "task"
```

| 項目   | 内容   |
| ------ | ------ |
| 型     | string |
| 必須   | yes    |
| 許容値 | `task` |

---

## 7. `task`

Task自体の基本情報を定義する。

```yaml
task:
  id: "task-scr-002-recommendation-input-screen-spec"
  title: "SCR-002 レコメンド条件入力画面 設計書作成"
  summary: "レコメンド結果の商品一覧表示に関する画面仕様を作成する"
```

### 7.1 `task.id`

Taskを識別するID。

| 項目 | 内容                                      |
| ---- | ----------------------------------------- |
| 型   | string                                    |
| 必須 | yes                                       |
| 命名 | kebab-case推奨                            |
| 例   | `task-scr-002-recommendation-input-screen-spec` |

---

### 7.2 `task.title`

Task名。

| 項目 | 内容                                |
| ---- | ----------------------------------- |
| 型   | string                              |
| 必須 | yes                                 |
| 例   | `SCR-002 レコメンド条件入力画面 設計書作成` |

---

### 7.3 `task.summary`

Task概要。

| 項目 | 内容                                     |
| ---- | ---------------------------------------- |
| 型   | string                                   |
| 必須 | 推奨                                     |
| 用途 | Issue本文・Slack通知・PR本文の概要に利用 |

§9.1 実運用YAMLでは `task.id` / `task.title` / `task.summary` のみ。工程・種別・優先度は `project.fields` / `issue` で同期する。`work_mode` はトップレベルに記載する。

---

## 7.4 `work_mode`

人主導 / AI主導の判定キー。正本は Task Definition設計書 **§17.1**・**§17.2**。

```yaml
work_mode: "ai-agent"
```

| 項目 | 内容 |
| ---- | ---- |
| 型 | string |
| 必須 | yes |
| 許容値 | `human-led`, `ai-agent` |

| `work_mode` | `branch.no_branch` 標準値 | 説明 |
| ----------- | ------------------------: | ---- |
| `human-led` | `true` | 未来着手 Issue。着手まで Branch 作成を遅延 |
| `ai-agent` | `false` | Issue 作成後に即時作業へ進む |

`branch.no_branch` は上記標準値と **一致必須** とする。意図的にずらす場合は `human_decision_points` に理由を明記する。

`/start-task` および AI Review では、`work_mode` と `branch.no_branch` の整合を確認する。

---

### 7.5 `task.type`（§9.0旧形式・任意・非推奨）

作業種別。

| 許容値           | 内容             |
| ---------------- | ---------------- |
| `docs`           | docs作成・修正   |
| `implementation` | source code実装  |
| `test`           | test追加・修正   |
| `fix`            | 不具合修正       |
| `review_fix`     | レビュー指摘対応 |
| `refactor`       | リファクタリング |
| `config`         | 設定ファイル修正 |
| `ci`             | CI/CD修正        |
| `chore`          | 雑務・運用補助   |

API contract / OpenAPI / Orval / generated への横断影響が主目的の場合は、通常Taskではなく `cross-cutting` 配下の Contract Definition を使用する。

---

### 7.6 `task.phase`（§9.0旧形式・任意・非推奨）

作業工程。

例：

```yaml
phase: "06_実装設計"
```

| 許容値例                | 内容               |
| ----------------------- | ------------------ |
| `concept-design`        | 概念設計           |
| `architecture-design`   | アーキテクチャ設計 |
| `logical-design`        | 論理設計           |
| `cross-cutting-design`  | 横断設計           |
| `implementation-design` | 実装設計           |
| `development`           | 開発               |
| `testing`               | 検証               |
| `release`               | リリース           |
| `operation`             | 運用・改善         |

---

### 7.6 `task.priority`（§6非標準・任意）

優先度。

| 許容値   | 内容     |
| -------- | -------- |
| `high`   | 優先度高 |
| `medium` | 通常     |
| `low`    | 優先度低 |

---

### 7.7 `task.status`（§6非標準・任意）

Definition自体の状態。

| 許容値       | 内容     |
| ------------ | -------- |
| `draft`      | 作成中   |
| `ready`      | 実行可能 |
| `blocked`    | 前提不足 |
| `deprecated` | 廃止     |

---

## 8. `parent`

親Epicや関連Issue / PRを定義する。

```yaml
parent:
  epic_issue: "[Epic]API-PUB-002:レコメンド実行"
  epic_issue_number: "#300"
  epic_branch: "feature/epic-300-api-pub-002-recommendation-run"
  related_issues:
    - "#102"
  related_prs:
    - "#201"
```

| 項目                 | 必須     | 内容                                                         |
| -------------------- | -------- | ------------------------------------------------------------ |
| `epic_issue`         | 条件付き | 親Epic Issue タイトル（Issue本文・検索用）                   |
| `epic_issue_number`  | 推奨     | 親Epic Issue 番号の**参照配置値**（例: `#101`）。`/start-task` §5.1 で GitHub 実在確認。実番号確定後に Definition を更新する |
| `epic_branch`        | 条件付き | 親Epic Branch                                                |
| `related_issues`     | 任意     | 関連Issue                                                    |
| `related_prs`        | 任意     | 関連PR                                                       |

**実在確認の報告**: 配置値の有無と GitHub 上の存在は別。結果は `存在` / `未検出` / `未確認`（Task Definition設計書 §14.1、`.cursor/commands/start-task.md` §5.1）。未検出時は `/start-epic` で親 Epic を新規作成するか、`parent` を実番号へ更新する。

任意で `dependencies.issues` に親Epic番号を含め `blocking: true` とした場合、親Epic未作成時は `/start-task` で Branch 作成前に停止できる（必須ではない）。

Task PRは原則として親Epic Branch向けに作成する。  
Task Branchから `develop` へ直接PRを作成する前提にしてはならない。

---

## 9. `commands`

このDefinitionが対応するCommandを定義する。

```yaml
commands:
  primary: "/work-issue"
  allowed:
    - "/start-task"
    - "/work-issue"
    - "/create-pr"
    - "/summarize-work"
  next:
    success: "/create-pr"
    review_fix: "/fix-review-comments"
    blocked: null
```

| 項目      | 必須 | 内容                |
| --------- | ---- | ------------------- |
| `primary` | 必須 | 主に実行するCommand |
| `allowed` | 推奨 | 利用可能なCommand   |
| `next`    | 推奨 | 状況別の次Command   |

`primary` の許容値例：

```yaml
"/start-task"
"/work-issue"
"/create-pr"
"/fix-review-comments"
"/summarize-work"
```

---

## 10. `agent`

担当Agentを定義する。

```yaml
agent:
  primary: "worker-ai"
  support:
    - "support-ai"
    - "test-ai"
  review:
    - "reviewer-ai"
```

| 項目      | 必須 | 内容          |
| --------- | ---- | ------------- |
| `primary` | 必須 | 主担当Agent   |
| `support` | 任意 | 補助Agent     |
| `review`  | 任意 | レビューAgent |

許容値例：

```yaml
orchestrator-ai
worker-ai
reviewer-ai
docs-reviewer-ai
test-ai
contract-ai
fixer-ai
support-ai
```

---

## 11. `background`

Taskの背景を記載する。

```yaml
background: |
  レコメンド結果画面の実装に先立ち、商品一覧表示の仕様を明確化する必要がある。
```

| 項目 | 内容                                |
| ---- | ----------------------------------- |
| 型   | string                              |
| 必須 | yes                                 |
| 用途 | Issue本文、PR本文、作業サマリに利用 |

---

## 12. `objective`

Taskの目的を記載する。

```yaml
objective: |
  レコメンド結果の商品一覧表示に必要な画面項目、表示条件、エラー時表示、関連APIを整理する。
```

| 項目 | 内容                                       |
| ---- | ------------------------------------------ |
| 型   | string                                     |
| 必須 | yes                                        |
| 注意 | 作業そのものではなく、達成したい状態を書く |

---

## 13. `scope`

今回実施することを定義する。

```yaml
scope:
  - "商品一覧表示の画面仕様を整理する"
  - "表示項目、並び順、空状態、エラー状態を定義する"
  - "関連するAPI入出力との接続点を整理する"
```

| 項目 | 内容                                 |
| ---- | ------------------------------------ |
| 型   | list[string]                         |
| 必須 | yes                                  |
| 注意 | AIが実施してよい作業範囲を明確にする |

---

## 14. `out_of_scope`

今回実施しないことを定義する。

```yaml
out_of_scope:
  - "画面実装"
  - "API実装"
  - "DB schema変更"
  - "OpenAPI変更"
```

| 項目 | 内容                                    |
| ---- | --------------------------------------- |
| 型   | list[string]                            |
| 必須 | yes                                     |
| 注意 | scope外作業の混入を防ぐため必ず記載する |

### 14.1 `MOD-RECO-*` implementation Task の Orchestrator 配線（Reco 共通）

正本は `docs/06_実装設計/reco/MOD-RECO-001_Recommendation Orchestratorモジュール仕様書.md` §8.4。

| 項目 | 記載方針 |
| ---- | -------- |
| モジュール本体 | `scope` にモジュールディレクトリ実装を記載 |
| Orchestrator 統合テスト | `scope` に明示 DI による 1 本以上を推奨 |
| `stubs.py` 差し替え | 原則 `out_of_scope`（**起動フェーズ `002`/`003` は例外**） |
| フェーズ Wiring | 別 Task（`MOD-RECO-001` Epic またはフェーズ代表 Epic） |

---

## 15. `input`

参照する入力資料を定義する。

```yaml
input:
  docs:
    - path: "docs/05_実装設計/API仕様書.md"
      required: true
      purpose: "商品一覧表示に必要なAPI入出力を確認するため"
  templates:
    - path: "prompts/templates/docs/screen-spec.md"
      required: true
      purpose: "画面仕様書を標準フォーマットで作成するため"
      applies_to:
        - "docs/05_実装設計/画面仕様書/SCR-002 レコメンド条件入力画面仕様書.md"
  files:
    - path: "apps/web/src/app/recommendations/page.tsx"
      required: false
      purpose: "既存画面構成の確認"
  issues:
    - "#101"
  prs: []
```

### 15.1 `input.docs`

参照すべき正本docsを記載する。

| 項目       | 必須 | 内容       |
| ---------- | ---- | ---------- |
| `path`     | yes  | docsパス   |
| `required` | yes  | 必須資料か |
| `purpose`  | yes  | 参照目的   |

設計・実装Taskでは、原則として `input.docs` を空にしない。

---

### 15.2 `input.templates`

| 項目         | 必須 | 内容                               |
| ------------ | ---- | ---------------------------------- |
| `path`       | yes  | 利用するテンプレートファイルのパス |
| `required`   | yes  | 必須テンプレートか                 |
| `purpose`    | yes  | テンプレートの利用目的             |
| `applies_to` | 推奨 | このテンプレートを適用する出力先   |

---

### 15.3 `input.files`

参照するsource code、config、script等を記載する。

| 項目       | 必須 | 内容         |
| ---------- | ---- | ------------ |
| `path`     | yes  | ファイルパス |
| `required` | yes  | 必須か       |
| `purpose`  | yes  | 参照目的     |

---

### 15.4 `input.issues`

参照するIssue番号を記載する。

```yaml
issues:
  - "#101"
```

---

### 15.5 `input.prs`

参照するPR番号を記載する。

```yaml
prs:
  - "#201"
```

---

## 16. `output`

作成・更新する出力先を定義する。

```yaml
output:
  docs:
    - path: "docs/05_実装設計/画面仕様書/SCR-002 レコメンド条件入力画面仕様書.md"
      action: "create"
      required: true
      template: "prompts/templates/docs/screen-spec.md"
  files:
    - path: "apps/web/src/app/recommendations/page.tsx"
      action: "update"
      required: false
  tests:
    - path: "apps/web/src/app/recommendations/page.test.tsx"
      action: "create"
      required: false
  generated:
    expected: false
    paths: []
    handling: "do_not_edit_manually"
  logs:
    ai_logs_required: false
    path: null
```

### 16.1 `output.docs`

作成・更新するdocsを定義する。

| 項目       | 必須     | 内容                           |
| ---------- | -------- | ------------------------------ |
| `path`     | yes      | 出力先                         |
| `action`   | yes      | `create` / `update` / `delete` |
| `required` | yes      | 必須成果物か                   |
| `template` | 条件付き | 利用する文書テンプレート       |

例：

````yaml
docs:
  - path: "docs/05_実装設計/画面仕様書/SCR-002 レコメンド条件入力画面仕様書.md"
    action: "create"
    required: true
    template: "prompts/templates/docs/screen-spec.md"

---

### 16.2 `output.files`

作成・更新するsource code、config、script等を定義する。

---

### 16.3 `output.tests`

作成・更新するtest fileを定義する。

---

### 16.4 `output.generated`

generatedファイルへの影響を定義する。

```yaml
generated:
  expected: false
  paths: []
  handling: "do_not_edit_manually"
````

| 項目       | 必須 | 内容                        |
| ---------- | ---- | --------------------------- |
| `expected` | yes  | generated差分が想定されるか |
| `paths`    | yes  | 対象generated path          |
| `handling` | yes  | 取り扱い                    |

`handling` の許容値：

| 値                       | 内容                  |
| ------------------------ | --------------------- |
| `none`                   | generated影響なし     |
| `do_not_edit_manually`   | 手動編集禁止          |
| `regenerate_required`    | 再生成が必要          |
| `contract_task_required` | Contract Task化が必要 |

generatedファイルを手動編集する前提は禁止する。

---

### 16.5 `output.logs`

AIログ出力要否を定義する。

通常作業ログをすべて `ai-logs/` に保存してはならない。

---

## 17. `deliverables`

成果物を定義する。

```yaml
deliverables:
  - "SCR-002 レコメンド条件入力画面仕様書"
  - "画面項目定義"
  - "空状態・エラー状態の表示仕様"
```

| 項目 | 内容                                 |
| ---- | ------------------------------------ |
| 型   | list[string]                         |
| 必須 | yes                                  |
| 注意 | 完了時に存在確認できる粒度で記載する |

---

## 18. `acceptance_criteria`

完了条件を定義する。

```yaml
acceptance_criteria:
  - "指定された画面仕様書が作成されている"
  - "表示項目、表示条件、空状態、エラー状態が定義されている"
  - "関連APIとの接続点が記載されている"
  - "out_of_scopeの実装作業を含んでいない"
```

| 項目 | 内容               |
| ---- | ------------------ |
| 型   | list[string]       |
| 必須 | yes                |
| 注意 | 検証可能な文にする |

悪い例：

```yaml
acceptance_criteria:
  - "いい感じに整理されている"
```

良い例：

```yaml
acceptance_criteria:
  - "画面仕様書に表示項目、表示条件、エラー状態、空状態が記載されている"
```

---

## 19. `branch`

Branch方針を定義する。

```yaml
branch:
  no_branch: false
  name: "docs/task-<issue-number>-scr-002-recommendation-input-screen-spec"
  base: "feature/epic-301-web-screens"
  target: "feature/epic-301-web-screens"
  worktree_required: false
```

| 項目                | 必須     | 内容                          |
| ------------------- | -------- | ----------------------------- |
| `no_branch`         | 必須     | Branchを作らない場合は `true` |
| `name`              | 条件付き | Branch名                      |
| `base`              | 条件付き | Branch base                   |
| `target`            | 条件付き | PR target                     |
| `worktree_required` | 推奨     | worktree分離要否              |

Task BranchのPR targetは、原則として親Epic Branchとする。  
Task Branchから `develop` へ直接PRを作成してはならない。

---

## 20. `project`

GitHub Projects上の管理項目を定義する（Task Definition設計書 §17）。

```yaml
project:
  project_name: "Gift Recommendation Service MVP Cycle 3"
  fields:
    phase: "06_実装設計"
    status: "Todo"
    priority: "medium"
    planned_start: null
    due_date: null
```

| 項目                   | 必須 | 内容                                                                 |
| ---------------------- | ---- | -------------------------------------------------------------------- |
| `project_name`         | 必須 | Project名                                                            |
| `fields.phase`         | 必須 | 対象工程。正式値は Projects運用ルール §6（例: `06_実装設計`）    |
| `fields.status`        | 必須 | `Backlog`, `Todo`, `In Progress`, `AI Review`, `Human Review`, `Done` |
| `fields.priority`      | 必須 | `low`, `medium`, `high`, `critical`                                  |
| `fields.planned_start` | 必須 | 予定開始日                                                           |
| `fields.due_date`      | 必須 | 期限                                                                 |

§9.1 実運用YAMLでは `project` 直下に `status` / `phase` を置かない。`fields.type` / `fields.area` / `fields.owner` は使用しない（Issue同期は `issue` ブロックを正本とする）。

Statusの正本はGitHub Projectsとする。


---

## 21. `issue`

Issueに同期するラベル分類を定義する（Task Definition設計書 §14）。

```yaml
issue:
  unit: "task"
  type: "docs"
  area: "web"
```

| 項目         | 内容                                                                     |
| ------------ | ------------------------------------------------------------------------ |
| `issue.unit` | `epic`, `task`                                                           |
| `issue.type` | `feature`, `fix`, `docs`, `refactor`, `chore`, `test`, `hotfix`, `spike` |
| `issue.area` | `web`, `api`, `reco`, `batch`, `db`, `docs`, `infra`, `project`          |

`labels` 配列は §9.1 実運用YAMLでは使用しない。


---

## 22. `dependencies`

依存関係を定義する。

```yaml
dependencies:
  epics:
    - "#300"
    - "#340"
  issues:
    - "#101"
  prs:
    - "#201"
  tasks:
    - "task-api-spec-update"
  blocking: true
```

| 項目       | 内容                     |
| ---------- | ------------------------ |
| `epics`    | 依存 Epic Issue 番号配列（識別子付き Task では必須。空配列も明示する） |
| `issues`   | 依存Issue                |
| `prs`      | 依存PR                   |
| `tasks`    | 依存Task ID              |
| `blocking` | 依存未完了時に開始不可か |

`dependencies.epics` に列挙した Epic が `Done` でない場合、`/start-task` は `human_decision_points` への理由記載を必須とする（[`.cursor/commands/start-task.md`](../../../.cursor/commands/start-task.md)、成果物化方針書 §3.5.3）。識別子付き Task では、`parent.epic_issue_number` が指す親 Epic は `dependencies.epics` には含めない（親自身は本 Task の前提として扱う）。

依存Issue / PRが未完了の場合、AIは勝手に作業開始しない。

---

## 23. `parallel_control`

並列作業時の競合制御を定義する（Task Definition設計書 §29）。

```yaml
parallel_control:
  depends_on: []
  blocks: []
  exclusive_files:
    - "docs/06_実装設計/web/SCR-002 レコメンド条件入力画面仕様書.md"
  conflict_risk: "low"
  generated_impact: false
  contract_impact: false
  db_impact: false
```

| 項目               | 必須 | 内容                               |
| ------------------ | ---- | ---------------------------------- |
| `depends_on`       | 任意 | 先行すべきTask / Issue             |
| `blocks`           | 任意 | このTaskがブロックする対象         |
| `exclusive_files`  | 推奨 | 同時編集を避けるべきファイル。識別子付き Task では、親 Epic の `epic_scope.allowed_paths` 内の path のみを記載する |
| `conflict_risk`    | 必須 | `low` / `medium` / `high`          |
| `generated_impact` | 必須 | generated影響有無                  |
| `contract_impact`  | 必須 | API contract影響有無               |
| `db_impact`        | 必須 | DB schema影響有無                  |

識別子付き Task における **`exclusive_files` と親 Epic `allowed_paths` の関係**:

- `parallel_control.exclusive_files` の各 path は、親 Epic Definition の `epic_scope.allowed_paths` のいずれかの glob に一致する必要がある
- `output.files` も同様に親 Epic の `allowed_paths` 内に収まらなければならない
- `allowed_paths` 外を編集する必要が出た場合は、別 Epic 配下の Task として切り出す（成果物化方針書 §3.5.2）
- `/start-task` は本検査を実施し、不一致の場合は停止して `human_decision_points` への理由追記を求める（[`.cursor/commands/start-task.md`](../../../.cursor/commands/start-task.md)）

---

## 23.5 `contract_gate`

Implementation Task 開始前の **Contract Gate**（先行 Contract Task 完了・OpenAPI / generated 整合）を定義する。

正本: [Contract Gate運用設計書](../../../docs/00_共通/AIエージェント運用/Contract Gate運用設計書.md)

```yaml
contract_gate:
  required: false
  gate_id: null
  prerequisite_contract_tasks: []
  verify_at:
    - "/start-task"
    - "/work-issue"
  checks:
    - "contract_pr_merged_to_parent_epic_branch"
    - "openapi_in_packages_contracts"
    - "orval_regenerated_if_generated_impact"
    - "generated_not_manually_edited"
  blocked_message: "Contract Gate未通過。先行 Contract Task のマージと OpenAPI/generated を確認してください。"
```

| 項目 | 必須 | 内容 |
| ---- | ---- | ---- |
| `required` | 必須 | Gate 確認が必要か。`output.generated.expected: true` または `apps/**` 実装変更では原則 `true` |
| `gate_id` | 条件付き | 対応 Contract Definition の `implementation_gate.gate_id` と一致 |
| `prerequisite_contract_tasks` | 条件付き | 先行 Contract Task（Issue 番号・Definition path） |
| `verify_at` | 推奨 | 確認する Command（手順反映は Command 修正 Task で詳細化） |
| `checks` | 推奨 | 本 Task で実施する Gate チェック項目 |
| `blocked_message` | 任意 | Gate 未通過時に表示する停止メッセージ |

`required: true` の場合、Agent は Gate 未通過と判断したら作業を開始してはならない。Command へのチェックリスト埋め込みは Epic #300 の Command 修正 Task の scope とする。

---

## 24. `test_policy`

テスト・検証方針を定義する。

```yaml
test_policy:
  required:
    - "docs review"
    - "markdown format check"
  commands:
    - "pnpm lint"
    - "pnpm test"
  manual_checks:
    - "Mermaid図がある場合は構文を確認する"
  not_required:
    - "e2e test"
  skip_reason:
    e2e test: "docs作成Taskのため対象外"
```

| 項目            | 必須     | 内容         |
| --------------- | -------- | ------------ |
| `required`      | 必須     | 必須検証     |
| `commands`      | 推奨     | 実行コマンド |
| `manual_checks` | 推奨     | 手動確認     |
| `not_required`  | 推奨     | 不要なテスト |
| `skip_reason`   | 条件付き | 未実施理由   |

実施していないテストを実施済みとして報告してはならない。

---

## 24. `review`

レビュー方針を定義する。

```yaml
review:
  human_review_required: true
  ai_review_required: true
  review_points:
    - "scope内の成果物になっているか"
    - "正本docsと矛盾していないか"
    - "out_of_scopeの実装作業を含んでいないか"
  specialist_reviews:
    docs: true
    test: false
    contract: false
    security: false
```

| 項目                    | 必須 | 内容             |
| ----------------------- | ---- | ---------------- |
| `human_review_required` | 必須 | Human Review要否 |
| `ai_review_required`    | 推奨 | AI Review要否    |
| `review_points`         | 必須 | 確認観点         |
| `specialist_reviews`    | 推奨 | 専門レビュー要否 |

Human Reviewを省略する前提は禁止する。

---

## 25. `operation_logging`

AIログ運用を定義する。

```yaml
operation_logging:
  level: "standard"
  ai_logs:
    intake: false
    incidents: false
    cross_cutting: false
    experiments: false
  reason: "通常Taskのため、IssueとPRを正本とする"
```

### 25.1 `level`

| 値         | 内容   |
| ---------- | ------ |
| `minimal`  | 最小限 |
| `standard` | 標準   |
| `detailed` | 詳細   |

原則は `standard` とする。

### 25.2 `ai_logs`

| 項目            | 内容                    |
| --------------- | ----------------------- |
| `intake`        | Issue化前フィードバック |
| `incidents`     | 作業不可・例外          |
| `cross_cutting` | 横断影響                |
| `experiments`   | AI運用検証・比較実験    |

通常作業ログをすべて `ai-logs/` に保存しない。

---

## 26. `risk_points`

リスク観点を記載する。

```yaml
risk_points:
  - "API仕様との整合漏れ"
  - "画面仕様がMVP範囲を超える可能性"
  - "後続実装Taskとの責務境界が曖昧になる可能性"
```

| 項目 | 内容         |
| ---- | ------------ |
| 型   | list[string] |
| 必須 | 推奨         |

---

## 27. `human_decision_points`

人間判断が必要な論点を記載する。

```yaml
human_decision_points:
  - "画面上に表示する商品件数をMVPで固定値にするか"
  - "お気に入り導線をMVP対象に含めるか"
```

| 項目     | 内容                   |
| -------- | ---------------------- |
| 型       | list[string]           |
| 必須     | yes                    |
| ない場合 | 空配列 `[]` を明記する |

AIが独断で判断してはいけない論点を明示する。

---

## 28. `stop_conditions`

作業停止条件を記載する。

```yaml
stop_conditions:
  - "必須 `input.docs` 間に矛盾がある場合"
  - "API contract変更が必要になった場合"
  - "DB schema変更が必要になった場合"
  - "generatedファイルの手動編集が必要に見える場合"
  - "secretや.env実値を扱う必要が出た場合"
```

| 項目 | 内容         |
| ---- | ------------ |
| 型   | list[string] |
| 必須 | yes          |

---

## 29. `notes`

補足事項を記載する。

```yaml
notes:
  - "作成するdocsはNotion転記を想定し、Markdown表形式を優先する"
```

| 項目 | 内容         |
| ---- | ------------ |
| 型   | list[string] |
| 必須 | no           |

---

## 30. 標準テンプレート

新しいTask Definitionは、原則として以下を雛形にする。

```yaml
schema_version: "1.0"
definition_type: "task"

task:
  id: ""
  title: ""
  summary: ""

parent:
  epic_issue: null
  epic_issue_number: null
  epic_branch: null
  related_issues: []
  related_prs: []

commands:
  primary: ""
  allowed: []
  next:
    success: null
    review_fix: null
    blocked: null

agent:
  primary: ""
  support: []
  review: []

background: ""

objective: ""

scope: []

out_of_scope: []

input:
  docs: []
  templates: []
  files: []
  issues: []
  prs: []

output:
  docs: []
  files: []
  tests: []
  generated:
    expected: false
    paths: []
    handling: "none"
  logs:
    ai_logs_required: false
    path: null

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
  contract_impact: false
  db_impact: false

contract_gate:
  required: false
  gate_id: null
  prerequisite_contract_tasks: []
  verify_at:
    - "/start-task"
    - "/work-issue"
  checks: []
  blocked_message: null

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
    docs: false
    test: false
    contract: false
    security: false

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

## 31. 記入例

記入例の正本は以下とする。

```text
prompts/definitions/_examples/task-definition.example.yaml
```

実運用の参照例:

```text
prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml
```


---

## 32. バリデーション観点

Task Definition作成・修正時は、以下を確認する。

### 32.1 構造確認（Task Definition設計書 §9.1）

- `schema_version` がある
- `definition_type: task` である
- `task.id` がある
- `task.title` がある
- `work_mode` がある（`human-led` または `ai-agent`）
- `work_mode` と `branch.no_branch` が §17.2 の標準値と一致している
- `scope` が空でない
- `out_of_scope` が空でない
- `input.docs` がある
- `output.docs` がある場合、`output.docs[].template` がある
- `deliverables` がある
- `acceptance_criteria` がある
- `branch` がある（`no_branch` が先頭フィールド）
- `project` がある（`project_name` + `fields` のみ。直下の `status` / `phase` なし）
- `issue` がある（`issue.unit` / `issue.type` / `issue.area`。`labels` 配列なし）
- `dependencies.blocking` が boolean である
- `parallel_control` がある
- `test_policy.required` が配列である
- `review.specialist_reviews.*` が boolean である
- `review.ai_review_required` がある
- `operation_logging.level` がある
- `human_decision_points` がある
- `stop_conditions` がある


---

### 32.2 scope確認

- scopeが具体的である
- out_of_scopeが具体的である
- scopeとout_of_scopeが矛盾していない
- scope外のAPI contract変更が混在していない
- scope外のDB schema変更が混在していない
- scope外のgenerated手動編集が混在していない

---

### 32.3 input / output確認

- `input.docs` が存在する
- output_docsまたはtarget filesが明確である
- 出力先が不明な成果物がない
- docs正本が明確である
- source code変更の場合、対象コンポーネントが明確である
- test変更の場合、対象testが明確である
- docs成果物を作成する場合、利用する文書テンプレートが明確である
- `input.templates` に指定されたテンプレートが存在する
- `output.docs[].template` が指定されている場合、`input.templates[].path` と対応している
- 指定テンプレートと作成対象docsの目的が矛盾していない
- 文書テンプレートの章構成に従って成果物を作成する方針になっている

---

### 32.4 Branch確認

- `work_mode` が明確である
- `work_mode` と `branch.no_branch` が矛盾していない（§17.2）
- `branch.no_branch` が明確である
- no_branch判定が明確である
- Branch baseが明確である
- PR targetが明確である
- Task Branchからdevelopへ直接PRする前提になっていない
- main / developへ直接pushする前提になっていない

---

### 32.4a Epic スコープ確認（識別子付き Task）

識別子付き Task（`task.title` が `{識別子}:{概要}` 形式）では、以下を検査する（[成果物一覧×Task Definition化方針書](../../../docs/00_共通/AIエージェント運用/成果物一覧×Task%20Definition化方針書.md) §3.5）。

- `parent.epic_issue_number` が記載されている
- `parent.epic_issue` のタイトル先頭識別子と `task.title` 先頭識別子が一致する（例: `[Epic]API-PUB-002:...` と `[Task]API-PUB-002:...`）
- `output.files` の各 path が、親 Epic の `epic_scope.allowed_paths` のいずれかに一致する
- `parallel_control.exclusive_files` の各 path が、親 Epic の `epic_scope.allowed_paths` のいずれかに一致する
- `dependencies.epics` が明示されている（空配列でも可。未記載は不可）
- `dependencies.epics` 内の Epic Issue が実在する

`allowed_paths` 外の path が必要になった場合は、該当 Epic 配下の別 Task として切り出し、本 Task の `dependencies.epics` に追加する。

---

### 32.5 test確認

- 必須テストが明確である
- 不要なテストには理由がある
- 実行コマンドが必要な場合、記載されている
- 未実施テストを実施済み扱いする構造になっていない

---

### 32.6 security確認

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

### 32.7 generated確認

- generatedファイル手動編集を前提にしていない
- generated差分がある場合、再生成方針が明確である
- OpenAPI / Orval / API client影響がある場合、Contract Task化が検討されている

---

## 33. 禁止事項

以下は禁止する。

- Definitionなしで大規模Taskを開始すること
- scopeが曖昧なDefinitionを使うこと
- out_of_scopeを書かずにTaskを開始すること
- `input.docs` なしで設計・実装Taskを開始すること
- 出力先が不明なTaskを開始すること
- 完了条件が検証不能なTaskを開始すること
- Human Reviewを省略する前提にすること
- main / developへ直接pushする前提にすること
- Task Branchからdevelopへ直接PRを作成する前提にすること
- generatedファイルを手動編集する前提にすること
- secretや`.env` 実値を記載すること
- Slack通知だけで作業記録を完結させること
- 通常作業ログをすべて `ai-logs/` に保存する前提にすること
- docs作成Taskで、指定された文書テンプレートを無視して成果物を作成すること
- 存在しないテンプレートを指定したままTaskを開始すること
- `input.templates` と `output.docs[].template` が矛盾した状態で作業を開始すること

---

## 34. 一言まとめ

Task Definition は、AI Agentに渡す作業条件の正本である。

Commandが「どう実行するか」を定義するのに対し、Task Definitionは「何を、どこまで、どの条件で実行するか」を定義する。

AI Agentは、Task Definitionのscope、out_of_scope、input、output、acceptance_criteria、test_policy、human_decision_points、stop_conditionsに従って作業し、曖昧な点や横断影響がある場合は人間判断へ回す。
