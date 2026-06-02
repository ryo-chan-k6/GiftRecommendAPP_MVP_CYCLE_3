# prompts 運用ガイド

## 1. 目的

`prompts/` は、AI Agentに対する作業依頼を標準化するための入力資材を管理するディレクトリである。

本プロジェクトでは、AI Agentへ自然文だけで作業を依頼するのではなく、原則として以下の形式で依頼する。

```text
/<Command> @<definition>
```

例：

```text
/start-epic @prompts/definitions/_examples/epic-definition.example.yaml
/start-task @prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml
/work-issue @prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml
/review-pr @prompts/definitions/_examples/review-definition.example.yaml #123
/create-contract-task @prompts/definitions/cross-cutting/recommendation-api-contract/contract-task.yaml
```

このとき、`prompts/` は主に以下を担う。

| 要素                             | 役割                                                                                             |
| -------------------------------- | ------------------------------------------------------------------------------------------------ |
| `prompts/definitions/`           | 作業対象、入力資料、出力先、完了条件、確認観点を定義する                                         |
| `prompts/definitions/_schemas/`  | Definitionの項目構造・必須項目・記述ルールを定義する                                             |
| `prompts/definitions/_examples/` | Definitionの記入例を管理する                                                                     |
| `prompts/templates/`             | Issue本文、PR本文、レビューコメント、Slack通知、docs雛形、ai-log文面などのテンプレートを定義する |

---

## 2. このディレクトリの位置づけ

AI Agent運用における各資材の関係は以下とする。

```text
AGENTS.md
  ↓
.cursor/rules/
  ↓
.cursor/agents/
  ↓
.cursor/commands/
  ↓
prompts/definitions/
  ↓
prompts/templates/
  ↓
Issue / Branch / PR / docs / Slack / ai-logs
```

| 資材                   | 役割                                                  |
| ---------------------- | ----------------------------------------------------- |
| `AGENTS.md`            | AI Agent全体の上位方針                                |
| `.cursor/rules/`       | 全Agent共通の行動ルール                               |
| `.cursor/agents/`      | Agentごとの責務・権限・停止条件                       |
| `.cursor/commands/`    | AI Agentに実行させる操作手順                          |
| `prompts/definitions/` | Commandに渡す作業定義                                 |
| `prompts/templates/`   | Issue、PR、レビュー、通知、docs、ai-logなどの出力形式 |
| `docs/`                | 設計成果物・仕様書の正本                              |
| `ai-logs/`             | 例外・横断影響・実験などの補助ログ保存先              |
| GitHub Issue           | 作業計画の正本                                        |
| Pull Request           | 作業結果・レビュー結果の正本                          |
| Slack                  | 通知・サマリ用。正本ではない                          |

---

## 3. 基本方針

### 3.1 Definitionなしの大規模作業は原則禁止

大規模な設計、実装、レビュー、修正作業は、原則としてDefinitionを指定して実行する。

```text
/start-task @prompts/definitions/tasks/<task-name>/<phase>.yaml
```

Definitionなしの自然文依頼は、軽微な確認・相談・補足説明に限定する。

---

### 3.2 CommandとDefinitionの責務を分ける

Commandには「どの手順で実行するか」を定義する。  
Definitionには「何を対象に、どの条件で実行するか」を定義する。

| 項目      | Command        | Definition           |
| --------- | -------------- | -------------------- |
| 実行手順  | 持つ           | 持たない             |
| Agent割当 | 持つ           | 必要に応じて補足する |
| 作業対象  | 持たない       | 持つ                 |
| 入力資料  | 持たない       | 持つ                 |
| 出力先    | 持たない       | 持つ                 |
| 完了条件  | 持たない       | 持つ                 |
| 確認観点  | 共通観点を持つ | Task固有観点を持つ   |

---

### 3.3 templatesは文面・成果物構造の型に限定する

`prompts/templates/` は、以下のような出力形式の標準化に利用する。

- GitHub Issue本文
- Pull Request本文
- AI Reviewコメント
- Slack通知
- 人間判断依頼
- docs成果物の章構成
- ai-log記録文面

templatesには、個別Task固有の作業条件を書かない。  
個別Task固有の条件は、`prompts/definitions/` に記載する。

---

### 3.4 テンプレート冒頭に「使い方」セクションを入れない

`prompts/templates/` 配下のテンプレートファイルは、実際にIssue / PR / コメント / Slack / docs / ai-logへ出力される本文として扱う。

そのため、テンプレート本体には原則として以下を含めない。

```text
## 使い方
```

テンプレート利用者向けの説明は、以下に寄せる。

| 説明内容             | 記載先                           |
| -------------------- | -------------------------------- |
| テンプレートの用途   | `prompts/README.md`              |
| Definition項目の意味 | `prompts/definitions/_schemas/`  |
| 記入例               | `prompts/definitions/_examples/` |

---

### 3.5 docs成果物テンプレートはDefinitionで明示する

docs成果物を作成・更新するTaskでは、利用する文書テンプレートをDefinition上で明示する。

