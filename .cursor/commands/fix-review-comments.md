# fix-review-comments

## 目的

`/fix-review-comments` は、AIレビューまたは人間レビューの指摘に対応するCommandである。

原則として、同一Issue・同一Branchで修正する。

主に以下の場合に利用する。

- AI Reviewで `request_changes` となった指摘に対応する場合
- Human Reviewで修正依頼が出た場合
- PRコメントに基づいて、同一Branchで追加修正する場合
- レビュー指摘対応後、再度AI Reviewへ戻す場合
- 指摘内容がscope内か、別Issue化すべきかを整理する場合

このCommandは、レビュー指摘への修正対応に限定する。  
新規仕様追加、大規模リファクタリング、API契約変更、DB schema変更、generated横断影響を通常のレビュー指摘対応に混在させてはならない。

---

## 標準形式

```text
/fix-review-comments @<definition>
```
例：

```text
/fix-review-comments @prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml
```
PR番号を併記してもよい。

```text
/fix-review-comments @prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml #123
```
Definitionなしでの実行は原則禁止する。

---

## 主担当Agent

| 項目   | Agent               |
| ------ | ------------------- |
| 主担当 | Fixer AI            |
| 補助   | Worker AI / Test AI |
| 後続   | Reviewer AI         |

---

## 参照する定義・Rules

必要に応じて以下を参照する。

- `AGENTS.md`
- `.cursor/agents/fixer-ai.md`
- `.cursor/agents/worker-ai.md`
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
- `.cursor/rules/ai-review.mdc`
- `.cursor/rules/security.mdc`
- `.cursor/rules/worktree.mdc`
- `.cursor/rules/git-commit-message.mdc`

レビュー指摘対応時は、特に以下を重視する。

- 指摘内容の意図を正しく分類する
- 同一Issue・同一Branchで対応可能か確認する
- Task Definitionのscope内か確認する
- scope外指摘を無理に同一Branchへ混在させない
- API契約変更、DB schema変更、generated差分を通常修正に混ぜない
- 修正後に必要なテスト・検証を再実行する
- 再レビュー可能な状態へ戻す

---

## 入力

| 入力            | 必須     | 内容                                              |
| --------------- | -------- | ------------------------------------------------- |
| PR              | 必須     | 修正対象PR                                        |
| review comments | 必須     | AIレビュー・人間レビューコメント                  |
| Issue           | 必須     | 作業計画、scope、完了条件を確認する               |
| Branch          | 必須     | 修正対象Branch                                    |
| Task Definition | 必須     | 作業条件、scope、out_of_scope、確認観点を定義する |
| existing diff   | 必須     | 現在の変更差分                                    |
| test results    | 条件付き | 既存のテスト・検証結果                            |
| CI results      | 条件付き | CI失敗や警告への対応が必要な場合に参照する        |
| `output.docs`     | 条件付き | docs指摘に対応する場合に参照する                  |
| `output.files`    | 条件付き | source code / config / test 修正対象              |

---

## 処理手順

### 1. PRレビューコメントを確認する

対象PRのレビューコメントを確認する。

確認対象は以下。

- AIレビューコメント
- 人間レビューコメント
- PR本文上の未解決事項
- CIコメント
- reviewerからの質問
- 修正依頼
- 承認条件
- follow-up候補

コメントが取得できない、または対象PRが不明な場合は停止する。

---

### 2. 指摘内容を分類する

レビューコメントを分類する。

| 分類             | 扱い                                |
| ---------------- | ----------------------------------- |
| typo / 文言修正  | 同一Branchで対応可能                |
| docs補足         | scope内であれば同一Branchで対応可能 |
| 実装不備         | scope内であれば同一Branchで対応可能 |
| test不足         | scope内であれば同一Branchで対応可能 |
| PR本文不足       | 同一PR内で対応可能                  |
| 設計方針変更     | 原則として人間確認または別Issue化   |
| API契約変更      | Contract Task化を検討               |
| DB schema変更    | 専用Task Issue化を検討              |
| generated差分    | 生成元・再生成方針を確認            |
| scope外要望      | 新しいTask Issue化を提案            |
| 意図不明コメント | 人間確認へ回す                      |

