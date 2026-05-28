# Epic Definition Schema

## 1. 目的

本ドキュメントは、`prompts/definitions/epics/` 配下に配置する Epic Definition の標準構造を定義する。

Epic Definition は、AI Agent に対して以下を明確に伝えるための親 Epic 作業定義である。

- どの workstream を Epic 単位で管理するか
- Epic Issue / Epic Branch をどう作成するか
- 子 Task の分割方針と PR target（親 Epic Branch）の前提
- develop への統合は Epic PR のみであること

**標準構造の正本**は `docs/00_共通/AIエージェント運用/Task Definition設計書.md` **§9.3（Epic Definition）**・**§10.2（epic 必須項目）** とする。task 型と共通の骨格は **§9.1** を参照する。本 Schema は検証・補足定義である。記入例は `_examples/epic-definition.example.yaml` を参照する。

---

## 2. 対象ファイル

```text
prompts/definitions/epics/<workstream_key>/epic.yaml
```

例：

```text
prompts/definitions/_examples/epic-definition.example.yaml
```

---

## 3. 対応Command

| Command | 利用目的 |
| --- | --- |
| `/start-epic` | Epic Issue 作成、Epic Branch 作成、子 Task 整理 |
| `/start-task` | 配下子 Task の Issue / Branch 作成（Epic 完了後） |
| `/summarize-work` | Epic 進捗・判断依頼の要約 |

---

## 4. 基本形式