Task Definition / Contract Definitionでは、以下を対応させる。

```yaml
input:
  templates:
    - path: "prompts/templates/docs/screen-spec.md"
      required: true
      purpose: "画面仕様書を標準フォーマットで作成するため"
      applies_to:
        - "docs/06_実装設計/web/SCR-002_レコメンド条件入力画面画面仕様書.md"

output:
  docs:
    - path: "docs/06_実装設計/web/SCR-002_レコメンド条件入力画面画面仕様書.md"
      action: "create"
      required: true
      template: "prompts/templates/docs/screen-spec.md"
```

原則は以下とする。

| 項目                     | 方針                                                              |
| ------------------------ | ----------------------------------------------------------------- |
| `input.templates`        | 作業時に参照するテンプレートを定義する                            |
| `output.docs[].template` | 出力docsに適用するテンプレートを定義する                          |
| 両者の関係               | `output.docs[].template` は `input.templates[].path` と対応させる |
| 矛盾時                   | AI Agentは作業を停止し、人間確認へ回す                            |

---

### 3.6 正本を混同しない

| 内容               | 正本                             |
| ------------------ | -------------------------------- |
| 作業計画           | GitHub Issue                     |
| 作業結果           | Pull Request                     |
| レビュー結果       | Pull Request                     |
| 設計成果物         | `docs/`                          |
| 通知               | Slack                            |
| Definition構造     | `prompts/definitions/_schemas/`  |
| Definition記入例   | `prompts/definitions/_examples/` |
| 文面形式           | `prompts/templates/`             |
| 例外・横断影響ログ | 必要に応じて `ai-logs/`          |

Slack通知やチャット回答だけで作業記録を完結させない。

---

## 4. ディレクトリ構成

```text
prompts/
├─ README.md
├─ definitions/
│  ├─ _examples/
│  │  ├─ task-definition.example.yaml
│  │  ├─ review-definition.example.yaml
│  │  └─ contract-definition.example.yaml
│  ├─ _schemas/
│  │  ├─ task-definition.schema.md
│  │  ├─ review-definition.schema.md
│  │  └─ contract-definition.schema.md
│  ├─ cross-cutting/
│  ├─ epics/
│  ├─ reviews/
│  └─ tasks/
└─ templates/
   ├─ ai-log/
   │  ├─ cross-cutting-log.md
   │  └─ incident-log.md
   ├─ docs/
   │  └─ screen-spec.md
   ├─ feedback/
   │  └─ human-decision-request.md
   ├─ issue/
   │  ├─ task-issue.md
   │  └─ contract-task-issue.md
   ├─ pr/
   │  └─ task-pr.md
   ├─ review/
   │  └─ ai-review-comment.md
   └─ slack/
      ├─ ai-review-result.md
      ├─ pr-created.md
      └─ work-summary.md
```

補足：

| パス                        | 意味                                 |
| --------------------------- | ------------------------------------ |
| `prompts/templates/ai-log/` | ai-log文面テンプレート置き場         |
| `ai-logs/`                  | 実際のAI補助ログ保存先               |
| `prompts/templates/docs/`   | docs成果物の章構成テンプレート置き場 |
| `docs/`                     | 実際の設計成果物・仕様書の保存先     |

---

## 5. definitions の役割

`prompts/definitions/` は、Commandに渡す作業定義を管理する。

Definitionは、AI Agentに対して以下を伝えるための資材である。

- 何を作業対象にするか
- 何を入力資料として参照するか
- どのテンプレートに従うか
- 何を出力するか
- どこに出力するか
- どこまでをscopeとするか
- どこからをout_of_scopeとするか
- 何をもって完了とするか
- どの観点で確認するか
- どのテスト・検証を実施するか
- 人間判断が必要な条件は何か

---

## 6. definitions 配下の役割

### 6.1 `_schemas/`

Definitionの構造を定義する。

想定ファイル：

```text
prompts/definitions/_schemas/
├─ task-definition.schema.md
├─ review-definition.schema.md
├─ contract-definition.schema.md
└─ epic-definition.schema.md
```

役割：

- 必須項目の定義
- 任意項目の定義
- 記述ルールの定義
- Definition作成時のチェック観点の定義
- Commandごとの必要入力の整理
- docsテンプレート指定方法の定義
- 停止条件・禁止事項の定義

---

### 6.2 `_examples/`

Definitionの記入例を管理する。

想定ファイル：

```text
prompts/definitions/_examples/
├─ task-definition.example.yaml
├─ review-definition.example.yaml
├─ contract-definition.example.yaml
└─ epic-definition.example.yaml
```

役割：

- 初回作成時の参考例
- schema理解の補助
- 新しいTask Definition作成時の雛形
- AI Agentへ記述粒度を伝えるサンプル

`_examples/` は参考例であり、実作業の正本ではない。

---

### 6.3 `epics/`

Epic単位のDefinitionを管理する。

想定用途：

- 複数Taskを束ねる作業単位の定義
- 親Epic Issue作成
- Epic Branch作成
- Task分割
- Epic PR作成前の確認

