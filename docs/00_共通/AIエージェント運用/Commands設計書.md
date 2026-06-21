# Commands設計書

## 1. 目的

本ドキュメントは、Gift Recommendation Service におけるAIエージェント運用で利用するCommandsの設計を定義する。

本プロジェクトでは、人間がAIエージェントへ作業依頼を行う際、自然文だけで依頼するのではなく、CommandとDefinitionを組み合わせて依頼する。

これにより、以下を実現する。

- AIへの依頼形式を標準化する
- 作業開始トリガーを明確にする
- Issue作成、Branch作成、PR作成、AIレビュー、修正対応を定型化する
- 人主導運用とAI主導運用の差異を制御する
- 複数AIエージェントの並列作業時でも、作業単位と責務を明確にする

---

## 2. 本ドキュメントの位置づけ

本ドキュメントは、AIエージェントに対する操作インタフェースであるCommandの正本である。

| 項目                           | 正本ドキュメント                           |
| ------------------------------ | ------------------------------------------ |
| AIエージェント運用の全体フロー | AIエージェント活用型\_開発運用フロー設計書 |
| AIエージェントの体制・責務     | AIエージェント体制・責務定義               |
| Command仕様                    | 本ドキュメント                             |
| Task Definition構造            | Task Definition設計書                      |
| prompts配置・命名              | Prompts運用ルール                          |
| AIレビュー観点                 | AIレビュー運用設計書                       |
| AIログ運用                     | AIログ運用ルール                           |
| Slack通知                      | Slack通知運用設計書                        |
| worktree運用                   | worktree運用ルール                         |

本ドキュメントでは、Commandの役割、種類、入力、処理内容、出力、状態遷移への影響を定義する。

`.cursor/commands/` に配置する具体的なCommandファイルは、本ドキュメントに従って作成する。

---

## 3. 基本方針

Commandは、AIエージェントに対して「何を実行するか」を指示する操作インタフェースである。

Definitionは、AIエージェントに対して「何を対象に、どの条件で実行するか」を渡す作業定義である。

```text
/<Command> @<definition>
```

例：

```
/start-task @prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml
/review-pr @prompts/definitions/_examples/review-definition.example.yaml
/fix-review-comments @prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml
```

| 要素       | 役割                                                     |
| ---------- | -------------------------------------------------------- |
| Command    | 実行する作業手順を指定する                               |
| Definition | 作業対象、入力資料、出力先、完了条件、確認観点を指定する |
| Agent      | Commandを実行するAIの役割を指定する                      |
| Rules      | Command実行時に従う共通ルールを指定する                  |

---

## 4. Commandの責務範囲

Commandは、AI作業の開始・継続・レビュー・修正を制御する。

Commandは、Project管理やGitHub運用のすべてを直接担うものではない。
Commandは Issue の起票・更新を起点とし、Projects同期やBranch作成などの後続処理は GitHub Actions workflow（仕様書で定義されたハーネス）に委譲する。

| 領域          | Commandの責務                                                  |
| ------------- | -------------------------------------------------------------- |
| 作業開始      | Task Definitionを読み、Issue化・Branch作成・作業開始へ進める   |
| 既存Issue作業 | Issue / Branch / Definitionを読み、作業を実行する              |
| PR作成        | 作業結果をPRテンプレートに沿って整理し、PR作成を支援する       |
| AIレビュー    | PR差分・Issue・Definition・docsを確認し、レビューする          |
| 指摘対応      | AIレビュー・人間レビューコメントを読み、同一Branchで修正する   |
| 横断契約変更  | OpenAPI / Orval / generated などの横断影響を専用Taskとして扱う |
| サマリ作成    | Slack通知や作業サマリを生成する                                |

---

## 5. Command配置

Command定義は、Cursor専用の実行資材として以下に配置する。

```
.cursor/commands/
```

推奨構成は以下とする。

```
.cursor/commands/
├─ start-epic.md
├─ start-task.md
├─ work-issue.md
├─ create-pr.md
├─ review-pr.md
├─ fix-review-comments.md
├─ create-contract-task.md
└─ summarize-work.md
```

| ファイル                  | 役割                                                       |
| ------------------------- | ---------------------------------------------------------- |
| `start-epic.md`           | Epic Definitionを読み、Epic Issue作成からEpic Branch作成まで進める |
| `start-task.md`           | Task Definitionを読み、Issue作成から作業開始まで進める     |
| `work-issue.md`           | 既存Issue / Branchに基づいて作業を実施する                 |
| `create-pr.md`            | 作業BranchからPRを作成する                                 |
| `review-pr.md`            | PR差分、Issue、docs、完了条件をAIレビューする              |
| `fix-review-comments.md`  | AIレビュー・人間レビューコメントに対応する                 |
| `create-contract-task.md` | OpenAPI / Orval / generated など横断契約変更Taskを作成する |
| `summarize-work.md`       | Slack通知や作業サマリを作成する                            |

---

## 6. Command命名規則

Commandファイル名は、kebab-caseで命名する。

```
<verb>-<object>.md
```

例：

```
start-epic.md
start-task.md
work-issue.md
create-pr.md
review-pr.md
fix-review-comments.md
create-contract-task.md
summarize-work.md
```

Command名は、ファイル名から拡張子を除いたものとする。

```
/start-epic
/start-task
/work-issue
/create-pr
/review-pr
/fix-review-comments
/create-contract-task
/summarize-work
```

---

## 7. 標準依頼形式

標準依頼形式は以下とする。

```
/<Command> @<definition>
```

例：

```
/start-task @prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml
```

Definitionが不要なCommandは原則作らない。

ただし、作業対象がPR番号やIssue番号で十分に一意に特定できる場合は、補助引数を許容する。

例：

```
/review-pr @prompts/definitions/_examples/review-definition.example.yaml #123
/fix-review-comments @prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml #123
```

---

## 8. Command共通入力

Commandは、原則として以下を参照する。

| 入力                 | 用途                                                     |
| -------------------- | -------------------------------------------------------- |
| Command本文          | 実行手順を定義する                                       |
| Task Definition      | 作業対象、入力資料、出力先、完了条件、確認観点を定義する |
| `.cursor/agents/`    | 実行Agentの責務を定義する                                |
| `.cursor/rules/`     | 共通ルールを定義する                                     |
| `AGENTS.md`          | AI Coding Agent向けの共通指示を定義する                  |
| `docs/`              | 設計成果物、仕様書、テスト成果物を参照する               |
| GitHub Issue         | 作業計画を参照する                                       |
| GitHub Projects      | Status、Phase、予定・実績を参照する                      |
| Git Branch           | 作業実体を参照する                                       |
| Pull Request         | レビュー対象を参照する                                   |
| `prompts/templates/` | Issue本文、PR本文、AIフィードバック文面生成に利用する    |

