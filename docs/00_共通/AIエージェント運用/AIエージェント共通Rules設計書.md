# AIエージェント共通Rules設計書

## 1. 目的

本ドキュメントは、Gift Recommendation Service における `.cursor/rules/` の設計方針を定義する。

本プロジェクトでは、AIエージェントを活用して、設計、開発、テスト、レビュー、Issue作成、PR作成、Slack通知などを行う。

その際、AIエージェントごとに判断基準や出力品質がぶれないよう、共通的に守るべきルールを `.cursor/rules/` に定義する。

本ドキュメントでは、以下を明確にする。

- `.cursor/rules/` の役割
- Ruleの配置場所
- Rule Typeの使い分け
- Ruleファイルの命名規則
- Ruleファイルの標準構成
- 作成対象Rule一覧
- Agent / Commandとの関係
- Task Definitionとの関係
- AIレビュー時の適用方針
- 保守・レビュー観点

---

## 2. 本ドキュメントの位置づけ

本ドキュメントは、AIエージェント共通Rulesの設計正本である。

| 項目                     | 正本ドキュメント                           |
| ------------------------ | ------------------------------------------ |
| AIエージェント運用全体   | AIエージェント活用型\_開発運用フロー設計書 |
| AIエージェント体制・責務 | AIエージェント体制・責務定義               |
| AI Agent定義             | AI Agent定義設計書                         |
| Command仕様              | Commands設計書                             |
| Task Definition構造      | Task Definition設計書                      |
| Prompts運用              | Prompts運用ルール                          |
| AIレビュー運用           | AIレビュー運用設計書                       |
| AIログ運用               | AIログ運用ルール                           |
| Slack通知                | Slack通知運用設計書                        |
| worktree運用             | worktree運用ルール                         |
| Rules設計                | 本ドキュメント                             |
| Rules実体                | `.cursor/rules/*.mdc`                      |

---

## 3. `.cursor/rules/` の役割

`.cursor/rules/` は、Cursor上でAI Agentに継続的に適用する共通ルールを配置する場所である。

本プロジェクトでは、`.cursor/rules/` を以下の用途で使用する。

| 用途           | 内容                                                              |
| -------------- | ----------------------------------------------------------------- |
| 共通品質基準   | docs、コード、テスト、レビューの品質基準を定義する                |
| 運用ルール適用 | Issue、Projects、Branch、PR、worktree等の運用ルールをAIに守らせる |
| 整合性確認     | docs整合性、用語揺れ、設計書・コード整合性を確認させる            |
| 禁止事項明示   | secret混入、scope外作業、generated手動編集などを禁止する          |
| AI Review補強  | AIレビュー時に必ず確認すべき観点を補強する                        |
| 出力平準化     | AI Agentごとの出力粒度・観点のばらつきを抑える                    |

---

## 4. 基本方針

| 方針                                    | 内容                                                      |
| --------------------------------------- | --------------------------------------------------------- |
| Rulesは共通ルールに限定する             | 個別タスク条件はTask Definitionに記載する                 |
| Rulesに成果物本文を書かない             | 成果物正本はdocsに置く                                    |
| RulesにCommand手順を書きすぎない        | 実行手順はCommands設計書と `.cursor/commands/` に寄せる   |
| RulesにAgent責務を重複しない            | Agent責務はAI Agent定義設計書に寄せる                     |
| Always Ruleは最小限にする               | 常時適用Ruleを増やしすぎない                              |
| ファイル種別に応じてAuto Attachedを使う | docs、code、test、OpenAPIなどは対象ファイルで自動適用する |
| AI Review観点は明示する                 | 整合性確認・レビュー観点はRuleにも定義する                |
| 日本語で記載する                        | 人間がレビューしやすく、AIにも意図が伝わりやすい形にする  |
| secretを含めない                        | APIキー、token、認証情報、`.env` 値は記載しない           |

---

## 5. 正本関係

RulesはAI Agentへの共通指示であり、運用・設計の正本ではない。

| 情報                 | 正本                 | `.cursor/rules/` の役割                    |
| -------------------- | -------------------- | ------------------------------------------ |
| プロジェクト運用方針 | docs                 | 要点をAI向けルール化する                   |
| Issue運用            | Issue運用ルール      | AIが守るべき要点を定義する                 |
| Projects運用         | Projects運用ルール   | Status遷移ルールをAI向けに定義する         |
| Branch運用           | ブランチ運用ルール   | Branch命名、base、targetをAI向けに定義する |
| AIレビュー観点       | AIレビュー運用設計書 | レビュー時の必須観点をAI向けに定義する     |
| Task個別条件         | Task Definition      | Rulesには書かない                          |
| Agent責務            | AI Agent定義設計書   | Rulesには重複しない                        |
| Command手順          | Commands設計書       | Rulesには詳細手順を重複しない              |
| 成果物本文           | docs                 | Rulesには成果物本文を書かない              |