分類時は、事実と推論を分けて整理する。

---

### 3. 同一Branchで対応可能か確認する

指摘内容が、現在のIssue・Branchで対応可能か確認する。

確認観点は以下。

- 対象Issueのscope内か
- Task Definitionのscope内か
- out_of_scopeに含まれていないか
- 既存PRの目的から逸脱しないか
- 修正によって別成果物への大きな影響が出ないか
- 他Taskとの競合が発生しないか
- API / DB / generated / CI/CD への横断影響がないか

同一Branchで対応できない場合は、修正せず停止する。

---

### 4. Definitionのscope内か確認する

Task Definitionを読み込み、以下を確認する。

- scope
- out_of_scope
- `output.files`
- `output.docs`
- test_files
- acceptance_criteria
- test_policy
- human_review_required

Issue、PR、Task Definition、レビューコメントの間に矛盾がある場合は、推測で進めず停止する。

---

### 5. Task Branchが親Epic Branchの最新状態を取り込んでいるか確認する

修正前に、Task Branchが親Epic Branchの最新状態を取り込んでいるか確認する。

最新でない場合は、修正前に最新化する。

ただし、以下の場合は推測で解消せず停止する。

- merge / rebaseで競合が発生した
- 親Epic Branch側の変更内容が現在PRの前提と衝突している
- 最新化によりTask Definitionのscope外変更が必要になる
- 他Taskの成果物と競合する可能性がある

---

### 6. 修正方針を整理する

実際に修正する前に、レビュー指摘ごとの対応方針を整理する。

```text
## 修正方針

| No | 指摘元 | 指摘内容 | 分類 | 対応方針 | 対応可否 | 備考 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | AI Review / Human Review / CI |  |  |  |  |  |
```
対応可否は以下のいずれかに分類する。

| 対応可否               | 意味                  |
| ---------------------- | --------------------- |
| fix_in_same_branch     | 同一Branchで修正する  |
| no_change_needed       | 説明のみで対応する    |
| needs_human_decision   | 人間判断が必要        |
| split_required         | 別Issue化が必要       |
| contract_task_required | Contract Task化が必要 |
| blocked                | 前提不足で対応不可    |

---

### 7. 対象Branchで修正する

対応可能な指摘のみ、対象Branchで修正する。

修正時の原則は以下。

- 指摘対応に必要な最小限の変更に留める
- scope外の改善をついでに実施しない
- 別Issue化すべき内容を混在させない
- 既存設計・用語・責務境界と整合させる
- source codeには、意図・制約・ドメイン判断が必要な箇所に適宜コメントを記載する
- コードを読めば分かるだけの冗長コメントは増やさない
- generatedファイルを手動編集しない
- secret、APIキー、`.env` 実値を出力・保存・commitしない

---

### 8. 必要なテストを再実行する

修正内容に応じて、必要なテスト・検証を再実行する。

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

テストを再実行できない場合は、以下を明記する。

- 再実行できなかったテスト
- 再実行できない理由
- 代替確認
- 残リスク
- 人間に確認してほしいこと

実施していないテストを実施済みとして報告してはならない。

---

### 9. commitを追加する

修正内容がscope内であり、自己確認が完了した場合はcommitを追加する。

commit作成前に以下を確認する。

- 指摘対応に必要な差分のみか
- 不要な変更が含まれていないか
- secretや`.env`実値が含まれていないか
- generatedファイルを手動編集していないか
- テスト結果を正しく記録しているか
- commit messageが運用ルールに従っているか
- Issue番号またはPRとの対応が分かるか

---

### 10. PR本文またはPRコメントを更新する

修正内容に応じて、PR本文またはPRコメントを更新する。

記載内容は以下。

- 対応したレビューコメント
- 修正内容
- 変更ファイル
- 再実行したテスト・検証
- 未対応の指摘
- 未対応理由
- 人間判断待ちの事項
- 再レビュー依頼

PR本文の作業結果・テスト結果が古くなっている場合は、必要に応じて更新する。

---

### 11. 修正サマリを記録する

修正後、以下の形式でサマリを作成する。