---

## 9. Command共通出力

Commandの出力先は、作業内容に応じて以下とする。

| 出力                    | 配置・反映先                                         |
| ----------------------- | ---------------------------------------------------- |
| Issue本文               | GitHub Issue                                         |
| Project同期項目         | GitHub Projects                                      |
| Branch                  | Git Branch                                           |
| 成果物                  | `docs/`                                              |
| ソースコード            | `apps/`, `packages/`, `db/`, `tests/`, `scripts/` 等 |
| PR本文                  | Pull Request                                         |
| レビューコメント        | Pull Request                                         |
| 作業サマリ              | Pull Request / Slack                                 |
| Issue化前フィードバック | チャット、必要に応じて `ai-logs/intake/`             |
| 例外ログ                | 必要に応じて `ai-logs/incidents/`                    |
| 人間判断ログ            | 必要に応じて `ai-logs/human-decisions/`              |
| 横断影響ログ            | 必要に応じて `ai-logs/cross-cutting/`                |

---

## 10. Command実行時の共通原則

Command実行時は、以下を共通原則とする。

| 原則               | 内容                                       |
| ------------------ | ------------------------------------------ |
| Issue起点          | 作業はIssueを起点に管理する                |
| Definition準拠     | AI主導タスクはTask Definitionに従う        |
| 正本尊重           | Issue、Projects、PR、docsの正本関係を守る  |
| Scope遵守          | Task Definitionのscope外作業をしない       |
| 出力先明確化       | 成果物の配置先を明確にする                 |
| 人間判断尊重       | 重要判断は人間へエスカレーションする       |
| 生成物手動編集禁止 | Orval等のgeneratedファイルを直接編集しない |
| Secret禁止         | secretやAPIキーを出力しない                |
| 明示トリガー       | Status変更だけでAI作業開始とみなさない     |

Command実行時の補足:

- Agent は `gh project item-edit` 等で Projects を直接更新しない。
- Agent は `git push` のみで Branch運用状態を確定しない。
- Issue作成・更新後の同期結果は workflow 実行結果を確認する。

---

## 11. CommandとStatus遷移

Commandは、GitHub ProjectsのStatus遷移と連動する。

Statusの正本はGitHub Projectsとする。

| Command                 | 主なStatus影響                                    | 正本 CLI / トリガー |
| ----------------------- | ------------------------------------------------- | ------------------- |
| `/start-epic`           | `Todo` → `In Progress`                            | Branch 作成 workflow |
| `/start-task`           | `Todo` → `In Progress`                            | Branch 作成 workflow |
| `/work-issue`           | `Todo` または `In Progress` → `In Progress`       | — |
| `/create-pr`            | `In Progress` → `AI Review`                       | PR open workflow |
| `/review-pr`            | `AI Review` → `Human Review` または `In Progress` | `publish-ai-review-and-dispatch.cjs` |
| `/fix-review-comments`  | `In Progress` → `AI Review`（完了時）             | `publish-fix-complete-and-dispatch.cjs` |
| `/create-contract-task` | 新規Issue作成後、原則 `Todo` → `In Progress`      | Branch 作成 workflow |
| `/summarize-work`       | 原則Status変更なし                                | — |

Status更新は、Command実行結果に基づいてGitHub ActionsまたはGitHub運用スクリプトが実施する。

Commandは、Status更新の意図を明確に出力する（Fix Outcome / Review Result）。

### 11.1 Issue close / Done制御

Issue close と Projects Status の `Done` 更新は、PR本文のGitHub自動closeキーワードに依存しない。

本プロジェクトでは、Task PRは原則として親Epic Branch向けに作成する。  
そのため、Task Issueの完了制御は、PR本文の `Closes #<Issue番号>` ではなく、PR merge時のGitHub Actions workflowで明示的に行う。

| 対象       | PR target     | PR本文のIssue参照                       | Done / close の制御                                |
| ---------- | ------------- | --------------------------------------- | -------------------------------------------------- |
| Task Issue | 親Epic Branch | `Related to #<Task Issue番号>`          | PR merge時workflowで制御                           |
| Epic Issue | `develop`     | 必要に応じて `Closes #<Epic Issue番号>` | Epic PR merge時workflowまたはGitHub自動closeで制御 |

Task Issueは、対応するTask PRが親Epic Branchへmergeされた時点で `Done` とする。

Epic Issueは、配下Task Issueがすべて `Done` となり、Epic Branchが `develop` へmergeされた時点で `Done` とする。

---

## 12. Command一覧

| Command                 | 主担当Agent     | 用途                                                                 |
| ----------------------- | --------------- | -------------------------------------------------------------------- |
| `/start-epic`           | Orchestrator AI | Epic DefinitionをもとにEpic Issue作成、Project同期、Epic Branch作成を行う |
| `/start-task`           | Orchestrator AI | Task DefinitionをもとにIssue作成、Project同期、Branch作成、作業開始を行う |
| `/work-issue`           | Worker AI       | 既存Issue / Branchで作業を実施する                                   |
| `/create-pr`            | Worker AI       | 作業結果を整理し、PRを作成する                                       |
| `/review-pr`            | Reviewer AI     | PRをAIレビューする                                                   |
| `/fix-review-comments`  | Fixer AI        | レビューコメントに基づき同一Branchで修正する                         |
| `/create-contract-task` | Contract AI     | OpenAPI / Orval / generated等の横断Taskを作成する                    |
| `/summarize-work`       | Support AI      | Slack通知・作業サマリを作成する                                      |

---

## 13. `/start-epic`

### 13.1 目的

`/start-epic` は、Epic Definition（`definition_type: epic`）をもとに、Epic単位の作業管理を開始するCommandである。

正本手順の詳細は `.cursor/commands/start-epic.md` とする。

### 13.2 標準形式

```
/start-epic @<definition>
```

例：

```
/start-epic @prompts/definitions/_examples/epic-definition.example.yaml
```

実運用: `prompts/definitions/epics/<識別子スラッグ>/epic.yaml`

### 13.3 主担当Agent

| 項目   | 値              |
| ------ | --------------- |
| 主担当 | Orchestrator AI |
| 補助   | Support AI      |

### 13.4 入力

