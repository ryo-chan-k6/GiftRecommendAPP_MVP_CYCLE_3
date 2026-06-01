# Task Definition設計書

## 1. 目的

本ドキュメントは、Gift Recommendation Service におけるAIエージェント向けの作業依頼定義ファイルである `Task Definition` の設計を定義する。

Task Definitionは、人間またはOrchestrator AIが、AIエージェントへ作業を依頼する際に使用する構造化された作業条件ファイルである。

本ドキュメントでは、以下を明確にする。

- Task Definitionの役割
- 配置場所
- ファイル形式
- 命名規則
- Definition種別
- 標準項目
- GitHub Issue / Projects / Branch / PR との対応関係
- Commandとの関係
- AIエージェントへの引き渡し情報
- 並列作業時の競合制御
- operation_logging の定義
- サンプルYAML

---

## 2. 本ドキュメントの位置づけ

本ドキュメントは、Task Definitionの構造・項目・利用ルールに関する正本である。

| 項目                               | 正本ドキュメント                           |
| ---------------------------------- | ------------------------------------------ |
| AIエージェント運用全体             | AIエージェント活用型\_開発運用フロー設計書 |
| AIエージェント体制・責務           | AIエージェント体制・責務定義               |
| Command仕様                        | Commands設計書                             |
| Task Definition構造                | 本ドキュメント                             |
| prompts配置・命名                  | Prompts運用ルール                          |
| Issue本文構造                      | Issue運用ルール / Issueテンプレート設計書  |
| Projects Status / Phase / 日付管理 | Projects運用ルール                         |
| Branch命名・base・target           | ブランチ運用ルール                         |
| AIログ粒度                         | AIログ運用ルール                           |

本ドキュメントでは、AIが作業を実行するために必要な「作業条件」を定義する。  
実際の作業計画の正本はGitHub Issue、進捗管理の正本はGitHub Projects、レビュー正本はPR、成果物正本はdocsとする。

---

## 3. Task Definitionとは

Task Definitionは、AIエージェントに渡す個別作業依頼条件である。

自然文だけでAIに依頼すると、作業範囲、入力資料、出力先、完了条件、確認観点が曖昧になりやすい。

そのため、本プロジェクトでは、以下のようにCommandとDefinitionを組み合わせてAIへ作業依頼する。

```text
/<Command> @<definition>
```

例：

```text
/start-task @prompts/definitions/tasks/recommendation-product-list/design.yaml
/work-issue @prompts/definitions/tasks/recommendation-product-list/implementation.yaml
/review-pr @prompts/definitions/reviews/recommendation-product-list/pr-review.yaml
```

| 要素            | 役割                                                     |
| --------------- | -------------------------------------------------------- |
| Command         | AIに実行させる操作・手順を指定する                       |
| Task Definition | 作業対象、入力資料、出力先、完了条件、確認観点を指定する |
| Agent           | 実行するAIエージェントの役割を指定する                   |
| Rules           | AIが従う共通ルールを指定する                             |

---

## 4. 基本方針

| 方針                                 | 内容                                                            |
| ------------------------------------ | --------------------------------------------------------------- |
| YAML形式で管理する                   | 人間・AI・scriptの双方が扱いやすいため                          |
| 1作業単位 = 1 Definitionを原則とする | Issue / Branch / PR と対応させやすくする                        |
| Issue本文の生成元として使う          | AI主導Issue作成時にIssue本文へ展開する                          |
| Projects同期項目を持つ               | Phase、Priority、Planned Start、Due Date等をIssue本文へ反映する |
| Branch制御項目を持つ                 | type、unit、branch_summary、no_branchを定義する                 |
| 入力・出力・完了条件を明示する       | AIの作業範囲を固定する                                          |
| 並列作業制御項目を持つ               | depends_on、exclusive_files、conflict_risk等を定義する          |
| 通常ログを保存しすぎない             | operation_loggingでログ粒度を制御する                           |
| secretを含めない                     | APIキー、トークン、認証情報は記載禁止とする                     |

---

## 5. 配置場所

Task Definitionは以下に配置する。

```text
prompts/definitions/
```

推奨構成は以下とする。

```text
prompts/definitions/
├─ _schemas/
├─ _examples/
├─ epics/
├─ tasks/
├─ reviews/
└─ cross-cutting/
```

| パス             | 役割                                                                           |
| ---------------- | ------------------------------------------------------------------------------ |
| `_schemas/`      | Task DefinitionのJSON Schema等を配置する                                       |
| `_examples/`     | 記述例を配置する                                                               |
| `epics/`         | Epic Issue作成用Definitionを配置する                                           |
| `tasks/`         | Task Issue作成・作業実施用Definitionを配置する                                 |
| `reviews/`       | PRレビュー用Definitionを配置する                                               |
| `cross-cutting/` | OpenAPI / Orval / generated / GitHub Actions等の横断Task用Definitionを配置する |

---

## 6. 識別子単位の配置

通常の機能開発では、**成果物識別子**に対応するディレクトリスラッグ（kebab-case）単位で Definition をまとめる（[成果物一覧×Task Definition化方針書](./成果物一覧×Task%20Definition化方針書.md) §3.5、[Issue運用ルール](../プロジェクト管理/Issue運用ルール.md) §4.1）。

```text
prompts/definitions/
├─ epics/
│  └─ scr-002-recommendation-input/
│     └─ epic.yaml
│
├─ tasks/
│  ├─ scr-002-recommendation-input/
│  │  └─ screen-spec.yaml
│  └─ api-int-002-reco-recommendation-run/
│     └─ api-spec.yaml
│
└─ reviews/
   └─ scr-002-recommendation-input/
      └─ pr-review.yaml
```

| 単位 | 例 |
| ---- | --- |
| ディレクトリスラッグ | `scr-002-recommendation-input` |
| Epic Definition | `epics/scr-002-recommendation-input/epic.yaml` |
| 画面仕様 Task Definition | `tasks/scr-002-recommendation-input/screen-spec.yaml` |
| API仕様 Task Definition | `tasks/api-int-002-reco-recommendation-run/api-spec.yaml` |
| レビュー Definition | `reviews/scr-002-recommendation-input/pr-review.yaml` |
| 記入例（Epic / Task / Review） | `prompts/definitions/_examples/*.yaml` |

---

## 7. Definition種別

Definition 種別は `definition_type` で表す（詳細は §12）。ファイル配置と Command の対応は以下とする。

| `definition_type` | 用途 | 主なCommand |
| ----------------- | ---- | ----------- |
| `epic` | 親Epic Issueを作成する | `/start-epic` |
| `task` | 子Task Issueを作成・実行する | `/start-task`, `/work-issue` |
| `review` | PRをAIレビューする | `/review-pr` |
| `fix` | レビュー指摘に対応する | `/fix-review-comments` |
| `contract` | OpenAPI / Orval / generated等の横断契約変更を扱う | `/create-contract-task` |
| `support` | 調査、影響分析、サマリ作成を行う | `/summarize-work` |

---

## 8. 命名規則

Task Definitionファイルは、作業の意味が分かるkebab-caseで命名する。

```text
<task-role>.yaml
```

例：

```text
epic.yaml
screen-spec.yaml
api-spec.yaml
batch-spec.yaml
pr-review.yaml
review-fix.yaml
contract-task.yaml
```

ディレクトリ名には **識別子スラッグ**（例: `scr-002-recommendation-input`）を使用する。ファイル名は作業種別を表す。

```text
prompts/definitions/tasks/<識別子スラッグ>/<作業種別>.yaml
```

例：

```text
prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml
prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml
```

---

## 9. 標準構造

Task Definition の**正本構造**は **§9.1 実運用YAML** とする。

`prompts/definitions/_schemas/task-definition.schema.md` は本節の検証・補足定義である。記入例は `prompts/definitions/_examples/task-definition.example.yaml`、実運用例は `prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml` を参照する。

### 9.0 旧形式（非推奨・新規作成禁止）