---

## 6. 配置場所

AI Agent共通Rulesの実体は、以下に配置する。

```text
.cursor/
└─ rules/
   ├─ project-operation.mdc
   ├─ github-operation.mdc
   ├─ docs-consistency.mdc
   ├─ terminology.mdc
   ├─ architecture-consistency.mdc
   ├─ code-consistency.mdc
   ├─ api-contract.mdc
   ├─ testing.mdc
   ├─ ai-review.mdc
   ├─ security.mdc
   └─ worktree.mdc
```

設計書は以下に配置する。

```text
docs/00_共通/AIエージェント運用/
└─ AIエージェント共通Rules設計書.md
```

---

## 7. Rule Type

本プロジェクトでは、Ruleを以下の4種類で設計する。

| Rule Type         | 用途                                      | 適用例                          |
| ----------------- | ----------------------------------------- | ------------------------------- |
| `Always`          | 常に守るべき最小限の共通ルール            | secret禁止、正本尊重、scope遵守 |
| `Auto Attached`   | 対象ファイルに応じて自動適用するルール    | docs、TypeScript、OpenAPI、test |
| `Agent Requested` | AIが必要に応じて参照するルール            | incident対応、横断影響判断      |
| `Manual`          | 人間またはCommandが明示的に参照するルール | 特殊レビュー、運用改善、検証    |

---

## 8. Rule Typeの使い分け

| 判断基準                                   | 推奨Rule Type                               |
| ------------------------------------------ | ------------------------------------------- |
| すべてのAI作業で必ず守る                   | `Always`                                    |
| 特定ファイル編集時に必要                   | `Auto Attached`                             |
| 特定状況でAIが自律的に参照すればよい       | `Agent Requested`                           |
| 人間が明示したときだけ使う                 | `Manual`                                    |
| 適用範囲が広すぎて常時適用すると邪魔になる | `Agent Requested` または `Manual`           |
| レビュー時だけ使う                         | `Agent Requested` またはCommand側で明示参照 |

Always Ruleは増やしすぎない。  
常時適用Ruleが増えると、AI Agentの文脈が重くなり、タスク固有の判断を阻害する可能性がある。

---

## 9. Ruleファイル命名規則

Ruleファイル名は、英語kebab-caseとする。

```text
<rule-name>.mdc
```

例：

```text
project-operation.mdc
github-operation.mdc
docs-consistency.mdc
architecture-consistency.mdc
code-consistency.mdc
```

命名では、以下を守る。

| ルール           | 内容                                       |
| ---------------- | ------------------------------------------ |
| 英語             | ファイル名は英語で記載する                 |
| kebab-case       | 単語区切りは `-` を使用する                |
| 役割が分かる名前 | `common.mdc` のような曖昧名は避ける        |
| 対象領域を含める | docs、code、api、testing等の領域を明示する |
| 拡張子は `.mdc`  | Cursor Rules実体として扱う                 |

---

## 10. Ruleファイル標準構成

Ruleファイルは、以下の構成を標準とする。

```markdown
---
description: <このRuleが適用される条件・目的>
globs:
  - "<対象ファイルパターン>"
alwaysApply: false
---

# <Rule名>

## 1. 目的

## 2. 適用対象

## 3. 必須ルール

## 4. 確認観点

## 5. 禁止事項

## 6. 停止条件

## 7. 関連ドキュメント
```

front matterの最終形式は、実装時にCursor上で動作確認する。  
本ドキュメントでは、Rule実体作成時の設計標準として扱う。

---

## 11. front matter標準項目

| 項目          |     必須 | 内容                 |
| ------------- | -------: | -------------------- |
| `description` |     必須 | Ruleの目的・適用条件 |
| `globs`       | 条件付き | 対象ファイルパターン |
| `alwaysApply` |     必須 | 常時適用するか       |

### 11.1 Always Rule例

```markdown
---
description: "すべてのAI Agentが常に守るプロジェクト基本ルール"
globs:
  - "*"
alwaysApply: true
---
```

### 11.2 Auto Attached Rule例