Epic Definition（`epic.id` / `epic.title` / `epic_scope` 等）、関連docs、Issueテンプレート。

### 13.5 処理

識別子・`epic_scope` 検証、Epic Issue作成、Project同期、no-branch判定（本文のみ）、Epic Branch作成、配下Task起票案内。

### 13.6 出力

Epic Issue、Project同期、Label、Epic Branch、サマリ。

### 13.7 成功条件

Epic Issue作成、Project追加、必要時Epic Branch作成、配下Task案内出力。

### 13.8 失敗・停止条件

- `definition_type` が `epic` でない、必須項目不足
- 識別子形式違反・正本一覧未検出、`epic_scope.allowed_paths` 未記載
- 入力docs欠落、横断影響で人間判断が必要、secret懸念

---

## 14. `/start-task`

### 14.1 目的

`/start-task` は、Task DefinitionをもとにAI主導タスクを開始するCommandである。

主に、AIがIssue作成からBranch作成、作業開始まで進める場合に利用する。

### 14.2 標準形式

```
/start-task @<definition>
```

例：

```
/start-task @prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml
```

### 14.3 主担当Agent

| 項目   | 値              |
| ------ | --------------- |
| 主担当 | Orchestrator AI |
| 補助   | Support AI      |
| 後続   | Worker AI       |

### 14.4 入力

| 入力            | 必須     | 内容                                           |
| --------------- | -------- | ---------------------------------------------- |
| Task Definition | 必須     | 作業対象、入力資料、出力先、完了条件を定義する |
| 関連docs        | 必須     | Definitionで指定された入力資料                 |
| 親Epic          | 条件付き | Taskの場合、親Epic Issue / Branch              |
| templates       | 必須     | Issue本文テンプレート等                        |

親 Epic が未作成の場合は、先に `/start-epic` で Epic Issue / Epic Branch を整備する（本 Command では親 Epic を新規作成しない）。

### 14.5 処理

```
1. Task Definitionを読み込む
2. schema妥当性を確認する
3. 入力docs・参照ファイルの存在を確認する
4. 作業範囲、対象外、出力先を確認する
5. 依存Issue / PR・dependencies.epics を確認する
6. 識別子付き Task の場合、親 Epic との整合を検査する（成果物一覧×Task Definition化方針書 §3.5）
   - task.title 識別子 prefix と Parent Epic Issue タイトル先頭識別子の一致
   - output.files / parallel_control.exclusive_files が親 Epic epic_scope.allowed_paths 内か
7. Issue化可能か判断する
8. 不足がある場合はIssue化前フィードバックを返す
9. 問題なければIssue本文を生成する
10. Issueを作成する
11. Projectへ追加する
12. Projectフィールドを同期する
13. Labelを同期する
14. no-branchを判定する（Issue本文チェックのみ。Label no-branch は付与しない）
15. AI主導タスクの場合はBranchを作成する（base / target は親 Epic Branch）
16. 作業開始可能であればStatusをIn Progressへ進める
17. Worker AIへ作業を引き継ぐ
18. 必要に応じてSlack通知を作成する
```

正本手順の詳細は `.cursor/commands/start-task.md` とする。

### 14.6 出力

| 出力                    | 反映先                       |
| ----------------------- | ---------------------------- |
| Issue本文               | GitHub Issue                 |
| Project同期項目         | GitHub Projects              |
| Label                   | GitHub Issue                 |
| Branch                  | Git Branch                   |
| 作業開始サマリ          | Slack / チャット             |
| Issue化前フィードバック | チャット / `ai-logs/intake/` |

### 14.7 成功条件

- Issueが作成されている
- IssueがProjectへ追加されている
- Projectフィールドが同期されている
- 必要なLabelが付与されている
- AI主導タスクの場合、Branchが作成されている
- 作業開始可能な場合、Statusが `In Progress` になっている

### 14.8 失敗・停止条件

以下の場合は、Issue作成前に停止する。

- Definitionが存在しない、または必須項目・schema妥当性に不足がある
- 入力docs・参照ファイルが存在しない
- 出力先が不明、作業範囲が曖昧、`scope` と `out_of_scope` が矛盾している
- 親Epicが不明、親Epic Branchが不明（未作成の場合は `/start-epic` を先に実行）
- 依存Issueが未完了、依存PRが未merge
- 依存 Epic（`dependencies.epics`）が `Done` でなく、`human_decision_points` に理由がない
- 識別子付き Task で `task.title` 識別子 prefix と Parent Epic 識別子 prefix が一致しない
- 識別子付き Task で `output.files` / `parallel_control.exclusive_files` が親 Epic の `epic_scope.allowed_paths` 外を含む
- 横断影響が大きく、人間判断が必要
- secretや権限に関わる不明点がある

---

## 15. `/work-issue`

### 15.1 目的

`/work-issue` は、既存Issue / Branchに基づき、Worker AIが設計・実装・テストなどの実作業を行うCommandである。

人主導タスクでBranch作成後にAIへ作業を依頼する場合や、AI主導タスクの作業再開時に利用する。

### 15.2 標準形式

```
/work-issue @<definition>
```

例：

```
/work-issue @prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml
```

### 15.3 主担当Agent

| 項目     | 値                   |
| -------- | -------------------- |
| 主担当   | Worker AI            |
| 補助     | Test AI / Support AI |
| レビュー | Reviewer AI          |

### 15.4 入力

| 入力            | 必須     | 内容                 |
| --------------- | -------- | -------------------- |
| Issue           | 必須     | 作業計画             |
| Branch          | 必須     | 作業実体             |
| Task Definition | 必須     | 作業条件             |
| input_docs      | 必須     | 参照すべき設計書     |
| target_files    | 条件付き | 実装対象ファイル     |
| output_docs     | 条件付き | 作成・更新する成果物 |
| test_files      | 条件付き | 作成・更新するテスト |

### 15.5 処理

```text
1. Issueを確認する
2. Task Definitionを確認する
3. Branchが正しいことを確認する
4. Project Statusが作業可能状態であることを確認する
5. Task Branchが親Epic Branchの最新状態を取り込んでいるか確認する
6. input_docsを確認する
7. scope / out_of_scopeを確認する
8. target_files / output_docsを確認する
9. 必要な作業を実施する
10. テスト・検証を実施する
11. 変更内容を自己確認する
12. commitを作成する
13. 作業サマリを作成する
14. 必要に応じて `/create-pr` へ進める
```

Task Branchが親Epic Branchの最新状態を取り込んでいない場合は、作業前に最新化する。

