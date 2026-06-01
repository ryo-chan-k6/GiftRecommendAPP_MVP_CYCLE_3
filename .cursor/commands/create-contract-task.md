# create-contract-task

## 目的

`/create-contract-task` は、OpenAPI / Orval / generated / API client など、横断影響がある契約変更Taskを作成するCommandである。

通常Taskに契約変更を混在させないために利用する。

主に以下の場合に利用する。

- Public API / Internal API の契約変更が必要になった場合
- OpenAPI定義の変更が必要になった場合
- Orval設定または生成手順に影響がある場合
- generated API client の差分が発生する場合
- provider / consumer の両方に影響する変更がある場合
- 通常Taskの作業中またはレビュー中に、契約変更を別Taskとして分離すべきと判断された場合
- API contract変更の影響範囲を整理し、専用Issueとして起票する場合

このCommandは、契約変更そのものを実装するCommandではない。  
契約変更の影響範囲を整理し、専用Task Issueを作成することを主目的とする。

---

## 標準形式

```text
/create-contract-task @<definition>
```
例：

```text
/create-contract-task @prompts/definitions/cross-cutting/api-contract-orval/contract-task.yaml
```
Definitionなしでの実行は原則禁止する。

---

## 主担当Agent

| 項目   | Agent                        |
| ------ | ---------------------------- |
| 主担当 | Contract AI                  |
| 補助   | Orchestrator AI / Support AI |
| 後続   | Worker AI / Reviewer AI      |

---

## 参照する定義・Rules

必要に応じて以下を参照する。

- `AGENTS.md`
- `.cursor/agents/contract-ai.md`
- `.cursor/agents/orchestrator-ai.md`
- `.cursor/agents/support-ai.md`
- `.cursor/agents/worker-ai.md`
- `.cursor/agents/reviewer-ai.md`
- `.cursor/rules/project-operation.mdc`
- `.cursor/rules/github-operation.mdc`
- `.cursor/rules/api-contract.mdc`
- `.cursor/rules/code-consistency.mdc`
- `.cursor/rules/testing.mdc`
- `.cursor/rules/docs-consistency.mdc`
- `.cursor/rules/architecture-consistency.mdc`
- `.cursor/rules/security.mdc`
- `.cursor/rules/worktree.mdc`
- `.cursor/rules/git-commit-message.mdc`
- `prompts/definitions/_schemas/contract-definition.schema.md`（§16.1 `work_mode`）
- [Contract Gate運用設計書](../../docs/00_共通/AIエージェント運用/Contract%20Gate運用設計書.md)

契約変更Task作成時は、特に以下を重視する。

- 通常Taskと契約変更Taskを分離する
- API contract変更の目的を明確にする
- OpenAPI / Orval / generated / API client への影響を確認する
- provider / consumer の影響を分けて整理する
- generatedファイルを手動編集しない
- 後方互換性への影響を確認する
- 関連Taskとの依存関係を明確にする
- 人間判断が必要な破壊的変更をAIだけで進めない

---

## 入力

| 入力                | 必須     | 内容                                                           |
| ------------------- | -------- | -------------------------------------------------------------- |
| Contract Definition | 必須     | 契約変更の作業条件、対象、目的、影響範囲を定義する             |
| OpenAPI             | 条件付き | API契約定義。変更対象または参照対象                            |
| Orval config        | 条件付き | Orval設定。生成対象・出力先・client生成条件を確認する          |
| generated diff      | 条件付き | 既に発生している生成物差分                                     |
| related tasks       | 推奨     | 影響を受けるTask、または契約変更を要求しているTask             |
| related docs        | 推奨     | API設計書、API一覧、API仕様書、関連設計書                      |
| Issue / PR          | 条件付き | 既存Taskの作業中・レビュー中に契約変更が発覚した場合に参照する |
| Project情報         | 推奨     | 作成するContract Task IssueのProject同期に利用する             |
| templates           | 推奨     | Issue本文、影響分析、Slack通知文面生成に利用する               |

---

## 処理手順

### 1. 契約変更の対象を確認する

Contract Definitionを読み込み、契約変更の対象を確認する。

`prompts/definitions/_schemas/contract-definition.schema.md` **§6.3** および [Task Definition設計書](../../docs/00_共通/AIエージェント運用/Task Definition設計書.md) **§16.2** に従い、`work_mode` と `branch.no_branch` の整合を確認する（不一致時は停止、または `human_decision_points` に理由必須）。

`implementation_gate`（schema §18.5）が有効な場合、Contract PR マージ後に解放する Implementation Task（`gate_id`・`releases_implementation_for`）を Issue 本文と影響分析に記載する。成果物テンプレートは契約面 `api-contract-spec.md` / `openapi-spec.md` を正とする。

