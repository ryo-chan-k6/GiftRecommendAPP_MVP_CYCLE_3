# AGENTS.md

## 1. 目的

このファイルは、Gift Recommendation Service リポジトリで作業するAI Agent向けの最上位運用ガイドである。

AI Agentは、リポジトリ作業を開始する前に、まず本ファイルを読むこと。

本ファイルでは、以下を定義する。

- プロジェクト概要
- 正本方針
- 作業前の参照順序
- AI Agentの行動境界
- `.cursor/rules/` との関係
- `.cursor/agents/` との関係
- `.cursor/commands/` との関係
- リポジトリ全体の安全ルール
- 人間確認が必要な条件

本ファイルは、詳細ルールをすべて記載するものではない。

詳細な共通ルールは `.cursor/rules/*.mdc` に定義する。  
Agent別の詳細責務は `.cursor/agents/*.md` に定義する。  
Command別の具体手順は `.cursor/commands/*.md` に定義する。  
個別Taskの作業条件は `prompts/definitions/**` に定義する。

---

## 2. プロジェクト概要

このリポジトリは、Gift Recommendation Service を開発・運用するためのリポジトリである。

このサービスは、贈答シーンの意味を推定し、商品側の意味と照合することでギフトを推薦する。

主要なドメイン概念は以下である。

- Gift Meaning
- Gift Meaning Space
- Social
- Symbolic
- Feature
- Context
- Relationship
- Occasion
- Semantic Concept
- User Meaning
- Item Meaning
- Retrieval
- Matching
- Ranking
- Risk
- Popularity
- λ_ctx

本プロジェクトでは、以下を前提にAI支援型の開発運用を行う。

- Cursor
- GitHub Issues
- GitHub Projects
- Git Branch
- Pull Request
- AI Review
- Human Review
- Task Definition
- AI logs
- git worktree

AI Agentは、リポジトリ内のdocsと運用ルールを正本として扱うこと。

---

## 3. リポジトリ構成

このリポジトリでは、主に以下の構成を前提とする。

```text
.
├─ AGENTS.md
├─ apps/
│  ├─ web/
│  ├─ api/
│  ├─ reco/
│  └─ batch/
├─ packages/
├─ docs/
├─ openapi/
├─ prompts/
│  ├─ definitions/
│  └─ templates/
├─ .cursor/
│  ├─ rules/
│  ├─ agents/
│  └─ commands/
├─ .github/
│  └─ workflows/
├─ .githooks/
└─ ai-logs/
```

工程ディレクトリは、[プロジェクトディレクトリ構成定義書.md](./docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md)を正とする。

---

## 4. 正本方針

AI Agentは、以下の正本方針に従う。

| 対象                       | 正本                       |
| -------------------------- | -------------------------- |
| 成果物                     | `docs/`                    |
| 作業計画                   | GitHub Issue               |
| 進捗・予定日・実績日       | GitHub Projects            |
| 作業Branch                 | Git Branch                 |
| レビュー記録               | Pull Request               |
| AI Review結果              | PR本文 / PRコメント        |
| Human判断                  | PRコメント / Issueコメント |
| Issue化前のフィードバック  | `ai-logs/intake/`          |
| incident / blocked / error | `ai-logs/incidents/`       |
| 人間判断が必要な事項       | `ai-logs/human-decisions/` |
| 横断影響ログ               | `ai-logs/cross-cutting/`   |
| 実験・検証結果             | `ai-logs/experiments/`     |
| 個別Task条件               | `prompts/definitions/**`   |
| 再利用テンプレート         | `prompts/templates/**`     |

AI Agentは、チャット履歴、一時メモ、未レビューの生成物を正本として扱ってはならない。  
正本として扱うには、該当するdocs、Issue、PR、Task Definition、ai-logsなどに反映されている必要がある。

正本間で矛盾がある場合、AI Agentは独断でどちらかを正として扱わず、作業を停止して人間へ報告する。

---

## 5. 作業前の参照順序

AI Agentは、作業開始前に以下の順で参照する。

```text
1. AGENTS.md
2. 関連する .cursor/agents/*.md
3. 関連する .cursor/rules/*.mdc
4. prompts/definitions/** のTask Definition
5. 関連Issue
6. 関連PRがある場合はPR本文・PR差分
7. 関連docs
8. 関連ソースファイル
```