ただし、競合や前提不整合が発生した場合は、推測で解消せず、人間へ確認する。

### 15.6 出力

| 出力           | 反映先                 |
| -------------- | ---------------------- |
| 設計書・仕様書 | `docs/`                |
| ソースコード   | 対象コンポーネント     |
| テストコード   | 対象テストディレクトリ |
| テスト結果     | PR本文 / docs          |
| commit         | Git Branch             |
| 作業サマリ     | PR本文案 / Slack       |

### 15.7 成功条件

- Definitionの完了条件を満たしている
- 作業範囲外の変更をしていない
- 必要な成果物が指定場所に配置されている
- 必要なテスト・検証が実施されている
- commitが作成されている

### 15.8 停止条件

以下の場合は作業を停止し、人間へ確認する。

- IssueとDefinitionの内容が矛盾する
- Branchが存在しない
- Branch baseが誤っている
- 対象ファイルが他Taskと競合している
- API契約変更が必要になる
- DB schema変更が必要になる
- 指定外の大きな設計変更が必要になる

---

## 16. `/create-pr`

### 16.1 目的

`/create-pr` は、作業BranchからPRを作成するCommandである。

PRはレビュー正本であり、作業結果、確認結果、AIレビュー依頼、人間レビュー観点を整理する。

### 16.2 標準形式

```
/create-pr @<definition>
```

例：

```
/create-pr @prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml
```

### 16.3 主担当Agent

| 項目   | 値          |
| ------ | ----------- |
| 主担当 | Worker AI   |
| 補助   | Support AI  |
| 後続   | Reviewer AI |

### 16.4 入力

| 入力            | 必須 | 内容                     |
| --------------- | ---- | ------------------------ |
| Issue           | 必須 | 対象Issue                |
| Branch          | 必須 | 作業Branch               |
| Task Definition | 必須 | 作業条件                 |
| PR Template     | 必須 | PR本文テンプレート       |
| diff            | 必須 | 変更差分                 |
| test results    | 推奨 | 実施したテスト・検証結果 |

### 16.5 処理

````
0. machine account 認証を確認する（`gh-bot-auth.cjs verify` + `print-setup`）。PR author が bot であること
1. 対象Issueを確認する
2. 作業Branchを確認する
3. Task Branchが親Epic Branchの最新状態を取り込んでいるか確認する
4. PR targetを確認する
5. diffを確認する
6. 変更内容を整理する
7. 実施した確認・テスト結果を整理する
8. 未実施事項・残課題を整理する
9. PRテンプレートに沿ってPR本文を作成する
10. Task PRの場合は Related to #<Task Issue番号> を記載する
11. Epic PRの場合は必要に応じて Closes #<Epic Issue番号> を記載する
12. PRを作成する
13. Project Statusを AI Review へ進める
14. 必要に応じてSlack通知を作成する```
````

Task PRでは、GitHubの自動closeキーワードには依存しない。

Task Issueの close / Projects Done 更新は、PR merge時のGitHub Actions workflowで明示的に制御する。

### 16.6 出力

| 出力           | 反映先              |
| -------------- | ------------------- |
| PR             | GitHub Pull Request |
| PR本文         | Pull Request        |
| Status更新意図 | GitHub Projects     |
| PR作成通知     | Slack               |

### 16.7 成功条件

- PRが作成されている
- PR targetが正しい
- Task Branchが親Epic Branchの最新状態を取り込んでいる
- IssueとPRが紐づいている
- Task PRの場合、`Related to #<Task Issue番号>` が記載されている
- Epic PRの場合、必要に応じて `Closes #<Epic Issue番号>` が記載されている
- 変更内容・テスト結果・レビュー観点が記載されている
- Statusが `AI Review` へ進む状態になっている
- Issue close / Projects Done はPR merge時workflowで制御される前提になっている

### 16.8 停止条件

以下の場合はPR作成を停止し、人間へ確認する。

- commitが存在しない
- PR targetが不明
- Task Branchからdevelopへ直接PRしようとしている
- Task Branchが親Epic Branchの最新状態を取り込んでいない
- 親Epic Branchとの最新化で競合が発生している
- テスト未実施理由が不明
- IssueとBranchの対応が不明
- PR本文に必要な情報を生成できない
- 前段成果物の大きな修正が必要であり、現在のTask内で扱うべきか判断できない

---

## 17. `/review-pr`

### 17.1 目的

`/review-pr` は、PRをAIレビューするCommandである。

人間レビュー前に、Issue、Task Definition、PR差分、docs、テスト結果、CI結果の整合性を確認する。

### 17.2 標準形式

```

/review-pr @<definition>

```

例：

```

/review-pr @prompts/definitions/_examples/review-definition.example.yaml

```

PR番号を併記してもよい。

```

/review-pr @prompts/definitions/_examples/review-definition.example.yaml #123

```

### 17.3 主担当Agent

| 項目   | 値                                       |
| ------ | ---------------------------------------- |
| 主担当 | Reviewer AI                              |
| 補助   | Docs Reviewer AI / Test AI / Contract AI |
| 後続   | Fixer AI / Human                         |

### 17.4 入力

| 入力            | 必須     | 内容                   |
| --------------- | -------- | ---------------------- |
| PR              | 必須     | レビュー対象           |
| PR diff         | 必須     | 変更差分               |
| Issue           | 必須     | 作業計画               |
| Task Definition | 必須     | 完了条件・確認観点     |
| output_docs     | 条件付き | 作成・更新された成果物 |
| test results    | 条件付き | テスト結果             |
| CI results      | 条件付き | CI結果                 |

### 17.5 処理

```text
0. machine account 認証を確認する（`gh-bot-auth.cjs`）
1. PRを確認する
2. 対象Issueを確認する
3. Task Definitionを確認する
4. PR targetを確認する
5. Task Branchが親Epic Branchの最新状態を取り込んでいるか確認する
6. PR diffを確認する
7. 識別子付き Task PR の場合、親 Epic スコープ越境を検査する（成果物一覧×Task Definition化方針書 §3.5、AIレビュー運用設計書 §13.2）
   - PR 差分 path が親 Epic epic_scope.allowed_paths 内か
   - PR / Issue 識別子 prefix と親 Epic 識別子 prefix の一致
   - MOD-RECO-NNN 配下 Task で apps/reco/src/reco/api/** に差分がある場合は blocked
8. output_docsを確認する
9. 完了条件を満たしているか確認する
10. 確認観点を満たしているか確認する
11. テスト結果・CI結果を確認する
12. generated差分の有無を確認する
13. 横断影響を確認する
14. 前段成果物の修正が必要か確認する
15. レビューコメントを作成する
16. AIレビュー結果をPRへ記録する（live-run / IDE 実行時）
17. **`publish-ai-review-and-dispatch.cjs` で Status dispatch を 1 回実行する**（§17.10）
18. 指摘なしなら Human Review へ進める
19. 指摘ありなら In Progress へ戻す判断材料を出す

```