```text
## 修正サマリ

### 対象PR
-

### 対象Issue
-

### 対象Branch
-

### 対応した指摘
-

### 修正内容
-

### 変更ファイル
-

### 再実行したテスト・検証
-

### 未対応の指摘
-

### 未対応理由
-

### Human確認事項
-

### 次に実行するCommand
-
```
---

### 12. Statusを AI Review へ戻す判断材料を出す

修正対応が完了し、再レビュー可能な状態であれば、Project Statusを `AI Review` へ戻す意図を出力する。

`/fix-review-comments` の主なStatus影響は以下。

| 状況                   | Status更新意図                            |
| ---------------------- | ----------------------------------------- |
| 指摘対応完了           | `In Progress` → `AI Review`               |
| 一部対応・人間判断待ち | 原則 `In Progress` のまま                 |
| 別Issue化が必要        | 原則 `In Progress` のまま                 |
| 対応不能               | 原則 `In Progress` または運用ルールに従う |

Status更新は、Commandが直接確定するのではなく、GitHub Actionsまたは運用スクリプトが実施できるよう、更新意図として明確に出力する。

---

### 13. 必要に応じてSlack通知を作成する

必要に応じて、レビュー指摘対応完了のSlack通知サマリを作成する。

Slack通知には以下を含める。

- 対象PR
- 対象Issue
- 対応した指摘
- 未対応事項
- 再レビュー依頼
- 次Status
- 人間確認事項

Slack通知は正本ではない。  
修正内容はPR、作業計画はIssue、成果物はdocsを正本とする。

---

### 14. 次Commandを提示する

修正完了後、再AI Reviewが必要な場合は、次Commandとして `/review-pr @<definition>` を提示する。

```text
/review-pr @<definition> #<PR番号>
```
---

## 出力

| 出力                | 反映先                                       |
| ------------------- | -------------------------------------------- |
| 修正commit          | Git Branch                                   |
| PR更新              | Pull Request                                 |
| コメント返信        | Pull Request                                 |
| 修正サマリ          | Pull Request / Slack / チャット              |
| 再レビュー依頼      | Pull Request / チャット                      |
| Status更新意図      | GitHub Projects / チャット                   |
| follow-up Issue候補 | Pull Request / Issue                         |
| 停止理由            | チャット / 必要に応じて `ai-logs/incidents/` |

---

## 成功条件

以下をすべて満たすこと。

- PRが確認されている
- review commentsが確認されている
- Issueが確認されている
- Branchが確認されている
- Task Definitionが確認されている
- existing diffが確認されている
- 指摘内容が分類されている
- 同一Branchで対応可能な指摘のみ修正している
- 対応範囲が同一Issueのscope内である
- scope外指摘を混在させていない
- 修正内容がPRに記録されている
- 必要なテスト・検証が再実行されている
- 実施できないテストがある場合、その理由と残リスクが明記されている
- 修正commitが作成されている
- 未対応の指摘がある場合、理由が明記されている
- 再レビュー可能な状態になっている
- Statusを `AI Review` へ戻す意図が明確である
- 次Commandとして `/review-pr` へ進める状態になっている

---

## 停止条件

以下の場合は修正作業を停止し、人間へ確認する。

- PRが存在しない
- review commentsを確認できない
- レビューコメントの意図が不明
- Issueが存在しない
- Branchが存在しない
- IssueとBranchの対応が不明
- Task Definitionが存在しない
- Issue、PR、Task Definition、レビューコメントの内容が矛盾する
- 指摘内容がscope外である
- 別Issue化すべき内容である
- API契約変更が必要になる
- DB schema変更が必要になる
- generated差分が発生する
- generatedファイルの手動編集が必要に見える
- CI/CD設定変更の扱いが不明
- 親Epic Branchとの最新化で競合が発生している
- 対象ファイルが他Taskと競合している
- 後続Taskへの影響が大きい
- secretや`.env`実値を扱う必要がある
- security上の懸念がある
- テスト再実行が必要だが実行可否を判断できない
- 人間判断なしに進めると危険である

---

## Human確認条件

以下の場合は、人間確認へ回す。