レビュー作業では、追加で以下を確認する。

```text
1. PR本文
2. PR差分
3. 関連Issue
4. Task Definition
5. 関連docs
6. 関連Rule
```

---

## 6. `.cursor/rules/` との関係

`.cursor/rules/` は、Cursor AI Agentに適用する詳細Ruleを定義する場所である。

`AGENTS.md` は最上位ガイドであり、詳細な判断ルールは `.cursor/rules/*.mdc` に分離する。

想定するRuleは以下である。

```text
.cursor/rules/
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
├─ worktree.mdc
└─ git-commit-message.mdc
```

### 6.1 Rule利用方針

| Rule                           | 使用する場面                                                             |
| ------------------------------ | ------------------------------------------------------------------------ |
| `project-operation.mdc`        | 正本、scope、人間判断など、プロジェクト全体方針を確認する場合            |
| `github-operation.mdc`         | Issue、Projects、Branch、PRを扱う場合                                    |
| `docs-consistency.mdc`         | `docs/**/*.md` を作成・修正・レビューする場合                            |
| `terminology.mdc`              | ドメイン用語、運用用語、命名の揺れを確認する場合                         |
| `architecture-consistency.mdc` | 設計、アーキテクチャ、モジュール、ディレクトリ、横断整合性を確認する場合 |
| `code-consistency.mdc`         | ソースコードを作成・修正・レビューする場合                               |
| `api-contract.mdc`             | API仕様、OpenAPI、Orval、generated、API clientを扱う場合                 |
| `testing.mdc`                  | テストを作成・修正・レビューする場合                                     |
| `ai-review.mdc`                | Human Review前にAI Reviewを行う場合                                      |
| `security.mdc`                 | secret、認証、権限、workflow、env、ログ、危険操作が関係する場合          |
| `worktree.mdc`                 | git worktreeや複数AI Agentによる並列作業を行う場合                       |
| `git-commit-message.mdc`       | Git commit messageを作成・レビューする場合                               |

本ファイルに各Ruleの詳細内容を重複記載しない。

---

## 7. `.cursor/agents/` との関係

`.cursor/agents/` は、AI Agentごとの詳細な役割、責務、権限境界を定義する場所である。

本ファイルでは、Agent構成の全体像のみを定義する。

想定するAgent定義は以下である。

```text
.cursor/agents/
├─ orchestrator-ai.md
├─ worker-ai.md
├─ reviewer-ai.md
├─ docs-reviewer-ai.md
├─ test-ai.md
├─ contract-ai.md
├─ fixer-ai.md
└─ support-ai.md
```

| Agent            | 主な責務                                        |
| ---------------- | ----------------------------------------------- |
| Orchestrator AI  | 人間依頼の整理、Issue化、Task分割、Agent割当    |
| Worker AI        | 設計、開発、docs作成、実装作業                  |
| Reviewer AI      | PR全体のAI Review                               |
| Docs Reviewer AI | docs整合性、用語、Markdown、Mermaid確認         |
| Test AI          | テスト観点、テストコード、テスト結果確認        |
| Contract AI      | OpenAPI、Orval、generated、API client整合性確認 |
| Fixer AI         | AI Review / Human Reviewコメント対応            |
| Support AI       | 調査、要約、影響分析、補助資料作成              |

Agentごとの詳細手順は `.cursor/agents/*.md` に記載し、`AGENTS.md` には書きすぎない。

---

## 8. `.cursor/commands/` との関係

`.cursor/commands/` は、Commandごとの具体的な作業手順を定義する場所である。

想定するCommandは以下である。

```text
.cursor/commands/
├─ start-epic.md
├─ start-task.md
├─ work-issue.md
├─ create-pr.md
├─ review-pr.md
├─ fix-review-comments.md
└─ create-contract-task.md
```

Command呼び出し形式は、以下を基本とする。

```text
/<command> @<definition>
```

例：

```text
/start-epic @prompts/definitions/epics/recommendation-product-list/epic.yaml
/start-task @prompts/definitions/tasks/recommendation-product-list/design.yaml
```

役割分担は以下とする。

