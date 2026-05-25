# AIエージェント運用 README

## 1. 目的

本ディレクトリは、Gift Recommendation Service におけるAIエージェント活用型の開発運用に関する設計書・運用ルールを管理する。

本プロジェクトでは、人間とAIエージェントが協業し、設計、開発、テスト、レビュー、修正対応を進める。

本ディレクトリでは、以下を定義・管理する。

- AIエージェント活用型の開発運用フロー
- AIエージェントの体制・責務
- Cursor Commandsの設計
- Task Definitionの設計
- prompts運用ルール
- AIレビュー運用
- AIログ運用
- Slack通知運用
- worktree運用

---

## 2. 本ディレクトリの位置づけ

AIエージェント運用系ドキュメントは、以下に配置する。

```text
docs/00_共通/AIエージェント運用/
```

本ディレクトリは、AIエージェント活用に関する設計・運用ルールを管理する場所である。

実際にAIが実行時に読み込むCommand、Agent、Rule、Task Definition、Prompt Templateは、以下に配置する。

| 配置先                             | 役割                                                |
| ---------------------------------- | --------------------------------------------------- |
| `docs/00_共通/AIエージェント運用/` | AIエージェント運用の設計書・ルール                  |
| `.cursor/commands/`                | Cursor Command定義                                  |
| `.cursor/agents/`                  | Cursor Agent定義                                    |
| `.cursor/rules/`                   | Cursor Rule定義                                     |
| `prompts/definitions/`             | Task Definition                                     |
| `prompts/templates/`               | Issue本文、PR本文、AIフィードバック等のテンプレート |
| `ai-logs/`                         | Issue化前・例外・横断影響・実験ログ                 |

---

## 3. 正本関係

AIエージェント運用における正本関係は以下とする。

| 対象               | 正本                               |
| ------------------ | ---------------------------------- |
| 作業計画           | GitHub Issue                       |
| 進捗・予定・実績   | GitHub Projects                    |
| 作業実体           | Git Branch / worktree              |
| レビュー           | Pull Request                       |
| 成果物             | `docs/`                            |
| AI作業依頼条件     | `prompts/definitions/`             |
| AI補助テンプレート | `prompts/templates/`               |
| AI運用ルール       | `docs/00_共通/AIエージェント運用/` |
| AI例外ログ         | `ai-logs/`                         |
| 通知・サマリ       | Slack                              |

Slackは通知・サマリ用途であり、作業計画や成果物の正本にはしない。

---

## 4. ドキュメント一覧

| ドキュメント                                   | 役割                                                        |
| ---------------------------------------------- | ----------------------------------------------------------- |
| `AIエージェント活用型_開発運用フロー設計書.md` | AI主導運用の全体フローを定義する                            |
| `AIエージェント体制・責務定義.md`              | Orchestrator / Worker / Reviewer / Fixer 等の責務を定義する |
| `Commands設計書.md`                            | `/start-epic`、`/start-task`、`/review-pr` 等のCommand仕様を定義する |
| `AI Agent定義設計書.md`                        | `.cursor/agents/` に配置するAgent定義の仕様を定義する       |
| `Task Definition設計書.md`                     | AIへの個別作業依頼条件の構造を定義する                      |
| `Prompts運用ルール.md`                         | `prompts/` 配下の管理・命名・利用ルールを定義する           |
| `AIレビュー運用設計書.md`                      | AI Reviewの観点、出力、PR反映方針を定義する                 |
| `AIログ運用ルール.md`                          | `ai-logs/` の記録対象、粒度、命名規則を定義する             |
| `Slack通知運用設計書.md`                       | Slack通知タイミング、通知内容、通知先を定義する             |
| `worktree運用ルール.md`                        | AI並列作業時のworktree配置・削除・競合回避を定義する        |
| `成果物一覧×Task Definition化方針書.md`        | 成果物種別ごとの Task Definition 化方針を定義する           |
| `AIエージェント共通Rules設計書.md`             | `.cursor/rules/` および `AGENTS.md` の設計正本を定義する    |

---

## 5. 推奨作成順序

AIエージェント運用系ドキュメントは、以下の順序で作成・更新する。

