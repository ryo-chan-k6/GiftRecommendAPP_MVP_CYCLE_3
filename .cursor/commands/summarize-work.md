# summarize-work

## 目的

`/summarize-work` は、作業結果やレビュー結果を要約し、Slack通知、PR追記、Issueコメントに利用するCommandである。

主に以下の場合に利用する。

- 作業完了後に、作業サマリを作成する場合
- PR作成前に、変更内容・テスト結果・残課題を整理する場合
- AIレビュー結果をSlack通知用に要約する場合
- Human Review向けに確認ポイントを整理する場合
- Issueコメントとして進捗・判断依頼・完了報告を作成する場合
- PR本文やPRコメントに追記するためのサマリを作成する場合
- 作業不可・人間判断待ちの内容を簡潔に整理する場合

このCommandは、要約・通知文面・記録補助を行うCommandである。  
source code、docs、test、configなどの実作業は行わない。

---

## 標準形式

```text
/summarize-work @<definition>
```
例：

```text
/summarize-work @prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml
```
Definitionなしでの実行は原則禁止する。  
ただし、Issue番号、PR番号、レビュー結果などで対象が十分に一意に特定できる場合は、補助引数として併記してよい。

例：

```text
/summarize-work @prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml #123
```
---

## 主担当Agent

| 項目   | Agent                              |
| ------ | ---------------------------------- |
| 主担当 | Support AI                         |
| 補助   | Worker AI / Reviewer AI / Fixer AI |

---

## 参照する定義・Rules

必要に応じて以下を参照する。

- `AGENTS.md`
- `.cursor/agents/support-ai.md`
- `.cursor/agents/worker-ai.md`
- `.cursor/agents/reviewer-ai.md`
- `.cursor/agents/fixer-ai.md`
- `.cursor/rules/project-operation.mdc`
- `.cursor/rules/github-operation.mdc`
- `.cursor/rules/docs-consistency.mdc`
- `.cursor/rules/terminology.mdc`
- `.cursor/rules/ai-review.mdc`
- `.cursor/rules/security.mdc`
- `.cursor/rules/worktree.mdc`

サマリ作成時は、特に以下を重視する。

- Slack通知は正本ではない
- 作業計画はIssueを正本とする
- 作業結果はPRを正本とする
- レビュー結果はPRを正本とする
- 成果物はdocsを正本とする
- 事実と推論を分ける
- 未確認事項を明示する
- 実施していないテストを実施済みと書かない
- secret、APIキー、`.env` 実値を出力しない

---

## 入力

| 入力             | 必須     | 内容                                                     |
| ---------------- | -------- | -------------------------------------------------------- |
| Issue            | 条件付き | 作業対象Issue。作業計画、目的、scope、完了条件を確認する |
| PR               | 条件付き | 作業対象PR。変更内容、レビュー結果、コメントを確認する   |
| diff             | 条件付き | 変更差分。変更ファイルや影響範囲の整理に利用する         |
| review result    | 条件付き | AIレビュー・人間レビュー結果                             |
| Task Definition  | 推奨     | 作業条件、完了条件、確認観点を確認する                   |
| 通知テンプレート | 推奨     | Slack通知、PR追記、Issueコメントの文面生成に利用する     |
| test results     | 条件付き | テスト・検証結果の整理に利用する                         |
| CI results       | 条件付き | CI結果の整理に利用する                                   |
| related docs     | 条件付き | 成果物や正本docsの確認に利用する                         |

---

## 処理手順

### 1. 要約対象を確認する

まず、何を要約するCommandかを確認する。

要約対象の例。