想定ファイル例：

```text
prompts/definitions/epics/
└─ scr-002-recommendation-input/
   └─ epic.yaml
```

---

### 6.4 `tasks/`

Task単位のDefinitionを管理する。

想定用途：

- 設計書作成
- 実装
- test追加
- docs修正
- config修正
- Issue作成
- Branch作成
- `/work-issue` による作業実行
- `/create-pr` によるPR作成

想定ファイル例：

```text
prompts/definitions/tasks/
├─ scr-002-recommendation-input/
│  └─ screen-spec.yaml
└─ api-int-002-reco-recommendation-run/
   └─ api-spec.yaml
```

---

### 6.5 `reviews/`

PR Review用のDefinitionを管理する。

想定用途：

- `/review-pr` の入力
- AI Review観点の指定
- docs / code / test / API contract の確認観点整理
- Human Reviewへ進める条件の定義
- Task Definitionで指定されたdocsテンプレートへの準拠確認

想定ファイル例：

```text
prompts/definitions/reviews/
└─ scr-002-recommendation-input/
   └─ pr-review.yaml
```

---

### 6.6 `cross-cutting/`

横断影響のあるDefinitionを管理する。

想定用途：

- API contract変更
- OpenAPI変更
- Orval設定変更
- generated差分
- DB schema変更
- CI/CD変更
- security影響
- 複数Taskにまたがる影響分析

想定ファイル例：

```text
prompts/definitions/cross-cutting/
└─ api-contract-orval/
   └─ contract-task.yaml
```

---

## 7. templates の役割

`prompts/templates/` は、AI AgentがIssue、PR、レビューコメント、Slack通知、docs成果物、ai-logなどを作成する際のテンプレートを管理する。

templatesは、文面構造・章構成を定義する。  
個別Taskの条件は書かない。

---

## 8. templates 配下の役割

### 8.1 `templates/issue/`

GitHub Issue本文テンプレートを管理する。

作成済みファイル：

```text
prompts/templates/issue/
├─ task-issue.md
└─ contract-task-issue.md
```

想定ファイル：

```text
prompts/templates/issue/
├─ task-issue.md
├─ epic-issue.md
├─ contract-task-issue.md
└─ bug-issue.md
```

利用Command例：

- `/start-task`
- `/create-contract-task`

---

### 8.2 `templates/pr/`

Pull Request本文テンプレートを管理する。

作成済みファイル：

```text
prompts/templates/pr/
└─ task-pr.md
```

想定ファイル：

```text
prompts/templates/pr/
├─ task-pr.md
├─ epic-pr.md
├─ contract-pr.md
└─ hotfix-pr.md
```

利用Command例：

- `/create-pr`

---

### 8.3 `templates/review/`

AI Reviewコメントやレビュー結果サマリのテンプレートを管理する。

作成済みファイル：

```text
prompts/templates/review/
└─ ai-review-comment.md
```

想定ファイル：

```text
prompts/templates/review/
├─ ai-review-comment.md
├─ docs-review-comment.md
├─ test-review-comment.md
├─ contract-review-comment.md
└─ review-result-summary.md
```

利用Command例：

- `/review-pr`
- `/fix-review-comments`
- `/summarize-work`

---

### 8.4 `templates/slack/`

Slack通知文面テンプレートを管理する。

作成済みファイル：

```text
prompts/templates/slack/
├─ ai-review-result.md
├─ pr-created.md
└─ work-summary.md
```

想定ファイル：

```text
prompts/templates/slack/
├─ task-started.md
├─ pr-created.md
├─ ai-review-result.md
├─ review-fix-completed.md
├─ contract-task-created.md
├─ work-summary.md
└─ human-decision-request.md
```

利用Command例：

- `/start-task`
- `/create-pr`
- `/review-pr`
- `/fix-review-comments`
- `/create-contract-task`
- `/summarize-work`

Slack通知は正本ではない。  
正本へのリンクまたは参照を含める。

---

### 8.5 `templates/feedback/`

Issue化前フィードバックや人間確認依頼のテンプレートを管理する。

作成済みファイル：

```text
prompts/templates/feedback/
└─ human-decision-request.md
```

想定ファイル：

```text
prompts/templates/feedback/
├─ intake-feedback.md
├─ human-decision-request.md
├─ blocked-feedback.md
└─ split-required-feedback.md
```

利用Command例：

- `/start-task`
- `/review-pr`
- `/fix-review-comments`
- `/create-contract-task`
- `/summarize-work`

---

### 8.6 `templates/ai-log/`

`ai-logs/` に記録する場合の文面テンプレートを管理する。

作成済みファイル：

```text
prompts/templates/ai-log/
├─ cross-cutting-log.md
└─ incident-log.md
```

想定ファイル：

```text
prompts/templates/ai-log/
├─ intake-log.md
├─ incident-log.md
├─ cross-cutting-log.md
└─ experiment-log.md
```

通常作業ログをすべて `ai-logs/` に保存しない。  
`ai-logs/` は、Issue化前フィードバック、作業不可・例外、横断影響、AI運用検証・比較実験などに限定する。

