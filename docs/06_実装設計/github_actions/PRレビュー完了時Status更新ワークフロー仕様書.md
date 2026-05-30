# PRレビュー完了時 Status 更新ワークフロー

## 1. ワークフローツール

本仕様は **GitHub Actions** と **GitHub Project（ProjectV2）** の GraphQL API を用いる。


| 項目              | 内容                                                            |
| --------------- | ------------------------------------------------------------- |
| 実装ファイル          | `.github/workflows/pr-review-status-sync.yml` |
| 判定ロジック（単体テスト対象） | workflow内ロジック、`.github/scripts/slack-notify.cjs`、`.github/scripts/dispatch-pr-review-status-sync.cjs`、`.github/scripts/publish-ai-review-and-dispatch.cjs` |
| Actions 表示名     | **PR Review Status Sync**                      |
| Run 名（一覧）     | `status-sync · {dispatch\|human-review\|manual} · PR #n · {review_result\|state}` |
| 正本              | 本ドキュメント（運用の数値・定数は実装 YAML と一致させる）                              |


## 2. 目的と正本

### 2.1 目的

[Projects運用ルール.md](../../00_共通/プロジェクト管理/Projects運用ルール.md) §10.2・§17.4〜§17.6 に従い、**AI Review 完了**または **Human Review 指摘**に応じて Projects の **Status** を更新する。


| 経路              | 概要                                                                     |
| --------------- | ---------------------------------------------------------------------- |
| AI Review 完了    | `repository_dispatch` の **Review Result** に応じ、`Human Review` または `In Progress` へ遷移する |
| Human Review 指摘 | GitHub PR Review の `changes_requested` に応じ、`In Progress` へ遷移する         |


Status の正式値は [Projects運用ルール.md](../../00_共通/プロジェクト管理/Projects運用ルール.md) §9 を正本とする。

運用上のレビュー結果分類は [AIレビュー運用設計書.md](../../00_共通/AIエージェント運用/AIレビュー運用設計書.md) §6、[review-pr.md](../../../.cursor/commands/review-pr.md) Status への影響を参照する。

### 2.2 対象外

本ワークフローでは、以下は行わない。


| 対象                                                            | 担当                                 |
| ------------------------------------------------------------- | ---------------------------------- |
| PR 作成時に Status を **AI Review** へ更新                            | PR作成時Status更新ワークフロー（別仕様書・後続作成）     |
| PR merge / Issue close 時に Status を **Done** へ更新、Actual End 設定 | PR merge時Status更新ワークフロー（別仕様書・後続作成） |
| Fixer AI による修正コミット、再 AI Review の実施                            | `/fix-review-comments`、Reviewer AI |
| ai-logs 記録                                                       | AIログ運用ルール                                  |
| Phase / Priority / Area / 日付フィールドの更新                          | 各同期 workflow                       |


### 2.3 Command・workflow の責務境界

[Projects運用ルール.md](../../00_共通/プロジェクト管理/Projects運用ルール.md) §17.5 では、In Progress へ戻した後に修正着手トリガーを明示する。


| 責務                             | 主体                                      |
| ------------------------------ | --------------------------------------- |
| Projects Status の更新            | 本ワークフロー                                 |
| AI Review 結果の PR コメント投稿        | Reviewer AI（`/review-pr`）               |
| 修正着手（同一 Branch）                | Fixer AI / 人間（`/fix-review-comments` 等） |
| 修正必要・Human Review 依頼の Slack 通知 | 本ワークフローとSlack通知共通script             |


本ワークフローは **Status 更新とSlack通知** を行う。Command 起票は行わない。

## 3. トリガー・権限・並行制御


| 項目                       | 内容                                                                               |
| ------------------------ | -------------------------------------------------------------------------------- |
| `on.repository_dispatch` | `types: [ai_review_status_sync]`。**AI Review 完了時の唯一の自動トリガ**（`/review-pr` または Harness から 1 回 dispatch） |
| `on.pull_request_review` | `types: [submitted]`。`state: changes_requested` を Human 経路で処理                    |
| `on.workflow_dispatch`   | 手動再実行。入力: PR 番号、Review Result 等                                    |
| `on.issue_comment`       | **使用しない**（Issue/PR コメントごとの Run 増殖・キャンセル連鎖を防ぐ） |
| `permissions`            | `contents: read`、`issues: write`、`pull-requests: read`（PR・コメント参照）。Project API は `PROJECTS_TOKEN` |
| `concurrency`            | `pr-review-status-sync-<PR番号>`（`client_payload.pr_number` / `inputs` / `pull_request.number`）。`cancel-in-progress: false` |

