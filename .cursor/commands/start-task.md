# start-task

## 目的

`/start-task` は、Task Definition（`definition_type: task`）をもとにAI主導タスクを開始するCommandである。

親 Epic Issue / Epic Branch が未作成の場合は、本 Command の前に `/start-epic` を実行する（正本: [Commands設計書](../../docs/00_共通/AIエージェント運用/Commands設計書.md) §14、[start-epic.md](./start-epic.md)）。

主に、AIが以下を一連の流れで進める場合に利用する。

- Task Definitionの確認
- 入力docs・参照ファイルの確認
- Issue化可否の判断
- Issue本文の生成
- Issue作成
- GitHub Projectsへの追加
- Projectフィールド同期
- Label同期
- no-branch判定
- Branch作成
- Status更新意図の出力
- Worker AIへの作業引き継ぎ
- 必要に応じたSlack通知サマリ作成

このCommandは、実作業そのものを行うためのCommandではない。
実作業は、Issue・Branch・Task Definitionが揃った後、原則として `work-issue.md` に引き継ぐ。

---

## 標準形式

```text
/start-task @<definition>
```

例：

```
/start-task @prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml
```

Definitionなしでの実行は原則禁止する。

---

## 主担当Agent

| 項目   | Agent           |
| ------ | --------------- |
| 主担当 | Orchestrator AI |
| 補助   | Support AI      |
| 後続   | Worker AI       |

---

## 参照する定義・Rules

必要に応じて以下を参照する。

- `AGENTS.md`
- `.cursor/agents/orchestrator-ai.md`
- `.cursor/agents/support-ai.md`
- `.cursor/agents/worker-ai.md`
- `.cursor/rules/project-operation.mdc`
- `.cursor/rules/github-operation.mdc`
- `.cursor/rules/docs-consistency.mdc`
- `.cursor/rules/terminology.mdc`
- `.cursor/rules/architecture-consistency.mdc`
- `.cursor/rules/code-consistency.mdc`
- `.cursor/rules/api-contract.mdc`
- `.cursor/rules/testing.mdc`
- `.cursor/rules/ai-review.mdc`
- `.cursor/rules/security.mdc`
- `.cursor/rules/worktree.mdc`
- `.cursor/rules/git-commit-message.mdc`

対象作業に関係しないRulesは詳細確認を省略してよい。

ただし、security、API contract、DB schema、generated、CI/CD、Branch、Project、Issueに影響する場合は、関連Rulesを必ず確認する。

---

## 入力

| 入力                | 必須     | 内容                                                     |
| ------------------- | -------- | -------------------------------------------------------- |
| Task Definition     | 必須     | 作業対象、入力資料、出力先、完了条件を定義する           |
| 関連docs            | 必須     | Definitionで指定された入力資料                           |
| 親Epic              | 条件付き | Taskの場合、親Epic Issue / 親Epic Branch                 |
| templates           | 必須     | Issue本文テンプレート、必要に応じてSlack通知テンプレート |
| GitHub Projects情報 | 推奨     | Project追加・Status・Phase・予定日等の同期に利用         |
| Label定義           | 推奨     | Issueへ付与するLabel判定に利用                           |

---

## 処理手順

### 0. Machine account 認証（GitHub 書き込み前・必須）

Issue 作成 / Branch push / commit の前に bot 認証を確認する（[github-operation.mdc](../../.cursor/rules/github-operation.mdc) §3.16）。

```bash
node .github/scripts/gh-bot-auth.cjs verify
eval "$(node .github/scripts/gh-bot-auth.cjs print-setup)"
```

### 1. Task Definitionを読み込む

指定されたDefinitionを読み込む。

確認する主な項目は以下。

- task_id
- title
- task_type
- parent_epic
- background
- objective
- scope
- out_of_scope
- `input.docs`
- `output.docs`
- `output.files`
- deliverables
- acceptance_criteria
- dependencies
- `issue`（unit / type / area）
- `project.fields`
- branch_policy
- no_branch
- test_policy
- operation_logging
- human_review_required

