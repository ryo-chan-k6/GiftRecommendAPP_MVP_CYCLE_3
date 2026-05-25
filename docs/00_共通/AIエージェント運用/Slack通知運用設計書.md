# Slack通知運用設計書

## 1. 目的

本ドキュメントは、Gift Recommendation Service におけるAIエージェント活用型開発運用で使用するSlack通知の運用ルールを定義する。

Slack通知は、AIエージェントによるIssue作成、作業開始、PR作成、AIレビュー完了、人間判断依頼、作業停止などを人間へ知らせるために使用する。

Slackは通知・サマリ用途であり、作業計画、レビュー結果、成果物の正本ではない。

---

## 2. 本ドキュメントの位置づけ

本ドキュメントは、Slack通知の通知対象、通知タイミング、通知内容、文面、正本関係に関する正本である。

| 項目                     | 正本ドキュメント                           |
| ------------------------ | ------------------------------------------ |
| AIエージェント運用全体   | AIエージェント活用型\_開発運用フロー設計書 |
| AIエージェント体制・責務 | AIエージェント体制・責務定義               |
| Command仕様              | Commands設計書                             |
| Task Definition構造      | Task Definition設計書                      |
| Prompts運用              | Prompts運用ルール                          |
| AIレビュー運用           | AIレビュー運用設計書                       |
| AIログ運用               | AIログ運用ルール                           |
| Slack通知運用            | 本ドキュメント                             |
| Projects Status管理      | Projects運用ルール                         |
| Issue運用                | Issue運用ルール                            |
| Branch / PR運用          | ブランチ運用ルール                         |

---

## 3. Slack通知の基本方針

Slackは、作業状況を人間がすぐ把握するための通知・サマリとして使用する。

| 方針                                 | 内容                                            |
| ------------------------------------ | ----------------------------------------------- |
| Slackは正本にしない                  | 正本はIssue、Projects、PR、docs、ai-logsに置く  |
| 通知は簡潔にする                     | 詳細はIssue / PR / docsへのリンクで確認する     |
| 人間アクションが必要な通知を優先する | Human Review、判断依頼、作業停止を重視する      |
| 通知しすぎない                       | 通常作業の細かい進捗は原則通知しない            |
| 日本語で通知する                     | 人間が即時理解できるようにする                  |
| リンクを必ず付ける                   | Issue / PR / docs / ai-logsへの導線を明確にする |
| secretを含めない                     | APIキー、token、環境変数値は通知しない          |

---

## 4. 正本関係

Slack通知は、各正本への入口として扱う。

| 情報           | 正本                 | Slackでの扱い                      |
| -------------- | -------------------- | ---------------------------------- |
| 作業計画       | GitHub Issue         | Issueリンクと要約を通知            |
| 進捗状態       | GitHub Projects      | Status変更の要約を通知             |
| 作業実体       | Branch / Commit      | Branch名、commit概要を通知         |
| レビュー結果   | Pull Request         | PRリンクとレビュー結果サマリを通知 |
| 成果物         | docs                 | 更新docsのリンクまたはパスを通知   |
| 例外・補助記録 | ai-logs              | ログパスと確認事項を通知           |
| 人間判断事項   | Issue / PR / ai-logs | 判断依頼として通知                 |

Slackだけに重要情報を閉じ込めてはならない。

---

## 5. 通知対象イベント

Slack通知対象は以下とする。

| イベント             |       通知要否 | 通知目的                                            |
| -------------------- | -------------: | --------------------------------------------------- |
| Issue作成            |       通知する | 新規タスク発生を知らせる                            |
| Branch作成           | 原則通知しない | Issue通知に含める                                   |
| 作業開始             | 原則通知しない | Projects Statusで管理する                           |
| PR作成               |       通知する | AI Review開始を知らせる                             |
| AIレビュー完了       |       通知する | Human Review依頼または修正必要を知らせる            |
| Human Review依頼     |       通知する | 人間レビューを促す                                  |
| レビュー指摘対応完了 |       通知する | 再AI ReviewまたはHuman Reviewへ進めることを知らせる |
| PR更新               | 条件付きで通知 | 人間確認が必要な場合のみ                            |
| PR merge             |       通知する | Task / Epic完了を知らせる                           |
| 作業停止・例外       |   必ず通知する | 人間の介入を促す                                    |
| 人間判断依頼         |   必ず通知する | 判断待ちを明確にする                                |
| 横断影響検知         |   必ず通知する | 影響範囲確認を促す                                  |
| ai-logs作成          | 条件付きで通知 | 人間確認が必要な場合に通知                          |
| 通常commit           | 原則通知しない | PRで確認する                                        |