| 成果物                   | 役割                    |
| ------------------------ | ----------------------- |
| `AGENTS.md`              | AI Agent全体の入口      |
| `.cursor/rules/*.mdc`    | 共通ルール・安全条件    |
| `.cursor/agents/*.md`    | Agent別の責務・権限境界 |
| `.cursor/commands/*.md`  | Command別の具体手順     |
| `prompts/definitions/**` | 個別Task条件            |

Commandの詳細手順は `.cursor/commands/*.md` に記載し、`AGENTS.md` には書きすぎない。

---

## 9. `prompts/` との関係

`prompts/` は、Task Definitionと再利用テンプレートを管理する場所である。

想定構成は以下である。

```text
prompts/
├─ README.md
├─ definitions/
│  ├─ _schemas/
│  ├─ _examples/
│  ├─ epics/
│  ├─ tasks/
│  ├─ reviews/
│  └─ cross-cutting/
└─ templates/
   ├─ issue-body/
   ├─ pr-body/
   └─ ai-feedback/
```

個別Taskの条件は `prompts/definitions/**` に記載する。

AI Agentは、Task固有条件を以下に埋め込んではならない。

- `AGENTS.md`
- `.cursor/rules/*.mdc`
- `.cursor/agents/*.md`
- `.cursor/commands/*.md`

Task Definitionには、必要に応じて以下を定義する。

- workstream
- title
- phase
- input docs
- output files
- target files
- exclusive files
- out of scope
- review points
- completion criteria
- operation_logging
- Planned Start
- Due Date

---

## 10. 標準ワークフロー

AI支援型開発の標準フローは以下である。

```text
Human request
  ↓
Task Definition
  ↓
Issue
  ↓
Project item
  ↓
Branch / worktree
  ↓
Work
  ↓
Commit
  ↓
Pull Request
  ↓
AI Review
  ↓
Human Review
  ↓
Humanによるmerge判断
  ↓
Done
```

AI Agentは、許可された範囲でPR作成およびAI Reviewまでを担当してよい。

ただし、AI Agentは最終merge判断を行ってはならない。  
merge判断は人間が行う。

---

## 11. Human-Led運用とAI-Led運用

本プロジェクトでは、Human-Led運用とAI-Led運用の両方を想定する。

### 11.1 Human-Led運用

主に、事業構想、概念設計、アプリケーション設計など、人間判断が強い工程で使用する。

典型フローは以下である。

```text
人間がIssue作成
Issueはno-branchから開始
人間が作業可能と判断したらno-branchを外す
workflowまたは人間がBranch作成
必要に応じてAI Agentが作業
AI Review
Human Review
人間がmerge判断
```

### 11.2 AI-Led運用

主に、実装設計、開発、テストなど、Task Definitionで作業条件を明確にできる工程で使用する。

典型フローは以下である。

```text
人間が /start-task @definition を実行
AI AgentがTask Definitionを読む
AI AgentがIssueを作成
AI AgentがProjectへ追加
AI AgentがBranchを作成
AI Agentが作業
AI Agentがcommit
AI AgentがPR作成
AI AgentがAI Review
Human Review
人間がmerge判断
```

どちらの運用でも、Human Reviewと人間によるmerge判断を省略してはならない。

**Machine account:** AI Agent の commit / push / PR 作成は `okuri-ai-bot`（Classic PAT）で行い、Human Review / merge は `ryo-chan-k6` が行う。詳細は [AI機械アカウント運用設計書](docs/00_共通/AIエージェント運用/AI機械アカウント運用設計書.md) および `.github/ai-bot-account.json`。

---

## 12. GitHub運用方針

基本関係は以下とする。

```text
1 Issue = 1 Project Task = 1 Branch = 1 PR
```

Issue種別は以下とする。

| 種別       | 意味    |
| ---------- | ------- |
| Epic Issue | 親Issue |
| Task Issue | 子Issue |

Issue title例は以下である。Epic 粒度は **成果物識別子単位を原則**とし、ID 未整備領域のみ機能・領域単位を例外として残す（Issue運用ルール §4.1、成果物一覧×Task Definition化方針書 §3.5）。

```text
[Epic]API-PUB-002:レコメンド実行
[Epic]MOD-RECO-001:Recommendation Orchestrator
[Epic]GitHub Projects自動化
[Task]API-PUB-002:レコメンド実行API仕様書作成
[Task]API-INT-002:Reco推薦実行API仕様書作成
```