Definitionが存在しない、または必須項目が不足している場合は停止する。

---

### 2. schema妥当性を確認する

Task Definition設計書に従い、schema妥当性を確認する。

確認観点は以下。

- 必須項目が揃っているか
- 型・形式が正しいか
- `scope` と `out_of_scope` が矛盾していないか
- `input.docs` が指定されているか
- `output.docs` または `output.files` が明確か
- `acceptance_criteria` が検証可能な形で書かれているか
- `dependencies` が未解決のままになっていないか
- `operation_logging` の扱いが明確か

不備がある場合は、Issue作成前フィードバックとして整理し、Issue作成へ進まない。

---

### 3. 入力docs・参照ファイルの存在を確認する

Definitionで指定された `input.docs`、関連docs、参照ファイルの存在を確認する。

確認結果は以下に分類する。

| 分類           | 扱い                          |
| -------------- | ----------------------------- |
| 存在確認済み   | Issue化可能性の判断に利用する |
| 存在しない     | Issue作成前に停止する         |
| パス不明       | 人間確認事項にする            |
| 内容不整合あり | 正本確認または人間判断へ回す  |

---

### 4. 作業範囲、対象外、出力先を確認する

以下を確認する。

- 作業範囲が明確か
- 対象外が明確か
- 成果物の出力先が明確か
- 既存docs/sourceへの影響範囲が明確か
- 新規作成と既存修正の区別が明確か
- API / DB / generated / CI/CD への横断影響がないか

作業範囲が曖昧な場合は、Issue作成前に停止する。

---

### 5. 依存Issue / PRを確認する

Definitionに依存Issue、依存PR、親Epic、依存Epicが指定されている場合は、状態を確認する。

確認観点は以下。

- 親Epic Issueが存在するか
- 親Epic Branchが存在するか
- 依存Issueが完了しているか
- 依存PRがmerge済みか
- **依存 Epic (`dependencies.epics`) の Status が `Done` か**（成果物化方針書 §3.5.3）
- 未完了依存がある場合、今回Taskを開始してよいか
- Task Branchのbaseが親Epic Branchでよいか

依存Issue / PRが未完了で開始不可の場合は停止する。依存 Epic が `Done` でない場合は、`human_decision_points` への理由記載がなければ停止し、人間確認へ回す。

親Epic Issue / 親Epic Branch の存在確認結果は、**Issue本文には記載せず**、以下の出力形式でチャット（および必要に応じて dry-run 結果）へ明示する。

#### 5.1 親 Epic / Branch 存在チェック結果の出力

**用語（事実と推論を分ける）**

| 用語 | 意味 |
| ---- | ---- |
| **配置値** | Task Definition の `parent.epic_issue_number` / `parent.epic_branch` / `parent.epic_issue` に書かれた参照値（例: `#300`）。Definition 上の設定そのものを指す |
| **実在確認** | `gh issue view` / `git branch` 等で GitHub・リポジトリ上に存在するかを調べる作業 |
| **実在確認結果** | `存在` / `未検出` / `未確認` のいずれか（下表） |

| 実在確認結果 | 意味 |
| ------------ | ---- |
| `存在` | 実在確認を実施し、配置値（またはタイトル検索）で対象を特定できた |
| `未検出` | 実在確認を実施したが、GitHub / リポジトリ上に該当が見つからなかった |
| `未確認` | 実在確認を未実施、または権限・環境理由で確認できなかった |

**禁止表現（改善点・次 Action・Human確認で使用しない）**

- `parent.epic_issue_number: "#300" 未存在`（配置値の不備と実在確認結果を混同する）
- `親 Epic Issue + Branch を整備（または #300 を実番号に更新）`（手順が曖昧）

**推奨表現**

- 改善点: `parent.epic_issue_number` に設定された `#300` の GitHub 実在確認: **未検出**（`gh issue view` 実施済み）。配置値は Definition に存在する。
- 次 Action: 下記「親 Epic 未検出時の標準手順」

