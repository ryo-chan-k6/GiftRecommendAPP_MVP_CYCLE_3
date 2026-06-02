# create-pr

## 目的

`/create-pr` は、作業BranchからPull Requestを作成するCommandである。

PRはレビュー正本であり、作業結果、変更差分、確認結果、テスト結果、AIレビュー依頼、人間レビュー観点を整理する。

主に以下の場合に利用する。

- `/work-issue` による作業が完了した場合
- 既存Task Branchの変更内容をPR化する場合
- AI Reviewへ進めるためにPR本文を整理する場合
- Task IssueとPRの紐づけを明確にする場合
- 実施済みテスト・未実施テスト・残課題をレビュー可能な形に整理する場合

このCommandは、実装・docs修正・test修正そのものを行うCommandではない。  
作業内容に不足がある場合は、PRを作成せず `/work-issue` へ戻す。

---

## 標準形式

```text
/create-pr @<definition>
```
例：

```text
/create-pr @prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml
```
Definitionなしでの実行は原則禁止する。

---

## 主担当Agent

| 項目   | Agent       |
| ------ | ----------- |
| 主担当 | Worker AI   |
| 補助   | Support AI  |
| 後続   | Reviewer AI |

---

## 参照する定義・Rules

必要に応じて以下を参照する。

- `AGENTS.md`
- `.cursor/agents/worker-ai.md`
- `.cursor/agents/support-ai.md`
- `.cursor/agents/reviewer-ai.md`
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

PR作成時は、特に以下を重視する。

- IssueとBranchの対応
- PR target
- Task Branchと親Epic Branchの関係
- Task IssueとPR本文の紐づけ
- テスト結果の明記
- Human Reviewを省略しないこと
- Issue close / Projects Done をPR本文の自動closeキーワードに依存しないこと

---

## 入力

| 入力               | 必須     | 内容                                              |
| ------------------ | -------- | ------------------------------------------------- |
| Issue              | 必須     | 対象Issue。作業計画、完了条件、関連Epicを確認する |
| Branch             | 必須     | 作業Branch。PR作成元Branch                        |
| Task Definition    | 必須     | 作業条件、scope、完了条件、確認観点を定義する     |
| PR Template        | 必須     | PR本文テンプレート                                |
| diff               | 必須     | 変更差分                                          |
| test results       | 推奨     | 実施したテスト・検証結果                          |
| parent Epic Branch | 条件付き | Task PRの場合、PR targetとして利用する            |
| related docs       | 条件付き | 作成・更新したdocs確認に利用する                  |
| CI results         | 条件付き | CI実行済みの場合、結果確認に利用する              |

---

## 処理手順

### 1. 対象Issueを確認する

対象Issueを確認し、以下を整理する。

- Issue番号
- Issueタイトル
- Issue種別
- 親Epic Issue
- 作業目的
- scope
- out_of_scope
- 完了条件
- 関連Branch
- 関連PR有無
- Project Status
- Label
- Human Review要否

Issueが存在しない、またはBranchとの対応が不明な場合はPR作成を停止する。

---

### 2. 作業Branchを確認する

現在の作業Branchを確認する。

確認観点は以下。

- 対象Issueに対応するBranchか
- Branch名がブランチ運用ルールに従っているか
- main / develop へ直接作業していないか
- Task Branchからdevelopへ直接PRしようとしていないか
- Task Branchのbaseが親Epic Branchになっているか
- 他TaskのBranchと混同していないか

Branchが不明、またはbaseが誤っている場合はPR作成を停止する。

---

### 3. Task Branchが親Epic Branchの最新状態を取り込んでいるか確認する

Task Branchが親Epic Branchの最新状態を取り込んでいるか確認する。

最新でない場合は、PR作成前に親Epic Branchの最新状態を取り込む。

ただし、以下の場合は推測で解消せず停止する。

- merge / rebaseで競合が発生した
- 親Epic Branch側の変更内容が現在Taskの前提と衝突している
- 最新化によりTask Definitionのscope外変更が必要になる
- 他Taskの成果物と競合する可能性がある