`[Epic]` / `[Task]` の直後に半角スペースを入れない。識別子付き Epic / Task は `{識別子}:{概要}` 形式（コロン前後にスペースなし）とする。詳細は Issue運用ルール §5.3、Task Definition設計書 §15.0（Epic タイトル規約）・§15.1（共通）・§15.2〜§15.4（種別）を正とする。

Projects Statusは以下を正とする。

```text
Backlog
Todo
In Progress
AI Review
Human Review
Done
```

標準Status遷移は以下である。

```text
Backlog
  ↓
Todo
  ↓
In Progress
  ↓
AI Review
  ↓
Human Review
  ↓
Done
```

修正が必要な場合は、以下のように戻す。

```text
AI Review / Human Review
  ↓
In Progress
  ↓
AI Review
```

---

## 13. Branch / PR方針

Branch名は以下の形式とする。

```text
<type>/<unit>-<issue-number>-<english-summary>
```

例：

```text
feature/epic-101-recommendation-api
docs/task-111-recommendation-api-design
feature/task-112-recommendation-api-implementation
test/task-113-recommendation-api-unit-test
```

Branch typeは、Issue label `type:*` に合わせる。

代表例：

```text
feature
fix
docs
refactor
chore
test
hotfix
spike
```

Branch unitは、Issue label `unit:*` に合わせる。

代表例：

```text
epic
task
```

Branch baseとPR targetは以下とする。

| Issue種別 | Branch base   | PR target     |
| --------- | ------------- | ------------- |
| Epic      | `develop`     | `develop`     |
| Task      | 親Epic Branch | 親Epic Branch |

Task PRを `develop` に直接向けてはならない。

以下のBranchへ直接commitしてはならない。

```text
main
develop
```

---

## 14. worktree方針

複数AI Agentによる並列作業では、git worktreeを使用する。

基本ルールは以下である。

```text
1 Task Branch = 1 worktree
```

AI Agentは、編集前に現在のディレクトリとBranchを確認する。

必須確認コマンドは以下である。

```bash
pwd
git branch --show-current
git status --short
git worktree list
```

1つのworktreeで複数Issueの作業を混在させてはならない。  
複数AI Agentが同じworktreeまたは同じBranchを同時編集してはならない。

worktree削除前には、以下を確認する。

```bash
git status --short
git log --oneline --decorate -5
```

以下があるworktreeを削除してはならない。

- 未コミット差分
- 未追跡ファイル
- 未解決conflict
- 未push commit
- PR状態不明
- Issue状態不明

---

## 15. commit message方針

commit messageは日本語を基本とする。

形式は以下とする。

```text
<type>: <日本語の変更概要>
```

scopeを付ける場合は以下とする。

```text
<type>(<scope>): <日本語の変更概要>
```

例：

```text
docs: AIエージェント共通Rules設計書を追加
docs(rules): git-commit-message.mdcを追加
fix(api): Recommendation Requestのbudget未指定時の判定を修正
test(reco): Ranking計算の境界値テストを追加
ci: PR作成時のdocs検証workflowを追加
```

英語のみのcommit messageは禁止する。

以下のような曖昧なmessageは禁止する。

```text
update
fix
wip
temp
修正
対応
更新
```

Cursor等で自動生成されたcommit messageは、そのまま採用せず、必ず内容を確認する。

local hookを利用する場合は、以下で有効化する。

```bash
git config core.hooksPath .githooks
```

---

## 16. docs方針

docsは成果物の正本である。

AI Agentは、docs作成・修正時に以下を守る。

- 適切なディレクトリに配置する
- 既存の文書名・章構成・表記に合わせる
- 関連docsと整合させる
- 同じ定義を複数docsに重複させすぎない
- 必要に応じて参照元docsを明示する
- 古いチャット内容を正本として扱わない
- 未確定事項を決定事項として書かない
- Markdown表を読みやすく保つ
- Mermaid図の構文破綻を避ける
- 現行の工程ディレクトリ名を使用する

docsを扱う場合は、以下のRuleを参照する。

```text
.cursor/rules/docs-consistency.mdc
.cursor/rules/terminology.mdc
.cursor/rules/architecture-consistency.mdc
```

---

## 17. 用語方針

AI Agentは、プロジェクト用語を一貫して使用する。

重要なドメイン用語は以下である。

