# work-issue

## 目的

`/work-issue` は、既存Issue / Branchに基づき、Worker AIが設計・実装・テストなどの実作業を行うCommandである。

主に以下の場合に利用する。

- 人主導タスクでIssue / Branch作成後にAIへ作業を依頼する場合
- `/start-task` によってIssue / Branch作成済みのAI主導タスクを継続する場合
- 既存Issueの作業を再開する場合
- Task Definitionに従って、docs / source code / test / config 等を作成・修正する場合

このCommandは、Issue作成やBranch作成を主目的としない。  
Issue作成・Branch作成が未完了の場合は、原則として `/start-task` を先に実行する。

---

## 標準形式

```text
/work-issue @<definition>
```
例：

```text
/work-issue @prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-contract-spec.yaml
```
Definitionなしでの実行は原則禁止する。

---

## 主担当Agent

| 項目     | Agent                |
| -------- | -------------------- |
| 主担当   | Worker AI            |
| 補助     | Test AI / Support AI |
| レビュー | Reviewer AI          |

---

## 参照する定義・Rules

必要に応じて以下を参照する。

- `AGENTS.md`
- `.cursor/agents/worker-ai.md`
- `.cursor/agents/support-ai.md`
- `.cursor/agents/test-ai.md`
- `.cursor/agents/reviewer-ai.md`
- `.cursor/rules/project-operation.mdc`
- `.cursor/rules/github-operation.mdc`
- `.cursor/rules/docs-consistency.mdc`
- `.cursor/rules/terminology.mdc`
- `.cursor/rules/architecture-consistency.mdc`
- `.cursor/rules/code-consistency.mdc`
- `.cursor/rules/api-contract.mdc`
- `.cursor/rules/testing.mdc`
- `.cursor/rules/security.mdc`
- `.cursor/rules/worktree.mdc`
- `.cursor/rules/git-commit-message.mdc`
- [Contract Gate運用設計書](../../docs/00_共通/AIエージェント運用/Contract%20Gate運用設計書.md)（`contract_gate.required: true` または generated / apps 変更 Task）

対象作業に関係しないRulesは詳細確認を省略してよい。  
ただし、docs、source code、test、API contract、DB schema、generated、CI/CD、Branch、securityに影響する場合は、関連Rulesを必ず確認する。

---

## 入力

| 入力            | 必須     | 内容                                                      |
| --------------- | -------- | --------------------------------------------------------- |
| Issue           | 必須     | 作業計画、背景、目的、完了条件を確認する                  |
| Branch          | 必須     | 作業実体。対象Issueに対応する作業Branch                   |
| Task Definition | 必須     | 作業条件、scope、out_of_scope、成果物、確認観点を定義する |
| `input.docs`      | 必須     | 参照すべき設計書・仕様書・正本docs                        |
| `output.files`    | 条件付き | 修正対象のsource code / config / script等                 |
| `output.docs`     | 条件付き | 作成・更新する設計書・仕様書・運用docs等                  |
| `output.tests`    | 条件付き | 作成・更新するtest code / fixture / mock等                |
| Project Status  | 推奨     | 作業可能状態か確認する                                    |
| 親Epic Branch   | 条件付き | Task Branchのbase確認・最新化に利用する                   |
| CI結果          | 条件付き | 既存CI失敗の修正や確認に利用する                          |

---

## 処理手順

### 0. Machine account 認証（GitHub 書き込み前・必須）

push / commit の前に bot 認証を確認する（[github-operation.mdc](../../.cursor/rules/github-operation.mdc) §3.16）。

```bash
node .github/scripts/gh-bot-auth.cjs verify
eval "$(node .github/scripts/gh-bot-auth.cjs print-setup)"
GIT_USER_JSON="$(node .github/scripts/gh-bot-auth.cjs print-git-user)"
GIT_NAME="$(node -e "console.log(JSON.parse(process.argv[1]).name)" "$GIT_USER_JSON")"
GIT_EMAIL="$(node -e "console.log(JSON.parse(process.argv[1]).email)" "$GIT_USER_JSON")"
```