---

### 4. PR targetを確認する

PR targetを確認する。

Task PRの場合、原則として親Epic BranchをPR targetとする。  
Task Branchから `develop` へ直接PRを作成しない。

| PR種別    | PR target        | Issue参照                               |
| --------- | ---------------- | --------------------------------------- |
| Task PR   | 親Epic Branch    | `Related to #<Task Issue番号>` のみ（**先頭行推奨**） |
| Epic PR   | `develop`        | 必要に応じて `Closes #<Epic Issue番号>` |
| Hotfix PR | 運用ルールに従う | Issue運用ルールに従う                   |

Task PR では **`Closes #<Task Issue番号>` を記載しない**（`pr-created` 等の workflow が Task Issue を誤って close する、および Projects 完了制御と競合するため）。  
Task Issueの close / Projects Done 更新は、PR本文の `Closes #...` に依存しない。  
Task Issueの完了制御は、Task PRが親Epic Branchへmergeされた時点でGitHub Actions workflowにより明示的に行う。

---

### 5. Task Definitionを確認する

Task Definitionを読み込み、以下を確認する。

- task_id
- title
- objective
- scope
- out_of_scope
- `input.docs`
- `output.docs`
- `output.files`
- test_files
- deliverables
- acceptance_criteria
- test_policy
- human_review_required
- `contract_gate`（Implementation Task で Gate 通過済みか PR 本文に明記する）

IssueとDefinitionの内容が矛盾する場合は、PR作成を停止する。

Implementation Task で `packages/contracts/**` または `apps/**/generated/**` の差分があるが、同一 Branch に先行 Contract 変更がない場合は、Contract Gate 未充足の可能性があるため PR 作成を停止し `/create-contract-task` を検討する。

---

### 5.5 Review Definition の解決可否を確認する（AI Review 前提・hard stop）

Task Definition の `review.ai_review_required` を確認する。

| `ai_review_required` | 扱い |
| -------------------- | ---- |
| `true`（既定） | PR head（本 Branch の変更ファイル）または規約パスから Review Definition が解決できることを必須とする |
| `false` | Review Definition を必須としない（AI Review 自動dispatch はスキップ）。ただし Task Definition に理由が明示されていること。Human Review は省略しない |

`ai_review_required: true` の場合、PR 作成前に、対象 Task に対応する **Review Definition** が以下のいずれかで解決可能かを確認する（正本: `.github/scripts/resolve-review-definition.cjs`、観点: [ai-review.mdc](../../.cursor/rules/ai-review.mdc) §3.18）。

1. 本 Branch の変更ファイルに `prompts/definitions/reviews/<workstream>/pr-review.yaml`（または Task Definition と同ディレクトリの `pr-review.yaml`）が含まれている
2. 上記が workstream 規約パス（`tasks/<workstream>/` と一致する `reviews/<workstream>/pr-review.yaml`）に存在する
3. PR 本文に Review Definition パスを明示する（`/review-pr @<path>` 等）

確認例（PR head の状態で実行。Review Definition が本 Branch の差分に含まれているかを確認する）:

```bash
git diff --name-only <親Epic Branch>...HEAD | grep -E 'prompts/definitions/reviews/.+/pr-review\.yaml$'
```

解決ロジック（`resolve-review-definition.cjs`）は CLI ではなくモジュールであり、`pr-created` workflow / Definition Run Harness から呼び出される。`/create-pr` 時点では、上記のように Review Definition が PR head の差分に含まれること（または規約パスに存在し PR 本文で明示されること）を確認する。

**hard stop**: `ai_review_required: true`（または未指定で既定 `true`）であるにもかかわらず、Review Definition が PR head（変更ファイル）からも規約パスからも解決できない場合は、**PR 作成を停止する**。Review Definition が default branch にしか無い／未作成のままでは、PR 作成後の AI Review 自動dispatch（`pr-created`）が `review_definition_not_found` で失敗するため、PR 作成前に作成して本 Branch（PR head）へ commit する。

