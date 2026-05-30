# review-pr

## 目的

`/review-pr` は、PRをAIレビューするCommandである。

人間レビュー前に、Issue、Task Definition、PR差分、docs、テスト結果、CI結果の整合性を確認し、Human Reviewへ進めてよいか、修正が必要か、人間判断が必要かを整理する。

主に以下の場合に利用する。

- `/create-pr` によりPRが作成された後、AI Reviewを実施する場合
- PR差分がIssue / Task Definitionのscopeを満たしているか確認する場合
- docs / source code / test / API contract / generated / CI結果を横断確認する場合
- Human Review前に、AI観点のレビューコメントをPRへ記録する場合
- 修正要否と次Statusの判断材料を出す場合

このCommandは、レビューを行うCommandであり、修正作業は行わない。  
修正が必要な場合は、原則として `/fix-review-comments` に引き継ぐ。

---

## 標準形式

```text
/review-pr @<definition>
```
例：

```text
/review-pr @prompts/definitions/_examples/review-definition.example.yaml
```
PR番号を併記してもよい。

```text
/review-pr @prompts/definitions/_examples/review-definition.example.yaml #123
```
Definitionなしでの実行は原則禁止する。

---

## 主担当Agent

| 項目   | Agent                                    |
| ------ | ---------------------------------------- |
| 主担当 | Reviewer AI                              |
| 補助   | Docs Reviewer AI / Test AI / Contract AI |
| 後続   | Fixer AI / Human                         |

---

## 参照する定義・Rules

必要に応じて以下を参照する。

- `AGENTS.md`
- `.cursor/agents/reviewer-ai.md`
- `.cursor/agents/docs-reviewer-ai.md`
- `.cursor/agents/test-ai.md`
- `.cursor/agents/contract-ai.md`
- `.cursor/agents/fixer-ai.md`
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

PRレビュー時は、特に以下を重視する。

- IssueとPRの対応
- Task Definitionのscope / out_of_scope
- PR target
- Task Branchと親Epic Branchの関係
- diffの妥当性
- docs / source code / test の整合性
- API contract / DB schema / generated への横断影響
- テスト結果・CI結果
- Human Reviewへ進める条件
- 修正が必要な場合の指摘粒度
- AIがmerge判断をしないこと

---

## 入力

| 入力            | 必須     | 内容                                               |
| --------------- | -------- | -------------------------------------------------- |
| PR              | 必須     | レビュー対象PR                                     |
| PR diff         | 必須     | 変更差分                                           |
| Issue           | 必須     | 作業計画、scope、完了条件を確認する                |
| Task Definition | 必須     | 完了条件・確認観点・対象成果物を定義する           |
| `output.docs`     | 条件付き | 作成・更新された成果物                             |
| test results    | 条件付き | 実施されたテスト・検証結果                         |
| CI results      | 条件付き | CI実行結果                                         |
| PR Template     | 推奨     | PR本文の記載内容確認に利用する                     |
| related docs    | 条件付き | 正本docs・関連docsとの整合性確認に利用する         |
| generated diff  | 条件付き | OpenAPI / Orval / generated 等の差分確認に利用する |

---

## 処理手順

### 1. PRを確認する

対象PRを確認する。

確認観点は以下。

- PR番号
- PRタイトル
- PR本文
- PR source branch
- PR target branch
- PR作成者
- 関連Issue
- 関連Task Definition
- 現在のReview状態
- 現在のProject Status
- CI実行状況

PRが存在しない、または対象PRを特定できない場合は停止する。

### 1.5 Review Definition の実番号反映状態を確認する

Review Definition に `target.pr` / `input.pr.number` / `target.issue` / `input.issue.number` がある場合、PR・Issue の実在と対応を確認する。

確認観点は以下。