---

## 6. 通知レベル

Slack通知には通知レベルを設定する。

| レベル            | 用途           | 通知例                               |
| ----------------- | -------------- | ------------------------------------ |
| `info`            | 通常通知       | Issue作成、PR作成、PR merge          |
| `review`          | レビュー依頼   | AI Review完了、Human Review依頼      |
| `action_required` | 人間対応が必要 | 人間判断依頼、レビュー指摘対応要否   |
| `warning`         | 注意が必要     | 横断影響、scope超過、generated影響   |
| `error`           | 作業停止       | branch競合、入力不足、secret混入疑い |

原則として、`action_required`、`warning`、`error` は人間が確認する。

---

## 7. 通知先

通知先は、運用フェーズに応じて設定する。

| 通知種別         | 通知先                                     |
| ---------------- | ------------------------------------------ |
| 通常通知         | 開発運用チャンネル                         |
| Human Review依頼 | 開発運用チャンネル                         |
| 人間判断依頼     | 開発運用チャンネル、必要に応じてメンション |
| 作業停止・例外   | 開発運用チャンネル、必要に応じてメンション |
| 横断影響         | 開発運用チャンネル                         |
| AI運用検証       | AI運用チャンネルまたは開発運用チャンネル   |

MVP段階では、単一の開発運用チャンネルに集約してよい。

---

## 8. メンション方針

Slack通知では、必要な場合のみメンションを付与する。

| 状況             | メンション         |
| ---------------- | ------------------ |
| 通常のIssue作成  | 不要               |
| 通常のPR作成     | 不要               |
| Human Review依頼 | 必要に応じて実施   |
| 人間判断依頼     | 原則メンションする |
| 作業停止・例外   | 原則メンションする |
| secret混入疑い   | 原則メンションする |
| 横断影響あり     | 必要に応じて実施   |

通知過多を避けるため、すべての通知にメンションを付けない。

---

## 9. 通知生成主体

Slack通知は、以下のいずれかが生成する。

| 生成主体       | 用途                                                  |
| -------------- | ----------------------------------------------------- |
| AI Agent       | PR作成通知、AIレビュー完了通知、判断依頼サマリ        |
| GitHub Actions | Issue作成、Project Status変更、PR mergeなどの自動通知 |
| Script         | Issue / PR / Project / ai-logsの情報を集約した通知    |
| Human          | 必要に応じた手動補足通知                              |

AI Agentが通知文を作成する場合でも、正本はIssue / PR / docs / ai-logsに置く。

---

## 10. 通知テンプレートの配置

Slack通知テンプレートは、以下に配置する。

```text
prompts/templates/slack/
```

標準テンプレートは以下とする。

```text
prompts/templates/slack/
├─ issue-created.md
├─ pr-created.md
├─ ai-review-completed.md
├─ human-review-request.md
├─ review-fix-completed.md
├─ pr-merged.md
├─ human-decision-required.md
├─ incident-detected.md
└─ cross-cutting-impact.md
```

| テンプレート                 | 用途                     |
| ---------------------------- | ------------------------ |
| `issue-created.md`           | Issue作成通知            |
| `pr-created.md`              | PR作成通知               |
| `ai-review-completed.md`     | AIレビュー完了通知       |
| `human-review-request.md`    | 人間レビュー依頼         |
| `review-fix-completed.md`    | レビュー指摘対応完了通知 |
| `pr-merged.md`               | PR merge / Done通知      |
| `human-decision-required.md` | 人間判断依頼             |
| `incident-detected.md`       | 作業停止・例外通知       |
| `cross-cutting-impact.md`    | 横断影響通知             |

---

## 11. 通知文面の標準構成

Slack通知は、以下の構成を標準とする。

```text
[通知レベル] タイトル

概要:
- 何が起きたか

対象:
- Issue:
- PR:
- Branch:
- Status:
- Agent:

人間に必要な対応:
- 対応要否
- 確認してほしいこと

リンク:
- Issue / PR / docs / ai-logs
```

通知は長くしすぎない。  
詳細はIssue / PR / ai-logsへ誘導する。