`ai_review_required: false` の場合は本 hard stop の対象外とするが、Task Definition に理由が明示されていることを確認する。

---

### 5.6 Epic PR の Review Definition を確認する（AI Review 前提・hard stop）

Epic PR（PR target が `develop` で、Epic Definition を入力として作成する場合）では、Task 向け Review Definition とは別に、Epic PR 向け Review Definition を必須とする。

| PR種別 | 必須 Review Definition |
| ------ | ---------------------- |
| Task PR | `prompts/definitions/reviews/<workstream>/pr-review.yaml`（または Task Definition sibling） |
| Epic PR | `prompts/definitions/reviews/<workstream>/epic/pr-review.yaml` |

Epic PR の場合、以下を確認する。

1. 本 Branch の変更ファイル、または規約パスに `prompts/definitions/reviews/<workstream>/epic/pr-review.yaml` が存在する
2. Review Definition の `review.type` が `epic_pr_review` である
3. Review Definition の `target.issue` が Epic Issue と一致する
4. PR 本文が Epic PR 規約（`Closes #<Epic Issue番号>`）と整合する

**hard stop**: Epic PR で上記が満たせない場合は PR 作成を停止する。Task 向け Review Definition（`.../pr-review.yaml`）のみで Epic PR を作成してはならない。

---

### 6. diffを確認する

作業Branchのdiffを確認する。

確認観点は以下。

- 変更ファイルがTask Definitionのscope内か
- 意図しないファイル変更がないか
- out_of_scopeの変更が含まれていないか
- secretや`.env`実値が含まれていないか
- generatedファイルを手動編集していないか
- API contract変更が混在していないか（契約変更は Contract Task / 先行 Contract PR に分離されているか）
- API docs が `api-contract-spec.md` / `api-implementation-spec.md` の意図した面のみを更新しているか（廃止済み `api-spec.md` を復活させていないか）
- DB schema変更が混在していないか
- CI/CD設定変更が混在していないか
- docsとsource codeの整合性が取れているか
- test追加・修正が必要な変更に対してtestが用意されているか

diffがTask Definitionのscopeを超えている場合は、PR作成を停止する。

---

### 7. 変更内容を整理する

PR本文に記載するため、変更内容を整理する。

整理対象は以下。

- 何を変更したか
- なぜ変更したか
- どのIssue / Task Definitionに対応するか
- 作成・更新した成果物
- 変更したsource code
- 追加・更新したtest
- 影響範囲
- レビューで重点確認してほしい箇所

---

### 8. 実施した確認・テスト結果を整理する

実施したテスト・検証結果を整理する。

記載対象の例。

- unit test
- integration test
- contract test
- e2e test
- lint
- typecheck
- build
- docs lint
- Mermaid構文確認
- OpenAPI validation
- Orval生成確認
- CI結果

テストを実施していない場合は、以下を必ず記載する。

- 未実施のテスト
- 未実施理由
- 代替確認
- 残リスク
- 人間に確認してほしいこと

実施していないテストを実施済みとして記載してはならない。

---

### 9. 未実施事項・残課題を整理する

PR本文に記載するため、未実施事項と残課題を整理する。

分類例。

| 分類                        | 扱い                                       |
| --------------------------- | ------------------------------------------ |
| 今回Taskの未完了事項        | PR作成前に `/work-issue` へ戻す            |
| scope外の後続作業           | follow-up Issue候補として整理する          |
| 人間判断が必要な事項        | Human Review観点として明記する             |
| Contract Task化が必要な事項 | `/create-contract-task` 候補として整理する |

未完了事項が完了条件に関わる場合は、PR作成を停止する。

---

### 10. PRテンプレートに沿ってPR本文を作成する

PR Templateに従い、PR本文を作成する。

PR本文には、少なくとも以下を含める。

```text
## 概要

## 対象Issue

## 対応内容

## 変更ファイル

## 作成・更新した成果物

## テスト・検証結果

## 未実施事項

## 残課題

## レビュー観点

## Human Reviewで確認してほしいこと

## 関連Issue / PR
```
Task PRの場合は、GitHubの自動closeキーワードを使用せず、以下を記載する。