| 確認対象 | 確認方法の例 | 結果の記載 |
| -------- | ------------ | ---------- |
| 親Epic Issue | `parent.epic_issue_number` があれば `gh issue view <番号>`、なければ `parent.epic_issue` タイトルで `gh issue list --search` | `存在` / `未検出` / `未確認` |
| 親Epic Branch | `git branch -a` または `git ls-remote --heads origin <branch>` | `存在` / `未検出` / `未確認` |

```
### 親 Epic / Branch 存在チェック

| 項目 | 配置値（Definition） | 実在確認結果 | 根拠 |
| ---- | -------------------- | ------------ | ---- |
| 親Epic Issue | `<parent.epic_issue>` / `<parent.epic_issue_number>` | 存在 / 未検出 / 未確認 | （確認コマンド・要約） |
| 親Epic Branch | `<parent.epic_branch>` | 存在 / 未検出 / 未確認 | （確認コマンド・要約） |

#### 判定
- Branch作成可否: 可 / 不可 / 人間確認待ち
- 補足: （未検出・未確認時は「親 Epic 未検出時の標準手順」へ誘導）
```

| 結果の組み合わせ | 扱い |
| ---------------- | ---- |
| 両方 `存在` | Branch作成へ進める（`no-branch = false` の場合） |
| いずれか `未検出` | Branch作成前に停止、または Issue 作成のみで人間確認（推測で Branch base を決めない） |
| いずれか `未確認` | 人間確認事項として報告し、作業開始可能と断定しない |

**親 Epic 未検出時の標準手順（次 Action / 推奨対応の正本）**

1. **親 Epic Issue が未作成の場合**: `parent.epic_issue` のタイトル（例: `[Epic]レコメンド実行API`）で Epic Issue を作成し、発行された**実 Issue 番号**を Task Definition の `parent.epic_issue_number` に反映する。あわせて `parent.epic_branch` をブランチ運用ルールに従い作成する。
2. **既に親 Epic Issue が存在する場合**: その**実 Issue 番号**（および必要なら `epic_issue` / `epic_branch`）で Task Definition の `parent` を更新する。配置値と実番号の不一致を解消する。
3. Definition 反映後、`/start-task` を再実行し、§5.1 で実在確認結果が `存在` になることを確認してから Branch 作成・`/work-issue` へ進む。

#### 5.2 識別子・スコープ整合チェック（識別子付き Task）

`task.title` が `{識別子}:{概要}` 形式（識別子付き Task）の場合、以下を順に検査する（[成果物一覧×Task Definition化方針書](../../docs/00_共通/AIエージェント運用/成果物一覧×Task%20Definition化方針書.md) §3.5、Task Definition設計書 §15.0）。

1. **識別子 prefix 一致**:
   - `task.title` 先頭の識別子（例: `API-PUB-002`）を取得
   - `parent.epic_issue` のタイトル先頭識別子（`gh issue view <番号> --json title`）と比較
   - 不一致なら停止し、「Task 識別子と Parent Epic 識別子が一致していない」旨を人間確認へ
2. **依存 Epic Status 確認**:
   - `dependencies.epics` の各 Epic Issue 番号について `gh issue view --json state` を取得
   - `Done` でない依存 Epic がある場合、`human_decision_points` に理由が記載されているか確認
   - 記載がなければ停止
3. **`allowed_paths` 検査**:
   - `parent.epic_issue` の Definition から `epic_scope.allowed_paths` を取得
   - 本 Task の `output.files` / `parallel_control.exclusive_files` の各 path が、`allowed_paths` のいずれかの glob と一致するかを検査
   - 一致しない path が 1 つでもあれば停止し、「親 Epic の `allowed_paths` 外」旨を人間確認へ
   - `forbidden_paths` が記載されている場合は、各 path がそれに該当しないことも確認

allowed_paths 外を編集する必要が出た場合は、別 Epic 配下の Task として切り出す。本 Task の `dependencies.epics` にその Epic Issue 番号を追加し、Definition を更新してから `/start-task` を再実行する。

