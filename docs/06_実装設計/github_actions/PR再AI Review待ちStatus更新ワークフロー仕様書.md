# PR再AI Review待ち Status 更新・Slack通知ワークフロー

## 1. 目的

`/fix-review-comments` 完了後（Fix Outcome = `ready_for_ai_review`）、対象 Issue の Projects Status を `In Progress` から `AI Review` へ更新し、Slack へ再 AI Review 依頼を通知する。

PR **初回作成時** の Status 更新は [PR作成時Status更新ワークフロー](./PR作成時Status更新・Slack通知ワークフロー仕様書.md)（`pr-created-status-and-slack.yml`）が担当し、本ワークフローは **fix 完了後の再 Review 待ち** のみを担う。

Status の正式値は [Projects運用ルール](../../00_共通/プロジェクト管理/Projects運用ルール.md) を正とする。

## 2. 実装ファイル

| 項目 | 内容 |
| ---- | ---- |
| 実装ファイル | `.github/workflows/pr-ready-for-ai-review.yml` |
| dispatch CLI | `.github/scripts/dispatch-pr-ready-for-ai-review.cjs` |
| 正本 CLI（コメント + dispatch） | `.github/scripts/publish-fix-complete-and-dispatch.cjs` |
| PR コメント正本 | [fix-complete-comment.md](../../../prompts/templates/review/fix-complete-comment.md) |
| 共通 script | `.github/scripts/slack-notify.cjs` |
| Actions 表示名 | `PR Ready For AI Review Status Sync` |
| Run 名（一覧） | `fix-ready · dispatch · PR #n · ready_for_ai_review` |

## 3. トリガー

```yaml
on:
  repository_dispatch:
    types:
      - fix_ready_for_ai_review
  workflow_dispatch:
```

| 経路 | 用途 |
| ---- | ---- |
| `repository_dispatch` | `/fix-review-comments` 完了時（`publish-fix-complete-and-dispatch.cjs` から 1 回） |
| `workflow_dispatch` | 手動 recovery・受入確認 |

## 4. client_payload / workflow_dispatch 入力

| フィールド | 必須 | 内容 |
| ---------- | ---- | ---- |
| `pr_number` | 必須 | 対象 PR 番号 |
| `fix_outcome` | 任意 | 既定 `ready_for_ai_review`。それ以外は Status 更新しない（正当スキップ） |
| `fix_body` | 任意 | dispatch 時の監査用（workflow 本体では未使用可） |
| `dry_run` | workflow_dispatch のみ | `true` のとき API 更新なし |

## 5. Status 遷移

| 条件 | 現在 Status（前提） | 次 Status |
| ---- | ------------------- | --------- |
| `fix_outcome` = `ready_for_ai_review` | `In Progress` | `AI Review` |

### 5.1 スキップ条件（正当スキップ・ジョブ成功）

| 条件 | 挙動 |
| ---- | ---- |
| `fix_outcome` ≠ `ready_for_ai_review` | スキップ |
| 現在 Status が `In Progress` でない（かつ `AI Review` でもない） | スキップ（冪等・誤更新防止） |
| 次 Status が現在 Status と同一（既に `AI Review`） | スキップ |
| PR from fork | スキップ |

### 5.2 ジョブ失敗

| 条件 | 挙動 |
| ---- | ---- |
| PR 本文から Task Issue を解決できない | ジョブ失敗 |
| Project / Project item を解決できない | ジョブ失敗 |

## 6. Slack 通知

| 項目 | 内容 |
| ---- | ---- |
| 通知レベル | `info` |
| タイトル | 再AI Review可能 |
| 必須リンク | PR、Issue |
| 次 Status | `AI Review` |
| humanAction | `/review-pr` を実行 |
| thread 単位 | PR（既存 thread marker があれば返信） |

PR 初回作成時の「PRを作成しました」とは **文面を分離** する。

## 7. 運用上の必須事項

- `/fix-review-comments` は Fix Outcome = `ready_for_ai_review` のとき **必ず** `publish-fix-complete-and-dispatch.cjs` を 1 回実行する（[fix-review-comments.md](../../../.cursor/commands/fix-review-comments.md) §12.5）
- `split_required` / `partial_fix` 等では dispatch **しない**（Status は `In Progress` 維持）
- dispatch 忘れ時は `--verify` / `--dispatch-only` / `workflow_dispatch` で recovery
- 人間が手動修正した場合（パターン B）は Fixer CLI を実行せず、**workflow_dispatch** または手動 Status 更新 + `/review-pr`
- Machine account PAT（`GH_BOT_TOKEN`）で PR コメント投稿・dispatch すること

## 8. 関連ドキュメント

- [PRレビュー完了時Status更新ワークフロー仕様書.md](./PRレビュー完了時Status更新ワークフロー仕様書.md) … AI/Human Review 完了時
- [PR作成時Status更新ワークフロー仕様書.md](./PR作成時Status更新・Slack通知ワークフロー仕様書.md) … PR 初回 open 時
- [Commands設計書.md](../../00_共通/AIエージェント運用/Commands設計書.md) §18
- [Projects運用ルール.md](../../00_共通/プロジェクト管理/Projects運用ルール.md) §17.3
