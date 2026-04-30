# Issue運用ルール

## Isuue運用方針

- リポジトリ運用の起点をIssueとする。
- タスクの進捗・スケジュール・優先度管理はすべてProjectsで行う。
  - Issueは作業内容・背景・完了条件・議論の記録に専念する。
- MVP初期では単一のAIエージェント利用の想定だが、将来的にはマルチエージェント（SubAgents）を用いて、業務責任範囲ごとに自立的に活動できるAI駆動開発スキームを目指す。
  - Issueや紐づくbranch作成などもAIエージェントが自律的に実行できる環境及び設定の検討に繋げることを意識すること。

- `Issueの管理レイヤーは下記の通り。`
  - 機能単位で親Issue（Epic）を作成する
  - タスク（Issue）は必ずいずれかの親Issueに属する
  - 成果物単位でSub-issueに分解する

- Issueの状態はProjectsのStatusで一元管理する  
  IssueのOpen/Closeは以下と連動する
  - Open = Backlog / Ready / Doing / Blocked / Review
  - Close = Done

### 作成原則

- すべての作業はIssue起点
- 成果物一覧から生成
- 1 Issue = 1 責務

### Titleルール

```text
[<UNIT>:<AREA>]<概要>
```

#### 例

```text
[EPIC:API] レコメンド取得API
[TASK:API] レコメンド取得API設計
[EPIC:WEB] 検索画面UI
[TASK:WEB] 検索画面UI設計
```

---

## Issue本文記載方針

- 以下の項目はProjectsで管理するため、Issue本文には重複して記載しない
  - Status
  - Priority
  - Start Date / Due Date
  - Estimate

- 本文には下記を記載する。
  - 目的
  - 背景・理由
  - 成果物
    - 対象ファイル・対象ドキュメント・対象機能を列挙する
  - 参照すべきdocs
    - 作業前に参照すべき正本docsを列挙する
  - 完了条件
  - 確認観点
- 詳細はIssueテンプレート定義ファイルを参照すること

## Issueフィールド定義

| フィールド    | 概要                               | 利用有無   | 利用ルール                                                                                                                                                                                                  | 凡例                                    |
| ------------- | ---------------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| Assignees     | 担当者（実行主体）を設定する       | △（将来◎） | MVP段階では未使用（単一開発のため）。将来的にAIエージェントや人間の役割分担が発生した場合に利用する。                                                                                                       | ryo-chan-k6 / ai-agent-reco             |
| Labels        | Issueの分類タグ                    | ◎          | 固定分類のみ使用（動的に増やさない）。主に「作業種別」「対象領域」など横断的分類に利用。Projectsと役割重複させない。                                                                                        | docs / web / api / reco / batch / infra |
| Projects      | 進捗・優先度・見積などの管理       | ◎（中核）  | Issueは必ずProjectsに紐づける。状態管理（Status）、優先度（Priority）、工数（Estimate）などはすべてProjectsで管理する。                                                                                     | Status: Todo / Doing / Done             |
| Milestone     | リリースやフェーズ単位のゴール管理 | △          | MVP段階では最小限利用（例：基本設計完了）。フェーズ境界の可視化用途に限定。                                                                                                                                 | 実装設計工程完了 / 開発工程完了         |
| Relationships | Issue間の依存関係（親子・関連）    | ◎          | タスクの分解・依存関係管理に使用。親Issue（Epic的）とIssueで階層構造を明示。（さらにSub-issueを用いて、タスク（Issue）と成果物（Sub-issue）の階層構造を管理する。）AIエージェントによるタスク分解にも活用。 | Parent: #1 → Child: #2                  |
| Development   | ブランチ・PRとの連携               | ◎          | Issue起点でブランチを作成する（`{type}/{issue-number}-{summary}`）。PRは必ずIssueと紐付ける。完了時はIssueをClose。                                                                                         | feature/12-add-user-auth                |

## Issue Labels定義

- メタデータとて、下記ラベル分類をIssue Labelsに定義し、運用する
- 各ラベル分類の必須制約は下記のとおり
  - unit：必須（1つ）
  - type：必須（1つ）
  - area：必須（1つ以上　※原則1つ）

### 作業単位（unit）

```
unit: epic
unit: task
```

### 作業種別（type）

```
type: feature
type: fix
type: docs
type: refactor
type: chore
type: test
type: hotfix
type: spike
```

### 対象領域（area）

```
area: web
area: api
area: reco
area: batch
area: db
area: docs
area: infra
area: project
```

## Development運用ルール

### ブランチ命名規則

```text
{type}/{issue-number}-{summary}
```

#### 例

- feature/12-add-user-auth
- fix/45-fix-ranking-bug
- docs/78-update-readme

### type一覧

- feature : 機能追加
- fix : バグ修正
- docs : ドキュメント
- refactor : リファクタ
- test : テスト
- chore : 設定・CIなど

### PRルール

- PRは必ずIssueに紐付ける（Fixes #xx）
- PRマージをもってIssueをDoneとする