commit は **必ず** bot 名義（例: `git -c user.name="$GIT_NAME" -c user.email="$GIT_EMAIL" commit ...`）。push は `GH_BOT_TOKEN` を `GH_TOKEN` に export した状態で行う。人間アカウントの `gh auth login` のまま push しない（PR author が人間になり Human Review 不可）。

### 1. Issueを確認する

対象Issueを確認し、以下を整理する。

- Issue番号
- Issueタイトル
- 背景
- 目的
- 作業範囲
- 完了条件
- 関連Epic
- 関連Branch
- 関連PR
- Label
- Project Status
- 人間確認事項

Issueが存在しない場合、または対象Issueを特定できない場合は停止する。

---

### 2. Task Definitionを確認する

指定されたTask Definitionを読み込み、以下を確認する。

- task_id
- title
- background
- objective
- scope
- out_of_scope
- `input.docs`
- `output.docs`
- `output.files`
- test_files
- deliverables
- acceptance_criteria
- dependencies
- test_policy
- operation_logging
- human_review_required

IssueとTask Definitionの内容が矛盾する場合は、推測で進めず停止する。

---

### 3. Branchが正しいことを確認する

現在の作業Branchを確認する。

確認観点は以下。

- 対象Issueに対応するBranchか
- Branch名がブランチ運用ルールに従っているか
- main / develop へ直接作業していないか
- Task Branchのbaseが親Epic Branchになっているか
- Task Branchからdevelopへ直接PRする前提になっていないか
- 他Taskの作業Branchと混同していないか

Branchが存在しない、baseが誤っている、または対象Issueとの対応が不明な場合は停止する。

---

### 3.5 Contract Gateを確認する（Implementation Task）

Task Definition の `contract_gate.required: true`、または `output.generated.expected: true` / `apps/**` を変更する Implementation Task では、作業開始前に [Contract Gate運用設計書](../../docs/00_共通/AIエージェント運用/Contract%20Gate運用設計書.md) §4 の必須チェックを確認する。

| No | チェック | 未充足時 |
| --: | -------- | -------- |
| 1 | 先行 Contract Task の PR が **親 Epic Branch にマージ済み** | 停止。Contract 完了を待つ |
| 2 | OpenAPI 正本が `packages/contracts/openapi/*.yaml` に反映済み | 停止 |
| 3 | generated 影響がある場合、Orval 再生成差分が Contract PR に含まれる | 停止 |
| 4 | generated を手動編集していない | 停止 |
| 5 | `breaking_change: true` の場合、Contract PR の Human Review 完了 | 停止・人間判断待ち |
| 6 | `contract_gate.prerequisite_contract_tasks` / `parallel_control.depends_on` の依存 Task 完了 | 停止 |

未通過時は `contract_gate.blocked_message`（定義にある場合）を出力し、実装・docs 作成に進まない。  
純粋な docs Task（`apps/**` / `packages/**` / generated 実体を変更しない）で `contract_gate.required: false` の場合は本節を省略してよい。

契約面 docs は `prompts/templates/docs/api-contract-spec.md` / `openapi-spec.md`、実装面は `api-implementation-spec.md` を正とする（廃止済み `api-spec.md` は新規作成に使わない）。

---

### 4. Project Statusが作業可能状態であることを確認する

GitHub Projects上のStatusを確認する。

`/work-issue` の主なStatus影響は、以下とする。

| 現在Status   | 扱い                                                         |
| ------------ | ------------------------------------------------------------ |
| Todo         | 作業開始可能であれば `In Progress` へ進める意図を出力する    |
| In Progress  | 作業継続可能                                                 |
| AI Review    | 原則として `/review-pr` または `/fix-review-comments` の対象 |
| Human Review | 原則として人間レビュー待ち                                   |
| Done         | 原則として作業しない                                         |

Status変更は、Commandが直接確定するのではなく、GitHub Actionsまたは運用スクリプトが実施できるよう、更新意図を明確に出力する。

---

### 5. Task Branchが親Epic Branchの最新状態を取り込んでいるか確認する

Task Branchが親Epic Branchの最新状態を取り込んでいるか確認する。