### 3.1 AI Review 経路の起動（repository_dispatch）

| 項目 | 内容 |
| ---- | ---- |
| イベント種別 | `ai_review_status_sync` |
| 起動主体 | `/review-pr` 完了後の Agent（**`publish-ai-review-and-dispatch.cjs` 推奨**）、`dispatch-pr-review-status-sync.cjs`、または `gh api .../dispatches` |
| Run 数 | **AI Review 1 回につき dispatch 1 回 → Workflow Run 1 回** |

`client_payload`（必須キー）:

| キー | 型 | 説明 |
| ---- | --- | ---- |
| `pr_number` | string | 対象 PR 番号 |
| `review_result` | string | `approve_for_human_review` / `request_changes` / `needs_human_decision` / `split_required` / `blocked`（または人間向けラベル） |
| `review_body` | string | 任意。`needs_human_decision` で §22 `次Status` が `In Progress` のときの本文 |

PR 作成時の Status 更新（`AI Review`）は [PR作成時Status更新ワークフロー](./PR作成時Status更新ワークフロー仕様書.md)（`pr-created-status-and-slack.yml`）が担当し、本ワークフローは **起動しない**。

Issue 作成時（metadata のコメント）でも本ワークフローは **起動しない**。

### 3.2 再実行ループ防止（必須）

| 対策 | 内容 |
| ---- | ---- |
| `issue_comment` トリガ廃止 | コメント投稿で Workflow が連鎖起動しない |
| dispatch 明示 | AI Review 完了は `repository_dispatch` のみ |
| 確認コメント | Status 更新後の PR コメントに **Review Result enum を含めない**（記録用。トリガにはならない） |
| 冪等（§5.3） | 現在 Status を読み、前提不一致・次 Status 同一なら更新・Slack をスキップ |

## 4. シークレット・定数


| 名前               | 用途                                                      |
| ---------------- | ------------------------------------------------------- |
| `PROJECTS_TOKEN` | GraphQL `projectV2` の参照・`updateProjectV2ItemFieldValue` |
| `GITHUB_TOKEN`   | PR・Review・Issue コメントの読み取り（権限範囲内）                        |
| `SLACK_BOT_TOKEN` | Slack `chat.postMessage` |
| `SLACK_CHANNEL_ID_DEVOPS` | Slack通知先 |
| `SLACK_MENTION_HUMAN_REVIEW` | Human Review依頼時の個人メンション |


次の定数は [Issue作成時Projectフィールド同期ワークフロー.md](./Issue作成時Projectフィールド同期ワークフロー.md) および [Planned Startに基づくStatus自動更新ワークフロー.md](./Planned%20Startに基づくStatus自動更新ワークフロー.md) と **同一値**に保つこと。


| 定数名                          | 説明                  |
| ---------------------------- | ------------------- |
| `PROJECT_OWNER`              | `user(login:)` クエリ用 |
| `PROJECT_NUMBER`             | Project 番号          |
| `REPOSITORY_NAME_WITH_OWNER` | 更新対象 Issue のフィルタ    |


Status 列および遷移先（Project 上の表示名と一致させる。照合は **大文字小文字を区別しない**）:


| 用途       | 定数値                            |
| -------- | ------------------------------ |
| Status 列 | `Status`                       |
| 遷移先      | `Human Review` / `In Progress` |


## 5. Status 遷移表（実装の単一正本）

### 5.1 AI Review 経路（repository_dispatch）

`client_payload.review_result`（および任意の `review_body`）から次 Status を決定する。PR コメントの機械パースは行わない。PR コメント正本フォーマットは [ai-review-comment.md](../../../prompts/templates/review/ai-review-comment.md) §1・§22（人間・監査用。`/review-pr` が投稿する）。


| Review Result                                                | 現在 Status（前提） | 次 Status              |
| ------------------------------------------------------------ | ------------- | --------------------- |
| `approve_for_human_review`                                   | `AI Review`   | `Human Review`        |
| `request_changes`                                            | `AI Review`   | `In Progress`         |
| `split_required`                                             | `AI Review`   | `In Progress`         |
| `blocked`                                                    | `AI Review`   | `In Progress`         |
| `needs_human_decision`                                       | `AI Review`   | **既定** `Human Review` |
| `needs_human_decision` かつコメントに `次Status` が `In Progress` と明示 | `AI Review`   | `In Progress`         |


`needs_human_decision` の自動化既定は `Human Review` とする。根拠は [review-definition.schema.md](../../../prompts/definitions/_schemas/review-definition.schema.md) の `status_policy.on_needs_human_decision` に合わせる。

