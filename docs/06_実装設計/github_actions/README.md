# GitHub Actions workflow 仕様書

本ディレクトリは、`.github/workflows/` に実装する automation workflow の仕様正本を配置する。

| 仕様書 | 実装ファイル（予定） | 概要 |
| ------ | -------------------- | ---- |
| [Issue作成時Projectフィールド同期ワークフロー.md](./Issue作成時Projectフィールド同期ワークフロー.md) / [Issue同期とブランチ作成ワークフロー.md](./Issue同期とブランチ作成ワークフロー.md) | `issue-metadata-project-branch.yml` | Issue 作成時の Project 追加・フィールド同期・Label 同期・Branch 作成・Slack通知 |
| [Planned Startに基づくStatus自動更新ワークフロー.md](./Planned%20Startに基づくStatus自動更新ワークフロー.md) | `update-projects-status-by-planned-start.yml` | Backlog → Todo |
| [Slack通知共通ワークフロー仕様書.md](./Slack通知共通ワークフロー仕様書.md) | `slack-notify-manual.yml` / `.github/scripts/slack-notify.cjs` | Slack通知の共通仕様・手動通知 |
| [PR作成時Status更新ワークフロー仕様書.md](./PR作成時Status更新ワークフロー仕様書.md) | `pr-created-status-and-slack.yml` | PR作成時の `AI Review` 更新・Slack通知 |
| [PRレビュー完了時Status更新ワークフロー仕様書.md](./PRレビュー完了時Status更新ワークフロー仕様書.md) | `pr-review-status-sync.yml` | AI/Human レビュー完了時の Status 更新・Slack通知 |
| [PR merge時Status更新ワークフロー仕様書.md](./PR%20merge時Status更新ワークフロー仕様書.md) | `pr-merged-done-and-slack.yml` | PR merge 時の `Done` 更新・Issue close・Slack通知 |

運用ルールの正本は [Projects運用ルール.md](../../00_共通/プロジェクト管理/Projects運用ルール.md) §16 を参照する。