| テンプレート                            | 実ログ保存先             | 用途                                                       |
| --------------------------------------- | ------------------------ | ---------------------------------------------------------- |
| `templates/ai-log/cross-cutting-log.md` | `ai-logs/cross-cutting/` | OpenAPI / Orval / generated / DB / CI/CDなど横断影響の記録 |
| `templates/ai-log/incident-log.md`      | `ai-logs/incidents/`     | 作業停止、例外、判断不能、再発防止の記録                   |

---

### 8.7 `templates/docs/`

docs成果物の章構成テンプレートを管理する。

作成済みファイル：

```text
prompts/templates/docs/
└─ screen-spec.md
```

想定ファイル：

```text
prompts/templates/docs/
├─ screen-spec.md
├─ api-contract-spec.md
├─ api-implementation-spec.md
├─ batch-spec.md
├─ module-spec.md
├─ table-spec.md
└─ test-spec.md
```

利用Command例：

- `/start-task`
- `/work-issue`
- `/create-contract-task`

docsテンプレートは、Definitionの `input.templates` と `output.docs[].template` で明示する。

---

## 9. Definitionの基本構造

### 9.1 Task Definition

Task Definitionの基本構造は以下とする。

```yaml
schema_version:
definition_type:

task:
  id:
  title:
  summary:

parent:
commands:
agent:

background:
objective:

scope:
out_of_scope:

input:
  docs:
  templates:
  files:
  issues:
  prs:

output:
  docs:
  files:
  tests:
  generated:
  logs:

deliverables:
acceptance_criteria:

branch:
project:
issue:
dependencies:
parallel_control:

test_policy:
review:
operation_logging:

risk_points:
human_decision_points:
stop_conditions:
notes:
```

項目の詳細は、`prompts/definitions/_schemas/task-definition.schema.md` を正本とする。

---

### 9.2 Review Definition

Review Definitionの基本構造は以下とする。

```yaml
schema_version:
definition_type:

review:
target:
commands:
agent:
review_scope:

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
    review_outputs:
    deliverables:

review_points:
acceptance_check:
result_policy:
status_policy:
outputs:
operation_logging:
human_decision_points:
stop_conditions:
notes:
```

Review Definitionでは、レビュー結果出力テンプレートと成果物テンプレートを分ける。

```yaml
input:
  templates:
    review_outputs:
      pr_comment: "prompts/templates/review/ai-review-comment.md"
      slack: "prompts/templates/slack/ai-review-result.md"
    deliverables:
      - path: "prompts/templates/docs/screen-spec.md"
        required: true
        purpose: "Task成果物が指定テンプレートに沿って作成されているか確認するため"
        applies_to:
          - "docs/06_実装設計/web/SCR-002_レコメンド条件入力画面画面仕様書.md"
```

項目の詳細は、`prompts/definitions/_schemas/review-definition.schema.md` を正本とする。

---

### 9.3 Contract Definition

Contract Definitionの基本構造は以下とする。

```yaml
schema_version:
definition_type:

contract:
source:
commands:
agent:
change:

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
provider_consumer:
generation_policy:

deliverables:
acceptance_criteria:

branch:
project:
issue:
dependencies:
parallel_control:

test_policy:
review:
operation_logging:

risk_points:
human_decision_points:
stop_conditions:
notes:
```

Contract Definitionでも、docs成果物を更新する場合は `input.templates` と `output.docs[].template` を対応させる。

項目の詳細は、`prompts/definitions/_schemas/contract-definition.schema.md` を正本とする。

---

## 10. Definition作成時の必須観点

Definition作成時は、少なくとも以下を明確にする。

| 観点                   | 内容                                        |
| ---------------------- | ------------------------------------------- |
| 作業目的               | なぜこのTaskを行うのか                      |
| scope                  | 今回実施すること                            |
| out_of_scope           | 今回実施しないこと                          |
| input.docs             | 参照すべき正本docs                          |
| input.templates        | 利用する文書・出力テンプレート              |
| output.docs            | 作成・更新するdocs                          |
| output.docs[].template | 出力docsに適用するテンプレート              |
| output.files           | 作成・修正するsource code / config / script |
| output.tests           | 作成・修正するtest                          |
| deliverables           | 成果物                                      |
| acceptance_criteria    | 完了条件                                    |
| dependencies           | 依存Issue / PR / Task                       |
| branch                 | Branch作成方針                              |
| test_policy            | テスト・検証方針                            |
| review                 | AI Review / Human Review方針                |
| human_decision_points  | 人間判断が必要な論点                        |
| stop_conditions        | AI Agentが停止すべき条件                    |

---

## 11. Definition作成時の禁止事項

以下は禁止する。