```text
Related to #<Task Issue番号>
```
Epic PRの場合は、必要に応じて以下を記載してよい。

```text
Closes #<Epic Issue番号>
```
---

### 11. PRを作成する

確認が完了した場合、PRを作成する。

**Machine account 認証（必須）:** PR open 前に bot 認証を確認する（[github-operation.mdc](../../.cursor/rules/github-operation.mdc) §3.16、[AI機械アカウント運用設計書](../../docs/00_共通/AIエージェント運用/AI機械アカウント運用設計書.md)）。

```bash
node .github/scripts/gh-bot-auth.cjs verify
eval "$(node .github/scripts/gh-bot-auth.cjs print-setup)"
```

PR 作成後、`gh pr view <番号> --json author --jq .author.login` が `.github/ai-bot-account.json` の `machine_account_login` であることを確認する。

PR作成時に確認すること。

- PR titleが適切か
- PR targetが正しいか
- PR source branchが正しいか
- Task IssueとPRが紐づいているか
- PR本文がテンプレートに沿っているか
- `Related to #<Task Issue番号>` が記載されているか
- テスト結果が記載されているか
- Human Review観点が記載されているか
- Issue close / Projects Done を自動closeキーワードに依存していないか

### 11.5 実PR番号をReview Definitionへ反映する

PR 作成に成功した場合、AI Agent は GitHub が返した**実 PR 番号**を対応 Review Definition へ反映する。

反映してよい値は、以下で実在確認できたものに限定する。

| 値 | 確認方法 |
| ---- | -------- |
| PR 番号 | `gh pr view <番号>` または PR 作成結果 URL |
| Task Issue 番号 | PR本文の `Related to #<Task Issue番号>` と `gh issue view <番号>` |
| PR target | `gh pr view <番号> --json baseRefName,headRefName` |

反映対象は以下。

| 対象Definition | 反映項目 |
| -------------- | -------- |
| 対応 Review Definition | `target.pr` / `input.pr.number` |
| 対応 Review Definition | `target.issue` / `input.issue.number`（未反映の場合のみ） |
| 対応 Review Definition | `target.source_branch` / `target.target_branch`（実Branchと不一致の場合のみ、人間確認後に反映） |

ガード条件:

- PR 番号を推測で記入しない。
- `target.pr` / `input.pr.number` に別 PR 番号が入っている場合は上書きせず、人間確認へ回す。
- `target.issue` / `input.issue.number` と PR本文の `Related to #...` が不一致の場合は更新せず、人間確認へ回す。
- PR target が Task Definition の `branch.target` または Review Definition の `target.target_branch` と不一致の場合は更新せず、PR作成結果を停止扱いで報告する。
- 対応 Review Definition が存在しない場合は、チャットで「未反映項目」として明示し、`/review-pr @<definition> #<PR番号>` の形で次Actionを提示する。
- dry-run では Definition を更新せず、反映予定の項目だけを出力する。
- `.env` 実値、token、secret を表示・保存しない。

---

### 12. Project Statusを AI Review へ進める

PR作成後、Project Statusを `AI Review` へ進める意図を出力する。

Status更新は、Commandが直接確定するのではなく、GitHub Actionsまたは運用スクリプトが実施できるよう、更新意図として明確に出力する。

---

### 13. 必要に応じてSlack通知を作成する

必要に応じて、PR作成通知用のSlackサマリを作成する。

Slack通知には以下を含める。

- PRタイトル
- PR URL
- 対象Issue
- 概要
- レビュー依頼先
- 注意事項
- 次のStatus

Slack通知は正本ではない。  
作業結果はPR、成果物はdocs、作業計画はIssueを正本とする。

---

### 14. 次Commandを提示する

PR作成後、次Commandとして `/review-pr @<definition>` を提示する。

```text
/review-pr @<definition> #<PR番号>
```
---

## 出力