最新でない場合は、作業前に親Epic Branchの最新状態を取り込む。

ただし、以下の場合は推測で解消せず停止する。

- merge / rebaseで競合が発生した
- 親Epic Branch側の変更内容が現在Taskの前提と衝突している
- 最新化によりTask Definitionのscope外変更が必要になる
- 他Taskの成果物と競合する可能性がある

---

### 6. `input.docs`を確認する

Task Definitionで指定された `input.docs` を確認する。

確認観点は以下。

- 指定されたdocsが存在するか
- docsの内容が現在Taskの前提と整合しているか
- 正本docsとして扱うべき資料が明確か
- 用語集・設計書・API仕様書・テーブル設計等との矛盾がないか
- 古い記述や廃止済み方針を参照していないか

正本docs間の矛盾を発見した場合は、AIが独断で解消せず、人間確認へ回す。

---

### 7. scope / out_of_scopeを確認する

Task Definitionの `scope` と `out_of_scope` を確認する。

以下を明確にする。

- 今回作業すること
- 今回作業しないこと
- 別Issue化すべきこと
- Contract Task化すべきこと
- 後続Taskへ回すこと

scope外作業が必要になった場合は、勝手に実施せず停止する。

---

### 8. `output.files` / `output.docs`を確認する

作成・修正対象を確認する。

| 種別         | 確認内容                                      |
| ------------ | --------------------------------------------- |
| `output.files` | source code、config、script、test等の修正対象 |
| `output.docs`  | 設計書、仕様書、運用docs等の成果物            |
| test_files   | test code、fixture、mock等                    |
| generated    | OpenAPI / Orval等の生成物差分があるか         |

`generated` ファイルは手動編集しない。  
generated差分が必要な場合は、生成元と再生成手順を確認する。

---

### 9. 必要な作業を実施する

Task Definitionのscope内で必要な作業を実施する。

作業種別ごとの方針は以下。

| 作業種別              | 方針                                                          |
| --------------------- | ------------------------------------------------------------- |
| docs作成・修正        | 正本docs、用語、章構成、Mermaid、関連docsとの整合性を確認する |
| source code実装・修正 | 既存アーキテクチャ、責務分離、命名、型、安全性に従う          |
| test追加・修正        | test_policyに従い、必要なテストを追加・更新する               |
| config修正            | CI/CD、環境変数、secret混入に注意する                         |
| API関連修正           | API仕様、OpenAPI、Orval、generated、client影響を確認する      |
| DB関連修正            | schema、migration、seed、ER、テーブル設計への影響を確認する   |

source codeには、意図・制約・ドメイン判断が必要な箇所に適宜コメントを記載する。  
ただし、コードを読めば分かるだけの冗長コメントは増やさない。

---

### 10. テスト・検証を実施する

Task Definitionの `test_policy` に従い、必要なテスト・検証を実施する。

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
- CI結果確認

テストを実施できない場合は、以下を明記する。

- 実施できなかったテスト
- 実施できない理由
- 代替確認
- 残リスク
- 人間に確認したいこと

実施していないテストを実施済みとして報告してはならない。

---

### 11. 変更内容を自己確認する

作業後、以下を確認する。

- Definitionのscope内に収まっているか
- out_of_scopeに触れていないか
- 意図しないファイル変更がないか
- 成果物が指定場所に配置されているか
- 正本docsとの矛盾がないか
- 用語揺れがないか
- API contract変更が混在していないか
- DB schema変更が混在していないか
- generatedファイルを手動編集していないか
- secretや`.env`実値を含んでいないか
- test / validation結果を正しく記録しているか

問題がある場合は、修正するか、停止して人間確認へ回す。

---

### 12. commitを作成する

変更内容がTask Definitionのscope内であり、自己確認が完了した場合はcommitを作成する。

**commit 前**に §0 の `print-git-user` で取得した `GIT_NAME` / `GIT_EMAIL` を使用する（ハードコード禁止）。未実行の場合は §0 に戻ってから commit する。

commit作成時は以下を確認する。