- scopeが曖昧なDefinitionを作成すること
- out_of_scopeを書かずに大規模Taskを開始すること
- input.docsを指定せずに設計・実装Taskを開始すること
- docs作成・更新Taskで、利用する文書テンプレートを曖昧にすること
- `input.templates` と `output.docs[].template` が矛盾した状態で作業を開始すること
- 存在しないテンプレートを指定したまま作業を開始すること
- 出力先が不明なTaskを開始すること
- 完了条件が検証不能なTaskを開始すること
- secret、APIキー、`.env` 実値をDefinitionに記載すること
- generatedファイルの手動編集を前提にすること
- Human Reviewを省略する前提にすること
- main / developへ直接pushする前提にすること
- Task Branchからdevelopへ直接PRを作成する前提にすること
- Slack通知だけで作業記録を完結させる前提にすること

---

## 12. ファイル命名規則

### 12.1 共通

ファイル名は原則としてkebab-caseとする。

```text
<name>.yaml
<name>.md
```

例：

```text
implementation.yaml
pr-review.yaml
task-issue.md
ai-review-comment.md
```

---

### 12.2 Definition

Definitionは、作業単位ごとにディレクトリを分ける。

```text
prompts/definitions/tasks/<task-name>/<phase>.yaml
```

例：

```text
prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml
prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml
prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml
```

---

### 12.3 Review Definition

```text
prompts/definitions/reviews/<task-name>/pr-review.yaml
```

例：

```text
prompts/definitions/_examples/review-definition.example.yaml
```

---

### 12.4 Cross-cutting Definition

```text
prompts/definitions/cross-cutting/<theme>/<name>.yaml
```

例：

```text
prompts/definitions/cross-cutting/api-contract-orval/contract-task.yaml
prompts/definitions/cross-cutting/recommendation-api-contract/contract-task.yaml
```

---

### 12.5 Template

```text
prompts/templates/<category>/<template-name>.md
```

例：

```text
prompts/templates/issue/task-issue.md
prompts/templates/pr/task-pr.md
prompts/templates/review/ai-review-comment.md
prompts/templates/slack/pr-created.md
prompts/templates/docs/screen-spec.md
prompts/templates/ai-log/cross-cutting-log.md
```

---

### 12.6 Example

```text
prompts/definitions/_examples/<definition-type>-definition.example.yaml
```

例：

```text
prompts/definitions/_examples/task-definition.example.yaml
prompts/definitions/_examples/review-definition.example.yaml
prompts/definitions/_examples/contract-definition.example.yaml
```

`example` の綴りを誤らない。

```text
OK: contract-definition.example.yaml
NG: contract-definition.exmaple.yaml
```

---

## 13. Commandとの対応

| Command                 | 主なDefinition                                     | 主なTemplate                                                                                          |
| ----------------------- | -------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `/start-epic`           | `definitions/epics/`                               | `templates/issue/epic-issue.md`, `templates/feedback/`, `templates/slack/`                            |
| `/start-task`           | `definitions/tasks/`                               | `templates/issue/task-issue.md`, `templates/feedback/`, `templates/slack/`                            |
| `/work-issue`           | `definitions/tasks/`, `definitions/cross-cutting/` | 必要に応じて `templates/docs/`, `templates/slack/`, `templates/ai-log/`                               |
| `/create-pr`            | `definitions/tasks/`, `definitions/cross-cutting/` | `templates/pr/task-pr.md`, `templates/slack/pr-created.md`                                            |
| `/review-pr`            | `definitions/reviews/`                             | `templates/review/ai-review-comment.md`, `templates/slack/ai-review-result.md`                        |
| `/fix-review-comments`  | `definitions/tasks/*/review-fix.yaml`              | `templates/review/`, `templates/slack/`, 必要に応じて `templates/feedback/`                           |
| `/create-contract-task` | `definitions/cross-cutting/`                       | `templates/issue/contract-task-issue.md`, `templates/ai-log/cross-cutting-log.md`, `templates/slack/` |
| `/summarize-work`       | 任意のDefinition                                   | `templates/slack/work-summary.md`, `templates/review/`, `templates/feedback/`                         |

---

## 14. 標準的な作業フロー

### 14.0 AI Review 3点セット（Epic / Task / Review Definition）必須

新しい workstream で AI主導Epic / Task を起票し、PR を AI Review へ進める場合は、原則として以下の **3点セット** を同じ workstream に揃える。Review Definition の作成漏れは、PR 作成後の AI Review 自動dispatch（`pr-created`）を `review_definition_not_found` で失敗させる（実例: PR #340）。

| Definition | 配置（規約） | 作成タイミング |
| ---------- | ------------ | -------------- |
| Epic Definition | `prompts/definitions/epics/<workstream>/epic.yaml` | `/start-epic` 前 |
| Task Definition | `prompts/definitions/tasks/<workstream>/<phase>.yaml` | `/start-task` 前 |
| Review Definition（Task PR） | `prompts/definitions/reviews/<workstream>/pr-review.yaml`（または Task Definition と同ディレクトリの `pr-review.yaml`） | `/create-pr` 前（Task PR） |
| Review Definition（Epic PR） | `prompts/definitions/reviews/<workstream>/epic/pr-review.yaml` | Epic PR 作成前 |

記入例（scaffold の起点）は以下を複製して使う。