---

## 12. Issue作成通知

### 12.1 通知タイミング

Issueが作成されたタイミングで通知する。

AI主導タスクでは、Orchestrator AIまたはworkflowがIssue作成後に通知する。

### 12.2 通知内容

```markdown
[info] Issueを作成しました

概要:

- {{issue_title}}
- {{summary}}

Project:

- Phase: {{phase}}
- Status: {{status}}
- Priority: {{priority}}
- Planned Start: {{planned_start}}
- Due Date: {{due_date}}

Branch:

- no-branch: {{no_branch}}
- Branch: {{branch_name}}

リンク:

- Issue: {{issue_url}}
```

### 12.3 補足

Branch作成も同時に行われた場合は、同じ通知内にBranch名を含める。  
Branch作成だけを単独通知しない。

---

## 13. PR作成通知

### 13.1 通知タイミング

AI AgentがPRを作成したタイミングで通知する。

### 13.2 通知内容

```markdown
[info] PRを作成しました

概要:

- {{pr_title}}
- {{summary}}

対象:

- Issue: {{issue_url}}
- PR: {{pr_url}}
- Branch: {{branch_name}}
- Target: {{pr_target}}
- Next Status: AI Review

主な変更:

- {{change_summary}}

確認結果:

- {{validation_summary}}

次の対応:

- AI Reviewを実施します。
```

### 13.3 補足

Task PRでは、PR本文に `Related to #<Task Issue番号>` が記載されている前提とする。

---

## 14. AIレビュー完了通知

### 14.1 通知タイミング

AI Reviewが完了し、PRへレビュー結果を記録したタイミングで通知する。

### 14.2 通知内容

```markdown
[review] AIレビューが完了しました

結果:

- Review Result: {{review_result}}
- Next Status: {{next_status}}

対象:

- Issue: {{issue_url}}
- PR: {{pr_url}}
- Reviewer: {{reviewer_agent}}

サマリ:

- {{review_summary}}

指摘:

- must: {{must_count}}
- should: {{should_count}}
- nit: {{nit_count}}
- question: {{question_count}}

人間に必要な対応:

- {{human_action}}

リンク:

- PR Review: {{pr_url}}
```

### 14.3 結果別の通知方針

| Review Result              | 通知レベル        | 内容             |
| -------------------------- | ----------------- | ---------------- |
| `approve_for_human_review` | `review`          | Human Review依頼 |
| `request_changes`          | `action_required` | 修正必要サマリ   |
| `needs_human_decision`     | `action_required` | 判断依頼         |
| `split_required`           | `warning`         | 別Issue化提案    |
| `blocked`                  | `error`           | 停止理由         |

---

## 15. Human Review依頼通知

### 15.1 通知タイミング

AI ReviewがOKとなり、Projects Statusが `Human Review` へ進んだタイミングで通知する。

### 15.2 通知内容

```markdown
[review] Human Reviewをお願いします

対象:

- Issue: {{issue_url}}
- PR: {{pr_url}}
- Status: Human Review

AIレビュー結果:

- {{ai_review_summary}}

人間に確認してほしいこと:

- {{human_review_points}}

リンク:

- PR: {{pr_url}}
```

### 15.3 補足

Human Review依頼では、必ずPRリンクを含める。  
レビュー観点はPR本文またはAIレビューコメントにも記録されていること。

---

## 16. レビュー指摘対応完了通知

### 16.1 通知タイミング

Fixer AIまたはWorker AIがレビュー指摘対応を完了し、PRを更新したタイミングで通知する。

### 16.2 通知内容

```markdown
[info] レビュー指摘対応が完了しました

対象:

- Issue: {{issue_url}}
- PR: {{pr_url}}
- Branch: {{branch_name}}

対応内容:

- {{fix_summary}}

確認結果:

- {{validation_summary}}

次の対応:

- 再度AI Reviewを実施します。

リンク:

- PR: {{pr_url}}
```

### 16.3 補足

軽微な修正でも、人間の確認待ちに進む場合は通知する。  
AI Reviewへ戻るだけの場合は、通知を簡略化してよい。

---

## 17. PR merge / Done通知

### 17.1 通知タイミング

PRがmergeされ、対象IssueまたはProjects Statusが `Done` になったタイミングで通知する。

### 17.2 通知内容

