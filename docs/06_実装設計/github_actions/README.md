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
| [Definition Run Harnessワークフロー仕様書.md](./Definition%20Run%20Harness%E3%83%AF%E3%83%BC%E3%82%AF%E3%83%95%E3%83%AD%E3%83%BC%E4%BB%95%E6%A7%98%E6%9B%B8.md) | `definition-run.yml` / `.github/scripts/definition-run-prompt-builder.cjs` / `.github/scripts/definition-run-post-verify.cjs` | 外部トリガから Cursor Cloud Agent に Definition Run を依頼する Harness（MVP: `/start-epic` dry-run のみ） |
| [Definition Run Harness Slack起点dry-run受入チェックリスト.md](./Definition%20Run%20Harness%20Slack%E8%B5%B7%E7%82%B9dry-run%E5%8F%97%E5%85%A5%E3%83%81%E3%82%A7%E3%83%83%E3%82%AF%E3%83%AA%E3%82%B9%E3%83%88.md) | `definition-run.yml`（運用受入） | Slack -> `repository_dispatch` -> Harness の運用導線を受け入れるための判定基準 |

運用ルールの正本は [Projects運用ルール.md](../../00_共通/プロジェクト管理/Projects運用ルール.md) §16 を参照する。
