# Issue 作成時 Project フィールド同期ワークフロー

## 1. ワークフローツール

本仕様は **GitHub Actions** と **GitHub Project（ProjectV2）** の GraphQL API を用いる。

| 項目 | 内容 |
| ---- | ---- |
| 実装ファイル | `.github/workflows/issue-opened-set-project-fields-from-issue-body.yml` |
| Actions 表示名 | **Set project Phase Priority Area from issue body** |
| 正本 | 本ドキュメント（運用の数値・定数は実装 YAML と一致させる） |

## 2. 目的と対象外

### 2.1 目的

Task 用 Issue フォーム（`.github/ISSUE_TEMPLATE/base.yml`）から Issue が **`issues.opened`** されたタイミングで、Issue 本文を読み取り、既に Project に存在するアイテムに対して、次の **シングルセレクト** フィールドを更新する。

| Project フィールド名 | 更新内容の由来 |
| -------------------- | -------------- |
| Phase | 本文セクション `### プロジェクト工程` の先頭行 |
| Priority | 本文セクション `### 優先度` の先頭行 |
| Area | 本文セクション `### 対象領域`（複数時は先頭 1 件のみ） |

### 2.2 対象外

- **Issue を Project に追加する処理**（アイテムの新規作成・紐づけ）は本ワークフローでは行わない。GitHub の既定ワークフローやリポジトリ設定など **別経路で既に Project に載る**前提とする。
- Status / Planned Start / Due Date 等、上記 3 フィールド以外の Project フィールドは更新しない。

## 3. トリガー・権限・並行制御

| 項目 | 内容 |
| ---- | ---- |
| `on` | `issues.types: [opened]` |
| `permissions` | `contents: read`（API 実行は `PROJECTS_TOKEN`） |
| `concurrency` | `project-fields-from-body-${{ github.event.issue.number }}`（同一 Issue の同時実行を直列化、`cancel-in-progress: false`） |

## 4. シークレット・定数

| 名前 | 用途 |
| ---- | ---- |
| `PROJECTS_TOKEN` | GraphQL `projectV2` の参照・`updateProjectV2ItemFieldValue`、および失敗時の `issues.createComment` |

次の定数は [update-projects-status-by-planned-start.yml](../../../../.github/workflows/update-projects-status-by-planned-start.yml) と **同一値**に保つこと（片方だけ変更しない）。

- `PROJECT_OWNER`（例: ユーザー login）
- `PROJECT_NUMBER`（ユーザー Project の番号）
- `REPOSITORY_NAME_WITH_OWNER`（`owner/name`）

フィールド名定数（Project 上の列名と一致させる）:

- `Phase`
- `Priority`
- `Area`

## 5. 対象 Issue の判定

- イベント payload の Issue 本文に **`### 作業単位`** が含まれる場合のみ、Task フォーム由来とみなし処理する。
- 含まれない場合は **スキップ**（手動作成 Issue 等）。ジョブは成功終了とする。

## 6. 本文パース

GitHub Issue forms は各フィールドを `### {フィールドのラベル}` 見出し以下に保存する。実装では見出し行でセクション分割し、値は先頭行または領域用の分割ルールに従う。

### 6.1 Phase

- セクションキー: `プロジェクト工程`（見出し `### プロジェクト工程`）
- **先頭行のみ**を使用する。
- 先頭行が **`なし`** の場合、**Phase フィールドは更新しない**（既存値のまま）。
- それ以外は、Project の Phase オプションの **`name` と完全一致**するオプションを選ぶ。見つからない場合は Issue に警告コメントし、Phase は更新しない。

### 6.2 Priority

- セクションキー: `優先度`（`### 優先度`）
- 先頭行を小文字化し、`high` / `medium` / `low` のときのみ処理する。
- Project の Priority オプションは、実装で **候補名のいずれかと一致**するものを探す（例: `priority: high`, `high`, `High` などの順で試行）。いずれも無い場合は警告コメント。

### 6.3 Area

- セクションキー: `対象領域`（`### 対象領域`）
- 値を改行・カンマ・読点で分割し、許可キー `web`, `api`, `reco`, `batch`, `db`, `docs`, `infra`, `project` にマッチするトークンを抽出（[Issue Label定義](../Issue%20Label定義.md) の `area:*` と整合）。
- **複数トークンがある場合は先頭 1 件のみ**を Project の Area に反映する（Project がシングルセレクトのため）。
- Project の Area オプションは、実装で **候補名のいずれかと一致**するものを探す（例: `web`, `area: web` など）。見つからない場合は警告コメント。

## 7. Project アイテムの特定とリトライ

- GraphQL で `user(login:).projectV2(number:)` の `items` をページングし、`content` が当該リポジトリの Issue かつ **`number` が一致**するノードの `item.id` を取得する。
- Issue の Project 紐づけが **作成直後に遅延**する場合があるため、一定回数・一定間隔で **再検索**する（実装の定数: 最大試行回数・待機ミリ秒）。
- 最後まで見つからない場合は **Issue にコメント**し、ジョブは **失敗にしない**（警告ログで終了）。

## 8. GraphQL 操作

1. **参照**: 同一クエリで `projectId`、各 Single select フィールドの `id` と `options { id, name }`、および `items` のページを取得する。
2. **更新**: `updateProjectV2ItemFieldValue` に `singleSelectOptionId` を渡し、Phase / Priority / Area をそれぞれ必要なものだけ更新する。

## 9. エラー・通知

| 状況 | 挙動 |
| ---- | ---- |
| Project フィールド名が見つからない | 警告ログ（該当フィールドの更新はスキップ） |
| Phase / Priority / Area のオプションが本文と一致しない | Issue コメントで通知（オプション名の一部を例示） |
| Project アイテムがリトライ後も見つからない | Issue コメントで通知、ジョブは成功扱いで終了 |
| `issues.createComment` が権限等で失敗 | 警告ログのみ |

## 10. 運用上の必須事項

- GitHub Project 上の **Phase / Priority / Area の各オプション名**を、Issue テンプレートの選択肢および [Issue Label定義](../Issue%20Label定義.md) の表記（例: `priority: high`, `area: web`）と **揃える**こと。
- `PROJECTS_TOKEN` には、対象リポジトリで Issue コメントが可能なスコープを含めること（失敗時通知のため）。

## 11. 関連ドキュメント

- [Projects運用ルール.md](../Projects運用ルール.md) … Projects フィールド一覧・Area 凡例
- [Issue同期とブランチ作成ワークフロー.md](./Issue同期とブランチ作成ワークフロー.md) … 同一 Issue 作成フロー上の別ワークフロー（ラベル・Milestone・ブランチ）
- [update-projects-status-by-planned-start.yml](../../../../.github/workflows/update-projects-status-by-planned-start.yml) … Project 定数の正本（揃え先）