- レビューコメントの意図が不明
- 指摘内容を修正すべきか説明で返すべきか判断が必要
- scope外指摘を同一PRで扱うべきか判断が必要
- 別Issue化すべきか判断が必要
- Contract Task化すべきか判断が必要
- API contract変更の許容判断が必要
- DB schema変更の許容判断が必要
- generated再生成方針の判断が必要
- CI/CD影響の許容判断が必要
- test再実行不可の許容判断が必要
- 親Epic Branchとの競合解消方針判断が必要
- 他Taskとの競合解消が必要
- security上の許容判断が必要
- Human Reviewの指摘内容が既存設計と衝突している
- AIレビュー指摘と人間レビュー指摘が矛盾している

---

## Statusへの影響

`/fix-review-comments` のStatus影響は以下とする。

| 状況                   | Status更新意図                   |
| ---------------------- | -------------------------------- |
| 指摘対応完了           | `In Progress` → `AI Review`      |
| 一部対応・人間判断待ち | `In Progress` のまま             |
| 別Issue化が必要        | `In Progress` のまま             |
| Contract Task化が必要  | `In Progress` のまま             |
| 修正不能               | 運用ルールに従い、人間確認へ回す |

Status更新は、Commandが直接確定するのではなく、GitHub Actionsまたは運用スクリプトが実施できるよう、更新意図として明確に出力する。

---

## ai-logs利用方針

通常のレビュー指摘対応ログをすべて `ai-logs/` に保存しない。

必要な場合のみ、以下の方針で記録候補にする。

記録対象・ディレクトリ構成の正本は [AIログ運用ルール](../../docs/00_共通/AIエージェント運用/AIログ運用ルール.md) §4・§6 とする。

| 種別                    | 保存先                     |
| ----------------------- | -------------------------- |
| Issue化前フィードバック | `ai-logs/intake/`          |
| 作業停止・例外          | `ai-logs/incidents/`       |
| 人間判断待ち            | `ai-logs/human-decisions/` |
| 横断影響                | `ai-logs/cross-cutting/`   |
| AI運用検証              | `ai-logs/experiments/`     |

通常の作業計画はIssue、作業結果とレビュー対応はPR、成果物はdocsを正本とする。

---

## Slack通知

必要に応じて、レビュー指摘対応サマリをSlack通知用に整形する。

通知例。

```text
## レビュー指摘対応通知

### PR
-

### 対象Issue
-

### 対応した指摘
-

### 未対応事項
-

### 再レビュー依頼
-

### 次のStatus
AI Review

### Human確認事項
-
```
Slack通知は正本ではない。  
レビュー指摘対応はPR、作業計画はIssue、成果物はdocsに記録する。

---

## 修正完了時の出力形式

修正が完了した場合は、以下の形式で出力する。

```text
## fix-review-comments 実行結果

### 判断
レビュー指摘対応完了です。次に `/review-pr` へ進めます。

### 対象PR
-

### 対象Issue
-

### 対象Branch
-

### 対応した指摘
-

### 修正内容
-

### 変更ファイル
-

### 再実行したテスト・検証
-

### 未対応の指摘
-

### 未対応理由
-

### Human確認事項
-

### Status更新意図
In Progress → AI Review

### 次に実行するCommand
/review-pr @<definition> #<PR番号>
```
---

## 停止時の出力形式

修正作業を停止する場合は、以下の形式で出力する。

```text
## fix-review-comments 停止

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
- レビューコメントを分類してから修正する
- 同一Issue・同一Branchで対応可能な指摘のみ修正する
- Definitionのscope外作業をしない
- out_of_scopeに含まれる作業を勝手に実施しない
- scope外指摘は別Issue化を提案する
- API契約変更はContract Task化を検討する
- DB schema変更は専用Task化を検討する
- generatedファイルを手動編集しない
- secret、APIキー、`.env`実値を出力しない
- 必要なテスト・検証を再実行する
- 実施していないテストを実施済みと書かない
- 修正内容をPRに記録する
- Human Reviewを省略しない
- AIがPRをmergeしない
- 通常作業ログをすべて `ai-logs/` に保存しない
- Slack通知だけで作業記録を完結させない