```markdown
---
description: "docs配下のMarkdown成果物を編集・レビューする際に参照するdocs整合性ルール"
globs:
  - "docs/**/*.md"
alwaysApply: false
---
```

### 11.3 Agent Requested Rule例

```markdown
---
description: "AIレビュー時に、PR差分、Issue、Task Definition、docs、コード、テストの整合性を確認するために参照するルール"
globs: []
alwaysApply: false
---
```

---

## 12. 作成対象Rule一覧

| 優先度 | Rule                           | Rule Type       | 目的                                                                           |
| -----: | ------------------------------ | --------------- | ------------------------------------------------------------------------------ |
|      1 | `project-operation.mdc`        | Always          | プロジェクト全体の基本原則を定義する                                           |
|      2 | `github-operation.mdc`         | Agent Requested | Issue / Projects / Branch / PR運用を定義する                                   |
|      3 | `docs-consistency.mdc`         | Auto Attached   | docs整合性、正本関係、配置を確認する                                           |
|      4 | `terminology.mdc`              | Auto Attached   | 用語揺れを防止する                                                             |
|      5 | `architecture-consistency.mdc` | Agent Requested | 方針書・設計書・実装の整合性を確認する                                         |
|      6 | `code-consistency.mdc`         | Auto Attached   | ソースファイル間の責務・型・I/F整合性を確認する                                |
|      7 | `api-contract.mdc`             | Auto Attached   | OpenAPI / Orval / generated整合性を確認する                                    |
|      8 | `testing.mdc`                  | Auto Attached   | テスト観点・テスト結果の妥当性を確認する                                       |
|      9 | `ai-review.mdc`                | Agent Requested | AI Review時の必須観点を定義する                                                |
|     10 | `security.mdc`                 | Always          | secret、権限、危険操作の禁止を定義する                                         |
|     11 | `worktree.mdc`                 | Agent Requested | worktree作業時の安全確認を定義する                                             |
|     12 | `git-commit-message.mdc`       | Agent Requested | AI Agentがcommit messageを作成する際の日本語コミットメッセージルールを定義する |

---

## 13. MVPで先に作成するRule

MVP段階では、最初から全Ruleを作成しなくてもよい。

まずは以下を優先して作成する。

| 優先 | Rule                           | 理由                                                                 |
| ---: | ------------------------------ | -------------------------------------------------------------------- |
|    1 | `project-operation.mdc`        | すべてのAI Agentの基本方針になるため                                 |
|    2 | `github-operation.mdc`         | Issue / Projects / Branch / PR運用の逸脱を防ぐため                   |
|    3 | `docs-consistency.mdc`         | 設計書作成・更新の品質に直結するため                                 |
|    4 | `architecture-consistency.mdc` | 方針書と実装の不整合を防ぐため                                       |
|    5 | `ai-review.mdc`                | AI Reviewの品質を平準化するため                                      |
|    6 | `security.mdc`                 | secret混入や危険操作を防ぐため                                       |
|    7 | `git-commit-message.mdc`       | AI Agentによるcommit作成時に、日本語コミットメッセージを徹底するため |

その後、実装作業が本格化するタイミングで以下を追加する。

| 追加Rule               | 追加タイミング                       |
| ---------------------- | ------------------------------------ |
| `code-consistency.mdc` | 開発・単体テスト開始前               |
| `testing.mdc`          | 単体テスト設計開始前                 |
| `api-contract.mdc`     | OpenAPI / Orval作業開始前            |
| `terminology.mdc`      | docs数が増え、用語揺れが増え始めた時 |
| `worktree.mdc`         | 複数AI Agent並列作業開始前           |

---

## 14. `project-operation.mdc`

### 14.1 目的

プロジェクト全体でAI Agentが守るべき基本原則を定義する。

### 14.2 主な内容

- 正本関係を守る
- Issue / PR / docs / Slack / ai-logsの役割を混同しない
- Task Definitionのscopeを守る
- 人間判断が必要な事項をAIが確定しない
- 作業できない場合は停止し、人間へ確認する
- 出力は日本語を基本とする
- 成果物はNotion貼り付けやMarkdown管理に適した形式にする

### 14.3 適用対象

すべてのAI Agent、すべてのCommand。

### 14.4 Rule Type

`Always`

---

## 15. `github-operation.mdc`

### 15.1 目的

GitHub上のIssue、Projects、Branch、PR運用をAI Agentに守らせる。

### 15.2 主な内容