```text
Gift Meaning
Gift Meaning Space
Social
Symbolic
Feature
Context
Relationship
Occasion
Semantic Concept
Semantic Map
Hint
Feature Hint Dictionary
User Meaning
Item Meaning
Retrieval
Matching
Ranking
Context Score
λ_ctx
Risk
Popularity
```

MVPにおけるFeature名は固定とする。

Social Features:

```text
formality
safety
brand_appropriateness
```

Symbolic Features:

```text
emotion
novelty
intimacy
symbolic_identity
story_richness
```

正本docsにない同義語、略称、別表記を勝手に導入してはならない。

---

## 18. code方針

ソースコード作成・修正時、AI Agentは以下を守る。

- Task Definitionのscope内で作業する
- app境界を守る
- module責務を守る
- 呼び出し元・呼び出し先のI/Fを一致させる
- 型定義と実装を一致させる
- `null` / `undefined` / `None` / empty を意図的に扱う
- error handlingを既存方針と整合させる
- 依存方向を逆転させない
- 不要な抽象化を避ける
- 意図、制約、ドメイン判断が必要な箇所にはコメントを記載する
- コードを読めば分かる内容だけを重複説明するコメントは避ける
- 挙動変更時はテスト更新要否を確認する
- 横断影響を検知した場合は報告する

主なapp責務は以下である。

| App          | 責務                                                             |
| ------------ | ---------------------------------------------------------------- |
| `apps/web`   | UI、画面、フロントエンド状態管理、API client利用                 |
| `apps/api`   | Web向けAPI、認証・認可境界、DBアクセス窓口、reco連携             |
| `apps/reco`  | レコメンド計算、意味特徴量、Matching / Rankingなどの推薦ロジック |
| `apps/batch` | データ取得、加工、特徴量生成、集計、定期・非同期処理             |
| `packages`   | 共通型、共通関数、共通設定                                       |

コードを扱う場合は、以下のRuleを参照する。

```text
.cursor/rules/code-consistency.mdc
.cursor/rules/security.mdc
.cursor/rules/testing.mdc
```

---

## 19. API contract方針

API関連ファイルを扱う場合、AI Agentは以下の整合性を保つ。

- API設計書
- API一覧
- API仕様書
- OpenAPI定義
- Orval設定
- generated
- API client
- web / api / reco / batch の利用側実装
- テスト

generatedファイルを手動編集してはならない。

OpenAPIを変更した場合は、generated差分とAPI client利用側への影響を確認する。

破壊的API変更は明示し、Human Reviewを必須とする。

API contractを扱う場合は、以下のRuleを参照する。

```text
.cursor/rules/api-contract.mdc
.cursor/rules/code-consistency.mdc
.cursor/rules/testing.mdc
.cursor/rules/security.mdc
```

---

## 20. testing方針

AI Agentは、code、API、DB、batch、domain logicを変更する場合、テスト更新要否を確認する。

必要に応じて、以下を検証する。

- 正常系
- 異常系
- 境界値
- optional / nullable
- 外部依存失敗
- API request / response schema
- DB access
- domain calculation
- batch再実行性

テストは以下に依存してはならない。

- production DB
- production API
- production secret
- 実token
- 実個人情報
- 不安定なnetwork
- 実行順序
- localにしかないファイル

テスト未実施の場合は、以下を明示する。

- 未実施対象
- 未実施理由
- 残るリスク
- 代替確認
- 推奨後続対応

---

## 21. AI Review方針

PRベース作業では、Human Review前にAI Reviewを実施する。

AI Reviewでは、以下を確認する。

- IssueとPR差分の整合
- Task Definition scope
- Branch / PR target
- PR本文の充足
- docs整合性
- 用語整合性
- architecture整合性
- code整合性
- API contract整合性
- DB変更影響
- test妥当性
- CI/CD影響
- security risk
- 横断影響

AI Reviewの結論は以下のいずれかとする。

| 結論                   | 意味                          |
| ---------------------- | ----------------------------- |
| `Human Reviewへ進行可` | Blocker / Must が残っていない |
| `修正後に再AI Review`  | Human Review前に修正が必要    |
| `Human判断待ち`        | AI Agentだけでは判断できない  |

AI Reviewはmerge承認ではない。  
merge判断は人間が行う。

---

## 22. security方針

AI Agentは、secretを出力・保存・commitしてはならない。

禁止対象は以下を含む。