```markdown
[info] PRがmergeされ、タスクが完了しました

対象:

- Issue: {{issue_url}}
- PR: {{pr_url}}
- Branch: {{branch_name}}
- Status: Done

完了内容:

- {{summary}}

リンク:

- PR: {{pr_url}}
- Issue: {{issue_url}}
```

### 17.3 Task / Epic別の扱い

| 種別       | Doneタイミング                                          |
| ---------- | ------------------------------------------------------- |
| Task Issue | Task PRが親Epic Branchへmergeされた時点                 |
| Epic Issue | Epic Branchがdevelopへmergeされ、配下Taskが完了した時点 |

---

## 18. 人間判断依頼通知

### 18.1 通知タイミング

AI Agentが人間判断を必要と判断したタイミングで通知する。

### 18.2 通知内容

```markdown
[action_required] 人間判断が必要です

判断事項:

- {{decision_title}}

背景:

- {{background_summary}}

選択肢:

- A: {{option_a}}
- B: {{option_b}}

AIの推奨:

- {{ai_recommendation}}

人間に決めてほしいこと:

- {{decision_request}}

対象:

- Issue: {{issue_url}}
- PR: {{pr_url}}
- ai-log: {{ai_log_path}}

リンク:

- {{reference_url}}
```

### 18.3 補足

人間判断の詳細は、Issue / PR / ai-logs のいずれかに記録する。  
Slack上の返答だけで意思決定を完結させない。

---

## 19. 作業停止・例外通知

### 19.1 通知タイミング

AI Agentが作業継続できない状態になったタイミングで通知する。

### 19.2 通知内容

```markdown
[error] AI作業が停止しました

発生内容:

- {{incident_summary}}

停止理由:

- {{stop_reason}}

対象:

- Issue: {{issue_url}}
- PR: {{pr_url}}
- Branch: {{branch_name}}
- Agent: {{agent_name}}

人間に確認してほしいこと:

- {{human_action}}

再開条件:

- {{restart_condition}}

リンク:

- ai-log: {{ai_log_path}}
- Issue / PR: {{target_url}}
```

### 19.3 補足

作業停止・例外は、必要に応じて `ai-logs/incidents/` に記録する。  
Slack通知だけで停止理由を完結させない。

---

## 20. 横断影響通知

### 20.1 通知タイミング

OpenAPI / Orval / generated / DB / GitHub Actions / 共通設定など、複数Taskへ影響する変更を検知したタイミングで通知する。

### 20.2 通知内容

```markdown
[warning] 横断影響を検知しました

概要:

- {{impact_summary}}

影響対象:

- docs: {{docs_impact}}
- web: {{web_impact}}
- api: {{api_impact}}
- reco: {{reco_impact}}
- batch: {{batch_impact}}
- db: {{db_impact}}
- generated: {{generated_impact}}

対応方針:

- {{action_plan}}

人間判断:

- {{human_decision_required}}

リンク:

- ai-log: {{ai_log_path}}
- Issue / PR: {{target_url}}
```

### 20.3 補足

横断影響がある場合は、専用Task化またはContract Task化を検討する。

---

## 21. ai-logs作成通知

### 21.1 通知タイミング

ai-logsを作成し、人間確認が必要な場合に通知する。

### 21.2 通知内容

```markdown
[action_required] AIログを作成しました

ログ種別:

- {{log_type}}

概要:

- {{summary}}

人間に確認してほしいこと:

- {{human_action}}

リンク:

- ai-log: {{ai_log_path}}
- 関連Issue: {{issue_url}}
- 関連PR: {{pr_url}}
```

### 21.3 補足

ai-logsを作成しても、人間確認が不要な場合はSlack通知を省略してよい。

---

## 22. Command別通知方針

| Command                 | 主な通知                                                 |
| ----------------------- | -------------------------------------------------------- |
| `/start-epic`           | Epic Issue 作成通知、人間判断依頼、Issue 化前フィードバック通知 |
| `/start-task`           | Task Issue 作成通知、人間判断依頼、Issue 化前フィードバック通知 |
| `/work-issue`           | 原則通知なし。作業停止・横断影響時のみ通知               |
| `/create-pr`            | PR作成通知                                               |
| `/review-pr`            | AIレビュー完了通知、Human Review依頼、修正必要通知       |
| `/fix-review-comments`  | レビュー指摘対応完了通知                                 |
| `/create-contract-task` | 横断影響通知、Contract Task作成通知                      |
| `/summarize-work`       | 必要に応じてサマリ通知                                   |