- Task Issueでは `1 Task Issue = 1 Projects Task = 1 Branch = 1 PR` を原則とする（Epic Issue の Branch / PR 関係はブランチ運用ルール §3 参照）
- Issue本文にProjects同期項目を持たせる
- Projects Statusは `Backlog`, `Todo`, `In Progress`, `AI Review`, `Human Review`, `Done`
- Task Branchは親Epic Branchから作成する
- Task PRは親Epic Branchへ向ける
- Epic PRはdevelopへ向ける
- Task PRで `Closes #<Task Issue番号>` に依存しない
- no-branchはIssue本文のチェックのみで扱う（GitHub Label `no-branch` は定義しない）
- PR merge判断はHumanが行う

### 15.3 適用対象

- `/start-epic`
- `/start-task`
- `/work-issue`
- `/create-pr`
- `/review-pr`
- `/fix-review-comments`
- GitHub関連ファイル変更時

### 15.4 Rule Type

`Agent Requested`

### 15.5 コミットメッセージとの関係

`github-operation.mdc` では、Issue / Projects / Branch / PRを中心としたGitHub運用ルールを定義する。

コミットメッセージの詳細ルールは、専用Ruleである `git-commit-message.mdc` を正とする。

AI Agentがcommitを作成する場合は、`github-operation.mdc` と併せて `git-commit-message.mdc` を参照する。

---

## 16. `git-commit-message.mdc`

### 16.1 目的

AI Agentがcommit messageを作成する際の、日本語コミットメッセージルールを定義する。

本Ruleは、AI Agentによるcommit作成時の標準ルールであり、Cursorエディタ上の `Generate Commit Message` ボタンの挙動を保証するものではない。

人主導運用で `Generate Commit Message` ボタンを使用し、日本語で自動生成されなかった場合は、人間が手動で日本語コミットメッセージへ修正する。

最終的な強制は、`.githooks/commit-msg` により行う。

### 16.2 主な内容

- コミットメッセージは日本語で記載する
- 形式は `<type>: <日本語の変更概要>` を標準とする
- `type` は `docs`, `feat`, `fix`, `test`, `chore`, `refactor` など英語でよい
- `:` 以降の変更概要は日本語必須とする
- 英語のみのコミットメッセージは禁止する
- AI Agentがcommit messageを生成する場合は、本Ruleを参照する
- 人主導運用でCursorの自動生成結果が英語になった場合は、人間が日本語へ修正する

### 16.3 適用対象

- `/work-issue`
- `/fix-review-comments`
- commitを作成するAI Agent作業
- commit messageをAI Agentが提案する作業

### 16.4 Rule Type

`Agent Requested`

### 16.5 コミットメッセージ例

```text
docs: AIエージェント共通Rules設計書を追加
docs: Projects運用ルールを最新化
fix: Issue同期ワークフローのno-branch判定を修正
test: Recommendation APIの単体テストを追加
chore: worktree作成スクリプトの初期設定を追加
```

---

## 17. `docs-consistency.mdc`

### 17.1 目的

docs成果物の整合性、正本関係、配置、章立て、参照関係を確認する。

### 17.2 主な内容

- 関連docsと矛盾しない
- 正本docsを参照する
- 古いチャット内容を正本として扱わない
- ディレクトリ構成定義書に従う
- プロジェクト工程定義と一致させる
- 同じ情報を複数docsに重複記載しすぎない
- 重複する場合は正本を明示して参照する
- Mermaid、表、Markdown構文を確認する

### 17.3 適用対象

```text
docs/**/*.md
```

### 17.4 Rule Type

`Auto Attached`

---

## 18. `terminology.mdc`

### 18.1 目的

用語揺れを防止し、ドメイン用語、機能名、モジュール名、運用用語を統一する。

### 18.2 主な内容

- ドメイン用語の表記統一
- 機能名・モジュール名の表記統一
- Projects Status名の表記統一
- Issue unitの表記統一
- Branch type / unitの表記統一
- `In Progress` などの大文字・スペース表記を統一する
- 日本語名と英語名の対応を崩さない

### 18.3 適用対象

```text
docs/**/*.md
prompts/**/*.md
prompts/**/*.yaml
prompts/**/*.yml
.github/**/*.md
.github/**/*.yml
.github/**/*.yaml
```

### 18.4 Rule Type

`Auto Attached`

---

## 19. `architecture-consistency.mdc`

### 19.1 目的

開発方針書、アーキテクチャ方針、ディレクトリ構成、設計書、ソースコードの整合性を確認する。

### 19.2 主な内容