以下の `version` / `kind` / `identity` / `github` ネスト形式は**廃止予定**である。既存資料の読み取り専用として残すが、新規 Definition では使用しない。

```yaml
# 非推奨: version / kind / identity / github 形式
version: "1.0"
kind: "task"
identity: { task_key: "", work_mode: "ai-agent" }
github: { issue: {}, project: {}, branch: {} }
```

旧形式と実運用形式の主な対応は以下とする。

| 旧形式 | 実運用形式（§9.1） |
| ------ | ------------------ |
| `version` | `schema_version` |
| `kind` | `definition_type` |
| `identity.task_key` | `task.id` |
| `identity.title` / `summary` | `task.title` / `task.summary` |
| `identity.work_mode` | トップレベル `work_mode` |
| `github.issue.*` | `issue` + `parent` |
| `github.project.*` | `project.fields.*` |
| `github.branch.*` | `branch` |
| `command` | `commands` |
| `scope.in_scope` / `out_of_scope` | `scope` / `out_of_scope` |
| `inputs` / `outputs` | `input` / `output` |
| `review_points` | `review.review_points` |
| `operation.operation_logging` | `operation_logging` |

---

### 9.1 実運用YAML（正本）

Task / Epic / Review / Contract の共通骨格は以下とする（種別ごとにルート識別子 `task` / `review` / `contract` 等を置き換える）。

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

`Estimate`（見積）は Projects 管理対象外とし、Definition に記載しない。

---

## 10. 必須項目

実運用形式（§9.1）の必須項目は以下とする。詳細は `prompts/definitions/_schemas/task-definition.schema.md` §5 も参照する。

| 項目 | 必須 | 説明 |
| ---- | ---- | ---- |
| `schema_version` | 必須 | Schema version |
| `definition_type` | 必須 | Definition種別（§12） |
| `task.id` / `task.title` | 必須 | Task識別子・タイトル |
| `work_mode` | 必須 | `human-led` または `ai-agent`（§17.1） |
| `commands.primary` | 必須 | 主Command |
| `agent.primary` | 必須 | 主担当Agent（§23） |
| `background` / `objective` | 必須 | 背景・目的 |
| `scope` / `out_of_scope` | 必須 | 作業範囲・対象外 |
| `input.docs` | 必須 | 参照正本docs |
| `deliverables` | 必須 | 成果物一覧 |
| `acceptance_criteria` | 必須 | 完了条件 |
| `branch` | 必須 | Branch方針（§21） |
| `project.project_name` | 必須 | Project名 |
| `project.fields.phase` 等 | 必須 | Projects同期項目（§18） |
| `issue.unit` / `type` / `area` | 必須 | Issue同期分類（§14） |
| `parent.epic_issue_number` | 識別子付き Task では必須 | 親 Epic Issue 番号。識別子 prefix が `task.title` と一致すること（§15.0） |
| `dependencies` | 必須 | 依存関係 |
| `dependencies.epics` | 識別子付き Task では必須 | 依存 Epic Issue 番号配列。空配列も明示する（成果物化方針書 §3.5.3） |
| `parallel_control` | 必須 | 並列作業制御 |
| `parallel_control.exclusive_files` | 識別子付き Task では推奨 | 親 Epic の `epic_scope.allowed_paths` 内に収まること |
| `test_policy` | 必須 | テスト方針 |
| `review.*` | 必須 | レビュー要否・観点 |
| `operation_logging.level` | 必須 | AIログ粒度（§35） |
| `human_decision_points` | 必須 | 人間判断事項 |
| `stop_conditions` | 必須 | 停止条件 |

**Epic Definition の追加必須項目**（schema 詳細は `prompts/definitions/_schemas/epic-definition.schema.md` §5）:

| 項目 | 必須 | 説明 |
| ---- | ---- | ---- |
| `epic_scope.artifact_id` | 識別子付き Epic では必須 | 正本一覧（API一覧 / 画面一覧 / バッチ処理一覧 / モジュール一覧 / Recoモジュール一覧）の識別子 |
| `epic_scope.allowed_paths` | 必須 | 配下 Task が触ってよいファイル境界（glob 配列）。空配列禁止 |
| `dependencies.epics` | API-PUB / API-INT / SCR Epic では必須 | 依存 Epic Issue 番号配列（成果物化方針書 §3.5.3） |

---

## 11. `schema_version`

`schema_version` は Task Definition の schema version を表す。

```yaml
schema_version: "1.0"
```

| 値 | 意味 |
| --- | ---- |
| `1.0` | 実運用形式の初期標準版 |

schema 変更時は後方互換性を考慮して更新する。旧キー `version` は使用しない。

---

## 12. `definition_type`

`definition_type` は Definition の種別を表す（旧 `kind` に相当）。

```yaml
definition_type: "task"
```

| 値 | 用途 | 主なCommand |
| --- | ---- | ----------- |
| `epic` | 親Epic Issue | `/start-epic` |
| `task` | 子Task Issue・実行 | `/start-task`, `/work-issue` |
| `review` | PRのAIレビュー | `/review-pr` |
| `fix` | レビュー指摘対応 | `/fix-review-comments` |
| `contract` | OpenAPI / Orval / generated | `/create-contract-task` |
| `support` | 調査・影響分析 | `/summarize-work` |

Task Definition ファイルでは原則 `task` 固定とする。Epic / Review / Contract は各 Definition のルートキー（`task` / `review` / `contract`）と組み合わせて識別する。

---

## 13. `task`

`task` は Definition 自体を識別する情報である（旧 `identity` に相当）。

```yaml
task:
  id: "task-scr-002-recommendation-input-screen-spec"
  title: "SCR-002:レコメンド条件入力画面仕様書作成"
  summary: "SCR-002（レコメンド条件入力画面）の画面仕様書を作成する"
```

| 項目 | 説明 |
| ---- | ---- |
| `id` | Definition 単位の一意キー（kebab-case 推奨） |
| `title` | 作業タイトル（`[Task]` プレフィックスは含めない。§15） |
| `summary` | 作業概要 |

工程・種別・優先度は `project.fields` / `issue` で同期する。`work_mode` はトップレベルに記載する（§17.1）。

---

## 14. `issue`（Issue同期項目）

§9.1 実運用YAMLでは、Issue作成・Issue本文の同期分類・GitHub Label 導出に `issue` ブロックを用いる。

```yaml
issue:
  unit: "task"
  type: "docs"
  area: "web"
```

| 項目    | 説明                                                                 |
| ------- | -------------------------------------------------------------------- |
| `unit`  | `epic` または `task`                                                 |
| `type`  | Branch type / 作業種別（`feature`, `docs` 等）                       |
| `area`  | 対象領域（`web`, `api`, `docs` 等）                                  |

- Issue本文（`task-issue.md` §12）には `unit` / `type` / `area` のみ記載する。
- GitHub Label（`unit: *`, `type: *`, `area: *`, `priority: *`）は **Issue本文に列挙しない**。
- `/start-task` が導出してチャットに出力する Label は `issue.*` と `project.fields.priority` の 4 種のみ。`ai-agent` / `human-led` は出力しない。
- `ai-agent` / `human-led` は、人間が `.github/ISSUE_TEMPLATE/base.yml` から Issue 作成した場合に workflow が「作業主体」から同期する（AI 生成 Issue 本文 `task-issue.md` の対象外）。
- **`labels` 配列は §9.1 実運用YAMLでは使用しない**（トップレベルにも `issue` 配下にも記載しない）。

GitHub Label は、Definition 作成時に `/start-task` 等が `issue.unit` / `issue.type` / `issue.area` および `project.fields.priority` から導出する。付与する Label は次の 4 種のみ（スペースあり形式: `unit: task` 等）。