---

### 6. Issue化可能か判断する

以下を満たす場合、Issue化可能と判断する。

- Definitionが存在する
- schemaが妥当である
- 入力docsが存在する
- 出力先が明確である
- scope / out_of_scope が明確である
- 親Epicが必要な場合、親Epic Issue / Branch が明確である
- 依存Issue / PR が開始可能な状態である
- secretや権限に関する不明点がない
- 横断影響が大きすぎず、通常Taskとして扱える
- 人間判断が必要な論点が残っていない

Issue化できない場合は、Issue作成前フィードバックを返す。

---

### 7. 不足がある場合はIssue化前フィードバックを返す

Issue化できない場合は、以下の形式で返す。

```
## Issue化前フィードバック

### 停止種別
-

### 確認した事実
-

### 推論
-

### 不足情報
-

### 影響範囲
-

### 人間に確認したいこと
1.
2.
3.

### 推奨対応
-
```

必要に応じて、`ai-logs/intake/` への記録候補として扱う。

ただし、通常作業ログをすべて `ai-logs/` に保存しない。

---

### 8. 問題なければIssue本文を生成する

Issue本文テンプレートに従い、Issue本文を生成する。

Issue本文には、少なくとも以下を含める。

- 背景
- 目的
- scope
- out_of_scope
- 入力資料
- 対象ファイル
- 出力先
- 成果物
- 完了条件
- 確認観点
- 依存Issue / PR
- 想定Branch
- 想定PR target
- Issue同期項目（`issue.unit` / `issue.type` / `issue.area`。GitHub Label 名の一覧は含めない）
- Project同期項目（`project.project_name` / `project.fields.*`）
- Human Review要否

`Planned Start` / `Due Date` は、Issue本文生成時にAI Agentが明示的な日付へ解決する。`project.fields.planned_start` / `project.fields.due_date` に `{{issue_created_date}}` / `{{issue_created_date+2d}}` が指定されている場合、またはAI主導Taskで未指定の場合、Issue本文にはプレースホルダを残さず以下を入れる。

| 項目 | 解決値 | 形式 |
| ---- | ------ | ---- |
| `project.fields.planned_start` | Issue作成日（JST） | `YYYY-MM-DD` |
| `project.fields.due_date` | Issue作成日（JST） + 2日 | `YYYY-MM-DD` |

明示的な日付がDefinitionに指定されている場合はその値を使用する。ただし、AI主導Taskで標準値と異なる場合は、チャット出力のProject同期項目に「Definition明示値」として根拠を残す。日付計算に失敗した場合はIssue作成前に停止し、未解決プレースホルダをIssue本文へ出力しない。

---

### 9. Issueを作成する

Issue本文をもとにGitHub Issueを作成する。

Issue作成後、Issue番号を後続処理で利用する。

### 9.5 実Task Issue番号を関連Definitionへ反映する

Task Issue 作成に成功した場合、AI Agent は GitHub が返した**実 Issue 番号**を関連 Definition へ反映する。

反映してよい値は、以下で実在確認できたものに限定する。

| 値 | 確認方法 |
| ---- | -------- |
| Task Issue 番号 | `gh issue view <番号>` または Issue 作成結果 URL |
| 親 Epic Issue 番号 | `gh issue view <番号>` |
| 親 Epic Branch 名 | `git branch -a` または `git ls-remote --heads origin <branch>` |

反映対象は以下。

| 対象Definition | 反映項目 |
| -------------- | -------- |
| 対応 Review Definition | `target.issue` / `input.issue.number` |
| 対応 Review Definition | `target.parent_epic_issue` / `target.parent_epic_branch` |
| Task Definition | `parent.epic_issue_number` / `parent.epic_branch`（未反映または実値不一致の場合のみ） |
| 依存関係が確定した Task Definition | `dependencies.epics` |

ガード条件:

- Issue 番号を推測で記入しない。
- Issue タイトル検索で複数候補が出た場合は更新せず、人間確認へ回す。
- `parent.epic_issue_number` が `null` のまま、または親 Epic Branch が未確認のまま Branch 作成へ進まない。
- `target.issue` / `input.issue.number` に別 Task Issue 番号が入っている場合は上書きせず、人間確認へ回す。
- `dependencies.epics` に同じ Issue 番号を重複追加しない。
- 対象 Review Definition が存在しない場合は、チャットで「未反映項目」として明示し、必要なら Review Definition 作成を後続Task候補にする。
- dry-run では Definition を更新せず、反映予定の項目だけを出力する。
- `.env` 実値、token、secret を表示・保存しない。

---

### 10. Projectへ追加する

作成したIssueを対象GitHub Projectへ追加する。

Projectが不明な場合は停止し、人間確認へ回す。

---

### 11. Projectフィールドを同期する

DefinitionまたはProject運用ルールに従い、Projectフィールドを同期する。

同期元は Task Definition の `project.fields` とする。ただし、`planned_start` / `due_date` は §8 で解決した日付を同期対象とし、Issue本文・Project同期意図・dry-run出力で同じ値を使用する。`project` 直下に `status` / `phase` / `priority` を置かない（正本は `project.fields.status` 等）。

同期対象の例。

- `project.fields.status`
- `project.fields.phase`
- `project.fields.planned_start`
- `project.fields.due_date`
- `project.fields.priority`
- Parent Epic（Relationships）
- Actual Start / Actual End（workflow 連携時）

`issue.unit` / `issue.type` / `issue.area` は Projects ではなく GitHub Label へ同期する（§12）。

`/start-task` の主な Status 影響は、作業開始可能な場合の `project.fields.status`: `Todo` → `In Progress` の更新意図とする。

ただし、Status更新はCommandが直接確定するのではなく、GitHub Actionsまたは運用スクリプトが実施できるよう、更新意図を明確に出力する。

---

### 12. Labelを同期する

Issueに必要な GitHub Label を付与する（workflow または `gh label` 等）。

**Issue本文には Label 名の一覧を記載しない。** `prompts/templates/issue/task-issue.md` の §12 は「Issue同期項目」（`issue.unit` / `issue.type` / `issue.area`）のみを示す。付与する GitHub Label は、作業開始サマリの `### Label` に出力する。

Label は Task Definition の `issue.*` と `project.fields.priority` から**導出**する（Task Definition に `labels` 配列は置かない）。

| GitHub Label | 導出元 |
| ------------ | ------ |
| `unit: <unit>` | `issue.unit` |
| `type: <type>` | `issue.type` |
| `area: <area>` | `issue.area` |
| `priority: <priority>` | `project.fields.priority` |

`/start-task` のチャット出力・dry-run の「付与予定 Label」には、上記 4 種のみを列挙する。  
`ai-agent` / `human-led` は Issue テンプレート（`task-issue.md`）に作業主体フィールドがなく、Task Definition からも導出しないため、**出力しない**。

`no-branch` は Label ではなく Issue 本文のチェックまたは `branch.no_branch` から workflow が判定する。付与予定 Label の一覧には含めない。

Label判断に迷う場合は、推測で付与せず人間確認事項にする。

---

### 13. no-branchを判定する

Definitionの `no_branch` または `branch_policy` を確認する。

| 判定              | 扱い                                                 |
| ----------------- | ---------------------------------------------------- |
| no-branch = true  | Branchを作成せず、Issue作成・Project同期までで止める |
| no-branch = false | AI主導タスクであればBranch作成へ進む                 |
| 不明              | 人間確認事項にする                                   |

---

### 14. AI主導タスクの場合はBranchを作成する

AI主導タスクであり、Branch作成が必要な場合は、ブランチ運用ルールに従ってBranchを作成する。

確認する内容。

- Branch名
- Branch base
- 親Epic Branch
- main / develop への直接作業ではないこと
- Task Branchからdevelopへ直接PRしないこと
- 並列作業時のworktree要否