- API key
- access token
- refresh token
- password
- cookie
- session
- private key
- client secret
- 認証情報付きdatabase URL
- Supabase key
- OpenAI API key
- GitHub token
- OAuth secret
- webhook secret
- Authorization headerの実値
- `.env` の実値

`.env.example` や `.env.sample` に記載してよいのは以下のみである。

- 環境変数名
- ダミー値
- 用途説明

client側コードにsecretを置いてはならない。

以下にsecretや認証情報を記載してはならない。

- source code
- docs
- Issue body
- PR body
- commit message
- comments
- logs
- test fixtures
- seed files
- generated examples
- ai-logs

secret漏えいの可能性がある場合、AI Agentは即座に作業を停止し、人間へ報告する。

---

## 23. 危険操作方針

AI Agentは、人間の明示承認なしに危険操作を行ってはならない。

危険操作の例は以下である。

- `main` への直接push
- `develop` への直接push
- PR merge
- force push
- history rewrite
- Branch削除
- `git reset --hard`
- 広範囲のファイル削除
- production deploy
- production DB migration
- production data削除
- `drop table`
- `truncate`
- 全件update / delete
- secret更新
- secret削除
- GitHub Secrets変更
- 権限昇格
- 大量外部API実行
- 大きなコスト影響がある操作

危険操作が必要に見える場合、AI Agentは以下を整理して人間へ確認する。

- 必要な理由
- 確認済みの事実
- AI Agentの推論
- 選択肢
- 推奨案
- 実施しない場合のリスク

---

## 24. ai-logs方針

`ai-logs/` は、通常作業ログをすべて保存する場所ではない。

`ai-logs/` は、以下の場合に限定して使用する。

- Issue化前のフィードバック
- incident
- blocked work
- error
- 人間判断が必要なログ
- 横断影響ログ
- OpenAPI / Orval / generated影響ログ
- 実験・検証結果
- AI運用検証ログ

想定構成は以下である。

```text
ai-logs/
├─ README.md
├─ intake/
├─ incidents/
├─ human-decisions/
├─ cross-cutting/
└─ experiments/
```

Issue作成後の作業計画はIssueで管理する。  
PR作成後の作業サマリー・レビューはPR本文またはPRコメントで管理する。  
成果物の正本はdocsで管理する。

---

## 25. 報告方針

AI Agentは、日本語で報告することを基本とする。

報告では、以下を区別する。

| 区分     | 意味                                                        |
| -------- | ----------------------------------------------------------- |
| 事実     | ファイル、差分、docs、コマンド、Issue、PRから確認できる内容 |
| 推論     | 事実から導いた影響・懸念・提案                              |
| 未確認   | まだ確認できていない内容                                    |
| 判断依頼 | 人間判断が必要な内容                                        |

作業完了報告では、必要に応じて以下を含める。

- 変更内容
- 変更ファイル
- 実行したテスト
- 未実施テスト
- 残リスク
- Human Review観点

以下の場合、作業完了と報告してはならない。

- 必須テストを実行しておらず、未実施理由もない
- scopeが未完了
- Blockerが残っている
- 人間判断が必要
- PRベース作業でAI Reviewが未完了

---

## 26. 人間確認が必要な条件

AI Agentは、以下の場合に作業を停止し、人間へ確認する。

- 正本docs間で矛盾がある
- Task Definitionのscopeが不明確
- Issue / Branch / PR targetが不明確
- Branch baseが不明確
- Task Branchが `develop` に直接向きそう
- out of scope変更が必要に見える
- generatedファイルを手動編集する必要がありそう
- 破壊的API変更が必要
- DB schema変更が必要
- migration影響が不明
- security方針変更が必要
- secret漏えいの疑いがある
- production影響がありそう
- 危険操作が必要
- test失敗原因が不明
- conflict解消に業務判断・設計判断が必要
- Human Reviewを省略しないと進められない
- AIにmerge判断を求められている

確認時は、以下を整理する。

```text
- 確認が必要な理由
- 現在確認できている事実
- AI Agentの推論
- 選択肢
- 推奨案
- 判断しない場合のリスク
```

---

## 27. 禁止事項

AI Agentは、以下を行ってはならない。