- commit対象ファイルが妥当か
- 不要な差分が含まれていないか
- secretや`.env`実値が含まれていないか
- generatedの手動編集が含まれていないか
- commit messageが運用ルールに従っているか
- Issue番号との対応が分かるか

commit messageは、Git commit message運用ルールに従う。

---

### 13. 作業サマリを作成する

作業完了後、以下を整理する。

```text
## work-issue 作業サマリ

### 対象Issue
-

### 対象Branch
-

### 作業目的
-

### 実施内容
-

### 変更ファイル
-

### 作成・更新した成果物
-

### テスト・検証結果
-

### 未実施事項
-

### 残課題
-

### 人間確認事項
-

### 次に実行するCommand
-
```
---

### 14. 必要に応じて `/create-pr` へ進める

以下を満たす場合は、次に `/create-pr @<definition>` へ進める。

- Definitionの完了条件を満たしている
- 必要な成果物が作成・更新されている
- 必要なテスト・検証が実施されている
- commitが作成されている
- PR作成に必要な情報が揃っている
- 人間確認待ちの重大論点が残っていない

PR作成はこのCommandの主責務ではない。  
PR作成は `/create-pr` に引き継ぐ。

---

## 出力

| 出力           | 反映先                                       |
| -------------- | -------------------------------------------- |
| 設計書・仕様書 | `docs/`                                      |
| ソースコード   | 対象コンポーネント                           |
| テストコード   | 対象テストディレクトリ                       |
| 設定ファイル   | 対象config / workflow / script               |
| テスト結果     | PR本文案 / docs / チャット                   |
| commit         | Git Branch                                   |
| 作業サマリ     | PR本文案 / Slack / チャット                  |
| Status更新意図 | GitHub Projects / チャット                   |
| 停止理由       | チャット / 必要に応じて `ai-logs/incidents/` |

---

## 成功条件

以下をすべて満たすこと。

- Issueが確認されている
- Branchが確認されている
- Task Definitionが確認されている
- Project Statusが作業可能状態である
- Task Branchが親Epic Branchの最新状態を取り込んでいる
- `input.docs`が確認されている
- scope / out_of_scope が確認されている
- `output.files` / `output.docs` / test_files が確認されている
- Definitionの完了条件を満たしている
- 作業範囲外の変更をしていない
- 必要な成果物が指定場所に配置されている
- 必要なテスト・検証が実施されている
- 実施できないテストがある場合、その理由と残リスクが明記されている
- 意図しないファイル変更がない
- secretや`.env`実値が含まれていない
- generatedファイルを手動編集していない
- commitが作成されている
- 作業サマリが作成されている
- 必要に応じて `/create-pr` へ進める状態になっている

---

## 停止条件

以下の場合は作業を停止し、人間へ確認する。

- Issueが存在しない
- IssueとDefinitionの内容が矛盾する
- Branchが存在しない
- Branch baseが誤っている
- main / develop へ直接作業しようとしている
- Task Branchからdevelopへ直接PRしようとしている
- Project Statusが作業可能状態ではない
- Task Branchが親Epic Branchの最新状態を取り込めない
- 親Epic Branchとの最新化で競合が発生している
- 対象ファイルが他Taskと競合している
- `input.docs`が存在しない
- 正本docs間に矛盾がある
- scope / out_of_scope が曖昧である
- 指定外の大きな設計変更が必要になる
- API契約変更が必要になる
- DB schema変更が必要になる
- generated差分が発生し、再生成方針が不明である
- generatedファイルの手動編集が必要に見える
- CI/CD設定変更が必要になる
- security上の懸念がある
- secretや`.env`実値を扱う必要がある
- 後続Taskへの影響が大きい
- 人間判断なしに進めると危険である
- テスト未実施理由を説明できない
- commit対象に不要・危険な差分が含まれている

---

## Human確認条件

以下の場合は、人間確認へ回す。