```text
prompts/definitions/_examples/epic-definition.example.yaml    → epics/<workstream>/epic.yaml
prompts/definitions/_examples/task-definition.example.yaml    → tasks/<workstream>/<phase>.yaml
prompts/definitions/_examples/review-definition.example.yaml  → reviews/<workstream>/pr-review.yaml
```

**Review Definition を PR head へ同梱する。** AI Review 自動dispatch（`pr-created` / Definition Run Harness）は、Review Definition を **default branch ではなく PR head（変更ファイル）または規約パス** から解決する（正本: `.github/scripts/resolve-review-definition.cjs`）。主な解決順序は以下。

1. PR / Issue 本文に明示された Review Definition パス（`/review-pr @<path>` 等）
2. Epic branch の場合、`prompts/definitions/reviews/<workstream>/epic/pr-review.yaml`
3. Task Definition と同ディレクトリの `pr-review.yaml`（sibling）
4. workstream 規約パス `prompts/definitions/reviews/<workstream>/pr-review.yaml`（workstream は `tasks/<workstream>/` と一致）
5. Issue 番号・PR 番号・branch summary・`target` によるスコアリング走査

そのため、Review Definition は対象PR（Task/Epic）と同じ workstream に作成し、PR head へ commit して PR の変更ファイルに含める。Epic PR では Task 向け Review Definition の流用を許容しない。

| `review.ai_review_required`（Task Definition） | Review Definition | AI Review 自動dispatch |
| ----------------------------------------------- | ----------------- | ---------------------- |
| `true`（既定） | **必須**（PR head へ同梱） | 実行 |
| `false` | 不要（理由を Task Definition に明示） | スキップ（Human Review は省略しない） |

Epic PR では、`review.ai_review_required` の値に関わらず、Epic 向け Review Definition（`reviews/<workstream>/epic/pr-review.yaml`）を必須とする。

関連: 規約・確認観点は [ai-review.mdc](../.cursor/rules/ai-review.mdc) §3.18・§3.19、起票手順は [start-task.md](../.cursor/commands/start-task.md) / [start-epic.md](../.cursor/commands/start-epic.md)、hard stop は [create-pr.md](../.cursor/commands/create-pr.md) §5.5、運用前提は [AIレビュー運用設計書](../docs/00_共通/AIエージェント運用/AIレビュー運用設計書.md) §5.1 を正とする。

---

### 14.1 AI主導Epic / Task開始

親 Epic 未作成時は先に Epic を起票する。

```text
/start-epic @prompts/definitions/epics/<workstream_key>/epic.yaml
/start-task @prompts/definitions/tasks/<task-name>/design.yaml
```

主な流れ（Task）：

```text
Definition確認
  ↓
schema確認
  ↓
input.docs / input.templates確認
  ↓
Issue本文生成
  ↓
Issue作成
  ↓
Project同期
  ↓
no-branch判定
  ↓
Branch作成
  ↓
Status: In Progress
  ↓
Worker AIへ引き継ぎ
```

---

### 14.2 既存Issueの作業実行

```text
/work-issue @prompts/definitions/tasks/<task-name>/implementation.yaml
```

主な流れ：

```text
Issue確認
  ↓
Branch確認
  ↓
Definition確認
  ↓
input.docs確認
  ↓
input.templates確認
  ↓
作業実施
  ↓
テスト・検証
  ↓
commit
```

docs成果物を作成・更新する場合は、`output.docs[].template` に指定されたテンプレートに沿う。

---

### 14.3 PR作成

```text
/create-pr @prompts/definitions/tasks/<task-name>/implementation.yaml
```

主な流れ：

```text
diff確認
  ↓
Definition確認
  ↓
テスト結果確認
  ↓
PR本文作成
  ↓
Task PR作成
  ↓
Related to #<Task Issue番号> 記載
  ↓
Slack通知作成
  ↓
Status: AI Review
```

Task PRでは、原則として `Closes #<Task Issue番号>` を使用しない。  
Task Issueの `Done` / close は、PR merge時のGitHub Actions workflowで制御する。

---

### 14.4 AI Review

```text
/review-pr @prompts/definitions/reviews/<task-name>/pr-review.yaml #<PR番号>
```

主な流れ：

```text
PR確認
  ↓
Issue確認
  ↓
Task Definition確認
  ↓
Review Definition確認
  ↓
diff確認
  ↓
docs / code / test / contract / CI確認
  ↓
テンプレート準拠確認
  ↓
レビュー結果分類
  ↓
PRコメント作成
  ↓
Slack通知作成
  ↓
Human Review または In Progress
```

Task Definitionで `output.docs[].template` が指定されている場合、Review Definitionでは成果物が指定テンプレートに沿っているかを確認する。

---

### 14.5 レビュー指摘対応

```text
/fix-review-comments @prompts/definitions/tasks/<task-name>/review-fix.yaml #<PR番号>
```

主な流れ：

```text
review comments確認
  ↓
指摘分類
  ↓
同一Branchで対応可否確認
  ↓
修正
  ↓
テスト再実行
  ↓
PR更新
  ↓
Status: AI Review
```