| 出力           | 反映先                                       |
| -------------- | -------------------------------------------- |
| PR             | GitHub Pull Request                          |
| PR本文         | Pull Request                                 |
| Issue参照      | Pull Request                                 |
| Status更新意図 | GitHub Projects / チャット                   |
| PR作成通知     | Slack / チャット                             |
| AI Review依頼  | Pull Request / チャット                      |
| 停止理由       | チャット / 必要に応じて `ai-logs/incidents/` |

---

## 成功条件

以下をすべて満たすこと。

- PRが作成されている
- PR source branchが正しい
- PR targetが正しい
- Task Branchが親Epic Branchの最新状態を取り込んでいる
- IssueとPRが紐づいている
- Task PRの場合、`Related to #<Task Issue番号>` が記載されている
- Epic PRの場合、必要に応じて `Closes #<Epic Issue番号>` が記載されている
- PR本文がテンプレートに沿っている
- 変更内容が整理されている
- 変更ファイルが整理されている
- `review.ai_review_required: true` の場合、対応する Review Definition が PR head（変更ファイル）または規約パスから解決可能である（§5.5）
- Epic PR の場合、`prompts/definitions/reviews/<workstream>/epic/pr-review.yaml` が解決可能である（§5.6）
- テスト結果が記載されている
- 未実施事項がある場合、その理由と残リスクが記載されている
- レビュー観点が記載されている
- Human Reviewで確認してほしいことが記載されている
- Statusを `AI Review` へ進める意図が明確である
- Issue close / Projects Done はPR merge時workflowで制御される前提になっている
- 次Commandとして `/review-pr` へ進める状態になっている

---

## 停止条件

以下の場合はPR作成を停止し、人間へ確認する。

- Issueが存在しない
- IssueとBranchの対応が不明
- Branchが存在しない
- Branch baseが誤っている
- commitが存在しない
- PR targetが不明
- Task Branchからdevelopへ直接PRしようとしている
- Task Branchが親Epic Branchの最新状態を取り込んでいない
- 親Epic Branchとの最新化で競合が発生している
- Task Definitionが存在しない
- IssueとTask Definitionの内容が矛盾する
- diffを確認できない
- diffにscope外変更が含まれている
- out_of_scopeの変更が含まれている
- secretや`.env`実値が含まれている
- generatedファイルを手動編集している
- API contract変更が通常Taskに混在している
- DB schema変更が通常Taskに混在している
- CI/CD設定変更の扱いが不明
- テスト未実施理由が不明
- 完了条件を満たしていない
- PR本文に必要な情報を生成できない
- 前段成果物の大きな修正が必要であり、現在のTask内で扱うべきか判断できない
- Task Definition の `review.ai_review_required` が `true`（または未指定で既定 `true`）であるのに、対応する Review Definition が PR head（変更ファイル）からも規約パスからも解決できない（§5.5。`false` の場合は対象外）
- Epic PR で、`prompts/definitions/reviews/<workstream>/epic/pr-review.yaml` が未作成・未解決、または `review.type: epic_pr_review` を満たさない
- Human Reviewを省略する前提になっている
- AIがmerge判断を行う必要がある

---

## Human確認条件

以下の場合は、人間確認へ回す。

- PR targetの判断が必要
- Branch baseの判断が必要
- Task Branchと親Epic Branchの競合解消が必要
- IssueとDefinitionのどちらを優先するか判断が必要
- scope外変更を同一PRに含めるべきか判断が必要
- 前段成果物の修正を現在Taskで扱うべきか判断が必要
- API contract変更をContract Task化すべきか判断が必要
- DB schema変更を専用Task化すべきか判断が必要
- generated再生成方針の判断が必要
- テスト未実施の許容判断が必要
- CI失敗をPR作成前に解消すべきか判断が必要
- security上の許容判断が必要
- Human Review観点の追加が必要
- PR作成前にIssue分割・Task分割すべき可能性がある

---

## Statusへの影響

`/create-pr` のStatus影響は以下とする。

| 状況            | Status更新意図                       |
| --------------- | ------------------------------------ |
| PR作成成功      | `In Progress` → `AI Review`          |
| PR作成停止      | 原則 `In Progress` のまま            |
| 人間判断待ち    | `In Progress` または運用ルールに従う |
| 既にAI Review中 | 重複PR作成せず停止                   |