| 要約対象            | 用途                                     |
| ------------------- | ---------------------------------------- |
| 作業サマリ          | `/work-issue` 後の作業結果整理           |
| PR作成サマリ        | `/create-pr` 前後の変更内容整理          |
| AIレビューサマリ    | `/review-pr` 後のレビュー結果整理        |
| 修正対応サマリ      | `/fix-review-comments` 後の指摘対応整理  |
| Contract Taskサマリ | `/create-contract-task` 後の横断影響整理 |
| 完了サマリ          | Issue / PR 完了時の報告                  |
| 判断依頼サマリ      | 人間判断が必要な論点の整理               |
| 停止サマリ          | 作業停止理由と推奨対応の整理             |

要約対象が不明な場合は、推測で文面を作成せず停止する。

---

### 2. 作業内容を整理する

Issue、PR、Task Definition、diff、review resultをもとに作業内容を整理する。

整理観点は以下。

- 作業目的
- 実施内容
- 作成・更新した成果物
- 変更したsource code
- 追加・更新したtest
- 設定変更
- API / DB / generated / CI/CD への影響
- security観点の注意事項
- scope内で完了したこと
- scope外として扱ったこと

事実として確認できる内容と、AIの推論を分けて整理する。

---

### 3. 変更ファイルを整理する

diffまたはPR情報をもとに、変更ファイルを整理する。

分類例。

| 分類         | 対象                                                 |
| ------------ | ---------------------------------------------------- |
| docs         | 設計書、仕様書、運用docs、Markdown、Mermaid          |
| source code  | `apps/`, `packages/`, `scripts/` 等                  |
| test         | unit / integration / contract / e2e / fixture / mock |
| API contract | API仕様、OpenAPI、Orval関連                          |
| DB           | schema、migration、seed、ER、テーブル設計            |
| CI/CD        | GitHub Actions、build、deploy、lint                  |
| generated    | OpenAPI / Orval 等の生成物                           |
| config       | 設定ファイル、tooling設定                            |

secret、APIキー、`.env` 実値をサマリに含めてはならない。

---

### 4. テスト結果を整理する

test results、CI results、PR本文をもとに、テスト・検証結果を整理する。

整理対象の例。

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

テスト未実施がある場合は、以下を明記する。

- 未実施のテスト
- 未実施理由
- 代替確認
- 残リスク
- 人間に確認してほしいこと

実施していないテストを実施済みとして書いてはならない。

---

### 5. レビュー結果を整理する

AIレビューまたは人間レビュー結果がある場合は、以下を整理する。

- レビュー結果分類
- 主な指摘
- 修正必須事項
- 任意改善事項
- 対応済み指摘
- 未対応指摘
- 未対応理由
- follow-up Issue候補
- Human Reviewで確認してほしいこと
- 次Action

レビュー結果分類の例。

| 分類                     | 意味                     |
| ------------------------ | ------------------------ |
| approve_for_human_review | Human Reviewへ進めてよい |
| request_changes          | 同一Branchで修正が必要   |
| needs_human_decision     | 人間判断が必要           |
| split_required           | 別Issue化が必要          |
| blocked                  | 前提不足でレビュー不可   |

---

### 6. 残課題を整理する

作業後に残っている課題を整理する。

分類例。

| 分類                   | 扱い                                      |
| ---------------------- | ----------------------------------------- |
| 現在Task内の未完了事項 | PR作成前または再レビュー前に対応が必要    |
| follow-up候補          | 別Issue化を検討                           |
| Contract Task候補      | `/create-contract-task` を検討            |
| 人間判断待ち           | Human ReviewまたはIssueコメントで判断依頼 |
| 後続Task依存           | 次Taskの前提として明記                    |
| 運用メモ               | IssueまたはPRへ補足として記録             |

残課題がない場合は、「なし」と明記する。

---

### 7. 通知先に応じた文面を作成する

通知先・記録先に応じて、文面を作成する。

| 出力先   | 文面方針                                                     |
| -------- | ------------------------------------------------------------ |
| Slack    | 短く、判断・状況・次Actionが分かる形にする                   |
| PR       | レビュー可能な粒度で、変更内容・テスト結果・残課題を明記する |
| Issue    | 作業計画・進捗・判断依頼・完了報告として整理する             |
| チャット | 人間が次Actionを判断しやすいように簡潔に整理する             |