確認観点は以下。

- 変更対象API
- API種別
  - Public API
  - Internal API
  - Batch連携API
  - Reco連携API
- 変更対象ファイル
  - API設計書
  - API一覧
  - API仕様書
  - OpenAPI定義
  - Orval設定
  - generated API client
  - provider実装
  - consumer実装
  - API test
- 変更理由
- 期待する変更結果
- 関連Issue / PR
- 関連Task
- 期限・優先度
- 人間判断要否

契約変更の目的が不明な場合は、Issue化せず停止する。

---

### 2. OpenAPI / Orval / generatedへの影響を確認する

契約変更による影響を確認する。

| 観点         | 確認内容                                                               |
| ------------ | ---------------------------------------------------------------------- |
| API設計書    | URL、method、request、response、error、認証認可の変更有無              |
| API一覧      | API追加・変更・廃止の有無                                              |
| API仕様書    | endpoint単位の仕様変更有無                                             |
| OpenAPI      | path、operationId、schema、parameters、responses、componentsの変更有無 |
| Orval config | 入力OpenAPI、出力先、生成対象、hook、client設定の変更有無              |
| generated    | API client、型定義、request function、mock生成物の差分有無             |
| provider     | apps/api、apps/reco等の実装影響                                        |
| consumer     | apps/web、batch、他clientの利用箇所影響                                |
| test         | contract test、API integration test、mock、fixtureへの影響             |
| docs         | 関連設計書、利用技術スタック、CI/CD方針書等への影響                    |

generatedファイルは手動編集しない。  
generated差分が必要な場合は、生成元と再生成手順をTask内に明記する。

---

### 3. 関連Taskを確認する

契約変更に関連するTaskを確認する。

確認対象は以下。

- 契約変更を要求しているTask
- 影響を受ける後続Task
- 影響を受けるPR
- 依存関係があるIssue
- 同時に進めると競合するTask
- Contract Task完了後に再開すべきTask

関連Taskの状態を以下に分類する。

| 状態         | 扱い                                                        |
| ------------ | ----------------------------------------------------------- |
| 未着手       | Contract Task完了後に着手する候補                           |
| In Progress  | 影響がある場合、作業継続可否を確認する                      |
| AI Review    | 契約変更が必要ならReviewで指摘し、Contract Task化する       |
| Human Review | 人間判断事項として影響を明記する                            |
| Done         | 原則再オープンせず、新しい修正TaskまたはContract Taskで扱う |

過去のTask Branchを再利用して契約変更を混在させてはならない。

---

### 4. Contract専用TaskとしてIssue化すべきか判断する

以下のいずれかに該当する場合は、Contract専用TaskとしてIssue化する。

- OpenAPI定義の変更が必要
- Orval設定の変更が必要
- generated API client の差分が発生する
- provider / consumer の両方に影響する
- API仕様書と実装の整合更新が必要
- API test / contract test の更新が必要
- 既存Taskのscopeを超えるAPI contract変更である
- 後続Taskへ影響する
- 後方互換性の判断が必要
- 破壊的変更の可能性がある
- Human Reviewで契約変更の分離が必要と判断された

以下の場合は、通常Task内の軽微修正として扱える可能性がある。

| 状況                                        | 扱い               |
| ------------------------------------------- | ------------------ |
| API仕様書のtypo修正                         | 通常Task内で対応可 |
| 実装に合わせた軽微な説明補足                | 通常Task内で対応可 |
| request / response の意味を変えない記述補正 | 通常Task内で対応可 |
| OpenAPIやgeneratedに影響しないdocs補足      | 通常Task内で対応可 |

ただし、判断に迷う場合はContract Task化を優先し、人間確認へ回す。

---

### 5. 必要に応じて影響分析を作成する

Contract専用TaskとしてIssue化する場合は、影響分析を作成する。

影響分析には以下を含める。

```text
## 契約変更 影響分析

### 変更対象
-

### 変更理由
-

### 影響範囲
#### API設計書
-
#### API一覧
-
#### API仕様書
-
#### OpenAPI
-
#### Orval
-
#### generated
-
#### provider
-
#### consumer
-
#### test
-
#### docs
-
#### CI/CD
-
#### security
-

### 後方互換性
-

### 破壊的変更の可能性
-

### 関連Issue / PR
-

### 依存関係
-

### 人間判断事項
-

### 推奨対応
-
```
横断影響が大きい場合は、必要に応じて `ai-logs/cross-cutting/` への記録候補とする。