---

## 23. Task Definitionとの関係

Task Definition の `operation_logging.level` および通知テンプレートにより、通知要否と文面を制御する。

```yaml
operation_logging:
  level: "standard"
  ai_logs:
    intake: false
    incidents: false
    cross_cutting: false
    experiments: false
  reason: ""
```

| 項目                      | Slack通知との関係                  |
| ------------------------- | ---------------------------------- |
| `human_decision_points`   | 判断依頼通知の内容に利用する（Task Definition §32） |
| `operation_logging.level` | ai-logs 作成時の通知要否に影響する |
| `contract_impact`         | trueの場合、横断影響通知を検討する |
| `generated_impact`        | trueの場合、横断影響通知を検討する |
| `db_impact`               | trueの場合、横断影響通知を検討する |

ただし、`slack_notify: false` であっても、`error`、`warning`、`action_required` は通知してよい。

---

## 24. Projects Statusとの関係

Projects Status変更に応じて通知する。

| Status遷移                     |                               通知要否 |
| ------------------------------ | -------------------------------------: |
| `Backlog` → `Todo`             |                         原則通知しない |
| `Todo` → `In Progress`         |                         原則通知しない |
| `In Progress` → `AI Review`    |                   PR作成通知として通知 |
| `AI Review` → `Human Review`   |             Human Review依頼として通知 |
| `AI Review` → `In Progress`    | 修正必要通知として通知（Status 更新は [PRレビュー完了時Status更新ワークフロー仕様書](../../06_実装設計/github_actions/PRレビュー完了時Status更新ワークフロー仕様書.md)） |
| `Human Review` → `In Progress` | 人間レビュー指摘対応として通知してよい（同上 workflow の Human 経路） |
| `Human Review` → `Done`        |          PR merge / Done通知として通知 |
| `In Progress` → 停止状態相当   |                     作業停止・例外通知 |

Status自体の正本はGitHub Projectsである。

---

## 25. Issue / PRとの関係

Slack通知には、原則としてIssueまたはPRへのリンクを含める。

| 通知               | 必須リンク          |
| ------------------ | ------------------- |
| Issue作成通知      | Issue               |
| PR作成通知         | PR、Issue           |
| AIレビュー完了通知 | PR                  |
| Human Review依頼   | PR                  |
| 修正必要通知       | PR                  |
| PR merge通知       | PR、Issue           |
| 人間判断依頼       | Issue / PR / ai-log |
| 作業停止通知       | Issue / PR / ai-log |
| 横断影響通知       | Issue / PR / ai-log |

リンクがない通知は、後から追跡できないため避ける。

---

## 26. スレッド運用

同一Issueまたは同一PRに関する通知は、可能であればSlackスレッドにまとめる。

| 単位             | スレッド化方針                     |
| ---------------- | ---------------------------------- |
| Issue単位        | Issue作成通知を親メッセージにする  |
| PR単位           | PR作成通知を親メッセージにする     |
| AIレビュー結果   | PR作成通知のスレッドに返信         |
| 修正完了         | PR作成通知のスレッドに返信         |
| Human Review依頼 | PR作成通知のスレッドに返信         |
| 作業停止         | 重要度が高い場合は新規通知してよい |

MVP段階では、厳密なスレッド管理は必須ではない。  
将来的に通知量が増えた場合に強化する。

---

## 27. 通知抑制ルール

以下は原則としてSlack通知しない。

| 通知しないもの         | 理由                              |
| ---------------------- | --------------------------------- |
| 通常commit             | 通知量が増えすぎるため            |
| 作業中の細かい進捗     | Projects / PRで確認できるため     |
| AI内部の検討過程       | 正本ではないため                  |
| 軽微なdocs修正途中経過 | PRで確認できるため                |
| CIの成功のみ           | PR画面で確認できるため            |
| Branch作成単体         | Issue作成通知に含めれば十分なため |
| 通常のStatus自動更新   | 重要な状態遷移以外は不要なため    |

通知は、人間にとって行動可能なものを優先する。

---

## 28. 通知エラー時の扱い

Slack通知に失敗しても、Issue / PR / docs / Projects の更新を取り消さない。

ただし、以下の対応を行う。