正本手順の詳細は `.cursor/commands/review-pr.md` とする。Status 同期の CLI 正本は §17.10。

前段成果物の修正が必要な場合は、以下の基準で扱う。

| 修正内容                             | 扱い                                    |
| ------------------------------------ | --------------------------------------- |
| 軽微な文言修正・補足                 | 現在のTask PR内で修正してよい           |
| 実装に合わせた小さな設計書補正       | 現在のTask PR内で修正してよい           |
| 仕様・設計方針に影響する修正         | 新しいTask Issue化を提案する            |
| API契約・DB・generatedに影響する修正 | Contract Taskまたは専用Task化を提案する |

---

### 17.6 出力

| 出力                | 反映先               |
| ------------------- | -------------------- |
| AIレビューコメント  | Pull Request         |
| AIレビューサマリ    | Pull Request / Slack |
| 修正要否            | Pull Request         |
| Status更新意図      | GitHub Projects      |
| follow-up Issue候補 | Pull Request / Issue |

### 17.7 レビュー結果分類

| 結果                     | 意味                     | 次Status                        |
| ------------------------ | ------------------------ | ------------------------------- |
| approve_for_human_review | Human Reviewへ進めてよい | Human Review                    |
| request_changes          | 同一Branchで修正が必要   | In Progress                     |
| needs_human_decision     | 人間判断が必要           | Human Review または In Progress |
| split_required           | 別Issue化が必要          | In Progress                     |
| blocked                  | 前提不足でレビュー不可   | In Progress                     |

### 17.8 成功条件

- PRへAIレビュー結果が記録されている
- **`publish-ai-review-and-dispatch.cjs` によりコメント投稿と `repository_dispatch` が 1 回完了している**（または `--verify` で dispatch 済みを確認済み）
- 修正要否が明確である
- Human Reviewへ進めてよいか判断できる
- 指摘がある場合、修正対象が明確である

### 17.9 停止条件

- PRが存在しない
- Issueとの紐づきが不明
- diffを確認できない
- Definitionが存在しない
- レビュー前提となる成果物が欠落している
- 識別子付き Task PR で差分 path が親 Epic の `epic_scope.allowed_paths` 外を含む（`blocked`）
- 識別子 prefix が親 Epic と不一致（`blocked`）
- `MOD-RECO-NNN` Epic 配下で `apps/reco/src/reco/api/**` に差分がある（`blocked`）

### 17.10 Status 同期（dispatch 忘れ防止）

AI Review 完了後の Projects Status 更新は [PR Review Status Sync](../../06_実装設計/github_actions/PRレビュー完了時Status更新ワークフロー仕様書.md) が担う。`/review-pr` は **コメント投稿と dispatch を分離しない**。

| 項目 | 内容 |
| ---- | ---- |
| 正本 CLI | `.github/scripts/publish-ai-review-and-dispatch.cjs` |
| 推奨 | `--comment-file` で ai-review-comment 形式を渡し、コメント + dispatch を 1 回実行 |
| 完了確認 | 同一 CLI の `--verify` |
| recovery | `--dispatch-only`（コメント投稿済み時） |
| Harness | `review-pr` + `live-run` 完了後、post-run 検証で dispatch 忘れを **ジョブ失敗** |
| Status=`AI Review` 自動起動 | `pr-created-status-and-slack.yml` / `pr-ready-for-ai-review.yml` が `dispatch-review-pr-harness.cjs` で Harness を dispatch（[AI Review自動起動ワークフロー連携仕様書](../../06_実装設計/github_actions/AI%20Review自動起動ワークフロー連携仕様書.md)） |
| Machine account | dispatch / PR コメント投稿前に `GH_BOT_TOKEN` で bot 認証（[AI機械アカウント運用設計書](./AI機械アカウント運用設計書.md)） |

詳細手順は `.cursor/commands/review-pr.md` §15.5 を正本とする。

---

## 18. `/fix-review-comments`

### 18.1 目的

`/fix-review-comments` は、AIレビューまたは人間レビューの指摘に対応するCommandである。

原則として、同一Issue・同一Branchで修正する。

### 18.2 標準形式

```

/fix-review-comments @<definition>

```

例：

```

/fix-review-comments @prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml

```

PR番号を併記してもよい。

```

/fix-review-comments @prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml #123

```

### 18.3 主担当Agent

| 項目   | 値                  |
| ------ | ------------------- |
| 主担当 | Fixer AI            |
| 補助   | Worker AI / Test AI |
| 後続   | Reviewer AI         |

### 18.4 入力

| 入力            | 必須 | 内容                             |
| --------------- | ---- | -------------------------------- |
| PR              | 必須 | 修正対象PR                       |
| review comments | 必須 | AIレビュー・人間レビューコメント |
| Issue           | 必須 | 作業計画                         |
| Branch          | 必須 | 修正対象Branch                   |
| Task Definition | 必須 | 作業条件                         |
| existing diff   | 必須 | 現在の変更差分                   |

### 18.5 処理

```

1. PRレビューコメントを確認する
2. 指摘内容を分類する
3. 同一Branchで対応可能か確認する
4. Definitionのscope内か確認する
5. Task Branchが親Epic Branchの最新状態を取り込んでいるか確認する
6. 修正方針を整理する
7. 対象Branchで修正する
8. 必要なテストを再実行する
9. commitを追加する
10. PR本文またはPRコメントを更新する
11. 修正サマリを記録する
12. Statusを AI Review へ戻す（Fix Outcome に応じ §18.10）
13. 必要に応じてSlack通知を作成する

```

レビュー指摘対応では、原則として同一Issue・同一Branchで修正する。

ただし、指摘内容が当初Taskのscopeを超える場合は、同一Branchへ混在させず、新しいTask Issue化を提案する。

---

### 18.6 出力

| 出力           | 反映先               |
| -------------- | -------------------- |
| 修正commit     | Git Branch           |
| PR更新         | Pull Request         |
| コメント返信   | Pull Request         |
| 修正サマリ     | Pull Request / Slack |
| 再レビュー依頼 | Pull Request         |

### 18.7 成功条件