- 開発方針書と実装が矛盾していないか
- ディレクトリ構成定義とファイル配置が一致しているか
- モジュール責務定義と実装責務が一致しているか
- API設計方針とAPI実装が一致しているか
- DevOps方針とGitHub Actionsが一致しているか
- CI/CD方針とworkflowが一致しているか
- テスト計画書とテスト実装が一致しているか
- out_of_scopeの設計変更を混在させていないか

### 19.3 適用対象

主にAI Review、設計変更、横断影響確認時。

### 19.4 Rule Type

`Agent Requested`

---

## 20. `code-consistency.mdc`

### 20.1 目的

ソースファイル間の整合性、責務分離、型、I/F、依存方向を確認する。

### 20.2 主な内容

- 呼び出し元・呼び出し先のI/Fが一致している
- 型定義と実装が一致している
- null / undefined / emptyの扱いが一致している
- エラー処理方針が一致している
- layer / module / domain / infraの依存方向が逆転していない
- ファイル名、関数名、型名、変数名が既存命名と整合している
- 既存責務に反する実装を混在させていない
- 不要な共通化や過剰抽象化をしていない

### 20.3 適用対象

```text
apps/**/*.ts
apps/**/*.tsx
apps/**/*.js
apps/**/*.jsx
apps/**/*.py
packages/**/*.ts
packages/**/*.tsx
```

### 20.4 Rule Type

`Auto Attached`

---

## 21. `api-contract.mdc`

### 21.1 目的

API仕様、OpenAPI、Orval、generated、API client、利用側実装の整合性を確認する。

### 21.2 主な内容

- API設計書とOpenAPI定義が一致している
- OpenAPI変更とgenerated差分が対応している
- Orval生成物を手動編集していない
- API client利用側に破壊的影響がない
- web / api / reco / batchの利用側影響を確認する
- Contract変更は通常Taskに混在させない
- 必要に応じてContract Task化する
- 横断影響がある場合はcross-cutting logを検討する

### 21.3 適用対象

```text
docs/**/*API*.md
openapi/**/*.yaml
openapi/**/*.yml
apps/**/generated/**
apps/**/api-client/**
orval.config.*
```

### 21.4 Rule Type

`Auto Attached`

---

## 22. `testing.mdc`

### 22.1 目的

テスト観点、テストコード、テスト結果、未実施理由の妥当性を確認する。

### 22.2 主な内容

- 正常系、異常系、境界値を確認する
- 実装とテストが同じ仕様を前提にしている
- テスト名から検証内容が分かる
- 外部依存は適切にmock化する
- CIで実行可能なテストになっている
- テスト未実施の場合は理由をPRに記載する
- Human Review前に必要な検証結果を記録する

### 22.3 適用対象

```text
apps/**/*.test.ts
apps/**/*.spec.ts
apps/**/*.test.tsx
apps/**/*.spec.tsx
apps/**/*.test.py
apps/**/*.spec.py
tests/**
```

### 22.4 Rule Type

`Auto Attached`

---

## 23. `ai-review.mdc`

### 23.1 目的

AI Review時に必ず確認する観点を定義し、Reviewer AIのレビュー品質を平準化する。

### 23.2 主な内容

- Issue目的との整合
- Task Definition完了条件との整合
- Task Definition review_pointsの確認
- docs間整合性
- 用語揺れ確認
- 方針書・設計書との整合
- 設計書・コード整合性
- ソースファイル間整合性
- テスト整合性
- Contract / generated影響
- DB影響
- Branch / PR target整合
- Human Reviewへ進めてよいかの判定

### 23.3 適用対象

- `/review-pr`
- `/fix-review-comments`
- PRレビュー時

### 23.4 Rule Type

`Agent Requested`

---

## 24. `security.mdc`

### 24.1 目的

secret混入、危険操作、権限逸脱を防ぐ。

### 24.2 主な内容

- APIキー、token、password、cookie、session情報を出力しない
- `.env` の値を表示しない
- secretをcommitしない
- main / developへ直接pushしない
- PRをAIだけでmergeしない
- 破壊的操作をHuman承認なしで実行しない
- 個人情報を不要に記録しない
- ai-logs / Slack / PRコメントにsecretを書かない

### 24.3 適用対象

すべてのAI Agent、すべてのCommand。

### 24.4 Rule Type

`Always`

---

## 25. `worktree.mdc`

### 25.1 目的

worktreeを利用した並列AI作業時の安全確認を定義する。

### 25.2 主な内容