---

### 6. Issue本文を生成する

Contract Task Issue本文を生成する。

Issue本文には、少なくとも以下を含める。

```text
## 背景

## 目的

## 契約変更対象

## scope

## out_of_scope

## 入力資料

## 更新対象

## 影響範囲

## 生成物の扱い

## 実施手順

## 完了条件

## 確認観点

## テスト・検証方針

## 関連Issue / PR

## 依存関係

## Human Reviewで確認してほしいこと
```
generatedファイルを手動編集しないことをIssue本文に明記する。  
必要な場合は、再生成コマンドまたは再生成方針を記載する。

---

### 7. Projectへ追加する

生成したContract Task IssueをGitHub Projectsへ追加する。

Projectが不明な場合は、Issue作成またはProject追加を停止し、人間確認へ回す。

---

### 8. Branch作成条件を設定する

Contract Task用のBranch作成条件を整理する。

確認観点は以下。

- Branch名
- Branch base
- 親Epic Branchとの関係
- 関連Task Branchとの依存関係
- no-branch対象か
- worktree分離が必要か
- 通常Task Branchに契約変更を混在させていないか

Contract Taskで実作業を進める場合は、後続の `/work-issue` に引き継ぐ。  
このCommand内では、実装・OpenAPI修正・Orval再生成そのものを主目的にしない。

---

### 9. 必要に応じて `ai-logs/cross-cutting/` に記録する

以下に該当する場合は、`ai-logs/cross-cutting/` への記録候補とする。

- OpenAPI / Orval / generated を横断する変更
- provider / consumer の複数コンポーネントへ影響する変更
- 後続Taskの順序や依存関係に影響する変更
- 破壊的変更の可能性がある変更
- 人間判断が必要な契約変更
- AI運用上、後から経緯を追跡すべき変更

通常の作業ログをすべて `ai-logs/` に保存しない。  
Contract Task IssueとPRが正本であり、`ai-logs` は必要な横断影響ログに限定する。

---

### 10. Slack通知用サマリを作成する

必要に応じて、Slack通知用サマリを作成する。

Slack通知には以下を含める。

- Contract Task Issue
- 変更対象API
- 変更理由
- 主な影響範囲
- 関連Task
- Human判断事項
- 次Action

Slack通知は正本ではない。  
作業計画はIssue、レビューはPR、成果物はdocsを正本とする。

---

### 11. 次Commandを提示する

Contract Task Issue作成後、実作業が必要な場合は次Commandとして `/work-issue` を提示する。

```text
/work-issue @<definition>
```
PR作成後のレビューが必要な場合は、後続で `/review-pr` を実行する。

---

## 出力

| 出力                | 反映先                                        |
| ------------------- | --------------------------------------------- |
| Contract Task Issue | GitHub Issue                                  |
| 影響分析            | Issue / 必要に応じて `ai-logs/cross-cutting/` |
| Project同期項目     | GitHub Projects                               |
| Branch              | Git Branch                                    |
| Status更新意図      | GitHub Projects / チャット                    |
| Slack通知           | Slack / チャット                              |
| 後続Command         | チャット / Issue                              |
| 停止理由            | チャット / 必要に応じて `ai-logs/incidents/`  |

---

## 成功条件

以下をすべて満たすこと。

- 契約変更の目的が明確である
- 契約変更対象が明確である
- 通常Taskから契約変更が分離されている
- OpenAPI / Orval / generated への影響が確認されている
- provider / consumer への影響が確認されている
- API test / contract test への影響が確認されている
- 関連Taskとの依存関係が整理されている
- 影響範囲がIssue本文に記載されている
- 生成物の扱いが明確である
- generatedファイルを手動編集しない前提になっている
- Contract Task Issueが作成されている
- IssueがProjectへ追加されている
- Branch作成条件が整理されている
- 必要に応じて `ai-logs/cross-cutting/` への記録候補が整理されている
- 必要に応じてSlack通知サマリが作成されている
- 後続Commandが明確である

---

## 停止条件

以下の場合は作業を停止し、人間へ確認する。

- Contract Definitionが存在しない
- `work_mode` が未定義、または `work_mode` と `branch.no_branch` が §16.2 標準値と矛盾し、`human_decision_points` に理由がない
- 契約変更の目的が不明
- 変更対象APIが不明
- 影響範囲が特定できない
- 関連Taskが不明
- Public APIの後方互換性に影響する
- 破壊的変更の可能性がある
- OpenAPI変更の方針が不明
- Orval再生成方針が不明
- generated差分の扱いが不明
- provider / consumer の影響範囲が不明
- API test / contract test の更新要否が不明
- 通常Taskに契約変更を混在させる必要があるように見える
- Project追加先が不明
- Branch baseが不明
- secretや`.env`実値を扱う必要がある
- security上の懸念がある
- 人間判断なしに進めると危険である