- レビュー指摘に対応している
- 対応範囲が同一Issueのscope内である
- 修正内容がPRに記録されている
- 必要なテストが再実行されている
- 再レビュー可能な状態になっている

### 18.8 停止条件

以下の場合は修正作業を停止し、人間へ確認する。

- レビューコメントの意図が不明
- 指摘内容がscope外である
- 別Issue化すべき内容である
- API契約変更が必要になる
- DB schema変更が必要になる
- generated差分が発生する
- 親Epic Branchとの最新化で競合が発生している
- 後続Taskへの影響が大きい
- 人間判断なしに進めると危険である

### 18.10 Status 同期（dispatch 忘れ防止）

Fix 完了後（Fix Outcome = `ready_for_ai_review`）の Projects Status 更新は [PR再AI Review待ちStatus更新ワークフロー](../../06_実装設計/github_actions/PR再AI%20Review待ちStatus更新ワークフロー仕様書.md) が担う。`/fix-review-comments` は **コメント投稿と dispatch を分離しない**。

| 項目 | 内容 |
| ---- | ---- |
| 正本 CLI | `.github/scripts/publish-fix-complete-and-dispatch.cjs` |
| PR コメント正本 | `prompts/templates/review/fix-complete-comment.md` |
| 推奨 | `--comment-file` で fix-complete-comment 形式を渡し、コメント + dispatch を 1 回実行 |
| 完了確認 | 同一 CLI の `--verify` |
| recovery | `--dispatch-only`（コメント投稿済み時）または `workflow_dispatch`（PR Ready For AI Review Status Sync） |
| Machine account | dispatch / PR コメント投稿前に `GH_BOT_TOKEN` で bot 認証 |

`split_required` / `partial_fix` / `blocked` 等では dispatch **しない**（Status は `In Progress` 維持）。

詳細手順は `.cursor/commands/fix-review-comments.md` §12.5 を正本とする。

---

## 19. `/create-contract-task`

### 19.1 目的

`/create-contract-task` は、OpenAPI / Orval / generated / API client など、横断影響がある契約変更Taskを作成するCommandである。

通常Taskに契約変更を混在させないために利用する。

### 19.2 標準形式

```

/create-contract-task @<definition>

```

例：

```

/create-contract-task @prompts/definitions/cross-cutting/api-contract-orval/contract-task.yaml

```

### 19.3 主担当Agent

| 項目   | 値                           |
| ------ | ---------------------------- |
| 主担当 | Contract AI                  |
| 補助   | Orchestrator AI / Support AI |
| 後続   | Worker AI / Reviewer AI      |

### 19.4 入力

| 入力                | 必須     | 内容               |
| ------------------- | -------- | ------------------ |
| Contract Definition | 必須     | 契約変更の作業条件 |
| OpenAPI             | 条件付き | API契約定義        |
| Orval config        | 条件付き | Orval設定          |
| generated diff      | 条件付き | 生成物差分         |
| related tasks       | 推奨     | 影響を受けるTask   |
| related docs        | 推奨     | API設計書・仕様書  |

### 19.5 処理

```

1. 契約変更の対象を確認する
2. OpenAPI / Orval / generatedへの影響を確認する
3. 関連Taskを確認する
4. Contract専用TaskとしてIssue化すべきか判断する
5. 必要に応じて影響分析を作成する
6. Issue本文を生成する
7. Projectへ追加する
8. Branch作成条件を設定する
9. 必要に応じて ai-logs/cross-cutting に記録する
10. Slack通知用サマリを作成する

```

### 19.6 出力

| 出力                | 反映先                           |
| ------------------- | -------------------------------- |
| Contract Task Issue | GitHub Issue                     |
| 影響分析            | Issue / `ai-logs/cross-cutting/` |
| Project同期項目     | GitHub Projects                  |
| Branch              | Git Branch                       |
| Slack通知           | Slack                            |

### 19.7 成功条件

- 契約変更が通常Taskから分離されている
- 影響範囲が明確である
- 生成物の扱いが明確である
- 関連Taskとの依存関係が整理されている

### 19.8 停止条件

- 契約変更の目的が不明
- 影響範囲が特定できない
- Public APIの後方互換性に影響する
- 人間判断なしに進めると危険である

---

## 20. `/summarize-work`

### 20.1 目的

`/summarize-work` は、作業結果やレビュー結果を要約し、Slack通知、PR追記、Issueコメントに利用するCommandである。

### 20.2 標準形式

```

/summarize-work @<definition>

```

例：

```

/summarize-work @prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml

```

### 20.3 主担当Agent

| 項目   | 値                                 |
| ------ | ---------------------------------- |
| 主担当 | Support AI                         |
| 補助   | Worker AI / Reviewer AI / Fixer AI |

### 20.4 入力

| 入力             | 必須     | 内容                      |
| ---------------- | -------- | ------------------------- |
| Issue            | 条件付き | 作業対象Issue             |
| PR               | 条件付き | 作業対象PR                |
| diff             | 条件付き | 変更差分                  |
| review result    | 条件付き | レビュー結果              |
| Task Definition  | 推奨     | 作業条件                  |
| 通知テンプレート | 推奨     | Slack通知文面テンプレート |

### 20.5 処理

```

1. 要約対象を確認する
2. 作業内容を整理する
3. 変更ファイルを整理する
4. テスト結果を整理する
5. レビュー結果を整理する
6. 残課題を整理する
7. 通知先に応じた文面を作成する

```

### 20.6 出力

| 出力           | 反映先             |
| -------------- | ------------------ |
| 作業サマリ     | Slack / PR / Issue |
| レビューサマリ | Slack / PR         |
| 完了サマリ     | Slack / Issue      |
| 判断依頼サマリ | Slack / Issue / PR |

### 20.7 注意点

Slack通知は正本ではない。

作業計画はIssue、レビューはPR、成果物はdocsに記録する。

---

## 21. Command実行UI

Commandは、主に以下のUI・経路で実行する。

| 経路                            | 用途                                                     |
| ------------------------------- | -------------------------------------------------------- |
| Cursor Chat                     | 人間が手動でAIエージェントへ依頼する                     |
| Cursor Agent / Background Agent | AI主導作業・並列作業で利用する                           |
| GitHub Issueコメント            | 既存Issueに対する作業再開・補足指示に利用する            |
| GitHub PRコメント               | レビュー指摘対応・再レビュー依頼に利用する               |
| Slack                           | 通知・サマリ受信を主用途とする。作業指示の正本にはしない |

標準はCursor上でのCommand実行とする。