| 項目 | 確認内容 |
| ---- | -------- |
| `target.pr` / `input.pr.number` | `gh pr view <番号>` で実在するか、コマンド引数の PR 番号と一致するか |
| `target.issue` / `input.issue.number` | `gh issue view <番号>` で実在するか、PR本文の `Related to #<Task Issue番号>` と一致するか |
| `target.source_branch` | PR の `headRefName` と一致するか |
| `target.target_branch` | PR の `baseRefName` と一致するか |
| `parent_epic_issue` / `parent_epic_branch` | Task PR の親 Epic と一致するか |

ガード条件:

- Review Definition の PR番号・Issue番号を推測で補完しない。
- コマンド引数の PR 番号と `target.pr` / `input.pr.number` が不一致の場合はレビューを停止する。
- `target.issue` / `input.issue.number` と PR本文の `Related to #...` が不一致の場合はレビューを停止する。
- `target.pr` / `input.pr.number` が `null` で、コマンド引数に PR 番号がある場合は、その番号を今回レビューの確認対象として利用してよい。ただし、Review Definition への永続反映は `/create-pr` の責務として「未反映項目」に記録する。
- `target.issue` / `input.issue.number` が `null` で、PR本文から Task Issue 番号を一意に特定できる場合は、今回レビューの確認対象として利用してよい。ただし、Review Definition への永続反映は `/start-task` または `/create-pr` の責務として「未反映項目」に記録する。
- PR本文に `Related to #...` が複数ある、または Task Issue を一意に特定できない場合はレビューを停止し、人間確認へ回す。
- `.env` 実値、token、secret を表示・保存しない。

`/review-pr` はレビュー Command であり、Review Definition の永続更新は原則として行わない。永続反映が必要な場合は、`/start-task` または `/create-pr` の番号反映手順へ戻す。

---

### 2. 対象Issueを確認する

PRに紐づくIssueを確認する。

確認観点は以下。

- Issue番号
- Issueタイトル
- Issue種別
- 親Epic Issue
- scope
- out_of_scope
- 完了条件
- Label
- Project Status
- 依存Issue / PR
- Human Review要否

Task PRの場合、PR本文には原則として以下が記載されていることを確認する。

```text
Related to #<Task Issue番号>
```
Task PRでは、原則として `Closes #<Task Issue番号>` を使用しない。  
Task Issueの close / Projects Done は、PR merge時のGitHub Actions workflowで制御される前提とする。

---

### 3. Task Definitionを確認する

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
- `review.review_points`
- test_policy
- human_review_required

Issue、Task Definition、PR本文の内容が矛盾する場合は、レビューを停止する。

---

### 4. PR targetを確認する

PR targetがブランチ運用ルールに沿っているか確認する。

| PR種別    | 正しいPR target  |
| --------- | ---------------- |
| Task PR   | 親Epic Branch    |
| Epic PR   | `develop`        |
| Hotfix PR | 運用ルールに従う |

Task Branchから `develop` へ直接PRを作成している場合は、レビューを停止する。

---

### 5. Task Branchが親Epic Branchの最新状態を取り込んでいるか確認する

Task Branchが親Epic Branchの最新状態を取り込んでいるか確認する。

確認観点は以下。

- 親Epic Branchの最新状態が取り込まれているか
- merge / rebaseの競合が残っていないか
- 他Taskの変更と競合していないか
- 古い前提のままPRが作成されていないか

最新化されていない場合は、原則として `request_changes` または `blocked` として扱う。

---

### 6. PR diffを確認する

PR diffを確認し、変更内容を分類する。

分類例。

| 分類         | 確認内容                                             |
| ------------ | ---------------------------------------------------- |
| docs         | 設計書、仕様書、運用docs、Mermaid、用語              |
| source code  | apps、packages、scripts、config等                    |
| test         | unit / integration / contract / e2e / fixture / mock |
| API contract | API仕様、OpenAPI、Orval、API client                  |
| DB           | schema、migration、seed、ER、テーブル設計            |
| CI/CD        | GitHub Actions、build、deploy、lint                  |
| generated    | OpenAPI / Orval 等の生成物                           |
| security     | secret、認証認可、権限、ログ、`.env` 実値            |

以下を確認する。