Slack通知は正本ではない。  
Slack通知だけで作業記録を完結させてはならない。

---

## 出力種別

### 1. 作業サマリ

作業完了後、PR本文案やSlack通知に利用する。

```text
## 作業サマリ

### 対象Issue
-

### 対象Branch / PR
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

### Human確認事項
-

### 次Action
-
```
---

### 2. レビューサマリ

AIレビュー・人間レビュー結果の通知やPR追記に利用する。

```text
## レビューサマリ

### 対象PR
-

### レビュー結果
approve_for_human_review / request_changes / needs_human_decision / split_required / blocked

### 主な確認内容
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

### Human Reviewで確認してほしいこと
-

### 次Action
-
```
---

### 3. 修正対応サマリ

レビュー指摘対応後のPRコメントやSlack通知に利用する。

```text
## 修正対応サマリ

### 対象PR
-

### 対象Issue
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

### 次Action
-
```
---

### 4. 完了サマリ

IssueまたはPRの完了報告に利用する。

```text
## 完了サマリ

### 対象Issue / PR
-

### 完了したこと
-

### 成果物
-

### 確認結果
-

### 残課題
-

### 後続Task
-

### 注意事項
-
```
---

### 5. 判断依頼サマリ

人間判断が必要な場合に利用する。

```text
## 判断依頼サマリ

### 判断が必要な理由
-

### 確認した事実
-

### 推論
-

### 選択肢
1.
2.
3.

### 推奨案
-

### 影響範囲
-

### 判断期限 / 優先度
-

### AIが勝手に進めない理由
-
```
---

### 6. 停止サマリ

作業継続できない場合に利用する。