GitHub IssueコメントやPRコメントからCommand相当の処理を起動する場合は、別途GitHub Actionsワークフロー仕様書で定義する。

---

## 22. Command実行前チェック

Command実行前に、AIエージェントは以下を確認する。

| チェック           | 内容                                         |
| ------------------ | -------------------------------------------- |
| Definition存在確認 | 指定されたDefinitionが存在するか             |
| schema確認         | 必須項目が揃っているか                       |
| 入力docs確認       | input_docsが存在するか                       |
| 出力先確認         | output_docs / target_files が明確か          |
| Issue確認          | 既存Issueを対象とする場合、Issueが存在するか |
| Branch確認         | 作業Branchが存在し、baseが正しいか           |
| PR確認             | PR対象Commandの場合、PRが存在するか          |
| Status確認         | 現在StatusがCommand実行可能な状態か          |
| scope確認          | 作業内容がscope内か                          |
| conflict確認       | 他Taskと変更対象が競合しないか               |
| secret確認         | secretを扱わないか                           |

---

## 23. Command実行後チェック

Command実行後に、AIエージェントは以下を確認する。

| チェック       | 内容                                                          |
| -------------- | ------------------------------------------------------------- |
| 成果物確認     | 指定された成果物が作成・更新されたか                          |
| 差分確認       | 意図しないファイル変更がないか                                |
| Branch鮮度確認 | Task Branchが親Epic Branchの最新状態を取り込んでいるか        |
| テスト確認     | 必要なテスト・検証を実施したか                                |
| PR確認         | PR本文に必要情報が記載されているか                            |
| Issue紐づけ    | Task PRでは `Related to #<Task Issue番号>` が記載されているか |
| Status確認     | 次のStatusへ進める状態か                                      |
| Done制御確認   | Issue close / Projects Done をworkflowで制御できる状態か      |
| Slack通知      | 必要な通知が作成されたか                                      |
| ai-logs確認    | 必要な例外ログのみ記録したか                                  |

---

## 24. エラー時の扱い

Command実行中に作業継続できない場合は、推測で進めない。

以下の形式で停止理由を整理する。

```

## 作業停止理由

- 停止種別:
- 発生箇所:
- 不足情報:
- 影響範囲:
- AIの判断:
- 人間に確認したいこと:
- 推奨対応:

```

### 24.1 停止種別

| 種別                 | 内容                       |
| -------------------- | -------------------------- |
| missing_input        | 入力資料不足               |
| invalid_definition   | Definition不備             |
| unclear_scope        | 作業範囲不明               |
| missing_output_path  | 出力先不明                 |
| dependency_not_ready | 依存Issue / PR未完了       |
| branch_error         | Branch不備                 |
| conflict_risk        | 競合リスク                 |
| contract_impact      | API契約・generated横断影響 |
| needs_human_decision | 人間判断が必要             |
| permission_error     | 権限不足                   |
| secret_risk          | secret混入リスク           |

---

### 24.2 前段成果物の修正が必要な場合

後続Taskの作業中またはレビュー中に、前段Taskで作成した成果物の修正が必要になる場合がある。

この場合、過去のTask Branchを再利用しない。

対応方針は以下とする。

| 状況                           | 対応                                            |
| ------------------------------ | ----------------------------------------------- |
| 軽微な文言修正                 | 現在のTask PR内で修正してよい                   |
| 実装に合わせた小さな設計書補正 | 現在のTask PR内で修正してよい                   |
| 仕様・設計方針の見直し         | 新しいTask Issueを作成する                      |
| API契約変更が必要              | Contract Taskを作成する                         |
| DB schema変更が必要            | 専用Task Issueを作成する                        |
| 他Taskへ影響する               | Orchestrator AIが影響分析し、人間へ判断依頼する |

前段Task Issueは、対応PRが親Epic Branchへmerge済みであれば `Done` のままとする。

過去のTask Issueを再オープンして作業を戻すのではなく、必要に応じて新しい修正Task Issueを作成する。

---

## 25. AIログとの関係

Command実行結果をすべて `ai-logs/` に保存しない。

AIログは以下の場合に限定する。

記録対象・ディレクトリ構成の正本は [AIログ運用ルール](./AIログ運用ルール.md) §4・§6 とする。

| 種別                    | 保存先                     |
| ----------------------- | -------------------------- |
| Issue化前フィードバック | `ai-logs/intake/`          |
| 作業停止・例外          | `ai-logs/incidents/`       |
| 人間判断待ち            | `ai-logs/human-decisions/` |
| 横断影響                | `ai-logs/cross-cutting/`   |
| AI運用検証              | `ai-logs/experiments/`     |

通常作業の記録先は以下とする。

| 記録内容 | 正本  |
| -------- | ----- |
| 作業計画 | Issue |
| 作業結果 | PR    |
| レビュー | PR    |
| 成果物   | docs  |
| 通知     | Slack |

---

## 26. Command追加方針

新しいCommandは、以下を満たす場合のみ追加する。

| 条件                   | 内容                                            |
| ---------------------- | ----------------------------------------------- |
| 操作が繰り返し発生する | 毎回同じ手順で実行する作業である                |
| 責務が明確             | 既存Commandと責務が重複しない                   |
| 入力が定義可能         | DefinitionまたはIssue / PRで入力を特定できる    |
| 出力が定義可能         | Issue / PR / docs / Slack等の出力先が明確である |
| Status影響が定義可能   | Projects Statusへの影響が明確である             |
| Agentが定義可能        | 主担当Agentを明確にできる                       |

既存Commandの責務で表現できる作業は、新Commandを作らない。

---

## 27. Command追加時の設計項目

Commandを追加する場合は、以下を定義する。

```

- Command名
- 目的
- 主担当Agent
- 標準形式
- 入力
- 処理手順
- 出力
- 成功条件
- 停止条件
- Statusへの影響
- Slack通知有無
- ai-logs利用有無
- 関連Definition
- 関連テンプレート

```

---

## 28. 禁止事項

以下は禁止する。

- Definitionなしで大規模作業Commandを実行すること
- Projects Status変更だけでAI作業開始とみなすこと
- Issueなしで作業開始すること
- Task Branchからdevelopへ直接PRを作成すること
- Commandがscope外作業を勝手に実行すること
- Commandが人間レビューを省略すること
- CommandがPRをmergeすること
- CommandがsecretやAPIキーを出力すること
- Orval等のgeneratedファイルを手動編集すること
- 通常作業ログをすべてai-logsへ保存すること
- Slack通知だけで作業記録を完結させること
- 既存Commandと責務が重複するCommandを乱立すること

