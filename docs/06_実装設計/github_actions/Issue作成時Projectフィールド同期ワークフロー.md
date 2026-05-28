# Issue 作成時 Project フィールド同期ワークフロー

## 1. ワークフローツール

本仕様は **GitHub Actions** と **GitHub Project（ProjectV2）** の GraphQL API を用いる。

| 項目 | 内容 |
| ---- | ---- |
| 実装ファイル | `.github/workflows/issue-metadata-project-branch.yml` |
| Actions 表示名 | **Issue metadata project and branch sync** |
| 正本 | 本ドキュメント（運用の数値・定数は実装 YAML と一致させる） |

## 2. 目的と対象外

### 2.1 目的

Issue運用メタデータを持つ Issue が作成または再同期されたタイミングで、Issue 本文を読み取り、ProjectV2 アイテムを追加または取得して次のフィールドを更新する。

| Project フィールド名 | 更新内容の由来 |
| -------------------- | -------------- |
| Status | `issues.opened` の初回同期時のみ、Issue運用メタデータの初期Statusを反映 |
| Phase | 本文セクション `### プロジェクト工程` の先頭行 |
| Priority | 本文セクション `### 優先度` の先頭行 |
| Area | 本文セクション `### 対象領域`（複数時は先頭 1 件のみ） |
| Planned Start | 本文セクション `### Planned Start` |
| Due Date | 本文セクション `### Due Date` |
| Actual Start | `ai-agent` は `issues.opened` 時にJST当日（未設定時のみ）、`human-led` はBranch新規作成時 |

### 2.2 対象外

- 既存値がある場合、`Actual Start` は上書きしない。
- `no-branch` チェック時およびBranch作成失敗時、`Actual Start` は設定しない。

## 3. トリガー・権限・並行制御

| 項目 | 内容 |
| ---- | ---- |
| `on` | `issues.types: [opened, edited]` / `workflow_dispatch` |
| `permissions` | `contents: write`, `issues: write`（API 実行は `PROJECTS_TOKEN` 優先、未設定時は `GITHUB_TOKEN`） |
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

- `Status`
- `Phase`
- `Priority`
- `Area`
- `Planned Start`
- `Due Date`
- `Actual Start`

## 5. 対象 Issue の判定

- イベント payload の Issue 本文に **`### 作業単位`** が含まれる場合のみ、Issue運用メタデータを持つIssueとして処理する。
- 含まれない場合は **スキップ**（手動作成 Issue 等）。ジョブは成功終了とする。

## 6. 本文パース

GitHub Issue forms は各フィールドを `### {フィールドのラベル}` 見出し以下に保存する。実装では見出し行でセクション分割し、値は先頭行または領域用の分割ルールに従う。

### 6.1 Phase

- セクションキー: `プロジェクト工程`（見出し `### プロジェクト工程`）
- **先頭行のみ**を使用する。
- 先頭行が **`なし`** または **`未定`** の場合、**Phase フィールドは更新しない**（既存値のまま）。
- Issue テンプレートはProjects正式値（例: `06_実装設計`）を使う。
- 旧テンプレート由来のMilestone風表記（例: `実装設計工程完了`）は、workflow側で互換候補としてProjects Phase正式値へ正規化する。
- 旧テンプレートの `結合・総合テスト工程完了` は、互換上 `08_モジュール結合テスト` を候補にする。より詳細なPhaseへ分ける必要がある場合は、人間がIssue本文を正式値へ修正して再実行する。

### 6.2 Priority

- セクションキー: `優先度`（`### 優先度`）
- 先頭行を小文字化し、`critical` / `high` / `medium` / `low` のときのみ処理する。
- Project の Priority オプションは、実装で **候補名のいずれかと一致**するものを探す（例: `priority: high`, `high`, `High` などの順で試行）。いずれも無い場合は警告コメント。

### 6.3 Area