| 分類 | Definition 上の入力 | 導出される Label 例 |
| ---- | ------------------- | ------------------- |
| unit | `issue.unit` | `unit: epic`, `unit: task` |
| type | `issue.type` | `type: feature`, `type: docs`, `type: test`, `type: chore`, `type: fix`, `type: refactor`, `type: hotfix`, `type: spike` |
| area | `issue.area` | `area: web`, `area: api`, `area: reco`, `area: batch`, `area: docs`, `area: db`, `area: infra`, `area: project` |
| priority | `project.fields.priority` | `priority: high`, `priority: medium`, `priority: low` |

親Epic・Branch・`no_branch` は `parent` / `branch` ブロックで定義する（§9.1）。

### 14.1 `parent`

```yaml
parent:
  epic_issue: "[Epic]レコメンド実行API"
  epic_issue_number: "#300"
  epic_branch: "feature/epic-300-recommendation-run-api"
```

| 項目                | 説明                                                                 |
| ------------------- | -------------------------------------------------------------------- |
| `epic_issue`        | 親Epic Issue タイトル（Issue本文表示・タイトル検索用）               |
| `epic_issue_number` | 親Epic Issue 番号の**参照配置値**（例: `#300`）。Sub-issue 紐づけ・`gh issue view` の入力。試作時は未発行番号のプレースホルダでもよい |
| `epic_branch`       | Task Branch の base / PR target                                      |

**配置値と実在確認**

- `epic_issue_number` に書いた `#300` は、Definition 上の**配置値**である。これだけをもって「#300 が未存在」とは言わない。
- `/start-task` §5.1 では、配置値に対する **GitHub 実在確認**を行い、結果を `存在` / `未検出` / `未確認` で報告する。
- 実在確認が `未検出` のときの対応（正本: `.cursor/commands/start-task.md` §5.1）:
  1. 親 Epic Issue を新規作成し、**実 Issue 番号**を `epic_issue_number` に反映する。
  2. 既存の親 Epic がある場合は、**実 Issue 番号**へ `parent` を更新する。
  3. 反映後に `/start-task` を再実行する。

親Epic未作成時に Branch 作成前に必ず止めたい場合は、任意で `dependencies.issues` に親Epic番号を入れ `blocking: true` とできる（本試作 Task では未使用）。

---

## 15. Issueタイトル規則

Issueタイトルは以下に統一する。`[Epic]` / `[Task]` の直後に**半角スペースを入れない**（プレフィックスと概要を連結する）。

```text
[Epic]<概要>
[Task]<概要>
```

例：

```text
[Epic]API-PUB-002:レコメンド実行
[Task]API-PUB-002:レコメンド実行API仕様書作成
```

Task Definitionでは、`task.title` に概要のみを記載する（`[Task]` プレフィックスは含めない）。`/start-task` では Issueタイトルを `[Task]` + `task.title` とする（**間に半角スペースを入れない**）。同様に Epic Definition では `epic.title`（または `task.title` 相当）に概要のみを記載し、`/start-epic` で `[Epic]` + 概要を連結する。

API-ID・画面ID・Batch ID 等の**成果物識別子**（本節では「モジュール識別子」と同義）を含む Task / Epic では、概要の先頭を識別子とし、**半角コロン `:`** で区切る（コロン前後にスペースを入れない）。全角コロン `：` は使用しない（`grep`・workflow・スクリプト整合のため）。

識別子は、各成果物の**正本一覧**（API一覧、画面一覧、バッチ処理一覧など）の列名どおりの表記を用いる。事業・要件粒度の機能IDや、未整備のモジュールIDを Task タイトル用識別子として新設しない。

```text
[Epic]{識別子}:{概要}
[Task]{識別子}:{概要}
```

種別ごとの詳細は §15.0（Epic タイトル規約）、§15.1（共通命名）、§15.2〜§15.4（API / 画面 / バッチ）を参照する。識別子の正本は `task.title`・成果物パス・Issue/Branch 命名に記載し、Task Definition YAML への専用ブロック（例: `artifact`）は本設計では定義しない。Epic と配下 Task は識別子 prefix（例: `API-PUB-002`）が一致する必要があり、`/start-task` §5 で検証する。

### 15.0 Epic タイトル規約

Epic の粒度・タイトル形式は、[成果物一覧×Task Definition化方針書](./成果物一覧×Task%20Definition化方針書.md) §3.5（Epic 粒度方針）および [Issue運用ルール](../プロジェクト管理/Issue運用ルール.md) §4.1 / §5.1 を正本とする。

| 粒度 | 適用 | Epic タイトル形式 | 例 |
| ---- | ---- | ------------------ | -- |
| 識別子単位（原則） | API-PUB / API-INT / SCR / BATCH / MOD-API / MOD-RECO / MOD-BATCH | `[Epic]{識別子}:{概要}` | `[Epic]MOD-RECO-001:Recommendation Orchestrator` |
| 機能・領域単位（例外） | DevOps / 横断運用 / ID 未整備 | `[Epic]{機能・領域名}` | `[Epic]GitHub Projects自動化` |

Epic Definition では次を必須とする（schema 詳細は `prompts/definitions/_schemas/epic-definition.schema.md` §4）:

- 識別子付き Epic では、`task.title`（または `epic.title`）が `{識別子}:{概要}` 形式である
- `project.fields.phase` は完了ゲートとして原則 `07_開発・単体テスト`（§18・§19）
- `epic_scope.allowed_paths` に配下 Task が触ってよいファイル境界を列挙する
- 依存 Epic がある場合、`dependencies.epics` に **Epic Issue 番号配列**で明示する

`/start-epic` は、識別子が正本一覧（API一覧・画面一覧・バッチ処理一覧・モジュール一覧・Recoモジュール一覧）に存在するかを実在確認し、`未検出` の場合は停止する。配下 Task の `parent.epic_issue` 識別子と Epic 識別子が一致しない場合、`/start-task` も停止する。

### 15.1 識別子付き Task の共通命名（推奨）

識別子付き Task では、層ごとに区切り文字を使い分ける。

| 層 | 区切り | 例 |
| --- | --- | --- |
| Issue / `task.title` | 識別子と概要の間: `:` | `SCR-002:レコメンド条件入力画面仕様書作成` |
| 成果物ファイル | 識別子と名称: `_` | `SCR-002_レコメンド条件入力画面画面仕様書.md` |
| Branch `english-summary` / `task.id` | kebab-case（識別子は小文字化） | `scr-002-recommendation-input-screen-spec` |

| 対象 | 共通形式 |
| --- | --- |
| `task.title` | `{識別子}:{概要}`（`[Task]` プレフィックスは含めない） |
| Issueタイトル | `[Task]{task.title}`（連結・半角スペースなし） |
| `task.id` / workstream ディレクトリ | 英語 kebab-case。識別子を含める場合は小文字化（[Prompts運用ルール](./Prompts運用ルール.md) §6） |

- Branch 名は [ブランチ運用ルール](../プロジェクト管理/ブランチ運用ルール.md) に従う。
- 調査例（識別子を `{ID}` とする）: `rg -F '[Task]{ID}:'` / `gh issue list --search '{ID}: in:title'`

### 15.2 個別API仕様書Taskの命名（推奨）

正本一覧: [API一覧.md](../../05_アプリケーション設計/アプリ/api/API一覧.md) の **API-ID**（例: `API-INT-002`）。

| 対象 | 形式 | 例（API-INT-002） |
| ---- | ---- | ----------------- |
| `task.title` | `{API-ID}:{機能名}API仕様書作成` | `API-INT-002:Reco推薦実行API仕様書作成` |
| Issueタイトル | `[Task]{task.title}` | `[Task]API-INT-002:Reco推薦実行API仕様書作成` |
| 成果物ファイル | `docs/06_実装設計/api/{API-ID}_{機能名}API仕様書.md` | `API-INT-002_Reco推薦実行API仕様書.md` |
| Branch `english-summary` | `{api-id-kebab}-...-api-spec` | `api-int-002-reco-recommendation-run-api-spec` |
| `task.id` | `task-{api-id-kebab}-...` 等 | `task-api-int-002-reco-recommendation-run-api-spec` |
| 親 Epic タイトル | `[Epic]{API-ID}:{機能名}` | `[Epic]API-INT-002:Reco推薦実行` |