- diffがTask Definitionのscope内か
- out_of_scopeの変更が含まれていないか
- 意図しないファイル変更がないか
- 変更理由がPR本文で説明されているか
- 成果物とsource codeの整合性があるか
- testが必要な変更に対してtestが用意されているか
- secretや`.env`実値が含まれていないか
- generatedファイルを手動編集していないか

#### 6.1 親 Epic スコープ越境チェック（識別子付き Task）

対象 PR の Task が識別子付き（`task.title` が `{識別子}:{概要}` 形式）の場合、PR 差分の全 path が親 Epic の `epic_scope.allowed_paths` 内に収まっていることを必ず検査する（[成果物一覧×Task Definition化方針書](../../docs/00_共通/AIエージェント運用/成果物一覧×Task%20Definition化方針書.md) §3.5、[AIレビュー運用設計書](../../docs/00_共通/AIエージェント運用/AIレビュー運用設計書.md) §13.2、[Commands設計書](../../docs/00_共通/AIエージェント運用/Commands設計書.md) §17）。

1. `parent.epic_issue` の Epic Definition から `epic_scope.allowed_paths` と `epic_scope.forbidden_paths` を取得
2. `gh pr diff <PR番号> --name-only` で差分 path 一覧を取得
3. 各 path が `allowed_paths` のいずれかの glob に一致するか検査
4. `forbidden_paths` に一致する path がないか検査
5. PR 識別子 prefix（PR タイトル / 関連 Issue タイトル先頭）と親 Epic 識別子 prefix が一致しているか確認

**越境した path が 1 つでもある場合は `blocked` または `request_changes` とする**。コメントには越境 path とそれが本来属するべき Epic 候補（例: `apps/reco/**` は `MOD-RECO` Epic）を明示する。

`MOD-RECO-NNN` 個別モジュール Epic 配下の Task で `apps/reco/src/app/**`（API-INT エンドポイント層）に差分が出ている場合も同様に `blocked` とする（エンドポイント層は API-INT-NNN Epic の `allowed_paths`）。

---

### 7. `output.docs`を確認する

作成・更新されたdocsを確認する。

確認観点は以下。

- 指定された成果物が作成・更新されているか
- 正本docsと矛盾していないか
- 用語集・ユビキタス言語と整合しているか
- 章構成・表記・粒度が既存docsと整合しているか
- 古い方針や廃止済み記述が残っていないか
- Mermaid構文に問題がないか
- docs間の参照関係が破綻していないか
- Notion転記やMarkdown利用を想定した体裁になっているか

docs専門確認が必要な場合は、Docs Reviewer AIの観点を利用する。

---

### 8. 完了条件を満たしているか確認する

Task Definitionの `acceptance_criteria` をもとに、完了条件を確認する。

確認結果は以下に分類する。

| 判定                | 意味                           |
| ------------------- | ------------------------------ |
| satisfied           | 完了条件を満たしている         |
| partially_satisfied | 一部不足がある                 |
| not_satisfied       | 完了条件を満たしていない       |
| unclear             | 判定に必要な情報が不足している |

完了条件を満たしていない場合は、原則として `request_changes` とする。

---

### 9. 確認観点を満たしているか確認する

Task DefinitionやReview Definitionに記載された確認観点をもとにレビューする。

確認観点の例。

- 設計方針に合っているか
- 既存アーキテクチャと整合しているか
- 責務分離が崩れていないか
- 命名が適切か
- 変更粒度が適切か
- 不要な抽象化や過剰実装がないか
- MVP範囲を超えていないか
- 運用ルールと矛盾していないか
- 後続Taskに悪影響を与えないか

---

### 10. テスト結果・CI結果を確認する

PR本文、test results、CI resultsを確認する。

確認対象の例。

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
- GitHub Actions結果

以下を確認する。

- 必要なテストが実施されているか
- テスト結果がPR本文に記載されているか
- CIが成功しているか
- 失敗しているCIがある場合、原因が説明されているか
- 未実施テストがある場合、未実施理由と残リスクが説明されているか