---

## Human確認条件

以下の場合は、人間確認へ回す。

- Public APIの後方互換性判断が必要
- breaking changeを許容するか判断が必要
- API path / method / resource設計の判断が必要
- request / response schema の仕様判断が必要
- error response の仕様判断が必要
- 認証認可仕様への影響判断が必要
- Contract Taskを通常Taskから分離すべきか判断が必要
- 関連Taskの優先順位変更が必要
- provider / consumer の対応順序判断が必要
- OpenAPIと実装のどちらを優先して補正するか判断が必要
- Orval設定変更の許容判断が必要
- generated差分の取り込み方針判断が必要
- contract testの追加・修正方針判断が必要
- CI/CD影響の許容判断が必要
- security上の許容判断が必要

---

## Statusへの影響

`/create-contract-task` のStatus影響は以下とする。

| 状況                          | Status更新意図                             |
| ----------------------------- | ------------------------------------------ |
| Contract Task Issue作成成功   | 原則 `Todo` → `In Progress`                |
| Issue作成のみで作業開始しない | `Todo` のまま                              |
| 人間判断待ち                  | 原則Status変更なし、または運用ルールに従う |
| 契約変更不要と判断            | Status変更なし                             |
| 影響範囲不明で停止            | Status変更なし                             |

Status更新は、Commandが直接確定するのではなく、GitHub Actionsまたは運用スクリプトが実施できるよう、更新意図として明確に出力する。

---

## ai-logs利用方針

通常の作業ログをすべて `ai-logs/` に保存しない。

`/create-contract-task` では、必要な場合のみ以下に記録候補を作る。

記録対象・ディレクトリ構成の正本は [AIログ運用ルール](../../docs/00_共通/AIエージェント運用/AIログ運用ルール.md) §4・§6 とする。

| 種別                    | 保存先                     |
| ----------------------- | -------------------------- |
| Issue化前フィードバック | `ai-logs/intake/`          |
| 作業停止・例外          | `ai-logs/incidents/`       |
| 人間判断待ち            | `ai-logs/human-decisions/` |
| 横断影響                | `ai-logs/cross-cutting/`   |
| AI運用検証              | `ai-logs/experiments/`     |

Contract Taskの作業計画はIssue、作業結果はPR、成果物はdocs、レビュー結果はPRを正本とする。

---

## Slack通知

必要に応じて、Contract Task作成通知をSlack通知用に整形する。

通知例。

```text
## Contract Task作成通知

### Contract Task Issue
-

### 変更対象
-

### 変更理由
-

### 主な影響範囲
-

### 関連Task
-

### Human判断事項
-

### 次Action
-
```
Slack通知は正本ではない。  
作業計画はIssue、レビューはPR、成果物はdocsに記録する。

---

## Contract Task作成完了時の出力形式

Contract Task Issueを作成した場合は、以下の形式で出力する。

```text
## create-contract-task 実行結果

### 判断
Contract Task Issueを作成しました。

### Contract Task Issue
-

### 変更対象
-

### 変更理由
-

### 影響範囲
#### API設計書
-
#### API一覧
-
#### API仕様書
-
#### OpenAPI
-
#### Orval
-
#### generated
-
#### provider
-
#### consumer
-
#### test
-
#### docs
-
#### CI/CD
-
#### security
-

### 後方互換性
-

### 破壊的変更の可能性
-

### 関連Issue / PR
-

### Project同期
-

### Branch作成条件
-

### ai-logs記録候補
-

### Human確認事項
-

### Status更新意図
-

### 次に実行するCommand
/work-issue @<definition>
```
---

## 停止時の出力形式

作業を停止する場合は、以下の形式で出力する。

```text
## create-contract-task 停止

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
- 契約変更の目的を明確にする
- 通常Taskに契約変更を混在させない
- OpenAPI / Orval / generated への影響を確認する
- provider / consumer への影響を分けて整理する
- generatedファイルを手動編集しない
- generated差分が必要な場合は、生成元と再生成手順を明記する
- Public APIの後方互換性に影響する場合は人間確認へ回す
- 破壊的変更の可能性がある場合は人間確認へ回す
- secret、APIキー、`.env`実値を出力しない
- Human Reviewを省略しない
- AIがPRをmergeしない
- 通常作業ログをすべて `ai-logs/` に保存しない
- Slack通知だけで作業記録を完結させない