| 順番 | ドキュメント                                   | 理由                                            |
| ---- | ---------------------------------------------- | ----------------------------------------------- |
| 1    | `AIエージェント活用型_開発運用フロー設計書.md` | 全体フローの前提となるため                      |
| 2    | `AIエージェント体制・責務定義.md`              | Agentごとの責務分担を定めるため                 |
| 3    | `Commands設計書.md`                            | 人間からAIへの操作IFを定めるため                |
| 4    | `成果物一覧×Task Definition化方針書.md`        | 成果物と Task の対応方針を定めるため            |
| 5    | `Task Definition設計書.md`                     | 個別作業依頼ファイルの構造を定めるため          |
| 6    | `Prompts運用ルール.md`                         | prompts配下の配置・命名・利用ルールを定めるため |
| 7    | `AIレビュー運用設計書.md`                      | AI Reviewの品質観点を定めるため                 |
| 8    | `AIログ運用ルール.md`                          | ai-logsの利用範囲を明確にするため               |
| 9    | `Slack通知運用設計書.md`                       | 通知タイミングと文面を定めるため                |
| 10   | `worktree運用ルール.md`                        | 並列AI作業時の作業領域分離を定めるため          |
| 11   | `AI Agent定義設計書.md`                        | `.cursor/agents/` 実装前の仕様を定めるため      |
| 12   | `AIエージェント共通Rules設計書.md`             | `.cursor/rules/` 設計正本を定めるため           |

---

## 6. 標準運用フロー

AI主導タスクでは、親 Epic 未作成時は `/start-epic` を先に実行し、以下の流れを標準とする。

```
（未作成時）/start-epic @epic-definition
  ↓
Epic Issue / Epic Branch 作成
  ↓
/start-task @task-definition
  ↓
Task Issue 作成
  ↓
Project同期
  ↓
Branch作成
  ↓
AI作業
  ↓
PR作成
  ↓
AI Review
  ↓
Human Review
  ↓
merge / Done
```

レビュー指摘がある場合は、原則として同一Issue・同一Branchで修正する。

```
AI Review / Human Review
  ↓ 指摘あり
In Progress
  ↓ /fix-review-comments @definition
同一Branchで修正
  ↓
AI Review
```

---

## 7. AIエージェントの基本役割

| Agent            | 主な責務                                          |
| ---------------- | ------------------------------------------------- |
| Orchestrator AI  | 依頼解析、入力検証、Issue作成、作業分割、進行制御 |
| Worker AI        | 設計、実装、テスト、成果物作成                    |
| Reviewer AI      | PR、Issue、docs、完了条件、確認観点のレビュー     |
| Fixer AI         | AIレビュー・人間レビュー指摘への修正対応          |
| Contract AI      | OpenAPI / Orval / generated 等の横断契約変更対応  |
| Test AI          | テスト観点確認、テスト実行、失敗解析              |
| Docs Reviewer AI | docs整合性、テンプレート準拠、用語揺れ確認        |
| Support AI       | 調査、影響分析、要約、補助資料作成                |

詳細は `AIエージェント体制・責務定義.md` に定義する。

---

## 8. CommandとDefinitionの関係

AI主導運用では、CommandとDefinitionを組み合わせて作業依頼を行う。

```
/<Command> @<definition>
```

例：

```
/start-epic @prompts/definitions/_examples/epic-definition.example.yaml
/start-task @prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml
/review-pr @prompts/definitions/_examples/review-definition.example.yaml
/fix-review-comments @prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml
```

| 要素       | 役割                                                     |
| ---------- | -------------------------------------------------------- |
| Command    | AIに実行させる操作・手順を指定する                       |
| Definition | 作業対象、入力資料、出力先、完了条件、確認観点を指定する |

Commandの仕様は `Commands設計書.md`、Definitionの構造は `Task Definition設計書.md` を正本とする。

---

## 9. AIログの扱い

`ai-logs/` は、通常作業ログをすべて保存する場所ではない。

Issue作成後の作業計画はIssue、作業結果とレビューはPR、成果物はdocsに記録する。

`ai-logs/` は以下に限定して利用する。正本は [AIログ運用ルール](./AIログ運用ルール.md) §4・§6 とする。