Branch作成で競合や前提不整合が発生した場合は、推測で解消せず停止する。

---

### 15. 作業開始可能であればStatusをIn Progressへ進める

以下を満たす場合、作業開始可能とする。

- Issueが作成されている
- Projectへ追加されている
- 必要なProjectフィールドが同期されている
- 必要なLabelが付与されている
- Branchが必要な場合、Branchが作成されている
- 依存Issue / PR が開始可能な状態である
- Worker AIへ引き継げる状態である

この場合、Project Statusを `In Progress` へ進める意図を出力する。

---

### 16. Worker AIへ作業を引き継ぐ

作業開始可能な場合は、Worker AIへ引き継ぐ情報を整理する。

引き継ぎ内容は以下。

- Issue番号
- Task Definition
- Branch
- PR target
- `input.docs`
- `output.docs`
- `output.files`
- scope
- out_of_scope
- acceptance_criteria
- test_policy
- 注意事項
- 停止条件

後続Commandは原則として `/work-issue @<definition>` とする。

---

### 17. 必要に応じてSlack通知を作成する

Slack通知が必要な場合は、通知用サマリを作成する。

Slack通知は正本ではない。

作業計画はIssue、作業結果はPR、成果物はdocsを正本とする。

---

## 出力

| 出力                    | 反映先                                    |
| ----------------------- | ----------------------------------------- |
| Issue本文               | GitHub Issue                              |
| Project同期項目         | GitHub Projects                           |
| Label                   | GitHub Issue                              |
| Branch                  | Git Branch                                |
| Status更新意図          | GitHub Projects / チャット                |
| Worker AI引き継ぎ情報   | チャット / 後続Command                    |
| 作業開始サマリ          | Slack / チャット                          |
| Issue化前フィードバック | チャット / 必要に応じて `ai-logs/intake/` |

---

## 成功条件

以下をすべて満たすこと。

- Issueが作成されている
- IssueがProjectへ追加されている
- Projectフィールドが同期されている
- 必要なLabelが付与されている
- AI主導タスクの場合、Branchが作成されている
- no-branchの場合、Branchを作成しない理由が明記されている
- 作業開始可能な場合、Statusを `In Progress` へ進める意図が明確である
- Worker AIへ引き継ぐ情報が整理されている
- 必要に応じてSlack通知サマリが作成されている
- Issue化前に停止した場合、停止理由と人間確認事項が明確である

---

## 失敗・停止条件

以下の場合は、Issue作成前に停止する。

- Definitionが存在しない
- Definitionの必須項目が不足している
- schema妥当性を確認できない
- 入力docsが存在しない
- 参照ファイルが存在しない
- 出力先が不明
- 作業範囲が曖昧
- `scope` と `out_of_scope` が矛盾している
- 親Epicが不明
- 親Epic Branchが不明
- 依存Issueが未完了
- 依存PRが未merge
- 依存 Epic (`dependencies.epics`) が `Done` でなく、`human_decision_points` に理由がない
- 識別子付き Task で `task.title` 識別子 prefix と Parent Epic 識別子 prefix が一致しない
- 識別子付き Task で `output.files` / `parallel_control.exclusive_files` が親 Epic の `epic_scope.allowed_paths` 外を含む
- Projectが不明
- Label判断に必要な情報が不足している
- Issue本文の `Planned Start` / `Due Date` をJST日付へ解決できない、または `{{issue_created_date}}` / `{{issue_created_date+2d}}` が本文に残る
- Branch baseが不明
- no-branch判定ができない
- 横断影響が大きく、人間判断が必要
- API contract変更が通常Taskに混在している
- DB schema変更が通常Taskに混在している
- generatedファイルの手動編集が必要に見える
- secretや権限に関わる不明点がある
- `.env` 実値を扱う必要がある
- main / develop へ直接変更する必要がある
- Human Reviewを省略する前提になっている
- AIがmerge判断を行う必要がある

---

## Human確認条件

以下の場合は、人間確認へ回す。

