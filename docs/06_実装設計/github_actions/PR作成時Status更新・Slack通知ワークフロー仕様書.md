# PR作成時 Status 更新・Slack通知ワークフロー

## 1. 目的

PR作成時に、対象Issueの Projects Status を `AI Review` へ更新し、SlackへPR作成通知を送信する。

Status の正式値は [Projects運用ルール](../../00_共通/プロジェクト管理/Projects運用ルール.md) を正とする。
Slack通知の文面・通知レベルは [Slack通知運用設計書](../../00_共通/AIエージェント運用/Slack通知運用設計書.md) を正とする。

## 2. 実装ファイル

| 項目 | 内容 |
| ---- | ---- |
| 実装ファイル | `.github/workflows/pr-created-status-and-slack.yml` |
| 共通script | `.github/scripts/slack-notify.cjs` |
| Actions表示名 | `PR Created Status Sync` |
| Run 名（一覧） | `pr-created · pr-open · PR #n` |

## 3. トリガー

```yaml
on:
  pull_request:
    types:
      - opened
  workflow_dispatch:
```

初期計画ではPR from forkを通知対象外とする。
`pull_request` 経路では、PRのhead repositoryが当該repositoryと一致しない場合は処理をスキップする。

## 4. 権限・Secret

| 項目 | 用途 |
| ---- | ---- |
| `PROJECTS_TOKEN` | ProjectV2のStatus更新 |
| `SLACK_BOT_TOKEN` | Slack通知 |
| `SLACK_CHANNEL_ID_DEVOPS` | Slack通知先 |
| `contents: read` | repository内容のcheckout |
| `issues: write` | PRコメントへのthread marker保存 |
| `pull-requests: read` | PR本文参照 |

workflow permissionsは必要最小限にする。

## 5. 処理概要

1. PR番号を取得する。
2. PR from forkの場合はスキップする。
3. PR本文から `Related to #<Issue番号>` または `Closes #<Issue番号>` を抽出する。
4. 対象IssueのProject itemを取得する。
5. Projects Statusを `AI Review` へ更新する。
6. Slackに `[info] PRを作成しました` を送信する。
7. Slack APIの戻り値 `ts` をPRコメントのthread markerに保存する。
8. Review Definition を解決し、Definition Run Harness（`review-pr` / `live-run`）を `repository_dispatch` で起動する（[AI Review自動起動](./AI%20Review自動起動ワークフロー連携仕様書.md)）。

## 6. スキップ条件

| 条件 | 扱い |
| ---- | ---- |
| PR from fork | ジョブ成功、処理なし |
| PR本文からIssue番号を解決できない | ジョブ失敗 |
| 対象IssueがProjectに存在しない | ジョブ失敗 |
| Slack設定不足 | Status更新は行い、Slack通知のみスキップ |

## 7. 通知内容

| 項目 | 内容 |
| ---- | ---- |
| 通知レベル | `info` |
| タイトル | PRを作成しました |
| 必須リンク | PR、Issue |
| 次Status | `AI Review` |
| thread単位 | PR |

## 8. 正本関係

Slack通知は正本ではない。
作業計画はIssue、進捗状態はProjects、作業結果とレビューはPRを正本とする。

