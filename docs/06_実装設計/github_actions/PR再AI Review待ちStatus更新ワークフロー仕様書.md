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
| AI Review 自動起動 CLI | `.github/scripts/dispatch-review-pr-harness.cjs` |
| Review Definition 解決 | `.github/scripts/resolve-review-definition.cjs` |
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
| 現在 Status が `In Progress` でない（かつ `AI Review` でもない） | スキップ（冪等・誤更新防止）。**Harness dispatch も行わない** |
| 次 Status が現在 Status と同一（既に `AI Review`） | Status 更新スキップ。**Harness dispatch は実行** |
| PR from fork | スキップ |

### 5.3 fix-ready `current_status_mismatch` 時の Harness recovery

fix-ready が `current_status_mismatch` でスキップされた場合、Projects Status は `In Progress` / `AI Review` 以外（例: `Human Review`）に留まる。  
このとき **fix-ready の再実行では Harness は起動しない**（意図した冪等ガード）。

**正本 recovery:** Definition Run Harness を **直接** `workflow_dispatch` する（Status 更新は不要）。

```bash
gh workflow run "Definition Run Harness" \
  -f command=review-pr \
  -f definition=prompts/definitions/<path>/pr-review.yaml \
  -f run_mode=live-run \
  -f target_pr=<PR番号> \
  -f request_issue=<Task Issue番号> \
  -f requested_by=fix-ready-harness-recovery \
  -f ref=<PR head ref> \
  --repo <owner>/<repo>
```

| 項目 | 必須 | 備考 |
| ---- | ---- | ---- |
| `definition` | 必須 | 対象 PR の Review Definition パス |
| `target_pr` | 必須 | 対象 PR 番号 |
| `ref` | **PR Branch 限定 Definition 時は必須** | PR head ref。未指定時 `develop` 固定となり `definition_not_found` になりうる |
| `request_issue` | 推奨 | トレース用 |

代替: `node .github/scripts/dispatch-review-pr-harness.cjs` を **`--context` なし**（手動 recovery）で実行してもよい（[Definition Run Harness recovery](./Definition%20Run%20Harness%E3%83%AF%E3%83%BC%E3%82%AF%E3%83%95%E3%83%AD%E3%83%BC%E4%BB%98%E6%A7%98%E6%9B%B8.md) §15 参照）。

**典型シナリオ:** Phase C-2 等で fix-ready 後に Harness が失敗し、Status が `Human Review` 等に遷移したまま fix-ready を再実行した場合（E2E run `26719313872`）。

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
| humanAction | Definition Run Harness により AI Review を自動実行 |
| thread 単位 | PR（既存 thread marker があれば返信） |

PR 初回作成時の「PRを作成しました」とは **文面を分離** する。

## 7. 運用上の必須事項

- `/fix-review-comments` は Fix Outcome = `ready_for_ai_review` のとき **必ず** `publish-fix-complete-and-dispatch.cjs` を 1 回実行する（[fix-review-comments.md](../../../.cursor/commands/fix-review-comments.md) §12.5）
- Status が `AI Review` になったら、workflow が **Definition Run Harness**（`review-pr` / `live-run`）を自動起動する（[AI Review自動起動ワークフロー連携仕様書.md](./AI%20Review自動起動ワークフロー連携仕様書.md)）
- `split_required` / `partial_fix` 等では dispatch **しない**（Status は `In Progress` 維持）
- dispatch 忘れ時は `--verify` / `--dispatch-only` / `workflow_dispatch` で recovery
- fix-ready が `current_status_mismatch` で Harness dispatch をスキップした場合は [§5.3](./PR再AI%20Review待ちStatus更新ワークフロー仕様書.md#53-fix-ready-current_status_mismatch-時の-harness-recovery) の **Harness 直接 dispatch** を使う（fix-ready 再実行では解消しない）
- 人間が手動修正した場合（パターン B）は Fixer CLI を実行せず、**workflow_dispatch** または手動 Status 更新 + `/review-pr`
- Machine account PAT（`GH_BOT_TOKEN`）で PR コメント投稿・dispatch すること

## 8. 関連ドキュメント

- [PRレビュー完了時Status更新ワークフロー仕様書.md](./PRレビュー完了時Status更新ワークフロー仕様書.md) … AI/Human Review 完了時
- [PR作成時Status更新ワークフロー仕様書.md](./PR作成時Status更新・Slack通知ワークフロー仕様書.md) … PR 初回 open 時
- [Commands設計書.md](../../00_共通/AIエージェント運用/Commands設計書.md) §18
- [Projects運用ルール.md](../../00_共通/プロジェクト管理/Projects運用ルール.md) §17.3