実施していないテストを実施済みとして扱ってはならない。

---

### 11. generated差分の有無を確認する

OpenAPI / Orval / generated 等の生成物差分を確認する。

確認観点は以下。

- generatedファイルを手動編集していないか
- 生成元の変更と生成物差分が対応しているか
- generated差分がTask Definitionのscope内か
- API clientやconsumer側に影響があるか
- 再生成手順がPR本文に記載されているか
- Contract Taskとして分離すべき変更ではないか

generated差分の扱いが不明な場合は、Contract AIの観点を利用する。

---

### 12. 横断影響を確認する

以下の横断影響を確認する。

| 観点             | 確認内容                                               |
| ---------------- | ------------------------------------------------------ |
| API contract     | API仕様、OpenAPI、Orval、client、provider/consumer影響 |
| DB schema        | schema、migration、seed、ER、テーブル設計への影響      |
| CI/CD            | workflow、build、deploy、releaseへの影響               |
| security         | secret、認証認可、権限、ログ、個人情報、`.env`実値     |
| docs正本         | 正本docs間の矛盾、用語揺れ、旧記述                     |
| downstream tasks | 後続Taskへの影響                                       |
| Project運用      | Status、Issue close、Done制御への影響                  |

横断影響が大きい場合は、`needs_human_decision`、`split_required`、またはContract Task化を提案する。

---

### 13. 前段成果物の修正が必要か確認する

後続TaskのPRレビュー中に、前段Taskで作成した成果物の修正が必要になる場合がある。

この場合、過去のTask Branchを再利用しない。

扱いは以下。

| 修正内容                             | 扱い                                              |
| ------------------------------------ | ------------------------------------------------- |
| 軽微な文言修正・補足                 | 現在のTask PR内で修正してよい                     |
| 実装に合わせた小さな設計書補正       | 現在のTask PR内で修正してよい                     |
| 仕様・設計方針に影響する修正         | 新しいTask Issue化を提案する                      |
| API契約・DB・generatedに影響する修正 | Contract Taskまたは専用Task化を提案する           |
| 他Taskへ影響する修正                 | Orchestrator AIによる影響分析と人間判断を提案する |

前段Task Issueは、対応PRが親Epic Branchへmerge済みであれば `Done` のままとする。

---

### 14. レビューコメントを作成する

レビュー結果をPRコメントとして作成する。

レビューコメントには以下を含める。

- 総合判定
- 良い点
- 指摘事項
- 修正必須事項
- 任意改善事項
- 確認した事実
- 推論
- 未確認事項
- テスト・CI確認結果
- 横断影響
- Human Reviewで確認してほしいこと
- 次Action

指摘事項は、修正担当が迷わない粒度で書く。

---

### 15. AIレビュー結果をPRへ記録する

AIレビュー結果をPRへ記録する。

記録内容は以下。

- AIレビューサマリ
- レビュー結果分類
- 修正要否
- 指摘内容
- Status更新意図
- follow-up Issue候補
- Human Review観点

PR コメントは [ai-review-comment.md](../../prompts/templates/review/ai-review-comment.md) 形式とする。特に §1 の `Review Result` 行と §22 の `次Status` を省略しない。

**dispatch 忘れ防止**: コメント投稿と Status 同期 dispatch は **1 コマンド** で行う（§15.5）。分離実行は recovery 時のみ。

---

### 15.5 Projects Status 同期を起動する（必須・1コマンド）

PR コメント投稿と `repository_dispatch` は **必ず同一コマンド** で実行する。  
Status 更新はコメント投稿では自動検知しない。dispatch 忘れは Projects Status が `AI Review` のまま残る。

**推奨（コメント + dispatch を原子的に実行）:**

```bash
node .github/scripts/publish-ai-review-and-dispatch.cjs \
  --repository <owner>/<repo> \
  --pr <PR番号> \
  --comment-file /path/to/ai-review-comment.md
```