- 1 Task Branch = 1 worktreeを原則とする
- 作業開始前に `pwd`, `git branch --show-current`, `git status --short` を確認する
- 複数AI Agentが同じworktreeを同時編集しない
- Task Branchは親Epic Branchから作成する
- PR作成前に親Epic Branchの最新状態を取り込む
- 未コミット差分の由来が不明な場合は作業停止する
- conflictを推測だけで解消しない
- worktreeは正本ではない

### 25.3 適用対象

- `/work-issue`
- `/create-pr`
- `/fix-review-comments`
- 並列AI作業時

### 25.4 Rule Type

`Agent Requested`

---

## 26. Agent別の適用方針

| Agent            | 主に参照するRules                                                                                                                                                              |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Orchestrator AI  | `project-operation`, `github-operation`, `docs-consistency`, `architecture-consistency`, `security`                                                                            |
| Worker AI        | `project-operation`, `github-operation`, `git-commit-message`, `docs-consistency`, `architecture-consistency`, `code-consistency`, `testing`, `security`, `worktree`           |
| Reviewer AI      | `project-operation`, `github-operation`, `docs-consistency`, `terminology`, `architecture-consistency`, `code-consistency`, `api-contract`, `testing`, `ai-review`, `security` |
| Docs Reviewer AI | `docs-consistency`, `terminology`, `project-operation`                                                                                                                         |
| Test AI          | `testing`, `code-consistency`, `architecture-consistency`                                                                                                                      |
| Contract AI      | `api-contract`, `architecture-consistency`, `github-operation`, `security`                                                                                                     |
| Fixer AI         | `project-operation`, `github-operation`, `git-commit-message`, `code-consistency`, `docs-consistency`, `testing`, `worktree`, `security`                                       |
| Support AI       | `project-operation`, `docs-consistency`, `architecture-consistency`                                                                                                            |

---

## 27. Command別の適用方針

| Command                 | 主に適用するRules                                                                                                                                         |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/start-epic` / `/start-task` | `project-operation`, `github-operation`, `docs-consistency`, `security`                                                                                   |
| `/work-issue`           | `project-operation`, `github-operation`, `git-commit-message`, `architecture-consistency`, `code-consistency`, `testing`, `worktree`, `security`          |
| `/create-pr`            | `github-operation`, `ai-review`, `worktree`, `security`                                                                                                   |
| `/review-pr`            | `ai-review`, `docs-consistency`, `terminology`, `architecture-consistency`, `code-consistency`, `api-contract`, `testing`, `github-operation`, `security` |
| `/fix-review-comments`  | `ai-review`, `github-operation`, `git-commit-message`, `code-consistency`, `docs-consistency`, `testing`, `worktree`, `security`                          |
| `/create-contract-task` | `api-contract`, `github-operation`, `architecture-consistency`, `security`                                                                                |
| `/summarize-work`       | `project-operation`, `docs-consistency`                                                                                                                   |

---

## 28. Task Definitionとの関係

Task Definitionには、個別タスク固有の条件を記載する。

Rulesには、タスク横断で共通するルールを記載する。

| 内容                         | 記載先                               |
| ---------------------------- | ------------------------------------ |
| 共通のdocs整合性確認         | `.cursor/rules/docs-consistency.mdc` |
| 対象タスクで参照するdocs     | Task Definition                      |
| 共通のAIレビュー観点         | `.cursor/rules/ai-review.mdc`        |
| 対象タスク固有のレビュー観点 | Task Definition `review_points`      |
| 共通の禁止事項               | `.cursor/rules/security.mdc`         |
| 対象タスクのout_of_scope     | Task Definition                      |
| 共通のBranch / PRルール      | `.cursor/rules/github-operation.mdc` |
| 対象Issue番号・Branch名      | Task Definition / Issue本文          |

---

## 29. AIレビューとの関係

AI Review時は、`ai-review.mdc` を中心に、対象変更に応じたRuleを併用する。

| 変更内容         | 併用Rule                                               |
| ---------------- | ------------------------------------------------------ |
| docs変更         | `docs-consistency.mdc`, `terminology.mdc`              |
| コード変更       | `architecture-consistency.mdc`, `code-consistency.mdc` |
| テスト変更       | `testing.mdc`, `code-consistency.mdc`                  |
| API変更          | `api-contract.mdc`, `architecture-consistency.mdc`     |
| generated変更    | `api-contract.mdc`, `security.mdc`                     |
| GitHub運用変更   | `github-operation.mdc`, `project-operation.mdc`        |
| worktree関連変更 | `worktree.mdc`, `github-operation.mdc`                 |

AI Reviewで必要Ruleの確認ができない場合、Reviewer AIは `approve_for_human_review` を出してはならない。

---

## 30. Rulesに書いてよいこと

Rulesには、以下を書いてよい。

- AI Agentが常に守るべき共通方針
- docs、コード、テスト、レビューの共通確認観点
- 禁止事項
- 停止条件
- 人間へエスカレーションする条件
- 正本関係の要点
- 関連ドキュメントへの参照
- Task Definitionで個別指定すべき項目の案内

---

## 31. Rulesに書かないこと

Rulesには、以下を書かない。

| 書かないもの              | 記載先                       |
| ------------------------- | ---------------------------- |
| 個別タスクの作業条件      | Task Definition              |
| 具体的なIssue本文         | Issue                        |
| 具体的なPR本文            | PR                           |
| 成果物本文                | docs                         |
| Commandの詳細手順         | `.cursor/commands/`          |
| Agentごとの詳細責務       | `.cursor/agents/`            |
| Slack通知テンプレート本文 | `prompts/templates/slack/`   |
| AIログテンプレート本文    | `prompts/templates/ai-logs/` |
| secret / APIキー          | 記載禁止                     |

---

## 32. Rule作成テンプレート

新しいRuleを作成する場合は、以下のテンプレートを使用する。

```markdown
---
description: "<Ruleの目的・適用条件>"
globs:
  - "<対象ファイルパターン>"
