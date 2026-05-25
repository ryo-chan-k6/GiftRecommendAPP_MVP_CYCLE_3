# PR merge時 Status 更新・Slack通知ワークフロー

## 1. 目的

PRがmergeされたタイミングで、対象Issueを完了扱いにし、Projects Statusを `Done` へ更新し、Slackへ完了通知を送信する。

Task Issueの完了制御は、PR本文の自動closeキーワードだけに依存せず、本workflowで明示的に行う。

## 2. 実装ファイル

| 項目 | 内容 |
| ---- | ---- |
| 実装ファイル | `.github/workflows/pr-merged-done-and-slack.yml` |
| 共通script | `.github/scripts/slack-notify.cjs` |
| Actions表示名 | `PR merged Done and Slack notification` |

## 3. トリガー

```yaml
on:
  pull_request:
    types:
      - closed
  workflow_dispatch:
```

`pull_request.closed` かつ `pull_request.merged == true` の場合のみ処理する。

初期計画ではPR from forkを通知対象外とする。

## 4. 権限・Secret

| 項目 | 用途 |
| ---- | ---- |
| `PROJECTS_TOKEN` | ProjectV2のStatus / Actual End更新 |
| `SLACK_BOT_TOKEN` | Slack通知 |
| `SLACK_CHANNEL_ID_DEVOPS` | Slack通知先 |
| `contents: read` | repository内容のcheckout |
| `issues: write` | Issue close、PRコメント、thread marker参照 |
| `pull-requests: read` | PR本文参照 |

## 5. 処理概要

1. merge済みPRかを確認する。
2. PR from forkの場合はスキップする。
3. PR本文から対象Issue番号を抽出する。
4. 対象IssueのProjects Statusを `Done` へ更新する。
5. `Actual End` をJST当日で設定する。
6. 対象Issueをcloseする。
7. Slackへ `[info] PRがmergeされ、タスクが完了しました` を送信する。
8. PR作成通知のthread markerがある場合は同じSlackスレッドへ返信する。

## 6. スキップ・失敗条件

| 条件 | 扱い |
| ---- | ---- |
| PRがmergeされずcloseされた | ジョブ成功、処理なし |
| PR from fork | ジョブ成功、処理なし |
| PR本文からIssue番号を解決できない | ジョブ失敗 |
| 対象IssueがProjectに存在しない | ジョブ失敗 |
| Slack設定不足 | Done更新は行い、Slack通知のみスキップ |

## 7. 通知内容

| 項目 | 内容 |
| ---- | ---- |
| 通知レベル | `info` |
| タイトル | PRがmergeされ、タスクが完了しました |
| 必須リンク | PR、Issue |
| Status | `Done` |
| thread単位 | PR |

## 8. 正本関係

Slack通知は正本ではない。
完了状態はProjects、作業結果はPR、作業計画とclose状態はIssueを正本とする。