`Review Result` はコメント §1 から自動抽出される。`needs_human_decision` で §22 `次Status` が `In Progress` のときは、コメント全文を `review_body` として dispatch に渡す。

**完了確認（dispatch 忘れチェック）:**

```bash
node .github/scripts/publish-ai-review-and-dispatch.cjs \
  --repository <owner>/<repo> \
  --pr <PR番号> \
  --verify
```

`ok: false` かつ `reason: dispatch_missing` の場合は、出力された `recovery_command` を実行する。

**Recovery（コメント投稿済み・dispatch のみ再実行）:**

```bash
node .github/scripts/publish-ai-review-and-dispatch.cjs \
  --repository <owner>/<repo> \
  --pr <PR番号> \
  --comment-file /path/to/ai-review-comment.md \
  --dispatch-only
```

**低レベル API（非推奨・分離実行）:**

```bash
node .github/scripts/dispatch-pr-review-status-sync.cjs \
  --repository <owner>/<repo> \
  --pr <PR番号> \
  --review-result <approve_for_human_review|request_changes|needs_human_decision|split_required|blocked>
```

`needs_human_decision` で PR コメント §22 の `次Status` が `In Progress` のときは `--review-body-file` を付ける。

dispatch が失敗した場合は、PR コメントは残るが Status は更新されない。`--dispatch-only` または `workflow_dispatch` で再実行する。

---

### 16. 指摘なしなら Human Review へ進める

指摘がなく、Human Reviewへ進めてよい場合は、レビュー結果を `approve_for_human_review` とする。

この場合、Project Statusを `Human Review` へ進める意図を出力する。

Status更新は、Commandが直接確定するのではなく、GitHub Actionsまたは運用スクリプトが実施できるよう、更新意図として明確に出力する。

---

### 17. 指摘ありなら In Progress へ戻す判断材料を出す

修正が必要な場合は、レビュー結果を `request_changes` とする。

この場合、Project Statusを `In Progress` へ戻す意図を出力し、次Commandとして `/fix-review-comments` を提示する。

```text
/fix-review-comments @<definition> #<PR番号>
```
---

## レビュー結果分類

| 結果                     | 意味                     | 次Status                        |
| ------------------------ | ------------------------ | ------------------------------- |
| approve_for_human_review | Human Reviewへ進めてよい | Human Review                    |
| request_changes          | 同一Branchで修正が必要   | In Progress                     |
| needs_human_decision     | 人間判断が必要           | Human Review または In Progress |
| split_required           | 別Issue化が必要          | In Progress                     |
| blocked                  | 前提不足でレビュー不可   | In Progress                     |

---

## 出力

| 出力                | 反映先                                       |
| ------------------- | -------------------------------------------- |
| AIレビューコメント  | Pull Request                                 |
| AIレビューサマリ    | Pull Request / Slack                         |
| 修正要否            | Pull Request                                 |
| Status更新意図      | GitHub Projects / チャット                   |
| follow-up Issue候補 | Pull Request / Issue                         |
| Human Review観点    | Pull Request                                 |
| 停止理由            | チャット / 必要に応じて `ai-logs/incidents/` |

---

## 成功条件

以下をすべて満たすこと。

- PRが確認されている
- 対象Issueが確認されている
- Task Definitionが確認されている
- PR targetが確認されている
- Task Branchが親Epic Branchの最新状態を取り込んでいるか確認されている
- PR diffが確認されている
- `output.docs`が確認されている
- 完了条件を満たしているか確認されている
- 確認観点を満たしているか確認されている
- テスト結果・CI結果が確認されている
- generated差分の有無が確認されている
- 横断影響が確認されている
- 前段成果物の修正要否が確認されている
- PRへAIレビュー結果が記録されている
- `publish-ai-review-and-dispatch.cjs` で **コメント投稿 + repository_dispatch を 1 回** 実行している（または `--verify` で dispatch 済みを確認済み）
- 修正要否が明確である
- Human Reviewへ進めてよいか判断できる
- 指摘がある場合、修正対象が明確である
- 次Statusの更新意図が明確である
- 次に実行すべきCommandが明確である