- Task Definitionのscopeを無視する
- scope外ファイルを無断編集する
- チャット履歴を正本として扱う
- プロジェクト方針を推測で作る
- 関連docs確認なしに正本docsを書き換える
- AGENTS、Rules、Agents、Commands間で詳細ルールを重複させる
- secretを露出する
- `.env` 実値をcommitする
- generatedファイルを手動編集する
- テスト未実施を説明なしに進める
- AI Reviewを省略する
- Human Reviewを省略する
- PRをmergeする
- `main` へ直接pushする
- `develop` へ直接pushする
- 英語のみのcommit messageを作成する
- 承認なしにforce pushする
- 承認なしに破壊的cleanupを行う
- conflictを推測で解消する
- 必要なHuman ReviewなしにDone扱いする

---

## 28. 作業開始前チェックリスト

作業開始前に、以下を確認する。

```text
[ ] AGENTS.mdを読んだ
[ ] 関連するAgent roleを特定した
[ ] 必要に応じて .cursor/agents/*.md を読んだ
[ ] 関連する .cursor/rules/*.mdc を読んだ
[ ] Task Definitionを読んだ
[ ] target filesを特定した
[ ] exclusive filesを特定した
[ ] out of scopeを特定した
[ ] 正本docsを特定した
[ ] Git作業がある場合、Branch / PR target方針を確認した
[ ] security riskがないことを確認した
```

---

## 29. commit前チェックリスト

commit前に、以下を確認する。

```text
[ ] 現在Branchが正しい
[ ] 現在worktreeが正しい
[ ] Branchがmainまたはdevelopではない
[ ] git statusを確認した
[ ] 差分がTask scope内である
[ ] secretが含まれていない
[ ] .env実値が含まれていない
[ ] debug codeが残っていない
[ ] conflict markerが残っていない
[ ] generated差分が意図したものである
[ ] テストを実行した、または未実施理由が明確である
[ ] commit messageが日本語方針に従っている
```

---

## 30. PR作成前チェックリスト

PR作成前に、以下を確認する。

```text
[ ] 関連Issueが存在する
[ ] Task Definitionが反映されている
[ ] PR targetが正しい
[ ] Task PRは親Epic Branchに向いている
[ ] Epic PRはdevelopに向いている
[ ] PR本文にscopeが記載されている
[ ] PR本文に変更ファイルが記載されている
[ ] PR本文にテスト結果が記載されている
[ ] PR本文に未実施事項が記載されている
[ ] PR本文に影響範囲が記載されている
[ ] PR本文にHuman Review観点が記載されている
[ ] AI Reviewを実行できる状態である
[ ] PR author が machine account（`.github/ai-bot-account.json`）である
```

---

## 31. Human Review前チェックリスト

Human Review依頼前に、以下を確認する。

```text
[ ] AI Reviewが完了している
[ ] Blockerが解消されている
[ ] Mustが解消されている、または明示的にエスカレーションされている
[ ] テスト結果または未実施理由が記載されている
[ ] security riskを確認済みである
[ ] API / DB / generated影響を確認済みである
[ ] Human判断事項が明確に整理されている
[ ] PR本文がレビュー可能な状態である
```

---

## 32. 保守方針

`AGENTS.md` の変更は、IssueとPRで管理する。

`AGENTS.md` を変更する場合は、以下への影響を確認する。

- `.cursor/rules/`
- `.cursor/agents/`
- `.cursor/commands/`
- `prompts/`
- GitHub運用
- AI Review
- security

`AGENTS.md` に詳細を書きすぎてはならない。

詳細化が必要な場合は、以下に分離する。

| 詳細種別           | 配置先                   |
| ------------------ | ------------------------ |
| 共通運用ルール     | `.cursor/rules/*.mdc`    |
| Agent別責務・権限  | `.cursor/agents/*.md`    |
| Command別手順      | `.cursor/commands/*.md`  |
| 個別Task条件       | `prompts/definitions/**` |
| 再利用テンプレート | `prompts/templates/**`   |
| 成果物本文         | `docs/**`                |

---

## 33. 最終ルール

AI Agentは、判断に迷った場合、以下を優先する。

```text
停止する
事実を報告する
推論を分ける
選択肢を示す
安全な推奨案を出す
人間へ確認する
```

正本docs、security、API contract、DB schema、Git履歴、Branch構造、PR target、production挙動に影響する可能性がある場合、推測で進めてはならない。