- ファイル名の `{API-ID}` は API一覧表記どおり（アンダースコア区切りは機能名との境界のみ）。
- 調査例: `rg -F '[Task]API-INT-002:'` / `gh issue list --search 'API-INT-002: in:title'`
- 試作例: `prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml`
- テンプレート: `prompts/templates/docs/api-contract-spec.md` + `api-implementation-spec.md`（1成果物に統合）
- Contract Gate: [Contract Gate運用設計書](./Contract%20Gate運用設計書.md)（Implementation 開始前の必須条件。schema: `contract_gate` / `implementation_gate`）

### 15.3 画面仕様書Taskの命名（推奨）

正本一覧: [画面一覧.md](../../05_アプリケーション設計/アプリ/web/画面一覧.md) の **画面ID**（例: `SCR-002`）。1画面 = 1 Task（[成果物一覧×Task Definition化方針書](./成果物一覧×Task Definition化方針書.md) §3）。

| 対象 | 形式 | 例（SCR-002） |
| ---- | ---- | ------------- |
| `task.title` | `{画面ID}:{概要}` | `SCR-002:レコメンド条件入力画面仕様書作成` |
| Issueタイトル | `[Task]{task.title}` | `[Task]SCR-002:レコメンド条件入力画面仕様書作成` |
| 成果物ファイル | `docs/06_実装設計/web/{画面ID}_{画面名}画面仕様書.md` | `SCR-002_レコメンド条件入力画面画面仕様書.md` |
| Branch `english-summary` | `scr-{nnn}-...-screen-spec` 等 | `scr-002-recommendation-input-screen-spec` |
| `task.id` | `task-scr-002-...` 等 | `task-scr-002-recommendation-input-screen-spec` |
| 親 Epic タイトル | `[Epic]{画面ID}:{画面名}` | `[Epic]SCR-002:レコメンド条件入力画面` |

- `{画面名}` は画面一覧の画面名に合わせる。
- 調査例: `rg -F '[Task]SCR-002:'` / `gh issue list --search 'SCR-002: in:title'`
- 試作例: `prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml`
- テンプレート: `prompts/templates/docs/screen-spec.md`（`{{screen.id}}` と一致）

### 15.4 バッチ仕様書Taskの命名（推奨）

正本一覧: [バッチ処理一覧.md](../../05_アプリケーション設計/アプリ/batch/バッチ処理一覧.md) の **Batch ID**（例: `BATCH-003`）。1バッチ = 1 Task（成果物化方針書 §3）。

| 対象 | 形式 | 例（BATCH-003） |
| ---- | ---- | --------------- |
| `task.title` | `{Batch ID}:{概要}` | `BATCH-003:楽天商品疑似差分取得バッチ仕様書作成` |
| Issueタイトル | `[Task]{task.title}` | `[Task]BATCH-003:楽天商品疑似差分取得バッチ仕様書作成` |
| 成果物ファイル | `docs/06_実装設計/batch/{Batch ID}_{バッチ名}バッチ仕様書.md` | `BATCH-003_楽天商品疑似差分取得バッチ仕様書.md` |
| Branch `english-summary` | `batch-{nnn}-...-batch-spec` 等 | `batch-003-rakuten-item-pseudo-diff-batch-spec` |
| `task.id` | `task-batch-003-...` 等 | `task-batch-003-rakuten-item-pseudo-diff-batch-spec` |
| 親 Epic タイトル | `[Epic]{Batch ID}:{バッチ名}` | `[Epic]BATCH-003:楽天商品疑似差分取得バッチ` |

**Batch ID の正本**

- Task・Issue・成果物ファイル名に用いる Batch ID の正本は **バッチ処理一覧** の `BATCH-*` とする。
- [処理構成定義書.md](../../05_アプリケーション設計/アプリ/処理構成定義書.md) §18.1 の `BT-*`（例: `BT-EXT-001`）は処理構成上の分類IDであり、**Task タイトル・Issue タイトルには使用しない**。`BATCH-*` と `BT-*` の対応表が必要な場合は別 Task で整備する。

- `{バッチ名}` はバッチ処理一覧の Batch名に合わせる。
- 調査例: `rg -F '[Task]BATCH-003:'` / `gh issue list --search 'BATCH-003: in:title'`
- 試作例: `prompts/definitions/tasks/batch-003-rakuten-item-pseudo-diff/batch-spec.yaml`

### 15.5 その他の成果物（Phase2）

以下は ID 体系または一覧正本が未統一のため、本節では詳細命名を固定しない。Task 化時は §15.1 の共通規則に従い、識別子を付ける場合は別途正本一覧を定義してから §15.2〜と同様の節を追加する。

| 成果物種別 | 現状 | Task タイトル識別子 |
| ---------- | ---- | ------------------- |
| GitHub Actions workflow 仕様書 | `docs/06_実装設計/github_actions/` は日本語ファイル名中心 | 識別子なし、または workflow 名を kebab-case で概要に含める |
| テーブル定義書 | テーブル一覧の `テーブル名` 列 | 物理テーブル名 |
| モジュール仕様書 | モジュール一覧 / Recoモジュール一覧の `MOD-API-NNN` / `MOD-RECO-NNN` / `MOD-BATCH-NNN` | **1モジュールID = 1 Epic / 1 Task単位**を原則とし、Task タイトルは `{MOD-ID}:{モジュール名}{作業内容}` とする |

**モジュール識別子 Epic の方針**

- Epic タイトル: `[Epic]{MOD-ID}:{モジュール名}`（例: `[Epic]MOD-RECO-001:Recommendation Orchestrator`）
- `epic_scope.allowed_paths`: 該当モジュールの実装・テスト・仕様書に限定する。`MOD-RECO-NNN` では `apps/reco/**` の該当モジュール範囲を対象とし、エンドポイント層 `apps/reco/src/app/**` は API-INT-NNN Epic 配下とする
- 配下 Task タイトル: `[Task]{MOD-ID}:{モジュール名}{作業内容}`（例: `[Task]MOD-RECO-001:Recommendation Orchestrator仕様書作成`）
- API Epic（API-PUB-NNN / API-INT-NNN）配下 Task が `apps/reco/**` など該当モジュール範囲を触る必要がある場合は、対象 `MOD-*` Epic 配下の Task として切り出し、API Epic の `dependencies.epics` に対象 Epic Issue 番号を追加する

---

## 17. `work_mode` と `no_branch`

`work_mode` はトップレベルに記載する。`no_branch` は `branch.no_branch` に記載する。両者は**標準値どおり一致必須**とする（意図的な例外は `human_decision_points` に理由必須）。

### 17.1 `work_mode`

```yaml
work_mode: "ai-agent"
```

| 値 | 意味 |
| --- | ---- |
| `human-led` | 人間主導タスク |
| `ai-agent` | AI主導タスク |

`work_mode` により、初期 Status、no-branch、Branch 作成タイミング、日付設定方針（§20）が変わる。

### 17.2 `branch.no_branch` 標準値

| `work_mode` | `branch.no_branch` 標準値 | 説明 |
| ----------- | ------------------------: | ---- |
| `human-led` | `true` | 未来着手 Issue が多いため、Issue 作成時は Branch を作成しない |
| `ai-agent` | `false` | Issue 作成後に即時作業へ進むため、Branch を作成する |

**Review Definition の例外:** `/review-pr` のみで Issue を新規作成しない場合は `ai-agent` + `branch.no_branch: true` とし、`human_decision_points` に理由を明記する。

`branch.no_branch` は Issue 本文の no-branch チェックに反映する。GitHub Label `no-branch` は定義しない（[Issue運用ルール](../プロジェクト管理/Issue運用ルール.md) §15.1）。

---

## 18. `project`（Project同期項目）

§9.1 実運用YAMLでは、GitHub Projects へ同期する項目を `project` ブロックで定義する。

Task Definition（子 Task）の例:

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

Epic Definition（識別子単位 Epic）の例:

```yaml
project:
  project_name: "Gift Recommendation Service MVP Cycle 3"
  fields:
    phase: "07_開発・単体テスト"
    status: "Todo"
    priority: "high"
    planned_start: null
    due_date: null
```

| 項目                   | 説明                                                                 |
| ---------------------- | -------------------------------------------------------------------- |
| `project_name`         | Project名                                                            |
| `fields.phase`         | Projects運用ルール §6 正式値。Task は**成果物工程**、識別子単位 Epic は**完了ゲート工程**（原則 `07_開発・単体テスト`）。§19・[Projects運用ルール](../プロジェクト管理/Projects運用ルール.md) §6.1 参照 |
| `fields.status`        | 初期Status（`Todo` 等。`/start-task` 成功時は `In Progress` へ進める意図を出す） |
| `fields.priority`      | 優先度（Label `priority:*` の導出元でもある）                          |
| `fields.planned_start` | 着手予定日                                                           |
| `fields.due_date`      | 期限日                                                               |

- `project` 直下に `status` / `phase` / `priority` を置かない（正本パスは `project.fields.*`）。
- `fields.area` / `fields.owner` は使用しない（対象領域は `issue.area`、担当は Projects Assignees）。
- Status の実行時正本は GitHub Projects。Definition の `fields.status` は初期値および `/start-task` の更新意図の入力とする。

---

## 19. Phase値

`phase` は、最新のプロジェクト工程に合わせて以下から選択する。

```text
00_共通
01_事業構想
02_ドメイン探索
03_ドメイン要件定義
04_ドメインモデル設計
05_アプリケーション設計
06_実装設計
07_開発・単体テスト
08_モジュール結合テスト
09_コンポーネント結合テスト
10_システムテスト
11_非機能テスト
12_レコメンド品質評価テスト
13_受入テスト
14_リリース
15_運用・改善
90_PoC
```

`definition_type: epic` かつ識別子単位 Epic（§15.0）では、`fields.phase` は原則 `07_開発・単体テスト` とする。子 Task は仕様書系で `06_実装設計`、実装・単体テスト系で `07_開発・単体テスト` を個別に指定する。機能・領域単位 Epic（例外）は Epic Definition で完了ゲートを個別指定し、Issue 本文に理由を明記する。

---

## 20. 日付設定ルール

### 20.1 AI主導タスク

AI主導タスクでは、以下を標準とする。

| 項目          | 値                |
| ------------- | ----------------- |
| Planned Start | Issue作成日       |
| Due Date      | Issue作成日 + 2日 |

YAMLでは、以下のプレースホルダを利用する。

```yaml
planned_start: "{{issue_created_date}}"
due_date: "{{issue_created_date+2d}}"
```

### 20.2 人主導タスク

人主導タスクでは、人間が明示的に日付を指定する。

```yaml
planned_start: "2026-05-20"
due_date: "2026-05-25"
```

---

## 21. `branch`

`branch` は Branch 作成に関する情報である（旧 `github.branch` に相当）。

```yaml
branch:
  no_branch: false
  name: "docs/task-<issue-number>-scr-002-recommendation-input-screen-spec"
  base: "feature/epic-301-web-screens"
  target: "feature/epic-301-web-screens"
  worktree_required: false
```

| 項目 | 説明 |
| ---- | ---- |
| `no_branch` | Branch を作成しない場合は `true`（§17.2 と `work_mode` 整合必須） |
| `name` | Branch 名（`<issue-number>` はプレースホルダ可） |
| `base` | Branch 作成元 |
| `target` | PR target |
| `worktree_required` | worktree 必須か |

`no_branch: true` のとき `name` / `base` / `target` は null または空でもよい。

Branch名は以下の規則で生成する（`issue.type` / `issue.unit` / Issue 番号 / `english-summary` から組み立て）。

```text
<type>/<unit>-<issue番号>-<english-summary>
```

例：

```text
docs/task-302-scr-002-recommendation-input-screen-spec
```

---

## 22. Branch base / PR target

| Issue種別 | Branch base   | PR target     |
| --------- | ------------- | ------------- |
| Epic      | `develop`     | `develop`     |
| Task      | 親Epic Branch | 親Epic Branch |

Task Branchからdevelopへ直接PRを作成しない。

Task PRでは `Related to #<Task Issue番号>` をPR本文へ記載し、Issue close / Projects DoneはPR merge時workflowで制御する。

---

## 23. `agent`

`agent` は、作業を担当する AI エージェントを定義する（`.cursor/agents/` の Agent 名に合わせる）。

```yaml
agent:
  primary: "worker-ai"
  support:
    - "orchestrator-ai"
    - "support-ai"
  review:
    - "reviewer-ai"
    - "docs-reviewer-ai"
```

| 項目 | 説明 |
| ---- | ---- |
| `primary` | 主担当 Agent |
| `support` | 補助 Agent |
| `review` | レビュー担当 Agent |

利用可能な Agent 名の例は以下とする（正本は AIエージェント体制・責務定義）。

```text
orchestrator-ai
worker-ai
reviewer-ai
fixer-ai
contract-ai
test-ai
docs-reviewer-ai
support-ai
```

旧形式の `supporters` / `reviewer` / 短縮名（`worker` 等）は使用しない。

---

## 24. `commands`

`commands` は、想定する Command と後続 Command を定義する（旧 `command` に相当）。

```yaml
commands:
  primary: "/start-task"
  allowed:
    - "/start-task"
    - "/work-issue"
    - "/create-pr"
  next:
    success: "/work-issue"
    review_fix: "/fix-review-comments"
    blocked: null
```

| 項目 | 説明 |
| ---- | ---- |
| `primary` | この Definition を起動する主 Command |
| `allowed` | 実行してよい Command 一覧 |
| `next.success` | 正常完了後の推奨 Command |
| `next.review_fix` | レビュー修正時の Command |
| `next.blocked` | ブロック時の Command（なければ `null`） |

---

## 25. `scope` / `out_of_scope`

`scope` と `out_of_scope` は、それぞれトップレベルの配列で作業範囲と対象外を定義する（旧 `scope.in_scope` / `scope.out_of_scope` に相当）。

```yaml
scope:
  - "SCR-002（レコメンド条件入力画面）の画面仕様書を作成する"
  - "表示・入力項目、画面状態、遷移、利用 API を整理する"
out_of_scope:
  - "画面実装"
  - "API実装"
  - "DB設計変更"
```

AI エージェントは `scope` の範囲内で作業する。`out_of_scope` に該当する変更が必要になった場合は、人間へ確認する。

---

## 26. `input`

`input` は、AI が参照すべき入力情報である（旧 `inputs` に相当）。

```yaml
input:
  docs:
    - path: "docs/05_アプリケーション設計/画面一覧.md"
      required: true
      purpose: "画面一覧との整合確認のため"
  templates: []
  files: []
  issues: []
  prs: []
```

| 項目 | 説明 |
| ---- | ---- |
| `docs` | 参照すべき設計書（`path` / `required` / `purpose` 推奨） |
| `templates` | 出力 docs 生成用テンプレート |
| `files` | 参照すべきソースファイル |
| `issues` / `prs` | 関連 Issue / PR |

必須 `input.docs` が存在しない場合、Orchestrator AI は Issue 化前フィードバックを返す。

---

## 27. `output`

`output` は、作成・更新対象である（旧 `outputs` に相当）。

```yaml
output:
  docs:
    - path: "docs/06_実装設計/web/SCR-002_レコメンド条件入力画面画面仕様書.md"
      template: "prompts/templates/docs/screen-spec.md"
  files: []
  tests: []
```

成果物正本は `docs/` に配置する。`generated` ブロックで OpenAPI / Orval 影響の有無を明示する（§33）。

---

## 28. `acceptance_criteria`

`acceptance_criteria` は、作業完了条件である。

```yaml
acceptance_criteria:
  - "指定された画面仕様書が作成されている"
  - "画面項目、画面イベント、入力、出力、エラー表示が整理されている"
  - "既存の画面一覧・画面遷移図と矛盾していない"
  - "Notionに貼り付け可能なMarkdown形式で記載されている"
```