- 仕様判断が必要
- MVP対象かどうか判断が必要
- scope拡張が必要
- 正本docs間に矛盾がある
- どの正本を優先するか判断が必要
- 親Epicとの対応関係が不明
- Branch baseが不明
- Project同期項目が不明
- Label付与方針が不明
- no-branch判定が不明
- 依存Issue / PR が未完了だが着手可否判断が必要
- API契約・DB・generated・CI/CDへの横断影響がある
- security上の許容判断が必要
- 通常TaskではなくContract Task化すべき可能性がある
- Issue分割・Task分割が必要
- AIだけで進めると危険である

---

## 作業開始サマリ形式

作業開始可能な場合は、以下の形式で出力する。

```
## start-task 実行結果

### 判断
作業開始可能です。

### 作成Issue
- Issue:

### Project同期
- Project:
- Status更新意図:
- 同期フィールド:

### Label（GitHub Issue に付与。Issue本文には記載しない）
- `unit: …` / `type: …` / `area: …` / `priority: …`（`issue.*` と `project.fields.priority` から導出。`ai-agent` / `human-led` は出力しない）

### 親 Epic / Branch 存在チェック
- （§5.1 の表形式で記載）

### Branch
- Branch:
- Branch base:
- no-branch:

### Worker AI引き継ぎ
- 後続Command:
- Task Definition:
- `input.docs`:
- `output.docs`:
- `output.files`:
- acceptance_criteria:

### 注意事項
-

### Human確認事項
-
```

---

## Issue化前フィードバック形式

Issue作成前に停止する場合は、以下の形式で出力する。

```
## start-task 停止

### 停止種別
-

### 停止理由
-

### 確認した事実
-

### 推論
-

### 不足情報
-

### 影響範囲
-

### 人間に確認したいこと
1.
2.
3.

### 推奨対応
-
```

---

## dry-run 実行時

実際の Issue / Branch / Project / Slack / ファイル変更を行わない rehearsal では、以下を出力する。

1. 生成される Task Issue タイトル
2. 生成される Task Issue 本文（§8 の日付解決を適用し、`Planned Start` はdry-run実行日のJST日付、`Due Date` はdry-run実行日のJST日付 + 2日を明示する。§12 は Issue同期項目のみ。GitHub Label 一覧は含めない）
3. 付与予定 Label（`unit` / `type` / `area` / `priority` のみ。Issue 本文とは別。`ai-agent` / `human-led` は含めない）
4. 想定 Branch 名
5. Project 更新意図（`project.fields.*` を明示。`planned_start` / `due_date` はIssue本文と同じ解決後日付を示す）
6. 親 Epic / Branch 存在チェック（§5.1。表の列は「配置値」「実在確認結果」）
7. 次 Action（親 Epic 未検出時は §5.1「親 Epic 未検出時の標準手順」をそのまま用いる）
8. Definition / Template / Commands 運用上の改善点（任意。`#300 未存在` 等の禁止表現を使わない）

dry-run でも §5.1 の実在確認を実施する。結果は `存在` / `未検出` / `未確認` で記載し、配置値（`parent.epic_issue_number` 等）が Definition にあることと混同しない。

---

## 出力ルール

- 事実と推論を分けて書く
- 未確認事項を明示する
- Definitionのscope外作業をしない
- Issueなしで作業開始しない
- Projects Status変更だけでAI作業開始とみなさない
- Status更新は、更新意図として明確に出力する
- main / develop へ直接pushしない
- Task Branchからdevelopへ直接PRを作成しない
- Human Reviewを省略しない
- AIがPRをmergeしない
- generatedファイルを手動編集しない
- secret、APIキー、`.env` 実値を出力しない
- 通常作業ログをすべて `ai-logs/` に保存しない
- Slack通知だけで作業記録を完結させない
- Issue本文に GitHub Label 名の一覧を記載しない（`issue` 同期項目と `project.fields` のみ）
- `project.status` のように `project.fields` 配下でない Project 項目パスを正本として扱わない