alwaysApply: false
---

# <Rule名>

## 1. 目的

## 2. 適用対象

## 3. 必須ルール

## 4. 確認観点

## 5. 禁止事項

## 6. 停止条件

## 7. 人間へ確認する条件

## 8. 関連ドキュメント
```

---

## 33. Rule作成時のチェックリスト

Rule作成時は、以下を確認する。

| チェック | 内容                                                              |
| -------- | ----------------------------------------------------------------- |
| 命名     | ファイル名が英語kebab-caseか                                      |
| 拡張子   | `.mdc` になっているか                                             |
| 目的     | Ruleの目的が明確か                                                |
| 適用範囲 | Alwaysにすべきか、Auto Attachedにすべきか判断されているか         |
| globs    | 対象ファイルパターンが広すぎないか                                |
| 重複     | 他Rule、Agent定義、Command、Task Definitionと重複しすぎていないか |
| 正本関係 | docs正本と矛盾していないか                                        |
| 禁止事項 | 危険操作やsecretに関する禁止事項が必要に応じて含まれているか      |
| 停止条件 | AIが止まるべき条件が明記されているか                              |
| 可読性   | AIと人間の両方が読みやすいか                                      |

---

## 34. Rule変更時のレビュー観点

`.cursor/rules/` を変更するPRでは、以下を確認する。

| 観点     | 内容                                           |
| -------- | ---------------------------------------------- |
| 影響範囲 | どのAgent / Command / ファイル種別に影響するか |
| 適用過多 | Always Ruleが増えすぎていないか                |
| 適用不足 | 必須確認観点がRuleから漏れていないか           |
| 正本整合 | docs側の運用ルールと矛盾していないか           |
| 重複     | 同じルールを複数ファイルに重複記載していないか |
| 粒度     | 1 Ruleが大きくなりすぎていないか               |
| 明確性   | AIが実行可能な指示になっているか               |
| 禁止事項 | 重要な禁止事項が抜けていないか                 |
| secret   | secretや個人情報を含んでいないか               |

---

## 35. Rule変更管理

Rule変更は、Issue / PRで管理する。

| 変更内容     | 扱い                                           |
| ------------ | ---------------------------------------------- |
| Rule新規追加 | AIエージェント運用改善TaskとしてIssue化する    |
| Rule削除     | 影響するAgent / Command / Definitionを確認する |
| Always化     | Human Review必須                               |
| globs変更    | 影響範囲をPRに記載する                         |
| 禁止事項変更 | Human Review必須                               |
| 停止条件変更 | Human Review必須                               |
| 文言修正     | 軽微変更として扱ってよい                       |
| Rule分割     | 影響範囲をPRに記載する                         |

---

## 36. `.cursor/agents/` との関係

`.cursor/agents/` は、Agentごとの責務・権限境界を定義する。

`.cursor/rules/` は、Agent横断で守る共通ルールを定義する。

| 項目         | `.cursor/agents/`         | `.cursor/rules/`       |
| ------------ | ------------------------- | ---------------------- |
| 役割         | 定義する                  | 定義しない             |
| 権限         | 定義する                  | 共通禁止事項のみ定義   |
| 作業範囲     | Agent単位で定義           | 共通ルールとして補助   |
| レビュー観点 | Agentごとの責務として定義 | 具体的な共通観点を定義 |
| 停止条件     | Agentごとの停止条件       | 共通停止条件           |

Agent定義にRules全文を重複記載しない。

---

## 37. `.cursor/commands/` との関係

`.cursor/commands/` は、Commandごとの実行手順を定義する。

`.cursor/rules/` は、Command実行時に守るべき共通ルールを定義する。

| 項目     | `.cursor/commands/` | `.cursor/rules/`       |
| -------- | ------------------- | ---------------------- |
| 実行手順 | 定義する            | 詳細には書かない       |
| 入力確認 | 定義する            | 共通観点を補助する     |
| 出力形式 | 定義する            | 共通品質基準を定義する |
| 禁止事項 | 必要最小限          | 共通禁止事項を定義する |
| 停止条件 | Command固有条件     | 共通停止条件           |

---

## 38. `AGENTS.md` との関係

`AGENTS.md` を利用する場合、プロジェクト全体の最上位ガイドとして扱う。

`.cursor/rules/` は、より具体的なCursor向け共通Ruleとして扱う。

| 項目     | AGENTS.md                | `.cursor/rules/`               |
| -------- | ------------------------ | ------------------------------ |
| 対象     | 複数AIツール横断         | Cursor中心                     |
| 内容     | プロジェクト全体の大方針 | ファイル種別・作業別の具体Rule |
| 粒度     | 粗い                     | やや細かい                     |
| 変更頻度 | 低い                     | 中程度                         |
| 用途     | AIツール共通の入口       | Cursor Agentの具体制御         |

AGENTS.mdとRulesが矛盾する場合は、docs側の正本を確認し、どちらかを修正する。

---

## 39. 禁止事項

以下は禁止する。

- RulesにsecretやAPIキーを記載すること
- Rulesに個別Task条件を記載すること
- Rulesに成果物本文を記載すること
- RulesにCommand詳細手順を重複記載すること
- RulesにAgent責務を重複記載すること
- Always Ruleを必要以上に増やすこと
- globsを広くしすぎて無関係な作業へ適用すること
- 古いdocsやチャット内容を正本としてRules化すること
- 正本docsと矛盾するRuleを作成すること
- Human判断が必要な事項をRulesで自動判断扱いにすること
- generated手動編集を許可するRuleを作ること
- PR mergeをAI Agentに許可するRuleを作ること

---

## 40. 関連ドキュメント

| ドキュメント                               | 役割                                 |
| ------------------------------------------ | ------------------------------------ |
| AIエージェント活用型\_開発運用フロー設計書 | AI運用全体の流れ                     |
| AIエージェント体制・責務定義               | Agentごとの責務                      |
| AI Agent定義設計書                         | `.cursor/agents/` の設計             |
| Commands設計書                             | `.cursor/commands/` の設計           |
| Task Definition設計書                      | 個別作業条件の構造                   |
| Prompts運用ルール                          | prompts配下の配置・命名              |
| AIレビュー運用設計書                       | AI Reviewの品質観点                  |
| AIログ運用ルール                           | ai-logsの利用範囲                    |
| Slack通知運用設計書                        | Slack通知タイミング・文面            |
| worktree運用ルール                         | 並列作業時の作業領域分離             |
| Issue運用ルール                            | Issue本文・ラベル・no-branch運用     |
| Projects運用ルール                         | Projects Status管理                  |
| ブランチ運用ルール                         | Branch命名・base・PR target          |
| ディレクトリ構成定義書                     | docs / prompts / .cursor等の配置方針 |

---

## 41. 一言まとめ

`.cursor/rules/` は、AI Agentが共通して守るべきルールを定義する場所である。

役割分担は以下とする。

```text
docs                 = 設計・運用の正本
.cursor/rules        = AI Agent共通ルール
.cursor/agents       = Agentごとの責務・権限
.cursor/commands     = Commandごとの実行手順
prompts/definitions  = 個別タスク条件
prompts/templates    = 出力テンプレート
Issue                = 作業計画
PR                   = 作業結果・レビュー
```

MVPでは、まず以下を優先して作成する。

```text
project-operation.mdc
github-operation.mdc
docs-consistency.mdc
architecture-consistency.mdc
ai-review.mdc
security.mdc
```

Rulesは、AI Agentの判断を縛るための共通ルールであり、個別タスクの詳細条件や成果物本文を記載する場所ではない。