AIレビューでは、acceptance_criteriaを満たしているかを確認する。

---

## 29. `review`

`review` は AI レビュー・人間レビュー時の要否と確認観点である（旧トップレベル `review_points` を `review.review_points` に集約）。

```yaml
review:
  human_review_required: true
  ai_review_required: true
  review_points:
    - "Issueの目的と成果物が一致しているか"
    - "入力docsと矛盾していないか"
  specialist_reviews:
    docs: true
    test: false
    contract: false
    security: false
```

`acceptance_criteria` は完了条件、`review.review_points` は品質確認観点である。作業手順は Command（`/work-issue` 等）と `scope` で足りるため、旧 `execution` ブロックは実運用形式では使用しない。

---

## 31. `parallel_control`

`parallel_control` は、複数AIエージェントの並列作業時の競合を制御するための情報である。

```yaml
parallel_control:
  depends_on: []
  blocks: []
  exclusive_files:
    - "docs/06_実装設計/web/SCR-002_レコメンド条件入力画面画面仕様書.md"
  conflict_risk: "medium"
  generated_impact: false
  contract_impact: false
  db_impact: false
```

| 項目               | 説明                                   |
| ------------------ | -------------------------------------- |
| `depends_on`       | 前提となるTask                         |
| `blocks`           | このTaskが完了するまで待つべき後続Task |
| `exclusive_files`  | 同時編集禁止ファイル                   |
| `conflict_risk`    | 競合リスク                             |
| `generated_impact` | generated差分が発生するか              |
| `contract_impact`  | OpenAPI / Orval等の契約影響があるか    |
| `db_impact`        | DB schema / migration影響があるか      |

---

## 32. `conflict_risk`

`conflict_risk` は以下から選択する。

```text
low
medium
high
```

| 値       | 意味                                                 |
| -------- | ---------------------------------------------------- |
| `low`    | 他Taskとの競合可能性が低い                           |
| `medium` | 同一docs、同一module、関連ファイルの編集可能性がある |
| `high`   | API契約、DB、generated、共通ロジック等に影響する     |

`high` の場合は、Orchestrator AIが作業順序や専用Task化を検討する。

---

## 33. 横断影響フラグ

以下のいずれかが `true` の場合、通常Taskとして進めてよいか慎重に判断する。

```yaml
generated_impact: true
contract_impact: true
db_impact: true
```

| フラグ             | trueの場合の扱い                                |
| ------------------ | ----------------------------------------------- |
| `generated_impact` | Orval等の自動生成物差分が発生する可能性がある   |
| `contract_impact`  | OpenAPI / API仕様変更が発生する可能性がある     |
| `db_impact`        | DB schema / migration変更が発生する可能性がある |

原則として、OpenAPI / Orval / generatedはContract専用Taskで扱う。

---

## 34. `human_decision_points` / `stop_conditions`

`human_decision_points` は人間に確認すべき事項、`stop_conditions` は AI が作業を停止する条件をトップレベル配列で定義する。

Slack 通知要否は Command / Slack通知運用設計書側で制御し、Definition には旧 `operation.slack_notify` を記載しない。

---

## 35. `operation_logging`

`operation_logging` は AI ログの記録粒度を制御する（旧 `operation.operation_logging` に相当）。

```yaml
operation_logging:
  level: "standard"
  ai_logs:
    intake: false
    incidents: false
    cross_cutting: false
    experiments: false
  reason: ""
```

| `level` | 方針 |
| ------- | ---- |
| `minimal` | 原則 ai-logs を作成しない |
| `standard` | 標準（Issue 化前 FB、横断影響、人間判断時のみ ai-logs） |
| `detailed` | 検証・実験向けの詳細記録 |

通常タスクの標準値は `standard` とする。Issue 化後の通常作業ログを毎回 `ai-logs/` に保存しない。

---

## 36. `notes`

`notes` は、AIへの補足指示である。

```yaml
notes:
  - "既存の画面仕様書テンプレートに従うこと"
  - "過剰に詳細化せず、実装設計として必要な粒度に留めること"
```

補足指示は、scopeやacceptance_criteriaと矛盾しない範囲で記載する。

---

## 37. Status制御との関係

Task DefinitionはStatusそのものの正本ではない。

Statusの正本はGitHub Projectsである。

ただし、Task Definitionの内容は、Issue作成・Branch作成・PR作成workflowを通じてStatus遷移に影響する。

| 条件                                         | Status遷移             |
| -------------------------------------------- | ---------------------- |
| 人主導Issue作成、no_branch=true              | `Backlog`              |
| Planned Start到来                            | `Todo`                 |
| no_branch解除、Branch作成                    | `In Progress`          |
| AI主導Issue作成、no_branch=false、Branch作成 | `Todo` → `In Progress` |
| PR作成                                       | `AI Review`            |
| AIレビューOK                                 | `Human Review`         |
| PR merge                                     | `Done`                 |

---

## 38. Issue本文への展開

Task Definitionは、Issue本文の生成元として利用する。

主な対応関係は以下とする。

| Task Definition | Issue本文 |
| --------------- | --------- |
| `task.title`（§15 で `[Task]` 付与） | Issueタイトル |
| `task.summary` | 概要 |
| `project.fields.*` | Project同期項目 |
| `issue.unit` / `type` / `area` | 本文分類（Label は workflow 導出） |
| `branch.no_branch` | no-branchチェック |
| `scope` | 作業範囲 |
| `out_of_scope` | 対象外 |
| `input.*` | 入力資料 |
| `output.*` | 出力対象 |
| `acceptance_criteria` | 完了条件 |
| `review.review_points` | 確認観点 |
| `parallel_control.*` | 並列作業・競合管理 |
| `human_decision_points` | 人間判断事項 |
| `contract_gate.*`（Implementation Task） | `task-issue.md` §8.5 |
| `implementation_gate.*`（Contract Task） | `contract-task-issue.md` §7.5 |

Task Definition → Issue本文 → label同期 → branch workflow の順で制御する。

---

## 39. PR本文への展開

Task Definitionは、PR本文作成時にも利用する。

| Task Definition | PR本文 |
| --------------- | ------ |
| `task.title` | PRタイトル・概要 |
| `parent.epic_issue` / `epic_issue_number` | 関連Epic |
| `output.*` | 作成・変更成果物 |
| `acceptance_criteria` | 完了条件チェック |
| `review.review_points` | レビュー観点 |
| `test_policy.manual_checks` | 実施した確認 |
| `contract_gate.*`（該当時） | `task-pr.md` §8.5 Contract Gate 確認 |
| `implementation_gate.*`（Contract Task） | `contract-pr.md` §13.5 Gate 解放 |
| `parallel_control.*` | 横断影響・競合確認 |
| `human_decision_points` | 人間確認事項 |

Task PRでは、PR本文に以下を記載する。

```text
Related to #<Task Issue番号>
```

Issue close / Projects Done は、PR merge時workflowで制御する。

---

## 40. バリデーションルール

Task Definitionは、作業開始前に以下を検証する。

| チェック | 内容 |
| -------- | ---- |
| `schema_version` | 必須項目が揃っているか（§10） |
| `definition_type` | 利用可能値か（§12） |
| `work_mode` | `human-led` または `ai-agent` か |
| Issueタイトル | `[Epic]` / `[Task]` 形式か（§15、直後スペースなし） |
| `project.fields.phase` | 定義済み工程か（§19） |
| `branch.no_branch` | `work_mode` と矛盾していないか（§17.2） |
| `input.docs` | 指定ファイルが存在するか |
| `output` | 出力先が明確か |
| `branch` | base / target が妥当か（§22） |
| `scope` / `out_of_scope` | 明確か |
| `acceptance_criteria` | 空でないか |
| `exclusive_files` | 並列作業時の競合がないか |
| secret | secret や API キーが含まれていないか |

---

## 41. エラー時の扱い