| 種別                    | 保存先                     | 用途                                                   |
| ----------------------- | -------------------------- | ------------------------------------------------------ |
| Issue化前フィードバック | `ai-logs/intake/`          | OrchestratorがIssue化前に人間判断を求める場合          |
| 作業停止・例外          | `ai-logs/incidents/`       | 入力不足、権限不足、依存未完了など                     |
| 人間判断待ち            | `ai-logs/human-decisions/` | AIだけでは判断できない設計・仕様・運用判断             |
| 横断影響                | `ai-logs/cross-cutting/`   | OpenAPI / Orval / generated など複数Taskに影響する場合 |
| AI運用検証              | `ai-logs/experiments/`     | AI運用やPoC的な試行錯誤を記録する場合                  |

---

## 10. 関連ディレクトリ

| ディレクトリ                       | 役割                                                |
| ---------------------------------- | --------------------------------------------------- |
| `docs/00_共通/AIエージェント運用/` | AIエージェント運用の設計書・ルール                  |
| `.cursor/commands/`                | Cursor Command定義                                  |
| `.cursor/agents/`                  | Cursor Agent定義                                    |
| `.cursor/rules/`                   | Cursor Rule定義                                     |
| `prompts/definitions/`             | Task Definition                                     |
| `prompts/templates/`               | AIがIssue本文・PR本文等を生成するためのテンプレート |
| `ai-logs/`                         | Issue化前・例外・横断影響・実験ログ                 |
| `.github/workflows/`               | GitHub Actions workflow                             |
| `.github/scripts/`                 | GitHub運用補助スクリプト                            |
| `scripts/ai/`                      | 汎用AI補助スクリプト                                |

---

## 11. 関連ドキュメント

| ドキュメント                            | 役割                                                              |
| --------------------------------------- | ----------------------------------------------------------------- |
| `プロジェクト運営基本方針.md`           | プロジェクト全体の運営方針を定義する                              |
| `プロジェクトディレクトリ構成定義書.md` | docs、prompts、ai-logs、.github、.cursor等の配置を定義する        |
| `Projects運用ルール.md`                 | ProjectsのStatus、Phase、予定・実績管理を定義する                 |
| `Issue運用ルール.md`                    | Issue本文、Issueタイトル、ラベル、no-branchを定義する             |
| `ブランチ運用ルール.md`                 | Branch命名、Branch base、PR targetを定義する                      |
| `Issueテンプレート設計書.md`            | Issue本文構造を定義する                                           |
| `PRテンプレート設計書.md`               | PR本文構造を定義する                                              |
| `GitHub Actionsワークフロー仕様書群`    | Project同期、Branch作成、Status更新、通知等の自動化仕様を定義する |
| `AGENTS.md`                             | AI Agent向け最上位運用ガイドを定義する                            |

---

## 12. 禁止事項

以下は禁止する。

- AIエージェント運用系ドキュメントを `docs/00_共通/プロジェクト管理/` に混在させること
- 本ディレクトリ配下のファイル名に `【AIエージェント運用】` 接頭辞を付けること
- Task Definitionを `.cursor/` に保存すること
- Cursor専用Commandを `prompts/` に保存すること
- AIログを通常作業サマリの保管場所として濫用すること
- Issue化後の通常作業ログをすべて `ai-logs/` に保存すること
- Slack通知だけで作業記録を完結させること
- AIレビューだけで完了判断すること
- 人間レビューなしでmergeすること
- secretやAPIキーをdocs、prompts、ai-logs、Issue、PRに記載すること

---

## 13. 一言まとめ

本ディレクトリは、AIエージェントを活用して設計・開発・テスト・レビューを進めるための運用設計書を管理する。

AIエージェントは作業主体として活用するが、最終的な品質責任、方針判断、merge判断、リリース判断は人間が持つ。

基本関係は以下である。

```
Issue = 作業計画
Projects = 進捗・予定・実績管理
Branch = 作業実体
PR = レビュー正本
docs = 成果物正本
prompts = AI作業指示定義
ai-logs = Issue化前・例外・横断影響・実験ログ
Slack = 通知・サマリ
```