[AIレビュー運用設計書.md](../../00_共通/AIエージェント運用/AIレビュー運用設計書.md) §6 の「または In Progress」は、**`client_payload.review_body`（または `workflow_dispatch` 入力）に `次Status` が `In Progress` と含まれる場合**に限り In Progress へ遷移する。

### 5.2 Human Review 経路（PR Review イベント）


| 条件                                                | 現在 Status（前提）  | 次 Status                             |
| ------------------------------------------------- | -------------- | ------------------------------------ |
| `pull_request_review.state` が `changes_requested` | `Human Review` | `In Progress`                        |
| `pull_request_review.state` が `approved`          | —              | **更新しない**（merge 時 Done workflow に委譲） |


Human Review で承認された場合、本ワークフローは Status を変更しない。Done への遷移は PR merge 時 workflow が担う。

### 5.3 共通のスキップ条件（正当スキップ）

以下は **誤更新防止** のため Status を更新せず、**ジョブは成功** とする。Summary に skipped 理由を記録する。


| 条件                      | 挙動             |
| ----------------------- | -------------- |
| 対象 Issue が Project に未追加 | スキップ（ログに理由）    |
| 現在 Status が前提と不一致       | スキップ（冪等・誤更新防止） |
| 次 Status が現在 Status と同一 | スキップ           |


### 5.4 AI 経路の致命的エラー（ジョブ失敗）

§5.4 で **AI 経路** に、次のいずれかが起きた場合は **Status を更新しない**。かつ `core.setFailed` でジョブ失敗とする（§9 参照）。


| 条件                           | 挙動    |
| ---------------------------- | ----- |
| `client_payload` に `pr_number` / `review_result` がない、または `review_result` が許容値でない | ジョブ失敗 |
| 紐づく Task Issue を PR から解決できない | ジョブ失敗 |


Human 経路では Review Result のパースは行わないため、本節は AI 経路のみに適用する。

## 6. 機械判定: Review Result（AI 経路）

### 6.1 `client_payload` の正規化

1. `review_result` を `.github/scripts/slack-notify.cjs` の `normalizeKnownReviewToken` で正規化する（英語 enum または `Human Reviewへ進行可` 等の人間向けラベル）
2. 正規化できない場合は §5.4 のパース失敗とする

### 6.2 次Status の明示（needs_human_decision 用）

`review_body`（未指定時は空文字）に対し、`次Status | \`In Progress\`` 形式が含まれるかを判定する（`statusFromReviewResult` と同じロジック）。


| 条件 | 解釈 |
| ---- | ---- |
| `review_result` が `needs_human_decision` かつ `review_body` に In Progress 明示 | `In Progress` へ |
| 上記以外の `needs_human_decision` | 既定どおり `Human Review` へ |

### 6.3 紐づく Issue の特定

1. `client_payload.pr_number` から PR を取得する
2. PR 本文の `Related to #<n>` / `Closes #<n>` 等から Task Issue 番号を解決する（[Task Definition設計書.md](../../00_共通/AIエージェント運用/Task%20Definition設計書.md) §22・§39 を参照）
3. 解決できない場合は §5.4 に従いジョブ失敗とする

### 6.4 dispatch ヘルパー

| スクリプト | 用途 |
| ---------- | ---- |
| [`.github/scripts/publish-ai-review-and-dispatch.cjs`](../../../.github/scripts/publish-ai-review-and-dispatch.cjs) | **推奨**。AI Review コメント投稿 + `repository_dispatch` を 1 コマンドで実行。`--verify` で dispatch 忘れを検査 |
| [`.github/scripts/dispatch-pr-review-status-sync.cjs`](../../../.github/scripts/dispatch-pr-review-status-sync.cjs) | dispatch のみ（recovery / 低レベル API） |

`/review-pr` §15.5 から **`publish-ai-review-and-dispatch.cjs` を正本** とする。

## 7. 処理概要

1. イベント種別に応じて AI 経路または Human 経路を選択する
2. `actions/checkout` で `.github/scripts/slack-notify.cjs` を読み込む（§6 正規化・§5.3 照合・確認コメント文案）
3. GraphQL で Project の **Status** フィールド ID と遷移先オプション ID を解決する
4. 対象 Issue の Project item を特定し、**現在 Status** を `fieldValueByName(name: "Status")` で読む
5. §5 の遷移表に従い次 Status を決定する（§5.3 のスキップ条件に該当すれば更新・確認コメント・Slack を行わず記録）
6. `updateProjectV2ItemFieldValue` で Status を更新する
7. PR に確認コメントを 1 件投稿する（`Project Status更新意図: Issue #<n> を \`<次Status>\` へ更新しました。`。**Review Result enum は含めない**）
8. Review Result に応じて Slack 通知を送信する（Slack 本文の Review Result は人間向けラベル可）
9. ジョブサマリーに Issue 番号・経路・Review Result・更新前後 Status・Slack 通知結果を出力する
10. §5.4 に該当した場合は `core.setFailed` し、Summary に PR 番号・Issue 番号（解決できた場合）・失敗理由・コメント URL を出力する