---

### 14.6 Contract Task作成

```text
/create-contract-task @prompts/definitions/cross-cutting/<theme>/contract-task.yaml
```

主な流れ：

```text
契約変更対象確認
  ↓
OpenAPI / Orval / generated影響確認
  ↓
provider / consumer影響確認
  ↓
通常Taskから分離
  ↓
Contract Task Issue本文生成
  ↓
Contract Task Issue作成
  ↓
Project同期
  ↓
必要に応じて ai-logs/cross-cutting 記録候補
```

Contract Taskでは、API仕様書などdocs成果物を更新する場合、`input.templates` と `output.docs[].template` を対応させる。

---

### 14.7 作業サマリ作成

```text
/summarize-work @prompts/definitions/tasks/<task-name>/implementation.yaml
```

主な流れ：

```text
対象Issue / PR確認
  ↓
作業内容整理
  ↓
変更ファイル整理
  ↓
テスト結果整理
  ↓
残課題整理
  ↓
次Action整理
  ↓
Slack / PR / Issue向け文面作成
```

---

## 15. no-branch 運用

Task Issue / Contract Task Issueでは、Issue本文に `no-branch` チェックボックスを含める。

原則は以下とする。

| 状態                | 意味                                |
| ------------------- | ----------------------------------- |
| `no-branch = false` | Issue作成時にBranchを作成する       |
| `no-branch = true`  | Issue作成時点ではBranchを作成しない |

AI主導運用では、原則として `no-branch = false` とする。  
人主導で未来着手Issueを作成する場合は、必要に応じて `no-branch` を使用する。

Issue本文とLabelの状態が矛盾する場合、AI Agentは推測で進めず、人間確認へ回す。

---

## 16. security / secret 取り扱い

以下は、Definition、Template、Issue、PR、Slack通知、ai-logsに記載してはならない。

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

必要な場合は、環境変数名のみ記載する。

例：

```text
OK: OPENAI_API_KEY を使用する
NG: OPENAI_API_KEY=sk-...
```

---

## 17. generatedファイルの扱い

OpenAPI / Orval 等により生成されるファイルは、原則として手動編集しない。

generated差分が必要な場合は、以下を明確にする。

- 生成元ファイル
- 再生成コマンド
- generated出力先
- providerへの影響
- consumerへの影響
- testへの影響
- Contract Task化要否

generatedファイルの手動編集が必要に見える場合は、作業を停止し、人間確認へ回す。

---

## 18. ai-logs との関係

通常作業のログをすべて `ai-logs/` に保存しない。

`ai-logs/` は以下に限定して利用する。

| 条件                                     | 保存先                   | テンプレート                                    |
| ---------------------------------------- | ------------------------ | ----------------------------------------------- |
| Issue化前フィードバック                  | `ai-logs/intake/`        | `prompts/templates/ai-log/intake-log.md`        |
| 作業不可・例外                           | `ai-logs/incidents/`     | `prompts/templates/ai-log/incident-log.md`      |
| OpenAPI / Orval / generated 等の横断影響 | `ai-logs/cross-cutting/` | `prompts/templates/ai-log/cross-cutting-log.md` |
| AI運用検証・比較実験                     | `ai-logs/experiments/`   | `prompts/templates/ai-log/experiment-log.md`    |

通常の記録先は以下とする。

| 記録内容 | 正本  |
| -------- | ----- |
| 作業計画 | Issue |
| 作業結果 | PR    |
| レビュー | PR    |
| 成果物   | docs  |
| 通知     | Slack |

---

## 19. Definitionレビュー観点

Definitionを作成・修正した場合は、以下を確認する。

- Commandと対応しているか
- schemaに従っているか
- scopeが明確か
- out_of_scopeが明確か
- input.docsが指定されているか
- docs成果物がある場合、input.templatesが指定されているか
- docs成果物がある場合、output.docs[].templateが指定されているか
- input.templates と output.docs[].template が対応しているか
- output.docs / output.files / output.tests が明確か
- acceptance_criteriaが検証可能か
- dependenciesが明確か
- branch方針が明確か
- no-branch方針が明確か
- test_policyが明確か
- review方針が明確か
- human_review_requiredが明確か
- Human判断事項が明確か
- stop_conditionsが明確か
- secretや`.env`実値を含んでいないか
- generated手動編集を前提にしていないか

---

## 20. Templateレビュー観点

Templateを作成・修正した場合は、以下を確認する。

- 出力先が明確か
- 正本関係と矛盾していないか
- Commandの出力形式と整合しているか
- 必要な項目が不足していないか
- 個別Task固有の条件を含んでいないか
- 冒頭に `## 使い方` を含んでいないか
- Slack通知を正本として扱っていないか
- Human Reviewを省略する表現がないか
- AIがmerge判断をする表現がないか
- secretや`.env`実値を出力する欄がないか
- generated手動編集を肯定する表現がないか
- docsテンプレートの場合、章構成が成果物としてそのまま使えるか

---

## 21. 作成済み資材一覧