- セクションキー: `対象領域`（`### 対象領域`）
- 値を改行・カンマ・読点で分割し、許可キー `web`, `api`, `reco`, `batch`, `db`, `docs`, `infra`, `project` にマッチするトークンを抽出（[Issue Label定義](../Issue%20Label定義.md) の `area:*` と整合）。
- **複数トークンがある場合は先頭 1 件のみ**を Project の Area に反映する（Project がシングルセレクトのため）。
- Project の Area オプションは、実装で **候補名のいずれかと一致**するものを探す（例: `web`, `area: web` など）。見つからない場合は警告コメント。

## 7. Project アイテムの特定とリトライ

- GraphQL `addProjectV2ItemById` でIssueをProjectV2へ追加する。
- 既にProjectV2上に存在する場合は、`items` をページングして当該Issueの `item.id` を取得する。
- `dry_run=true` の場合はProjectV2への追加・更新を行わず、既存アイテムがなければdry run用の仮IDで後続ログ確認のみ行う。

## 8. GraphQL 操作

1. **参照**: `projectId`、各フィールドの `id` と Single select の `options { id, name }` を取得する。
2. **追加・特定**: `addProjectV2ItemById` でIssueをProjectV2へ追加し、既存時は `items` をページングして `item.id` を取得する。
3. **更新**: `updateProjectV2ItemFieldValue` に `singleSelectOptionId` または `date` を渡し、`issues.opened` では初期Status / Phase / Priority / Area / Planned Start / Due Date を更新し、`issues.edited` では Status を除く同項目を更新する。Actual Startは作業主体ルールに従って更新する。

## 9. エラー・通知

| 状況 | 挙動 |
| ---- | ---- |
| Project フィールド名が見つからない | 警告ログ（該当フィールドの更新はスキップ） |
| Phase / Priority / Area のオプションが本文と一致しない | 該当フィールドの更新をスキップし、必要に応じて警告ログまたはIssueコメントで通知 |
| Project アイテムを追加・特定できない | 警告ログを出し、Projectフィールド同期をスキップ |
| `issues.createComment` が権限等で失敗 | 警告ログのみ |

## 10. 運用上の必須事項

- **Phase**: Issue の「プロジェクト工程」と Project の Phase は、Projects正式値（例: `06_実装設計`、`07_開発・単体テスト`）に揃える。識別子単位 Epic Issue は完了ゲートとして原則 `07_開発・単体テスト`（[Projects運用ルール](../../00_共通/プロジェクト管理/Projects運用ルール.md) §6.1）。子 Task は成果物工程に応じて 06 または 07。旧Issue本文に残るMilestone風表記はworkflow側で互換正規化する。
- **Status**: 継続同期（`issues.edited`）では更新しない。
- **Actual Start**: `ai-agent` は `issues.opened` でJST当日を設定（未設定時のみ）。`human-led` はBranch新規作成時のみ設定する。既存値は上書きしない。
- **Priority / Area**: GitHub Project 上の各オプション名を、Issue テンプレートの選択肢および [Issue Label定義](../Issue%20Label定義.md) の表記（例: `priority: high`, `area: web`）と **揃える**こと（実装は候補名のいずれかとの一致で解決する）。
- `PROJECTS_TOKEN` には、対象リポジトリで Issue コメントが可能なスコープを含めること（失敗時通知のため）。

## 11. 関連ドキュメント

- [Projects運用ルール.md](../Projects運用ルール.md) … Projects フィールド一覧・Area 凡例
- [Issue同期とブランチ作成ワークフロー.md](./Issue同期とブランチ作成ワークフロー.md) … 同一 Issue 作成フロー上の別ワークフロー（ラベル・Milestone・ブランチ）
- [update-projects-status-by-planned-start.yml](../../../../.github/workflows/update-projects-status-by-planned-start.yml) … Project 定数の正本（揃え先）
- [Planned Startに基づくStatus自動更新ワークフロー.md](./Planned%20Startに基づくStatus自動更新ワークフロー.md) … Planned Start 到来時の Backlog→Todo 自動更新