| 条件                      | 対応                                |
| ------------------------- | ----------------------------------- |
| 通知失敗                  | workflowログまたはincidentに記録    |
| Human Review依頼通知失敗  | PRコメントまたはIssueコメントで補完 |
| 人間判断依頼通知失敗      | Issue / PR上に明示的に記録          |
| 作業停止通知失敗          | ai-logs/incidentsに記録             |
| Slack webhook / token不備 | secret設定を人間へ確認              |

Slack通知は補助機能であり、作業正本を壊してはならない。

---

## 29. secret / 個人情報の扱い

Slack通知に以下を含めてはならない。

- APIキー
- access token
- refresh token
- private key
- password
- cookie
- session情報
- `.env` の値
- 個人情報
- 不要な社外秘情報

secret混入が疑われる場合は、通知を停止し、人間へ報告する。

---

## 30. 通知テンプレート作成ルール

Slack通知テンプレート作成時は、以下を守る。

| ルール                    | 内容                                  |
| ------------------------- | ------------------------------------- |
| 1通知種別 = 1テンプレート | 用途ごとに分ける                      |
| 日本語で記載する          | 人間が理解しやすくする                |
| 詳細を書きすぎない        | Issue / PR / ai-logsへ誘導する        |
| リンクを含める            | 追跡性を確保する                      |
| 人間アクションを明記する  | 確認すべきことを明確にする            |
| secretを含めない          | 安全性を確保する                      |
| 正本関係を崩さない        | Slackを作業計画・レビュー正本にしない |

---

## 31. 通知レビュー観点

Slack通知設計・テンプレート変更時は、以下を確認する。

| 観点           | 内容                                             |
| -------------- | ------------------------------------------------ |
| 通知対象       | 本当に通知が必要なイベントか                     |
| 通知量         | 通知過多にならないか                             |
| 正本関係       | Slackだけに重要情報を置いていないか              |
| リンク         | Issue / PR / docs / ai-logsへのリンクがあるか    |
| 人間アクション | 人間が何をすべきか分かるか                       |
| 文面           | 簡潔で分かりやすいか                             |
| secret         | 秘密情報が含まれないか                           |
| 運用整合       | Issue / PR / Projects / AIログ運用と矛盾しないか |

---

## 32. 禁止事項

以下は禁止する。

- Slack通知を作業計画の正本にすること
- Slack通知をレビュー結果の正本にすること
- Slack通知だけで人間判断を完結させること
- Issue / PRリンクなしで重要通知を行うこと
- 通常commitごとに通知すること
- AIの内部思考過程を通知すること
- secretやAPIキーを通知すること
- 通知に過剰な詳細を含めること
- `slack_notify: false` を理由に作業停止・人間判断依頼を通知しないこと
- エラー通知に再開条件を書かないこと

---

## 33. 関連ドキュメント

| ドキュメント                               | 役割                                       |
| ------------------------------------------ | ------------------------------------------ |
| AIエージェント活用型\_開発運用フロー設計書 | AI主導運用の全体フローを定義               |
| AIエージェント体制・責務定義               | Agentごとの責務を定義                      |
| Commands設計書                             | Commandごとの通知発生条件を定義            |
| Task Definition設計書                      | `slack_notify`、人間判断事項を定義         |
| Prompts運用ルール                          | Slack通知テンプレート配置を定義            |
| AIレビュー運用設計書                       | AIレビュー完了通知・Human Review依頼を定義 |
| AIログ運用ルール                           | ai-logs作成時の通知方針を定義              |
| Projects運用ルール                         | Status遷移を定義                           |
| Issue運用ルール                            | Issue正本・Issue本文構造を定義             |
| ブランチ運用ルール                         | Branch / PR targetを定義                   |

---

## 34. 一言まとめ

Slackは、AIエージェント運用における通知・サマリのために使う。

正本関係は以下とする。

```text
Issue    = 作業計画
Projects = 進捗状態
Branch   = 作業実体
PR       = 作業結果・レビュー
docs     = 成果物
ai-logs  = 例外・補助記録
Slack    = 通知・サマリ
```

Slackで必ず通知するのは、以下である。

```text
PR作成
AIレビュー完了
Human Review依頼
人間判断依頼
作業停止・例外
横断影響
PR merge / Done
```

Slack通知は、人間が「何を確認すべきか」「どこを見ればよいか」を素早く判断するための入口として扱う。