## 8. GraphQL

[Planned Startに基づくStatus自動更新ワークフロー.md](./Planned%20Startに基づくStatus自動更新ワークフロー.md) §6 と同様とする。

- `updateProjectV2ItemFieldValue` の `value` には `**singleSelectOptionId` のみ** を渡す
- 対象は当該リポジトリの **Issue** に紐づく Project item のみ
- **現在 Status の読取**は `node(id: $projectItemId) { ... on ProjectV2Item { fieldValueByName(name: "Status") { ... } } }` を用いる（`ProjectV2.item(id:)` は使用しない）

## 9. エラー・通知

[Planned Startに基づくStatus自動更新ワークフロー.md](./Planned%20Startに基づくStatus自動更新ワークフロー.md) §7 と同様、**設定不備・AI 経路の判定不能** はジョブ失敗とし、**正当スキップのみで更新 0 件** はジョブ成功とする。


| 状況                                                    | 挙動                                              |
| ----------------------------------------------------- | ----------------------------------------------- |
| Project が取得できない                                       | `core.setFailed` でジョブ失敗                         |
| `Status` フィールドまたは遷移先オプションが見つからない                      | `core.setFailed` でジョブ失敗                         |
| 正当スキップのみで更新 0 件（§5.3）                                 | ジョブ成功（Summary に skipped 内訳）                 |
| `client_payload` 不正（§5.4） | `core.setFailed` |
| Task Issue を PR から解決できない（§5.4）       | `core.setFailed` |
| 一部 item の更新で API 失敗                                   | 例外によりジョブ失敗（再実行で冪等に再試行可能）                        |


ジョブ失敗時は、PR の Checks / Actions 一覧で検知できること。失敗を放置すると Projects の Status が `AI Review` のまま残るため、**`/review-pr` の dispatch 再実行**、または **`workflow_dispatch`** で再実行する。

Slack通知に失敗しても、Projects Status の更新は取り消さない。通知失敗は workflow summary に記録する。

## 10. 運用上の必須事項

- Project の Status に **AI Review** / **Human Review** / **In Progress** が存在し、表示名が [Projects運用ルール.md](../../00_共通/プロジェクト管理/Projects運用ルール.md) §9 と一致すること
- `/review-pr` は **`publish-ai-review-and-dispatch.cjs`**（コメント + dispatch）を **1 回** 実行すること。完了前に `--verify` で dispatch 済みを確認してもよい
- PR コメントは [ai-review-comment.md](../../../prompts/templates/review/ai-review-comment.md) 形式で投稿すること（人間・監査用。Status 同期のトリガには使わない）
- dispatch 忘れ時は `--dispatch-only` または `workflow_dispatch` で再実行する
- PR 本文に Task Issue への参照（`Related to #<n>` 等）を含めること（§6.4）。不足時はワークフローが失敗する
- 本ワークフローが **失敗（赤）** した場合は、Summary の PR・失敗理由を確認し、テンプレート・コメント・Issue 参照を修正してから再実行すること
- `PROJECTS_TOKEN` には対象 Project の読み書きに必要なスコープを付与すること
- Human Review 指摘は GitHub 上の **Request changes**（`changes_requested`）で行うこと（コメントのみでは本経路は動作しない）

## 11. 関連ドキュメント

- [Projects運用ルール.md](../../00_共通/プロジェクト管理/Projects運用ルール.md) … Status 定義・§17 詳細ルール
- [AIレビュー運用設計書.md](../../00_共通/AIエージェント運用/AIレビュー運用設計書.md) … Review Result と Status の対応
- [Issue運用ルール.md](../../00_共通/プロジェクト管理/Issue運用ルール.md) … Issue と PR の関係
- [review-pr.md](../../../.cursor/commands/review-pr.md) … Status 更新意図の出力
- [ai-review-comment.md](../../../prompts/templates/review/ai-review-comment.md) … PR コメント正本フォーマット
- [review-definition.schema.md](../../../prompts/definitions/_schemas/review-definition.schema.md) … `status_policy`
- [Issue作成時Projectフィールド同期ワークフロー.md](./Issue作成時Projectフィールド同期ワークフロー.md) … Project 定数の揃え先

検証結果は、必要に応じて `docs/08_モジュール結合テスト/` 以降のテスト工程配下に記録する。