現時点で作成済みの主要資材は以下。

| 区分              | ファイル                                                         | 目的                              |
| ----------------- | ---------------------------------------------------------------- | --------------------------------- |
| Schema            | `prompts/definitions/_schemas/task-definition.schema.md`         | Task Definition構造を定義する     |
| Schema            | `prompts/definitions/_schemas/review-definition.schema.md`       | Review Definition構造を定義する   |
| Schema            | `prompts/definitions/_schemas/contract-definition.schema.md`     | Contract Definition構造を定義する |
| Example           | `prompts/definitions/_examples/task-definition.example.yaml`     | Task Definition記入例             |
| Example           | `prompts/definitions/_examples/review-definition.example.yaml`   | Review Definition記入例           |
| Example           | `prompts/definitions/_examples/contract-definition.example.yaml` | Contract Definition記入例         |
| Issue Template    | `prompts/templates/issue/epic-issue.md`                          | Epic Issue本文                    |
| Issue Template    | `prompts/templates/issue/task-issue.md`                          | Task Issue本文（§8.5 `contract_gate`） |
| Issue Template    | `prompts/templates/issue/contract-task-issue.md`                 | Contract Task Issue本文（§7.5 `implementation_gate`） |
| PR Template       | `prompts/templates/pr/task-pr.md`                                | Task PR本文（§8.5 Contract Gate 確認） |
| PR Template       | `prompts/templates/pr/contract-pr.md`                            | Contract PR本文（§13.5 Gate 解放） |
| PR Template       | `prompts/templates/pr/epic-pr.md`                                | Epic PR本文                       |
| PR Template       | `prompts/templates/pr/task-pr.md`                                | Task PR本文                       |
| PR Template       | `prompts/templates/pr/contract-pr.md`                            | Contract Task PR本文              |
| Review Template   | `prompts/templates/review/ai-review-comment.md`                  | AI Reviewコメント                 |
| Slack Template    | `prompts/templates/slack/pr-created.md`                          | PR作成通知                        |
| Slack Template    | `prompts/templates/slack/ai-review-result.md`                    | AI Review結果通知                 |
| Slack Template    | `prompts/templates/slack/work-summary.md`                        | 作業サマリ通知                    |
| Feedback Template | `prompts/templates/feedback/human-decision-request.md`           | 人間判断依頼                      |
| Docs Template     | `prompts/templates/docs/screen-spec.md`                          | 画面仕様書テンプレート            |
| AI Log Template   | `prompts/templates/ai-log/cross-cutting-log.md`                  | 横断影響ログ                      |
| AI Log Template   | `prompts/templates/ai-log/incident-log.md`                       | incidentログ                      |

---

## 22. 今後の作成候補

次に整備する候補は以下。

| 優先 | 作成物                                                  | 目的                                        |
| ---: | ------------------------------------------------------- | ------------------------------------------- |
|    1 | `prompts/templates/docs/api-contract-spec.md`           | API契約仕様書（契約面）の標準テンプレート   |
|    2 | `prompts/templates/docs/api-implementation-spec.md`     | API実装仕様書（実装面）の標準テンプレート   |
|    3 | `prompts/templates/slack/contract-task-created.md`      | Contract Task作成通知を標準化する           |
|    3 | `prompts/templates/slack/review-fix-completed.md`       | レビュー指摘対応完了通知を標準化する        |
|    4 | `prompts/templates/feedback/blocked-feedback.md`        | blocked時のフィードバック形式を標準化する   |
|    5 | `prompts/templates/feedback/split-required-feedback.md` | 別Issue化が必要な場合の通知形式を標準化する |
|    6 | `prompts/templates/ai-log/intake-log.md`                | Issue化前フィードバックログを標準化する     |
|    7 | `prompts/templates/ai-log/experiment-log.md`            | AI運用検証・比較実験ログを標準化する        |
|    8 | `prompts/definitions/epics/` の実Definition             | Epic運用を実Taskに適用する                  |
|    9 | `prompts/definitions/tasks/` の実Definition             | 実作業Taskを定義する                        |
|   10 | `prompts/definitions/reviews/` の実Definition           | 実PR Reviewを定義する                       |
|   11 | `prompts/definitions/cross-cutting/` の実Definition     | Contract / 横断Taskを定義する               |

---

## 23. 一言まとめ

`prompts/` は、AI Agentへの作業依頼を再現可能にするための入力資材置き場である。

- `definitions/` は、作業条件を定義する
- `_schemas/` は、Definitionの構造を定義する
- `_examples/` は、Definitionの記入例を提供する
- `templates/` は、出力文面・成果物構造の型を定義する
- `docs/` は、設計成果物・仕様書の正本である
- `ai-logs/` は、例外・横断影響・実験などの補助ログ保存先である

AI作業は、原則として以下の形式で開始する。

```text
/<Command> @<definition>
```

Command、Definition、Template、Issue、PR、docs、ai-logsの責務を分けることで、AI主導作業でも作業範囲・成果物・レビュー観点・正本関係を明確に保つ。