Task Definitionに不備がある場合、AIエージェントは作業を強行しない。

以下のいずれかに該当する場合は、Issue化前フィードバックを返す。

| 条件                           | 対応                     |
| ------------------------------ | ------------------------ |
| 入力docsが存在しない           | 不足資料として人間へ確認 |
| 出力先が不明                   | 出力先確認               |
| scopeが曖昧                    | 作業範囲確認             |
| acceptance_criteriaが不足      | 完了条件確認             |
| `parent.epic_issue_number` が必要だが未指定 | 親Epic確認 |
| no_branch設定がwork_modeと矛盾 | 設定確認                 |
| contract_impact=true           | Contract Task化を提案    |
| db_impact=true                 | 専用Task化を提案         |
| secretが含まれる               | 作業停止                 |

---

## 42. Epic Definitionサンプル

> **注記（レガシー例）**: 以下は `recommendation-product-list` workstream 単位の**レガシー例**である（`[Epic]Recommendation Product List`）。**新規 Epic** は §15.0 の識別子単位（例: `[Epic]SCR-002:レコメンド条件入力画面`）を採用する。パス `epics/recommendation-product-list/` は移行完了まで参照用として残す。

```yaml
version: "1.0"
kind: "epic"

identity:
  task_key: "recommendation-product-list-epic"
  workstream_key: "recommendation-product-list"
  title: "Recommendation Product List"
  summary: "レコメンド商品一覧画面に関する設計・開発・単体テストを管理するEpic"
  work_mode: "ai-agent"

github:
  issue:
    unit: "epic"
    type: "feature"
    title: "[Epic]Recommendation Product List"
    parent_issue: null
    labels:
      - "unit: epic"
      - "type: feature"
      - "area: web"
      - "priority: high"
    no_branch: false
  project:
    phase: "07_開発・単体テスト"
    priority: "high"
    area: "web"
    estimate: "L"
    planned_start: "{{issue_created_date}}"
    due_date: "{{issue_created_date+2d}}"
  branch:
    create_branch: true
    branch_summary: "recommendation-product-list"
    base: "develop"
    target: "develop"

agent:
  primary: "orchestrator"
  supporters:
    - "support"
  reviewer: "reviewer"

command:
  intended: "/start-epic"
  next:
    - "/start-task"

scope:
  in_scope:
    - "レコメンド商品一覧画面に関する子Taskを管理する"
    - "設計、開発、単体テストの作業単位を整理する"
  out_of_scope:
    - "各子Taskの詳細作業"
    - "本番リリース作業"

inputs:
  docs:
    - "docs/05_アプリケーション設計/画面一覧.md"
    - "docs/05_アプリケーション設計/画面遷移図.md"
  files: []
  issues: []
  prs: []

outputs:
  docs: []
  files: []
  tests: []

acceptance_criteria:
  - "Epic Issueが作成されている"
  - "Epic Branchがdevelopから作成されている"
  - "配下Taskの作業単位が整理されている"

review_points:
  - "Epicの作業範囲が広すぎないか"
  - "子Taskに分割可能な粒度になっているか"

execution:
  steps:
    - "入力資料を確認する"
    - "Epic Issueを作成する"
    - "Epic Branchを作成する"
    - "子Task候補を整理する"
  validation:
    - "Issueタイトルが[Epic]形式であること"
    - "Branch baseがdevelopであること"

parallel_control:
  depends_on: []
  blocks: []
  exclusive_files: []
  conflict_risk: "low"
  generated_impact: false
  contract_impact: false
  db_impact: false

operation:
  operation_logging: "standard"
  slack_notify: true
  human_decision_required: false
  human_decision_points: []

notes:
  - "Epicは作業管理単位であり、成果物そのものではない"
```

---

## 43. Task Definitionサンプル

```yaml
version: "1.0"
kind: "task"

identity:
  task_key: "recommendation-product-list-design"
  workstream_key: "recommendation-product-list"
  title: "レコメンド商品一覧画面仕様書作成"
  summary: "レコメンド商品一覧画面の画面仕様書を作成する"
  work_mode: "ai-agent"

github:
  issue:
    unit: "task"
    type: "docs"
    title: "[Task]レコメンド商品一覧画面仕様書作成"
    parent_issue: 101
    labels:
      - "unit: task"
      - "type: docs"
      - "area: web"
      - "priority: high"
    no_branch: false
  project:
    phase: "06_実装設計"
    priority: "high"
    area: "web"
    estimate: "M"
    planned_start: "{{issue_created_date}}"
    due_date: "{{issue_created_date+2d}}"
  branch:
    create_branch: true
    branch_summary: "recommendation-product-list-design"
    base: "feature/epic-101-recommendation-product-list"
    target: "feature/epic-101-recommendation-product-list"

agent:
  primary: "worker"
  supporters:
    - "docs-reviewer"
  reviewer: "reviewer"

command:
  intended: "/start-task"
  next:
    - "/work-issue"
    - "/create-pr"
    - "/review-pr"

scope:
  in_scope:
    - "レコメンド商品一覧画面の画面仕様書を作成する"
    - "画面項目、画面イベント、入力、出力、エラー表示を整理する"
    - "既存の画面一覧・画面遷移図との整合を確認する"
  out_of_scope:
    - "画面実装"
    - "API実装"
    - "DB設計変更"

inputs:
  docs:
    - "docs/05_アプリケーション設計/画面一覧.md"
    - "docs/05_アプリケーション設計/画面遷移図.md"
    - "docs/00_共通/設計書テンプレート/画面仕様書テンプレート.md"
  files: []
  issues:
    - 101
  prs: []

outputs:
  docs:
    - "docs/06_実装設計/web/レコメンド商品一覧画面仕様書.md"
  files: []
  tests: []

acceptance_criteria:
  - "画面仕様書が指定パスに作成されている"
  - "画面項目、画面イベント、入力、出力、エラー表示が整理されている"
  - "既存の画面一覧・画面遷移図と矛盾していない"
  - "Markdown形式でNotionに貼り付け可能である"

review_points:
  - "実装者が迷わない粒度で記載されているか"
  - "画面仕様として不足している章がないか"
  - "入力docsとの整合性があるか"
  - "過剰に詳細化されていないか"

execution:
  steps:
    - "input_docsを確認する"
    - "画面仕様書テンプレートを確認する"
    - "画面仕様書を作成する"
    - "関連docsとの整合性を確認する"
  validation:
    - "Markdownとして破綻していないこと"
    - "指定されたoutput_docsに成果物が作成されていること"
    - "参照docsと矛盾していないこと"

parallel_control:
  depends_on:
    - "recommendation-product-list-epic"
  blocks:
    - "recommendation-product-list-implementation"
  exclusive_files:
    - "docs/06_実装設計/web/レコメンド商品一覧画面仕様書.md"
  conflict_risk: "medium"
  generated_impact: false
  contract_impact: false
  db_impact: false

operation:
  operation_logging: "standard"
  slack_notify: true
  human_decision_required: false
  human_decision_points: []

notes:
  - "既存のテンプレートに従って作成すること"
  - "設計判断が必要な不足情報がある場合はIssue化前フィードバックとして返すこと"
```

---

## 44. Review Definitionサンプル

