# Slack通知共通ワークフロー仕様書

## 1. 目的

本仕様書は、GitHub Actions から Slack Bot token を用いて Slack 通知を送信する共通仕様を定義する。

Slack通知の通知対象、通知レベル、文面方針の正本は [Slack通知運用設計書](../../00_共通/AIエージェント運用/Slack通知運用設計書.md) とする。

本仕様書では、GitHub Actions 実装上の以下を扱う。

- Secret / Variables
- `chat.postMessage` 呼び出し
- `thread_ts` 管理
- 通知失敗時の扱い
- PR from fork の対象外方針

## 2. 実装ファイル

| 種別 | ファイル | 役割 |
| ---- | -------- | ---- |
| 共通script | `.github/scripts/slack-notify.cjs` | Slack payload生成、送信、thread marker操作 |
| 単体テスト | `.github/scripts/slack-notify.test.cjs` | payload、marker、error handlingの検証 |
| 手動通知workflow | `.github/workflows/slack-notify-manual.yml` | 人間判断、incident、横断影響、レビュー指摘対応完了の手動通知 |

## 3. GitHub Secrets / Variables

| 種別 | 名前 | 用途 |
| ---- | ---- | ---- |
| Repository Secret | `SLACK_BOT_TOKEN` | Slack `chat.postMessage` の認証に使用する Bot User OAuth Token |
| Repository Variable | `SLACK_CHANNEL_ID_DEVOPS` | 開発運用チャンネルの channel ID |
| Repository Variable | `SLACK_CHANNEL_ID_SYSTEM_ALERTS` | daily / weekly 親バッチ失敗通知用のシステムエラー通知チャンネル ID |
| Repository Variable | `SLACK_MENTION_HUMAN_REVIEW` | Human Review依頼時の個人メンション |
| Repository Variable | `SLACK_MENTION_INCIDENT` | incident / 作業停止時の個人メンション |
| Repository Variable | `SLACK_CHANNEL_ID_AI_OPS` | 必要になった場合のAI運用チャンネル |

`SLACK_BOT_TOKEN` の実値を workflow log、Issue、PR、docs、ai-logs に出力してはならない。

## 4. Slack App設定

| 項目 | 方針 |
| ---- | ---- |
| 投稿方式 | Slack Web API `chat.postMessage` |
| 必須scope | `chat:write` |
| `chat:write.public` | 初期計画では使用しない |
| チャンネル参加 | Botを対象チャンネルへ招待する |
| メンション | 個人IDを Variables に保持する |

## 5. 通知対象外

初期計画では、PR from fork を通知対象外とする。

理由は、fork 由来のPRでは `SLACK_BOT_TOKEN` などのSecret露出リスクが高く、別途security設計が必要になるためである。

対象workflowでは、必要に応じて以下を確認する。

```text
pull_request.head.repo.full_name == github.repository
```

## 6. thread_ts管理

同一IssueまたはPRに関する通知は、可能な範囲でSlackスレッドにまとめる。

| 対象 | 親メッセージ | 保存先 |
| ---- | ------------ | ------ |
| Issue単位 | Issue作成通知 | IssueコメントのHTML marker |
| PR単位 | PR作成通知 | PRコメントのHTML marker |

marker形式は共通scriptが生成する。

```text
<!-- slack-thread:v1 key=... channel=... ts=... -->
```

Slack `ts` はSecretではないが、Slack通知追跡用の内部メタデータとして扱う。

## 7. 通知失敗時の扱い

Slack通知に失敗しても、Issue / PR / Projects / docs の正本更新を取り消さない。

| 状況 | 扱い |
| ---- | ---- |
| Slack APIが `ok: false` を返した | workflow summaryに `error` のみ記録する |
| `SLACK_BOT_TOKEN` 未設定 | 通知をスキップし、summaryに設定不足を記録する |
| `SLACK_CHANNEL_ID_DEVOPS` 未設定 | 通知をスキップし、summaryに設定不足を記録する |
| `SLACK_CHANNEL_ID_SYSTEM_ALERTS` 未設定 | バッチ失敗通知をスキップし、旧開発運用チャンネルへ fallback しない |
| Human Review / incident通知失敗 | Issue / PRコメントまたはActionsログで補完する |

token実値、Authorization header、Slack API request body中のsecretは出力しない。

## 8. 通知レベル

| レベル | 用途 |
| ------ | ---- |
| `info` | Issue作成、PR作成、PR merge / Done |
| `review` | AI Review完了、Human Review依頼 |
| `action_required` | 人間判断依頼、修正必要 |
| `warning` | 横断影響、分割提案 |
| `error` | 作業停止、incident |

通知レベルの意味は [Slack通知運用設計書](../../00_共通/AIエージェント運用/Slack通知運用設計書.md) を正とする。

## 9. 関連workflow

| workflow | 通知 |
| -------- | ---- |
| `.github/workflows/issue-metadata-project-branch.yml` | Issue作成通知 |
| `.github/workflows/pr-created-status-and-slack.yml` | PR作成通知、AI Review遷移通知 |
| `.github/workflows/pr-ready-for-ai-review.yml` | fix 完了後の再 AI Review 通知、In Progress → AI Review |
| `.github/workflows/pr-review-status-sync.yml` | AI Review完了通知、Human Review依頼、修正必要通知 |
| `.github/workflows/pr-merged-done-and-slack.yml` | PR merge / Done通知 |
| `.github/workflows/slack-notify-manual.yml` | 人間判断、incident、横断影響、レビュー指摘対応完了 |
| `.github/workflows/batch-daily-orchestrator.yml` | システムエラー通知チャンネルへの日次親workflow失敗通知（`error` / incidentメンション） |
| `.github/workflows/batch-weekly-orchestrator.yml` | システムエラー通知チャンネルへの週次親workflow失敗通知（`error` / incidentメンション） |

親 Batch workflow の通知は、`needs.*.result` に `failure` がある場合のみ実行する。
通知先は `SLACK_CHANNEL_ID_SYSTEM_ALERTS` のみとし、未設定時に `SLACK_CHANNEL_ID_DEVOPS` へ fallback しない。
Issue / PR / AI Review等の作業通知は、従来どおり `SLACK_CHANNEL_ID_DEVOPS` を使用する。
通知本文には失敗 job 名、workflow、run番号、ref、Actions Run URLを含める。
Slack通知stepは `continue-on-error: true` とし、通知自体の失敗で本線の結果を上書きしない。

