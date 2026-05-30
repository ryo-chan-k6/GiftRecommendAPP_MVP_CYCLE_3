# Planned Start に基づく Status 自動更新ワークフロー

## 1. ワークフローツール

本仕様は **GitHub Actions** と **GitHub Project（ProjectV2）** の GraphQL API を用いる。

| 項目 | 内容 |
| ---- | ---- |
| 実装ファイル | `.github/workflows/update-projects-status-by-planned-start.yml` |
| 判定ロジック（単体テスト対象） | `.github/scripts/planned-start-status-policy.cjs` |
| Actions 表示名 | **Planned Start Status Sync** |
| Run 名（一覧） | `planned-start · {schedule\|manual}` |
| 正本 | 本ドキュメント（運用の数値・定数は実装 YAML と一致させる） |

## 2. 目的と対象外

### 2.1 目的

[Projects運用ルール.md](../Projects運用ルール.md) の Status 定義に従い、**着手予定日（Planned Start）が到来したタスク**を **Backlog から Todo** へ移す。

| Projects 上の条件（すべて満たす） | 実行する更新 |
| ---------------------------------- | ------------ |
| アイテムが **当該リポジトリの Issue** である | 他リポジトリ Issue は対象外 |
| **Status** が **Backlog**（大文字小文字は区別しない） | それ以外は変更しない |
| **Planned Start** に日付が入っている | 未設定・不正形式は変更しない |
| **Planned Start** の暦日が **JST の当日以前**（当日を含む） | 未来日のみのタスクは変更しない |

**日付比較の解釈（重要）**

- 運用ルール上、**Backlog** は「着手開始予定日がまだ」、**Todo** は「着手予定日を過ぎた」タスクと定義されている。
- したがって本ワークフローでは、カレンダー上 **Planned Start ≤ JST 当日** のときに Backlog→Todo とする（**当日 0:00 JST の実行直後から Todo 扱い**）。
- 依頼文面で `Planned Start > 当日` と書かれていた場合、上記運用定義と意味が逆になるため、**運用ルールを正**として実装している。

### 2.2 対象外

- **Pull Request**・**Draft issue** など Issue 以外のアイテム（Project に載っていてもスキップ）。
- Status が Backlog 以外、または Planned Start が空の Issue（スキップ）。
- Phase / Priority / Area など **Status 以外のフィールド**の更新。

## 3. トリガー・権限・並行制御

| 項目 | 内容 |
| ---- | ---- |
| `on.schedule` | `cron: "0 15 * * *"`（**UTC 毎日 15:00**＝**JST 毎日 0:00**。日本は DST がないため固定） |
| `on.workflow_dispatch` | 手動実行（初回検証・再実行用） |
| `permissions` | `contents: read`（スクリプト読み込みのため `actions/checkout` を使用）。Project API は `PROJECTS_TOKEN` |
| `concurrency` | `project-status-by-planned-start`（`cancel-in-progress: false`） |

## 4. シークレット・定数

| 名前 | 用途 |
| ---- | ---- |
| `PROJECTS_TOKEN` | GraphQL `projectV2` の参照・`updateProjectV2ItemFieldValue` |

次の定数は [issue-opened-set-project-fields-from-issue-body.yml](../../../../.github/workflows/issue-opened-set-project-fields-from-issue-body.yml) と **同一値**に保つこと（片方だけ変更しない）。

| 定数名 | 例 | 説明 |
| ------ | -- | ---- |
| `PROJECT_OWNER` | ユーザー login | `user(login:)` クエリ用 |
| `PROJECT_NUMBER` | 整数 | `users/<owner>/projects/<N>` の N |
| `REPOSITORY_NAME_WITH_OWNER` | `owner/name` | 更新対象 Issue のフィルタ |

フィールド名・遷移先 Status（Project 上の表示名と一致させる）:

| 用途 | 定数値 |
| ---- | ------ |
| Status 列 | `Status` |
| 日付列 | `Planned Start` |
| 遷移先のシングルセレクト名 | `Todo`（候補照合は **大文字小文字を区別しない**） |

## 5. 処理概要

1. `actions/checkout` でリポジトリを取得し、`planned-start-status-policy.cjs` を `require` する。
2. GraphQL で `user(login:).projectV2(number:)` を取得し、**Status** シングルセレクトのフィールド ID と **Todo** オプション ID を解決する。
3. **items** をカーソルページング（100 件ずつ）し、各ノードの `fieldValues` から **Status** と **Planned Start** を読む。
4. 当該リポジトリの Issue かつ `shouldPromoteFromBacklogToTodo` が真のとき、`updateProjectV2ItemFieldValue` で Status を Todo に更新する。
5. ジョブサマリー（GitHub Actions の Summary）に、JST 当日・更新件数・更新した Issue 番号を出力する。

## 6. GraphQL

### 6.1 参照

- Project の `fields` から `ProjectV2SingleSelectField`（`Status`）の `options` を取得。
- Project の `items` と各 item の `fieldValues` について、`ProjectV2ItemFieldSingleSelectValue` と `ProjectV2ItemFieldDateValue` を展開し、紐づく `field.name` で列を識別する（GitHub ドキュメントの例に準拠）。

### 6.2 更新

- `updateProjectV2ItemFieldValue` の `value` には **`singleSelectOptionId` のみ** を渡す（他キーを付けない）。

## 7. エラー・通知

| 状況 | 挙動 |
| ---- | ---- |
| Project が取得できない | `core.setFailed` でジョブ失敗 |
| `Status` フィールドまたは `Todo` オプションが見つからない | `core.setFailed` でジョブ失敗 |
| 更新対象が 0 件 | ジョブ成功（ログおよび Summary に 0 件と記録） |
| 一部 item の更新で API 失敗 | 例外によりジョブ失敗（再実行で冪等に再試行可能） |

## 8. 運用上の必須事項

- **Project の Status** に **Backlog** と **Todo** が存在し、表示名が実装の候補（`Todo` の大小無視）と一致すること。
- **Planned Start** は GitHub Project の **日付**型フィールドとし、運用どおり **全タスクに日付を入れる**こと（未設定は自動昇格しない）。
- `PROJECTS_TOKEN` には対象ユーザー Project の読み書きに必要なスコープを付与すること。

## 9. 関連ドキュメント

- [Projects運用ルール.md](../../00_共通/プロジェクト管理/Projects運用ルール.md) … フィールド一覧・Status 定義
- [Issue作成時Projectフィールド同期ワークフロー.md](./Issue作成時Projectフィールド同期ワークフロー.md) … Project 定数の揃え先（同一）

検証結果は、必要に応じて `docs/08_モジュール結合テスト/` 以降のテスト工程配下に記録する。