```yaml
schema_version: "1.0"
definition_type: "epic"

epic:
  id: ""
  title: ""
  summary: ""

work_mode: "ai-agent"

commands:
  primary: "/start-epic"
  allowed: []
  next: {}

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

deliverables: []
acceptance_criteria: []

branch:
  no_branch: false
  name: null
  base: "develop"
  target: "develop"
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
  unit: "epic"
  type: ""
  area: ""

epic_scope:
  artifact_id: ""
  allowed_paths: []
  forbidden_paths: []
  child_task_areas: []

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
  contract_impact: false
  generated_impact: false
  db_impact: false

test_policy:
  required: []
  commands: []
  manual_checks: []
  not_required: []
  skip_reason: {}

review:
  human_review_required: true
  ai_review_required: false
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

Epic では `parent` ブロックは使用しない（親 Epic を持たない）。

---

## 5. 必須項目一覧

Task Definition設計書 **§10.2（epic）** に準拠する。

| 項目 | 必須 | 内容 |
| --- | --- | --- |
| `schema_version` | 必須 | Schema version |
| `definition_type` | 必須 | `epic` 固定 |
| `epic.id` / `epic.title` | 必須 | Epic 識別子・タイトル |
| `work_mode` | 必須 | `human-led` または `ai-agent` |
| `commands.primary` | 必須 | `/start-epic` |
| `agent.primary` | 必須 | 主担当 Agent（例: `orchestrator-ai`） |
| `background` / `objective` | 必須 | 背景・目的 |
| `scope` / `out_of_scope` | 必須 | 作業範囲・対象外 |
| `input.docs` | 必須 | 参照正本 docs |
| `deliverables` | 必須 | Epic Issue / Branch / 子 Task 整理等 |
| `acceptance_criteria` | 必須 | 完了条件 |
| `branch.base` / `branch.target` | 必須 | いずれも `develop` |
| `issue.unit` | 必須 | `epic` 固定 |
| `issue.type` / `issue.area` | 必須 | Issue 同期分類 |
| `project.project_name` | 必須 | Project 名 |
| `project.fields.*` | 必須 | Projects 同期項目 |
| `epic_scope.artifact_id` | 識別子付き Epic では必須 | 正本一覧に存在する識別子（例: `API-PUB-002` / `SCR-002` / `BATCH-003` / `MOD-RECO-001` / `MOD-API-001` / `MOD-BATCH-001`）。機能・領域単位 Epic では `""` 可 |
| `epic_scope.allowed_paths` | 必須 | 配下 Task が触ってよいファイル境界（glob 配列）。空配列禁止（成果物化方針書 §3.5.2） |
| `epic_scope.forbidden_paths` | 任意 | `allowed_paths` 配下から個別除外する path（例: API-INT Epic で `apps/reco/src/modules/**` を除外） |
| `epic_scope.child_task_areas` | 任意 | 想定される子 Task の作業区分（例: `["api-spec", "openapi", "implementation", "unit-test"]`） |
| `dependencies` | 必須 | 依存関係。`dependencies.epics`（依存 Epic Issue 番号配列）を含む |
| `dependencies.epics` | API-PUB / API-INT / SCR Epic では必須 | 依存 Epic Issue 番号配列。空配列も明示する（成果物化方針書 §3.5.3） |
| `parallel_control` | 必須 | 並列作業制御 |
| `test_policy` | 必須 | Epic 向け検証（manual_checks 可） |
| `review.*` | 必須 | レビュー要否・観点 |
| `operation_logging.level` | 必須 | AI ログ粒度 |
| `human_decision_points` | 必須 | 人間判断事項 |
| `stop_conditions` | 必須 | 停止条件 |

---

## 6. 項目定義（Epic 固有）

### 6.1 `definition_type`

```yaml
definition_type: "epic"
```

| 項目 | 内容 |
| --- | --- |
| 許容値 | `epic` のみ |

---

### 6.2 `epic`

```yaml
epic:
  id: "epic-scr-002-recommendation-input"
  title: "SCR-002 レコメンド条件入力画面"
  summary: "設計・開発・単体テストを管理するEpic"
```

| 項目 | 説明 |
| --- | --- |
| `id` | kebab-case 推奨。workstream と対応 |
| `title` | `[Epic]` プレフィックスは含めない（§15） |
| `summary` | Epic 概要 |

---

### 6.3 `branch`（Epic）

| 項目 | Epic での値 |
| --- | --- |
| `base` | `develop` 固定 |
| `target` | `develop` 固定（Epic PR の target） |
| `no_branch` | `ai-agent` では通常 `false` |

Task Branch の base は親 Epic Branch である。Task PR を `develop` に直接向けない（ブランチ運用ルール）。

---

### 6.4 `issue`（Epic）

```yaml
issue:
  unit: "epic"
  type: "feature"
  area: "web"
```

| 項目 | 説明 |
| --- | --- |
| `unit` | `epic` 固定 |
| `type` | Branch type 相当（`feature` 等） |
| `area` | 対象領域 |

`labels` 配列は Definition に記載しない（設計書 §14。Label は `issue.*` と `project.fields.priority` から導出）。

---

### 6.4.1 `project.fields`（Epic）

| 項目 | 識別子単位 Epic | 機能・領域単位 Epic（例外） |
| ---- | --------------- | --------------------------- |
| `fields.phase` | 原則 `07_開発・単体テスト`（完了ゲート） | Epic Definition で指定。Issue 本文に理由を明記 |
| Issue 本文 Milestone（`/start-epic`） | 原則 `開発・単体テスト工程完了` | Definition / 対象領域に応じて指定 |

Epic の `Phase` は「配下の唯一の docs 工程」ではない。`06_実装設計` の仕様書と `07_開発・単体テスト` の実装は**子 Task の `project.fields.phase`** で管理する（[Projects運用ルール](../../../docs/00_共通/プロジェクト管理/Projects運用ルール.md) §6.1）。

`child_task_areas` と子 Task の推奨 Phase の対応例:

| `child_task_areas` | 子 Task の推奨 `fields.phase` |
| ------------------ | --------------------------- |
| `api-spec`, `module-spec`, `screen-spec`, `batch-spec` | `06_実装設計` |
| `implementation`, `api-client`, `unit-test` | `07_開発・単体テスト` |
| `openapi` | Contract Task として分離する場合は別途。それ以外は `06_実装設計` 寄り |

---

### 6.5 `epic_scope`

`epic_scope` は、Epic 配下 Task が触ってよい**ファイル境界の宣言**である。AI 自動フローでの scope 越境を防ぐガードレールとして、`/start-task` の事前検査および `/review-pr` の差分検査で参照される（成果物化方針書 §3.5、[`.cursor/commands/start-task.md`](../../../.cursor/commands/start-task.md)）。

```yaml
epic_scope:
  artifact_id: "API-PUB-002"
  allowed_paths:
    - "apps/api/src/app/recommendations/**"
    - "apps/web/src/lib/api-client/recommendations/**"
    - "openapi/paths/recommendations/**"
    - "docs/06_実装設計/api/API-PUB-002_*.md"
  forbidden_paths:
    - "apps/reco/**"
  child_task_areas:
    - "api-spec"
    - "openapi"
    - "implementation"
    - "unit-test"
```

| 項目 | 説明 |
| --- | --- |
| `artifact_id` | 正本一覧に存在する成果物識別子。`/start-epic` §5 で実在確認する |
| `allowed_paths` | glob 配列。配下 Task の `output.files` / `parallel_control.exclusive_files` / PR 差分はこの集合内に収まらなければならない |
| `forbidden_paths` | `allowed_paths` 配下から個別除外する path |
| `child_task_areas` | 想定される子 Task の作業区分。Task Definition 作成時の参考情報 |

`MOD-RECO-NNN` 個別モジュール Epic の典型例:

```yaml
epic_scope:
  artifact_id: "MOD-RECO"
  allowed_paths:
    - "apps/reco/**"
    - "docs/06_実装設計/reco/**"
  forbidden_paths:
    - "apps/reco/src/app/**"
```

機能・領域単位 Epic（例外）では `artifact_id: ""` とし、`allowed_paths` は対象領域に応じて記載する（[Issue運用ルール](../../../docs/00_共通/プロジェクト管理/Issue運用ルール.md) §4.1）。

---

### 6.6 `dependencies.epics`

`dependencies.epics` は、本 Epic が依存する**他 Epic の Issue 番号配列**である。`/start-task` は依存 Epic の Status を確認し、`Done` でない場合は配下 Task の `human_decision_points` に理由記載を必須とする。

```yaml
dependencies:
  epics:
    - "#310"
    - "#340"
  issues: []
  prs: []
  tasks: []
  blocking: false
```

API Epic の典型依存:

| Epic 種別 | 典型 `dependencies.epics` |
| --------- | ------------------------ |
| `API-PUB-NNN` | `API-INT-NNN` Epic、必要な `MOD-RECO-NNN` Epic |
| `API-INT-NNN` | 必要な `MOD-RECO-NNN` Epic |
| `SCR-NNN` | `API-PUB-NNN` Epic（画面が呼ぶ API の Epic） |
| `BATCH-NNN` | 原則なし（独立） |
| `MOD-API-NNN` / `MOD-RECO-NNN` / `MOD-BATCH-NNN` | 原則なし |

---

### 6.7 共通項目の参照

以下は task 型と同一の意味を持つ。詳細は `task-definition.schema.md` を参照する。

| ブロック | 設計書 |
| --- | --- |
| `work_mode` | §17 |
| `commands` / `agent` | §19–23 |
| `input` / `output` | §11 以降（task schema §8 相当） |
| `project` | §18 |
| `parallel_control` | §31 |
| `operation_logging` | §35 |

旧キー（`version` / `kind` / `identity` / `github`）は §9.2 の対応表を参照し、新規 Epic では使用しない。

---

## 7. バリデーション観点

| チェック | 内容 |
| --- | --- |
| `definition_type` | `epic` か |
| `commands.primary` | `/start-epic` か |
| `branch` | base / target が `develop` か |
| `issue.unit` | `epic` か |
| `parent` | 記載されていないか（Epic は親を持たない） |
| scope | 子 Task の詳細実装を Epic に混在させていないか |
| `epic.title` | 識別子付き Epic では `{識別子}:{概要}` 形式か（Task Definition設計書 §15.0） |
| `epic_scope.artifact_id` | 識別子付き Epic では正本一覧（API一覧 / 画面一覧 / バッチ処理一覧 / モジュール一覧 / Recoモジュール一覧）に存在するか |
| `epic_scope.allowed_paths` | 空配列でないか。glob として妥当か |
| `dependencies.epics` | API-PUB / API-INT / SCR Epic で記載されているか。配列内の Issue 番号が実在するか |
| `project.fields.phase` | 識別子単位 Epic では原則 `07_開発・単体テスト` か（完了ゲート）。`06_実装設計` のみは不整合 |
| secret | secret が含まれていないか |

Prompts運用ルール §29 も参照する。