---

## 停止条件

以下の場合はレビューを停止し、人間へ確認する。

- PRが存在しない
- Issueとの紐づきが不明
- diffを確認できない
- Definitionが存在しない
- Issue、Task Definition、PR本文の内容が矛盾する
- レビュー前提となる成果物が欠落している
- PR targetが不明
- Task Branchからdevelopへ直接PRされている
- Task Branchと親Epic Branchの関係が不明
- Task Branchが親Epic Branchの最新状態を取り込んでいない
- 識別子付き Task で PR 差分 path が親 Epic の `epic_scope.allowed_paths` 外を含む（§6.1）
- 識別子付き Task で PR タイトル識別子 prefix と親 Epic 識別子 prefix が一致しない
- `input.docs` / `output.docs` を確認できない
- テスト結果・CI結果を確認できない
- secretや`.env`実値の混入が疑われる
- generatedファイルの手動編集が疑われる
- API contract変更の扱いが不明
- DB schema変更の扱いが不明
- 大きな横断影響があり、AIだけで判断できない
- Human Reviewを省略する前提になっている
- AIがmerge判断を行う必要がある

---

## Human確認条件

以下の場合は、人間確認へ回す。

- IssueとTask Definitionのどちらを優先するか判断が必要
- PR targetの妥当性判断が必要
- scope外変更を現在PRに含めるべきか判断が必要
- 前段成果物の修正を現在Taskで扱うべきか判断が必要
- 別Issue化すべきか判断が必要
- Contract Task化すべきか判断が必要
- API contract変更の許容判断が必要
- DB schema変更の許容判断が必要
- generated再生成方針の判断が必要
- CI失敗を許容してHuman Reviewへ進めてよいか判断が必要
- テスト未実施を許容してよいか判断が必要
- security上の許容判断が必要
- AIレビュー観点と人間の指示が衝突している
- merge可否に関する判断が必要

---

## Statusへの影響

`/review-pr` のStatus影響は以下とする。

| レビュー結果             | Status更新意図                      |
| ------------------------ | ----------------------------------- |
| approve_for_human_review | `AI Review` → `Human Review`        |
| request_changes          | `AI Review` → `In Progress`         |
| needs_human_decision     | `Human Review` または `In Progress` |
| split_required           | `In Progress`                       |
| blocked                  | `In Progress`                       |

Status更新は、Commandが直接確定するのではなく、[PRレビュー完了時Status更新ワークフロー仕様書](../../docs/06_実装設計/github_actions/PRレビュー完了時Status更新ワークフロー仕様書.md) が実施する。`/review-pr` は §15.5 の **`publish-ai-review-and-dispatch.cjs` を 1 回** 呼び出し（コメント + dispatch）、更新意図を PR コメントにも明記する。

---

## ai-logs利用方針

通常のAIレビュー結果をすべて `ai-logs/` に保存しない。

必要な場合のみ、以下の方針で記録候補にする。

記録対象・ディレクトリ構成の正本は [AIログ運用ルール](../../docs/00_共通/AIエージェント運用/AIログ運用ルール.md) §4・§6 とする。

| 種別                    | 保存先                     |
| ----------------------- | -------------------------- |
| Issue化前フィードバック | `ai-logs/intake/`          |
| 作業停止・例外          | `ai-logs/incidents/`       |
| 人間判断待ち            | `ai-logs/human-decisions/` |
| 横断影響                | `ai-logs/cross-cutting/`   |
| AI運用検証              | `ai-logs/experiments/`     |

通常の作業計画はIssue、レビュー結果はPR、成果物はdocsを正本とする。

---

## Slack通知

必要に応じて、AIレビュー結果をSlack通知用に整形する。

通知例。

```text
## AIレビュー結果通知

### PR
-

### 対象Issue
-

### レビュー結果
approve_for_human_review / request_changes / needs_human_decision / split_required / blocked

### 主な指摘
-

### Human Review観点
-

### 次のStatus
-

### 次Action
-
```
Slack通知は正本ではない。  
レビュー結果はPR、作業計画はIssue、成果物はdocsに記録する。