Status更新は、Commandが直接確定するのではなく、GitHub Actionsまたは運用スクリプトが実施できるよう、更新意図として明確に出力する。

---

## Issue close / Done制御

Task Issueの完了制御は、PR本文のGitHub自動closeキーワードに依存しない。

Task PRでは原則として以下を記載する。

```text
Related to #<Task Issue番号>
```
Task Issueは、対応するTask PRが親Epic Branchへmergeされた時点で、GitHub Actions workflowにより `Done` とする。

Epic PRでは必要に応じて以下を記載してよい。

```text
Closes #<Epic Issue番号>
```
Epic Issueは、配下Task Issueがすべて `Done` となり、Epic Branchが `develop` へmergeされた時点で `Done` とする。

---

## ai-logs利用方針

通常のPR作成ログをすべて `ai-logs/` に保存しない。

必要な場合のみ、以下の方針で記録候補にする。

記録対象・ディレクトリ構成の正本は [AIログ運用ルール](../../docs/00_共通/AIエージェント運用/AIログ運用ルール.md) §4・§6 とする。

| 種別                    | 保存先                     |
| ----------------------- | -------------------------- |
| Issue化前フィードバック | `ai-logs/intake/`          |
| 作業停止・例外          | `ai-logs/incidents/`       |
| 人間判断待ち            | `ai-logs/human-decisions/` |
| 横断影響                | `ai-logs/cross-cutting/`   |
| AI運用検証              | `ai-logs/experiments/`     |

通常の作業計画はIssue、作業結果はPR、成果物はdocsを正本とする。

---

## Slack通知

必要に応じて、PR作成通知をSlack通知用に整形する。

通知例。

```text
## PR作成通知

### PR
-

### 対象Issue
-

### 概要
-

### レビュー依頼
-

### 注意事項
-

### 次のStatus
AI Review
```
Slack通知は正本ではない。  
PR内容はPull Request、作業計画はIssue、成果物はdocsに記録する。

---

## PR作成完了時の出力形式

PR作成が完了した場合は、以下の形式で出力する。

```text
## create-pr 実行結果

### 判断
PR作成完了です。次に `/review-pr` へ進めます。

### 対象Issue
-

### 対象Branch
-

### PR
-

### PR target
-

### Issue紐づけ
-

### 変更概要
-

### テスト・検証結果
-

### 未実施事項
-

### 残課題
-

### Human Review観点
-

### Status更新意図
In Progress → AI Review

### 次に実行するCommand
/review-pr @<definition> #<PR番号>
```
---

## 停止時の出力形式

PR作成を停止する場合は、以下の形式で出力する。

```text
## create-pr 停止

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

## 出力ルール

- 事実と推論を分けて書く
- 未確認事項を明示する
- IssueとBranchの対応を確認する
- PR targetを確認する
- Task Branchが親Epic Branchの最新状態を取り込んでいるか確認する
- Task Branchからdevelopへ直接PRを作成しない
- Task PRでは `Related to #<Task Issue番号>` を記載する
- Task PRでは原則として `Closes #<Task Issue番号>` を使用しない
- Issue close / Projects Done をPR本文の自動closeキーワードに依存しない
- PR本文に変更内容、テスト結果、未実施事項、レビュー観点を記載する
- 実施していないテストを実施済みと書かない
- Definitionのscope外変更をPRに含めない
- `review.ai_review_required: true` のTaskで Review Definition が PR head から解決できない場合はPRを作成せず停止する（§5.5）
- Epic PR では Task 向け Review Definition を流用せず、Epic 向け `.../epic/pr-review.yaml` が解決できない場合はPRを作成せず停止する（§5.6）
- generatedファイルを手動編集しない
- secret、APIキー、`.env`実値を出力しない
- Human Reviewを省略しない
- AIがPRをmergeしない
- 通常作業ログをすべて `ai-logs/` に保存しない
- Slack通知だけで作業記録を完結させない