---

## 29. Definition Run（通称）と外部トリガによる実行

### 29.1 通称: Definition Run

本プロジェクトでは、`/<Command> @<Definition>` の組み合わせで実行する 1 回の AI 作業単位を **Definition Run** と呼ぶ。

Definition Run の例:

| 呼び出し | 意味 |
| -------- | ---- |
| `/start-epic @prompts/definitions/epics/scr-002-recommendation-input/epic.yaml` | SCR-002 Epic Definition の Definition Run |
| `/start-task @prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml` | screen-spec Task Definition の Definition Run |

Cursor IDE のチャット欄から直接実行することが基本だが、後述する外部トリガからも実行できる。

### 29.2 外部トリガによる実行（GitHub Actions / 将来 Slack）

Definition Run は、Cursor IDE 以外からも実行できる。MVP では GitHub Actions の `workflow_dispatch` / `repository_dispatch` をトリガに、Cursor Cloud Agent 上で Definition Run を実行する Harness を提供する。

| トリガ | 経路 | フェーズ |
| ------ | ---- | -------- |
| Cursor IDE | チャット → ローカル Agent / Cloud Agent | 既存 |
| `workflow_dispatch` | GitHub Actions UI / `gh workflow run` → Cloud Agent | MVP |
| `repository_dispatch` | 外部システム → GitHub API → Cloud Agent | MVP |
| Slack | Slack → `repository_dispatch` 発火 → 上記経路 | Phase C（後続） |

正本仕様は [Definition Run Harness ワークフロー仕様書](../../06_実装設計/github_actions/Definition%20Run%20Harness%E3%83%AF%E3%83%BC%E3%82%AF%E3%83%95%E3%83%AD%E3%83%BC%E4%BB%95%E6%A7%98%E6%9B%B8.md) とする。

### 29.3 外部実行時の制約

外部トリガで実行する場合も、本ドキュメント §4 / §10 と各 Command の手順（`.cursor/commands/<command>.md`）に従う。特に以下を守る。

- `run_mode=dry-run` の場合、Issue / Branch / Project / PR / Label / Definition への書き込みを行わない（`gh` CLI / `git push` / GitHub API の write 系操作は全面禁止）
- Projects 同期・Branch 作成・PR 作成は本 Harness 自身では行わず、Issue 起票後の既存 workflow に委譲する（§4 / §10）
- secret / API キー / `.env` 実値は出力・log・Summary に出さない
- 違反は Harness の post-run 検証で検知されジョブが失敗する

### 29.4 MVP 対応範囲

| 項目 | MVP の扱い |
| ---- | ---------- |
| 対応 Command | `/start-epic`（dry-run） / `/review-pr`（dry-run / live-run） |
| `run_mode` | Command レジストリ準拠（`start-epic` は `dry-run` のみ、`review-pr` は `dry-run` / `live-run`） |
| Slack 入力 | 未対応（Phase C） |
| `live-run` | `review-pr` は対応済み。他 command は未対応（Phase D。Environments approval 等の承認ゲート追加が前提） |

他 Command（`/start-task` 等）への横展開は、Harness 側の Command レジストリへの追記と各 Command の md への「Definition Run としての外部実行」節の複製で行う（Harness 仕様書 §14 横展開チェックリスト）。

### 29.5 Layer2 テスト workflow dispatch（Agent 手順）

Definition Run Harness（§29）とは別系統として、Epic C Layer2 テスト（`test-system.yml` / `test-reco-quality.yml` 等）を Agent が `gh workflow run` で dispatch する手順を定義する。

| 項目 | 内容 |
| ---- | ---- |
| 正本 | [Layer2 Agent dispatch手順書.md](../../05_アプリケーション設計/テスト/Layer2%20Agent%20dispatch%E6%89%8B%E9%A0%86%E6%9B%B8.md) |
| トリガ | `workflow_dispatch`（GHA UI / `gh workflow run`） |
| Agent 経路 | Cursor IDE Agent → `gh` CLI → GHA run → artifact / job summary 読取 |
| Fix ループ | dispatch → 読取 → Fix → 再 dispatch（Epic C `agent_test_operations.common_pattern`） |
| Layer1 との分離 | 通常 PR CI（`ci.yml` 群）には Layer2 workflow を含めない |

`/work-issue` 完了前に Layer2 検証が Task Definition `test_policy` で要求される場合、Agent は上記正本に従う（`.cursor/commands/work-issue.md` §Layer2 テスト dispatch）。

---

## 30. 関連ドキュメント

| ドキュメント                               | 役割                                     |
| ------------------------------------------ | ---------------------------------------- |
| AIエージェント活用型\_開発運用フロー設計書 | AI主導運用の全体フローを定義             |
| AIエージェント体制・責務定義               | Agentごとの責務を定義                    |
| Task Definition設計書                      | Definitionのschemaを定義                 |
| Prompts運用ルール                          | prompts配下の配置・命名を定義            |
| AIレビュー運用設計書                       | AIレビュー観点と出力形式を定義           |
| AIログ運用ルール                           | ai-logsの記録対象を定義                  |
| Slack通知運用設計書                        | Slack通知条件を定義                      |
| worktree運用ルール                         | 並列作業時の作業領域分離を定義           |
| Issue運用ルール                            | Issue本文、タイトル、ラベル、no-branch（本文のみ）を定義 |
| Projects運用ルール                         | Status、Phase、予定・実績管理を定義      |
| ブランチ運用ルール                         | Branch命名、Branch base、PR targetを定義 |
| GitHub Actionsワークフロー仕様書           | Command後続の自動化処理を定義            |
| Definition Run Harnessワークフロー仕様書   | 外部トリガから Cursor Cloud Agent に Definition Run を依頼する Harness を定義 |
| Layer2 Agent dispatch手順書              | Layer2 テスト workflow の Agent dispatch / 結果読取 / Fix ループ手順を定義 |

---

## 31. 一言まとめ

Commandは、AIエージェントに対する作業開始・作業継続・レビュー・修正の操作インタフェースである。

標準形式は以下とする。

```

/<Command> @<definition>

```

代表的なCommandは以下である。

```

/start-epic
/start-task
/work-issue
/create-pr
/review-pr
/fix-review-comments
/create-contract-task
/summarize-work

```

Commandは作業手順を定義し、Definitionは作業条件を定義する。

AI作業はCommandで明示的に開始し、Issue、Projects、Branch、PR、docsの正本関係に従って進める。