---

## レビュー完了時の出力形式

レビューが完了した場合は、以下の形式で出力する。

```text
## review-pr 実行結果

### 判断
-

### レビュー結果分類
approve_for_human_review / request_changes / needs_human_decision / split_required / blocked

### 対象PR
-

### 対象Issue
-

### PR target
-

### 確認した事実
-

### 推論
-

### 良い点
-

### 指摘事項
-

### 修正必須事項
-

### 任意改善事項
-

### テスト・CI確認結果
-

### generated確認結果
-

### 横断影響
-

### 前段成果物の修正要否
-

### Human Reviewで確認してほしいこと
-

### Status更新意図
-

### 次に実行するCommand
-
```
---

## 停止時の出力形式

レビューを停止する場合は、以下の形式で出力する。

```text
## review-pr 停止

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

Definition Run Harness 等で `run_mode=dry-run` の場合、PR への書き込み・Status 更新は行わない。以下を出力する。

1. レビュー結果分類（Review Result）
2. ai-review-comment.md 形式の **投稿予定コメント全文**（§1 `Review Result` / §22 `次Status` を含む）
3. 実行予定の `publish-ai-review-and-dispatch.cjs` コマンド例（`--repository` / `--pr` / `--comment-file`）
4. Status更新意図（現在 Status → 次 Status）
5. 次に実行する Command（`/fix-review-comments` 等）

dry-run では `gh pr comment` / `repository_dispatch` / Projects 直接更新を行わない。

---

## Definition Run としての外部実行

本 Command は Cursor IDE に加え、Definition Run Harness からも実行できる。正本は [Definition Run Harness ワークフロー仕様書](../../docs/06_実装設計/github_actions/Definition%20Run%20Harness%E3%83%AF%E3%83%BC%E3%82%AF%E3%83%95%E3%83%AD%E3%83%BC%E4%BB%95%E6%A7%98%E6%9B%B8.md) とする。

### 外部実行時に守る条件

| run_mode | 挙動 |
| -------- | ---- |
| `dry-run` | レビュー結果を「dry-run 実行時」フォーマットで出力。PR コメント・dispatch・Status 更新は **禁止** |
| `live-run` | 本 md 手順に従い、完了時 **必ず** `publish-ai-review-and-dispatch.cjs` を 1 回実行 |

Harness 入力:

| 入力 | 必須 | 説明 |
| ---- | ---- | ---- |
| `command` | 必須 | `review-pr` |
| `definition` | 必須 | `prompts/definitions/` 配下の review Definition |
| `run_mode` | 必須 | `dry-run` または `live-run` |
| `target_pr` | live-run 時必須 | 対象 PR 番号 |

live-run 完了後、Harness post-run 検証が dispatch 忘れを検知する。違反時は Guard Violations に `review_dispatch` が列挙され、ジョブは失敗する。

---

## 出力ルール

- 事実と推論を分けて書く
- 未確認事項を明示する
- PR、Issue、Task Definition、diffを確認する
- PR targetを確認する
- Task Branchが親Epic Branchの最新状態を取り込んでいるか確認する
- Task Branchからdevelopへ直接PRされていないか確認する
- Task PRでは `Related to #<Task Issue番号>` を確認する
- Issue close / Projects Done をPR本文の自動closeキーワードに依存しない
- 完了条件と確認観点を明示的に確認する
- docs / source code / test / API contract / DB / generated / CI/CD / security の横断影響を確認する
- generatedファイルの手動編集を見逃さない
- secret、APIキー、`.env`実値の混入を見逃さない
- 実施していないテストを実施済みとして扱わない
- 修正が必要な場合は、修正対象を明確にする
- レビューCommand内で修正作業をしない
- Human Reviewを省略しない
- AIがPRをmergeしない
- 通常レビュー結果をすべて `ai-logs/` に保存しない
- Slack通知だけでレビュー記録を完結させない