- IssueとTask Definitionのどちらを優先するか判断が必要
- 仕様判断が必要
- MVP対象かどうか判断が必要
- scope拡張が必要
- 別Issue化すべきか判断が必要
- Contract Task化すべきか判断が必要
- 正本docsの優先順位判断が必要
- API contract変更の許容判断が必要
- DB schema変更の許容判断が必要
- generated再生成方針の判断が必要
- CI/CD影響の許容判断が必要
- test未実施の許容判断が必要
- Branch競合の解消方針判断が必要
- 他Taskとの競合解消が必要
- security上の許容判断が必要

---

## Statusへの影響

`/work-issue` のStatus影響は以下とする。

| 状況                  | Status更新意図                    |
| --------------------- | --------------------------------- |
| Todoから作業開始可能  | `Todo` → `In Progress`            |
| In Progressで作業継続 | `In Progress` のまま              |
| 作業完了しPR作成可能  | 次Command `/create-pr` に引き継ぐ |
| 停止・人間確認が必要  | 原則 `In Progress` のまま         |
| 作業対象外Status      | Status変更せず停止                |

Status更新は、Commandが直接確定するのではなく、GitHub Actionsまたは運用スクリプトが実施できるよう、更新意図として明確に出力する。

---

## ai-logs利用方針

通常作業のログをすべて `ai-logs/` に保存しない。

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

必要に応じて、作業サマリをSlack通知用に整形する。

ただし、Slack通知は正本ではない。  
作業結果はPR、成果物はdocs、作業計画はIssueに記録する。

---

## 作業完了時の出力形式

作業が完了した場合は、以下の形式で出力する。

```text
## work-issue 実行結果

### 判断
作業完了です。必要に応じて `/create-pr` へ進めます。

### 対象Issue
-

### 対象Branch
-

### 実施内容
-

### 変更ファイル
-

### 作成・更新した成果物
-

### テスト・検証結果
-

### 未実施事項
-

### 残課題
-

### Human確認事項
-

### Status更新意図
-

### 次に実行するCommand
-
```
---

## 停止時の出力形式

作業を停止する場合は、以下の形式で出力する。

```text
## work-issue 停止

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

## Layer2 テスト dispatch（Epic C 関連 Task）

Task Definition の `test_policy` に workflow_dispatch 実行・artifact 読取が含まれる場合、または Epic C（`gha-test-environment`）配下の Layer2 テスト検証が必要な場合、Agent は以下を実施する。

**正本:** [Layer2 Agent dispatch手順書.md](../../docs/05_アプリケーション設計/テスト/Layer2%20Agent%20dispatch%E6%89%8B%E9%A0%86%E6%9B%B8.md)

| 手順 | 内容 |
| ---- | ---- |
| 1 | 対象 workflow（`test-system.yml` / `test-reco-quality.yml` 等）と `--ref`（Task Branch）を決定 |
| 2 | bot 認証後 `gh workflow run` で dispatch（§0） |
| 3 | `gh run watch` / `gh run view` / artifact ダウンロードで結果読取 |
| 4 | 失敗時は scope 内 Fix → commit → 再 dispatch（**自動 Fix は最大 2 回**。上限到達時は Slack `incident_detected` でエスカレーション。正本: 手順書 §9） |
| 5 | PR 本文「テスト・検証結果」に run URL・入力・判定を記載 |

Layer2 dispatch は Definition Run Harness（`/review-pr` 等）とは別系統である（Commands設計書 §29.5）。cloud dev URL 依存手順（Epic B defer）は out of scope。

---

## 出力ルール

- 事実と推論を分けて書く
- 未確認事項を明示する
- IssueとDefinitionの整合性を確認する
- Branchが正しいことを確認する
- Task Branchが親Epic Branchの最新状態を取り込んでいるか確認する
- Definitionのscope外作業をしない
- out_of_scopeに含まれる作業を勝手に実施しない
- 正本docs間の矛盾をAIが独断で解消しない
- main / develop へ直接pushしない
- Task Branchからdevelopへ直接PRを作成しない
- generatedファイルを手動編集しない
- secret、APIキー、`.env`実値を出力しない
- 実施していないテストを実施済みと書かない
- Human Reviewを省略しない
- AIがPRをmergeしない
- 通常作業ログをすべて `ai-logs/` に保存しない
- Slack通知だけで作業記録を完結させない