```text
## 停止サマリ

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

## 出力

| 出力                | 反映先                        |
| ------------------- | ----------------------------- |
| 作業サマリ          | Slack / PR / Issue / チャット |
| レビューサマリ      | Slack / PR / チャット         |
| 修正対応サマリ      | Slack / PR / Issue / チャット |
| 完了サマリ          | Slack / Issue / PR            |
| 判断依頼サマリ      | Slack / Issue / PR / チャット |
| 停止サマリ          | チャット / Issue / PR         |
| follow-up Issue候補 | Issue / PR / チャット         |

---

## 成功条件

以下を満たすこと。

- 要約対象が明確である
- 出力先が明確である
- 作業内容が整理されている
- 変更ファイルが整理されている
- テスト結果が整理されている
- レビュー結果がある場合、レビュー結果が整理されている
- 残課題が整理されている
- Human確認事項が整理されている
- 次Actionが明確である
- Slack通知用の場合、短く判断しやすい文面になっている
- PR / Issue向けの場合、正本記録として必要な情報が含まれている
- 事実と推論が分かれている
- 未確認事項が明示されている
- secret、APIキー、`.env` 実値が含まれていない

---

## 停止条件

以下の場合は、サマリ作成を停止し、人間へ確認する。

- 要約対象が不明
- Issue / PR / Definition のどれを対象にするか不明
- 作業結果を確認できない
- diffを確認できない
- review resultを確認できない
- テスト結果の有無が不明
- 事実として書ける内容と推論の区別ができない
- secret、APIキー、`.env` 実値が含まれる可能性がある
- Slack通知だけで正本記録を完結させる前提になっている
- サマリ作成ではなく実作業が必要になっている
- AIがmerge判断や最終承認判断を行う必要がある

---

## Human確認条件

以下の場合は、人間確認へ回す。

- どの出力先向けのサマリか不明
- Slack向けにどの粒度で通知するか判断が必要
- PR本文に追記すべきか、PRコメントにすべきか判断が必要
- Issueコメントに残すべきか判断が必要
- 未実施テストをどう扱うか判断が必要
- 残課題を現在Task内で扱うか、別Issue化するか判断が必要
- Human Reviewへ進めてよいか判断が必要
- 作業完了扱いにしてよいか判断が必要
- Contract Task化すべき横断影響がある
- security上、文面に含めてよい情報か判断が必要

---

## Statusへの影響

`/summarize-work` は、原則としてProjects Statusを変更しない。

| 状況                      | Status更新意図                                                              |
| ------------------------- | --------------------------------------------------------------------------- |
| Slack通知用サマリ作成     | Status変更なし                                                              |
| PR追記用サマリ作成        | Status変更なし                                                              |
| Issueコメント用サマリ作成 | Status変更なし                                                              |
| 判断依頼サマリ作成        | Status変更なし                                                              |
| 完了サマリ作成            | 原則Status変更なし。変更が必要な場合は別Commandまたは運用スクリプトに委ねる |

Status変更が必要に見える場合は、このCommand内で確定せず、対象Commandまたは運用ルールに従って更新意図を整理する。

---

## ai-logs利用方針

通常の作業サマリをすべて `ai-logs/` に保存しない。

必要な場合のみ、以下の方針で記録候補にする。

記録対象・ディレクトリ構成の正本は [AIログ運用ルール](../../docs/00_共通/AIエージェント運用/AIログ運用ルール.md) §4・§6 とする。

| 種別                    | 保存先                     |
| ----------------------- | -------------------------- |
| Issue化前フィードバック | `ai-logs/intake/`          |
| 作業停止・例外          | `ai-logs/incidents/`       |
| 人間判断待ち            | `ai-logs/human-decisions/` |
| 横断影響                | `ai-logs/cross-cutting/`   |
| AI運用検証              | `ai-logs/experiments/`     |

通常の作業計画はIssue、作業結果はPR、レビューはPR、成果物はdocsを正本とする。

---

## Slack通知

Slack通知を作成する場合は、以下の方針に従う。

- 短く書く
- 対象Issue / PRを明記する
- 結論を先に書く
- 次Actionを明記する
- 人間判断が必要な場合は、判断ポイントを明記する
- 正本への参照先を明記する
- secret、APIキー、`.env` 実値を含めない
- Slack通知だけで作業記録を完結させない

Slack通知例。

```text
## Slack通知サマリ

### 結論
-

### 対象
-

### 実施内容
-

### 確認結果
-

### 残課題 / 判断依頼
-

### 次Action
-

### 正本
-
```
---

## PR追記用サマリ

PR本文またはPRコメントに追記する場合は、以下を含める。

```text
## 追記サマリ

### 追記理由
-

### 変更内容
-

### テスト・検証結果
-

### 未実施事項
-

### Human Review観点
-

### 次Action
-
```
PRはレビュー正本であるため、レビューに必要な情報を省略しない。

---

## Issueコメント用サマリ

Issueコメントに記録する場合は、以下を含める。

```text
## Issueコメントサマリ

### 状況
-

### 実施済み
-

### 未実施
-

### 判断待ち
-

### 次Action
-

### 関連PR / docs
-
```
Issueは作業計画の正本であるため、作業計画・判断履歴・依存関係の整理に必要な情報を含める。

---

## 出力ルール

- 事実と推論を分けて書く
- 未確認事項を明示する
- 要約対象と出力先を明確にする
- Slack通知は正本ではないことを前提にする
- 作業計画はIssueを正本とする
- 作業結果はPRを正本とする
- レビュー結果はPRを正本とする
- 成果物はdocsを正本とする
- 実施していないテストを実施済みと書かない
- secret、APIキー、`.env` 実値を出力しない
- generatedファイルの手動編集を肯定する表現をしない
- Human Reviewを省略する表現をしない
- AIがPRをmergeできるような表現をしない
- 通常作業ログをすべて `ai-logs/` に保存する前提にしない
- Slack通知だけで作業記録を完結させない
- サマリ作成Command内で実作業をしない