```yaml
version: "1.0"
kind: "review"

identity:
  task_key: "recommendation-product-list-pr-review"
  workstream_key: "recommendation-product-list"
  title: "レコメンド商品一覧画面仕様書 PRレビュー"
  summary: "レコメンド商品一覧画面仕様書作成PRをAIレビューする"
  work_mode: "ai-agent"

github:
  issue:
    unit: "task"
    type: "docs"
    title: "[Task]レコメンド商品一覧画面仕様書 PRレビュー"
    parent_issue: 101
    labels:
      - "unit: task"
      - "type: docs"
      - "area: web"
      - "priority: high"
    no_branch: true
  project:
    phase: "06_実装設計"
    priority: "high"
    area: "web"
    estimate: "S"
    planned_start: "{{issue_created_date}}"
    due_date: "{{issue_created_date+2d}}"
  branch:
    create_branch: false
    branch_summary: "recommendation-product-list-pr-review"
    base: ""
    target: ""

agent:
  primary: "reviewer"
  supporters:
    - "docs-reviewer"
  reviewer: "human"

command:
  intended: "/review-pr"
  next:
    - "/fix-review-comments"

scope:
  in_scope:
    - "PR差分を確認する"
    - "Issue、Task Definition、成果物、完了条件、確認観点の整合を確認する"
    - "Human Reviewへ進めてよいか判断材料を作成する"
  out_of_scope:
    - "PR merge"
    - "人間レビューの代替"
    - "大幅な仕様変更"

inputs:
  docs:
    - "docs/06_実装設計/web/レコメンド商品一覧画面仕様書.md"
  files: []
  issues:
    - 111
  prs:
    - 123

outputs:
  docs: []
  files: []
  tests: []

acceptance_criteria:
  - "PRにAIレビュー結果が記録されている"
  - "修正要否が明確である"
  - "Human Reviewへ進めてよいか判断できる"

review_points:
  - "Issueの目的とPR差分が一致しているか"
  - "Task Definitionの完了条件を満たしているか"
  - "成果物がテンプレートに準拠しているか"
  - "既存docsと矛盾していないか"
  - "前段成果物の修正が必要な場合、軽微修正か別Task化か判断されているか"

execution:
  steps:
    - "PRを確認する"
    - "IssueとTask Definitionを確認する"
    - "PR diffを確認する"
    - "成果物を確認する"
    - "AIレビューコメントを作成する"
  validation:
    - "レビュー結果分類が明確であること"
    - "指摘がある場合、修正対象が明確であること"

parallel_control:
  depends_on: []
  blocks: []
  exclusive_files: []
  conflict_risk: "low"
  generated_impact: false
  contract_impact: false
  db_impact: false

operation:
  operation_logging: "standard"
  slack_notify: true
  human_decision_required: false
  human_decision_points: []

notes:
  - "AIレビューOKでも、人間レビューは省略しない"
```

---

## 45. Contract Definitionサンプル

```yaml
version: "1.0"
kind: "contract"

identity:
  task_key: "api-contract-orval-update"
  workstream_key: "api-contract-orval"
  title: "OpenAPI / Orval generated更新"
  summary: "OpenAPI変更とOrval生成物の整合確認を行う"
  work_mode: "ai-agent"

github:
  issue:
    unit: "task"
    type: "feature"
    title: "[Task]OpenAPI / Orval generated更新"
    parent_issue: null
    labels:
      - "unit: task"
      - "type: feature"
      - "area: api"
      - "priority: high"
    no_branch: false
  project:
    phase: "06_実装設計"
    priority: "high"
    area: "api"
    estimate: "M"
    planned_start: "{{issue_created_date}}"
    due_date: "{{issue_created_date+2d}}"
  branch:
    create_branch: true
    branch_summary: "api-contract-orval-update"
    base: "develop"
    target: "develop"

agent:
  primary: "contract"
  supporters:
    - "test"
    - "support"
  reviewer: "reviewer"

command:
  intended: "/create-contract-task"
  next:
    - "/work-issue"
    - "/create-pr"
    - "/review-pr"

scope:
  in_scope:
    - "OpenAPI定義の変更影響を確認する"
    - "Orval生成を実行する"
    - "generated差分を確認する"
    - "利用側への影響を整理する"
  out_of_scope:
    - "API仕様の方針変更"
    - "DB schema変更"
    - "無関係な実装修正"

inputs:
  docs:
    - "docs/05_アプリケーション設計/API一覧.md"
    - "docs/05_アプリケーション設計/API設計方針書.md"
  files:
    - "packages/contracts/openapi/public-api.yaml"
    - "packages/contracts/openapi/internal-reco-api.yaml"
    - "orval.config.ts"
  issues: []
  prs: []

outputs:
  docs: []
  files:
    - "packages/contracts/openapi/public-api.yaml"
    - "packages/contracts/openapi/internal-reco-api.yaml"
    - "apps/web/src/generated/api/"
    - "apps/api/src/generated/reco-client/"
  tests: []

acceptance_criteria:
  - "OpenAPI変更の影響範囲が整理されている"
  - "Orval生成が実行されている"
  - "generated差分が期待通りである"
  - "利用側修正の有無が明確である"

review_points:
  - "API契約変更が必要最小限か"
  - "後方互換性に問題がないか"
  - "generatedファイルを手動編集していないか"
  - "他Taskへの影響が整理されているか"

execution:
  steps:
    - "OpenAPI差分を確認する"
    - "Orval生成を実行する"
    - "generated差分を確認する"
    - "利用側影響を整理する"
  validation:
    - "生成コマンドが成功すること"
    - "generated差分がOpenAPI差分と対応していること"

parallel_control:
  depends_on: []
  blocks: []
  exclusive_files:
    - "packages/contracts/openapi/public-api.yaml"
    - "packages/contracts/openapi/internal-reco-api.yaml"
    - "orval.config.ts"
    - "apps/web/src/generated/api/"
    - "apps/api/src/generated/reco-client/"
  conflict_risk: "high"
  generated_impact: true
  contract_impact: true
  db_impact: false

operation:
  operation_logging: "standard"
  slack_notify: true
  human_decision_required: true
  human_decision_points:
    - "Public APIの後方互換性に影響がある場合"
    - "複数Taskへの影響が大きい場合"

notes:
  - "generatedファイルは手動編集しない"
  - "横断影響がある場合はai-logs/cross-cuttingへの記録を検討する"
```

---

## 46. 禁止事項

以下は禁止する。

- Task Definitionなしで大規模AI主導作業を開始すること
- DefinitionにsecretやAPIキーを記載すること
- `out_of_scope` に含まれる作業をAIが勝手に実施すること
- `generated_impact=true` の作業を通常Taskとして無断実行すること
- `contract_impact=true` の作業を人間判断なしに進めること
- `db_impact=true` の作業を専用Task化せずに進めること
- Task Branchからdevelopへ直接PRすること
- 過去のTask Branchを再利用して後続修正を行うこと
- Issue化後の通常作業ログをすべてai-logsへ保存すること
- Slack通知だけで作業記録を完結させること

---

## 47. 関連ドキュメント

| ドキュメント                               | 役割                                         |
| ------------------------------------------ | -------------------------------------------- |
| AIエージェント活用型\_開発運用フロー設計書 | AI主導運用の全体フローを定義                 |
| AIエージェント体制・責務定義               | Agentごとの責務を定義                        |
| Commands設計書                             | Command仕様を定義                            |
| Prompts運用ルール                          | prompts配下の配置・命名を定義                |
| AIレビュー運用設計書                       | AIレビュー観点と結果反映ルールを定義         |
| AIログ運用ルール                           | ai-logsの記録対象・粒度を定義                |
| Slack通知運用設計書                        | Slack通知条件と文面を定義                    |
| worktree運用ルール                         | 並列AI作業時の作業領域分離を定義             |
| Projects運用ルール                         | Status、Phase、予定・実績管理を定義          |
| Issue運用ルール                            | Issue本文、タイトル、ラベル、no-branchを定義 |
| ブランチ運用ルール                         | Branch命名、Branch base、PR targetを定義     |

---

## 48. 一言まとめ

Task Definitionは、AIエージェントに渡す作業依頼条件の正本である。

Commandは「何を実行するか」を定義し、Task Definitionは「何を対象に、どの条件で実行するか」を定義する。

基本形は以下である。

```text
/<Command> @<definition>
```

Task Definitionには、以下を明示する。

```text
作業対象
入力資料
出力先
Issue / Projects同期項目
Branch制御
作業範囲
対象外
完了条件
確認観点
並列作業時の競合制御
operation_logging
Slack通知
人間判断事項
```

AIエージェントはTask Definitionに従って作業するが、最終的な方針判断、品質判断、merge判断、リリース判断は人間が行う。
