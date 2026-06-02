# AI Review 自動起動ワークフロー連携仕様書

## 1. 目的

Projects Status が `AI Review` になったタイミングで、Definition Run Harness 経由の `/review-pr`（`live-run`）を **自動起動** し、AI Review 完了後に Status が `Human Review` または `In Progress` へ進むまで滞留させない。

Status 更新のみで `/review-pr` が手動待ちになる運用ギャップを解消する。

## 2. 実装ファイル

| 種別 | ファイル | 役割 |
| ---- | -------- | ---- |
| Review Definition 解決 | `.github/scripts/resolve-review-definition.cjs` | PR / Issue / Branch から `pr-review.yaml` を解決 |
| Harness dispatch（低レベル） | `.github/scripts/dispatch-definition-run.cjs` | `repository_dispatch` `definition-run` |
| 正本 CLI | `.github/scripts/dispatch-review-pr-harness.cjs` | 解決 + `ai_review_required` 判定 + Harness dispatch |
| 単体テスト | `.github/scripts/resolve-review-definition.test.cjs` | 解決ロジック |
| 単体テスト | `.github/scripts/dispatch-review-pr-harness.test.cjs` | dispatch 連携 |
| Harness | `.github/workflows/definition-run.yml` | Cursor Cloud Agent で `/review-pr` 実行 |
| 起動元 workflow | `.github/workflows/pr-created-status-and-slack.yml` | PR open → `AI Review` 後に dispatch |
| 起動元 workflow | `.github/workflows/pr-ready-for-ai-review.yml` | fix 完了 → `AI Review` 後に dispatch |

## 3. 処理フロー

```text
PR open / fix-ready (ready_for_ai_review)
  → Status Sync workflow
  → Status = AI Review
  → dispatch-review-pr-harness.cjs
  → repository_dispatch (definition-run)
  → Definition Run Harness (review-pr / live-run)
  → Reviewer AI が publish-ai-review-and-dispatch.cjs
  → PR Review Status Sync
  → Human Review または In Progress
```

## 4. Review Definition 解決順

1. CLI `--definition` 明示指定
2. PR / Issue 本文の `/review-pr @path` または `Review Definition:` / ディレクトリヒント行
3. Branch summary から `prompts/definitions/_e2e/{summary}/pr-review.yaml`（**develop 上に存在する場合**）
4. Task Definition 候補（branch summary ディレクトリ / **filename summary** / Issue 番号 `task-{n}` パス）から、同ディレクトリの `pr-review.yaml` または `prompts/definitions/reviews/{workstream}/pr-review.yaml`
5. 全 `pr-review.yaml` スキャン（Issue 番号 / task_definition リンク / summary 一致でスコアリング。**score ≥ 40 のみ採用**）
6. **fallback（`dispatch-review-pr-harness.cjs`）:**
   - PR changed files から **Task Definition** を解決し、`review.ai_review_required: false` なら **AI Review を skip（job 成功）**
   - 同一 Task から sibling / workstream review を再試行
   - PR changed files から `pr-review.yaml` を抽出
7. fallback 時は Harness dispatch に **PR head ref** を渡し、Cursor Agent が PR Branch を clone する

解決不能・曖昧かつ AI Review 必須の場合は dispatch ステップが **失敗** し、Job Summary / Actions log に recovery コマンドを残す。

### 4.1 Branch summary と Task ファイル名の不一致

Issue 運用メタデータの `Branch summary`（例: `fixer-e2e-ai`）と Task Definition ファイル名（例: `fixer-e2e-verify.yaml`）が一致しない場合、手順 4 の summary 一致だけでは解決できない。  
このとき手順 6 の **PR changed files による Task 解決** または PR 本文での Definition 明示が必要である（PR #333 / Issue #336 参照）。

## 5. スキップ条件（dispatch しない・ジョブ成功）

| 条件 | 理由 |
| ---- | ---- |
| `dry_run=true` | 受入確認 |
| PR from fork | 既存 Status workflow と同様 |
| `fix_outcome` ≠ `ready_for_ai_review` | fix-ready 経路のみ |
| Task Definition で `review.ai_review_required: false` | AI Review 省略 |
| PR / 関連 Issue に `type: infra` または `area: infra` ラベル | インフラ PR（CI / workflow 改修）。自動 dispatch 対象外 |
| 変更ファイルが `.github/` 配下のみ（自動 dispatch 経路） | workflow / script 改修 PR。ラベル未付与でも skip（例: PR #297） |

インフラ PR では Status=`AI Review` 更新は行っても Harness 自動起動は **しない**。AI Review が必要な場合は手動で `/review-pr` または Harness `workflow_dispatch` を実行する。

## 6. 前提

| 項目 | 内容 |
| ---- | ---- |
| Secret | `CURSOR_API_KEY`（Definition Run Harness） |
| Token | `PROJECTS_TOKEN` または `GITHUB_TOKEN`（`repository_dispatch`） |
| Review Definition | PR に対応する `pr-review.yaml` がリポジトリに存在すること |
| Harness 完了後 | Agent が `publish-ai-review-and-dispatch.cjs` を 1 回実行（post-verify で検証） |

## 7. 関連ドキュメント

- [Definition Run Harnessワークフロー仕様書.md](./Definition%20Run%20Harness%E3%83%AF%E3%83%BC%E3%82%AF%E3%83%95%E3%83%AD%E3%83%BC%E4%BB%98%E6%A7%98%E6%9B%B8.md)
- [PR作成時Status更新ワークフロー仕様書.md](./PR作成時Status更新・Slack通知ワークフロー仕様書.md)
- [PR再AI Review待ちStatus更新ワークフロー仕様書.md](./PR%E5%86%8DAI%20Review%E5%BE%85%E3%81%A1Status%E6%9B%B4%E6%96%B0%E3%83%AF%E3%83%BC%E3%82%AF%E3%83%95%E3%83%AD%E3%83%BC%E4%BB%98%E6%A7%98%E6%9B%B8.md)
- [PRレビュー完了時Status更新ワークフロー仕様書.md](./PRレビュー完了時Status更新ワークフロー仕様書.md)
- [Commands設計書.md](../../00_共通/AIエージェント運用/Commands設計書.md) §17
