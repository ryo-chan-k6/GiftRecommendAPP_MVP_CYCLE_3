# Definition Run Harnessワークフロー仕様書

## 1. 目的

本仕様書は、Slack や GitHub Actions などの外部トリガから Definition Run（`/start-epic` / `/start-task` 等の Cursor Command を Definition と組み合わせて実行する単位）を Cursor Cloud Agent に依頼するための GitHub Actions Harness を定義する。

本 Harness は、1 Command（MVP では `/start-epic`）で framework を確立し、他 Command への横展開を「Command レジストリへの追記 + 軽微な差分」で済む構造にする。

更新系処理（Projects 同期・Branch 作成・PR 操作）は本 Harness 自身では行わず、Issue 起票後の既存 workflow に委譲する。本方針は [Commands設計書](../../00_共通/AIエージェント運用/Commands設計書.md) §4 / §10 に従う（§13 参照）。

Definition Run の通称・Command 定義・Task Definition 構造の正本は以下を参照する。

| 項目 | 正本ドキュメント |
| ---- | ---------------- |
| Definition Run 通称・Command 仕様 | [Commands設計書](../../00_共通/AIエージェント運用/Commands設計書.md) |
| Task Definition 構造 | [Task Definition設計書](../../00_共通/AIエージェント運用/Task%20Definition設計書.md) |
| Issue 運用メタデータ / 初回・継続同期 | [Issue運用ルール](../../00_共通/プロジェクト管理/Issue運用ルール.md) §10 / §10.1 |
| Phase / Milestone（識別子単位 Epic） | [Projects運用ルール](../../00_共通/プロジェクト管理/Projects運用ルール.md) §6.1 |
| Slack 通知方針 | [Slack通知運用設計書](../../00_共通/AIエージェント運用/Slack通知運用設計書.md) |

## 2. 実装ファイル

| 種別 | ファイル | 役割 |
| ---- | -------- | ---- |
| workflow | `.github/workflows/definition-run.yml` | `repository_dispatch` / `workflow_dispatch` トリガ、入力検証、Cursor SDK 呼び出し、post-run 検証、Job Summary 出力 |
| 共通 script | `.github/scripts/definition-run-prompt-builder.cjs` | Command レジストリ、入力検証、プロンプト組み立て、secret マスク |
| 単体テスト | `.github/scripts/definition-run-prompt-builder.test.cjs` | builder の正常系・異常系・secret マスクの検証 |
| 共通 script | `.github/scripts/definition-run-post-verify.cjs` | 実行後の Issue / PR / Branch 新規作成検知、**review-pr dispatch 忘れ検証**、違反判定、Job Summary 用 Markdown 生成 |
| 単体テスト | `.github/scripts/definition-run-post-verify.test.cjs` | post-verify の正常系・違反検出系の検証 |
| Actions 表示名 | `Definition Run Harness` | |

## 3. トリガ

```yaml
on:
  repository_dispatch:
    types:
      - definition-run
  workflow_dispatch:
    inputs:
      command: ...
      definition: ...
      run_mode: ...
      request_issue: ...
      requested_by: ...
```

| トリガ | 用途 |
| ---- | ---- |
| `repository_dispatch (types: [definition-run])` | Slack や Bridge からの自動トリガ（Phase C 以降） |
| `workflow_dispatch` | 人間からの手動実行・受入確認 |

両トリガの inputs / payload は **同形** に揃える。

## 4. 入力契約

| 項目 | 必須 | 値 | 説明 |
| ---- | ---- | ---- | ---- |
| `command` | 必須 | `start-epic`（dry-run のみ）／ `review-pr`（dry-run / live-run）／ 将来 `start-task` 等 | Command レジストリに登録された値のみ受理。それ以外は失敗 |
| `definition` | 必須 | リポジトリ相対パス | `prompts/definitions/` 配下に限定。実ファイル存在を検証 |
| `run_mode` | 必須 | `dry-run` / `live-run` | Command ごとに supported を参照。`start-epic` は `dry-run` のみ。`review-pr` は両方可 |
| `request_issue` | 任意 | 数値 | トレース相関キー。Job Summary 冒頭に表示するのみ（Issue へのコメント投稿はしない） |
| `target_pr` | 条件付き必須 | 数値 | **`review-pr` + `live-run` 時は必須**。post-run で dispatch 忘れ検証に使用 |
| `requested_by` | 任意 | 自由文字列 | 監査用識別子（Slack user / GitHub user 等）。Job Summary に表示。改行・長さ制限あり |

## 5. 処理フロー

```text
1. checkout
2. 入力検証 (Command レジストリ参照 / definition パス prefix / 実ファイル存在 / definition_type 整合 / run_mode==dry-run)
3. プロンプト組み立て (builder スクリプト呼び出し、secret マスク)
4. Cursor SDK で Cloud Agent 起動 (Agent.create + agent.send + cloud: { repos: [{ url, startingRef }] }, autoCreatePR: false)
5. **review-pr live-run のみ:** transcript から AI Review コメントを抽出し `GH_BOT_TOKEN` で `publish-ai-review-and-dispatch.cjs` を実行（bot fallback）
6. post-run 検証 (Issue / PR / Branch 新規作成監視 → 違反検知時は job 失敗)
7. Job Summary 出力 ($GITHUB_STEP_SUMMARY、secret スキャナ通過後)
```

各ステップは `::group::<step-name>` で折り畳み、冒頭に「決定的な1行」を出力する（例: `decision: validated allowed_command=start-epic`）。

## 6. 権限 / Secrets

| 種別 | 名前 | 用途 |
| ---- | ---- | ---- |
| permissions | `contents: read` | リポジトリ checkout |
| permissions | `issues: read` | post-verify で Issue 一覧取得 |
| permissions | `pull-requests: read` | post-verify で PR 一覧取得 |
| Secret | `CURSOR_API_KEY` | Cursor SDK の認証。workflow env のみで使用、プロンプト・log・Summary には絶対に出さない |
| Secret | `GH_BOT_TOKEN` | **`review-pr` + `live-run` 時**の `publish-ai-review-and-dispatch.cjs` bot fallback（Cloud Agent は PR コメント POST 不可） |
| Token | `GITHUB_TOKEN` | post-verify で gh API を叩く（read のみ。write 全廃） |
| permissions | `actions: read` | review-pr post-verify で workflow runs 参照 |

write 系権限は MVP 段階で **付与しない**。Cloud Agent が誤って書き込みを試みても物理的に成功しない構造とする。

## 7. framework と Command 固有要素の分離

横展開時に framework を改修しなくて済むよう、責務を分離する。

### 7.1 framework（全 Command 共通・1 箇所に集約）

- workflow 構造（トリガ / inputs / 権限 / concurrency / ステップ並び）
- 入力契約（`command` / `definition` / `run_mode` / `request_issue` / `requested_by`）
- 入力検証ロジック（許可リスト参照 / definition パス prefix / 実ファイル存在 / `definition_type` 整合）
- プロンプトテンプレート骨格（`${command}` / `${definition}` / `${run_mode}` を差し込む）
- Cursor SDK 呼び出し
- post-run 検証
- 結果整形・Job Summary
- Secrets 管理と secret マスク

### 7.2 Command 固有要素（Command レジストリ）

`.github/scripts/definition-run-prompt-builder.cjs` 内に **`COMMAND_REGISTRY`** として定義し、横展開はここへ行を足すだけにする。

```text
COMMAND_REGISTRY = {
  "start-epic": {
    definition_type: "epic",
    default_ref: "develop",
    dry_run_supported: true,
    live_run_supported: false,
    output_section: "dry-run 実行時",
  },
  // 横展開時はここに追記:
  // "start-task":  { definition_type: "task",  default_ref: "<parent epic branch>", ... },
  // "create-pr":   { definition_type: "task",  ... },
  // "review-pr":   { definition_type: "review", ... },
}
```

レジストリのキー:

| キー | 説明 |
| ---- | ---- |
| `definition_type` | Definition YAML の `definition_type` と一致すること（`epic` / `task` / `review` 等） |
| `default_ref` | Cloud Agent が clone する ref。dry-run はリポジトリ既定で可、live-run 時は要設計 |
| `dry_run_supported` | dry-run を許可するか |
| `live_run_supported` | live-run を許可するか（MVP は全て `false`） |
| `output_section` | `.cursor/commands/<command>.md` の dry-run 出力セクション名 |

## 8. プロンプト雛形

```text
このリポジトリで Definition Run を実行する。

遵守:
- AGENTS.md
- .cursor/rules/*.mdc
- .cursor/commands/${command}.md

実行コマンド: /${command}
対象Definition: @${definition}
run_mode: ${run_mode}

run_mode が dry-run の場合、Issue / Branch / Project / PR / Label / Definition への
あらゆる書き込みを行わない。gh CLI / git push / GitHub API の write 系操作は全面禁止。
Agent は `gh project item-edit` 等で Projects を直接更新せず、git push のみで Branch 運用状態を確定しない。
Issue 作成・更新後の同期は既存 workflow が行うため、Harness は同期処理を行わない。

結果は .cursor/commands/${command}.md の「${output_section}」セクションのフォーマットで出力する。
```

## 9. 出力戦略（Job Summary + Actions log のみ）

### 9.1 Job Summary（実行結果の表示先）

`$GITHUB_STEP_SUMMARY` に Markdown で書き出す。Actions 既定保持期間（90日）に従う。リポジトリには何も commit しない。

雛形:

```markdown
## Definition Run Result

| 項目 | 値 |
| ---- | ---- |
| status | finished / error |
| command | start-epic |
| definition | prompts/definitions/epics/.../epic.yaml |
| run_mode | dry-run |
| requested_by | <user> |
| request_issue | #<num> or - |

### IDs
- agent.id: ...
- run.id: ...
- Cursor dashboard: <link>
- Actions run: <link>

### Guard Violations (post-run)
- <空ならNone、違反ありなら検出内容と発生時刻・actor>

### Result (head 40 lines)
\`\`\`
<最終出力先頭40行>
... (truncated, see Actions log for full output)
\`\`\`

### Timings
- queued / started / finished / elapsed
```

### 9.2 Actions raw log（デバッグ・調査の底本）

- 全 Node 実行ステップを `::group::<step-name>` で囲み、折り畳み可能にする
- 各ステップ冒頭に「決定的な1行」を必ず出す（grep のため）
- Cloud Agent からのストリーミングイベント（assistant text / tool call / error）を `::group::cursor-stream` 配下に全文出力
- 例外時は `::error::` annotation を発火させ、run ページに目立たせる
- token / API key / secret らしき文字列は prompt builder 側で `***` に置換してから log / Summary へ出す
- `CURSOR_API_KEY` は workflow env で持つだけで、プロンプト本文・log・Summary には**絶対に入れない**

### 9.3 採用しないもの

| 採用しないもの | 理由 |
| -------------- | ---- |
| workflow artifact のアップロード | 容量・retention 管理の複雑さ回避 |
| Issue comment の自動投稿 | Issue 汚染回避（`request_issue` は Job Summary 表示のみ） |
| `ai-logs/` への自動 commit | リポジトリ汚染回避、incident 時は手動で対応 |

## 10. 影響局所化（標準ガード + post-run 検証）

### 10.1 標準ガード（実行前・実行中）

| 層 | 仕組み |
| --- | --- |
| (a) Cloud Agent VM 隔離 | Cursor 側の隔離 VM 上で clone 実行、`autoCreatePR: false` |
| (b) `GITHUB_TOKEN` 権限最小化 | read 系のみ。write 全廃 |
| (c) `CURSOR_API_KEY` 非露出 | Harness の env でのみ使用、プロンプトに含めない、log / Summary に出さない |
| (d) プロンプト禁止条項 | dry-run 時の Issue / Branch / PR / Label / Definition への書き込み全面禁止、`gh project item-edit` / `git push` 直接禁止、Harness は同期処理を行わない旨を明示 |
| (e) concurrency 制御 | 同一 Definition の二重起動を直列化 |
| (f) secret マスク | builder 側で出力前に既知パターン置換 |

### 10.2 post-run 検証（実行後・違反検知）

`.github/scripts/definition-run-post-verify.cjs` をステップ 5 で実行する。

検証内容:

1. ジョブ開始時刻を `started_at` として記録
2. Cloud Agent 完了後、`started_at` 以降に作成された Issue / PR / Branch の有無を gh API で確認
3. MVP（dry-run）の違反検知ルール:
   - dry-run なのに新規 Issue / PR / Branch が作成されていたら **違反**
   - 違反内容（種別・番号・URL・作成時刻・actor）を Job Summary の Guard Violations 欄に列挙
   - 検出時は `process.exit(1)` で job を失敗扱いにする
4. 違反がなければ `violations: []` を Job Summary に記録

### 10.3 Phase D（live-run 解禁）拡張時の許容ルール（将来）

policy（[Commands設計書](../../00_共通/AIエージェント運用/Commands設計書.md) §4 / §10）に従い、live-run でもエージェントが直接行ってよいのは **Issue 起票・更新のみ**。Projects 同期と Branch 作成は既存 workflow に委譲する。post-verify は actor を区別して以下のとおり判定する。

| 作成主体（actor） | 作成対象 | 判定 |
| --- | --- | --- |
| Definition Run の API キー（Cloud Agent） | Issue 起票（Definition で指定された Issue タイトル prefix と一致） | 許容 |
| 同上 | Project フィールド更新 | **違反**（既存 workflow に委譲すべき） |
| 同上 | Branch 作成 | **違反**（既存 workflow に委譲すべき） |
| 同上 | PR 作成 | **違反**（`/create-pr` と既存 workflow に委譲すべき） |
| `github-actions[bot]`（既存 workflow） | Issue 起票後の Project 同期 | 許容 |
| `github-actions[bot]`（既存 workflow） | Issue 本文 no-branch 解除後の Branch 作成 | 許容 |
| `github-actions[bot]`（既存 workflow） | PR 作成時の Status / Slack 同期 | 許容 |

MVP 段階ではこの actor 判別ロジックを **コメントだけ書いておき**、Phase D 解禁時に有効化する。

### 10.4 secret 漏えい対策

- `GITHUB_TOKEN` は最小権限（read のみ）
- `CURSOR_API_KEY` は Actions が既定でマスクするが、prompt builder でも一次マスクを通す
- 入力 `requested_by` 等の自由文字列も builder で長さ制限・改行除去
- Job Summary 出力直前に Markdown 全体を secret スキャナ（既知パターン正規表現）に通してから書き出す

## 11. dry-run / live-run の取り扱い（将来）

| run_mode | MVP の扱い | Phase D 以降の扱い |
| -------- | ---------- | ------------------ |
| `dry-run` | 受理。書き込み全面禁止 | 引き続き受理 |
| `live-run` | **必ず失敗**（許可リスト外） | Command レジストリの `live_run_supported: true` 化 + 権限・ref 設計 + GitHub Environments approval + post-verify の許容ルール更新を別 PR で行う |

## 12. 失敗・停止条件

以下の場合、job を失敗扱いにする。

- 必須入力（`command` / `definition` / `run_mode`）の欠落
- `command` が Command レジストリに存在しない
- `definition` が `prompts/definitions/` prefix 外
- `definition` の実ファイルが存在しない
- `definition` YAML の `definition_type` がレジストリ定義と一致しない
- `run_mode` がレジストリで supported でない（MVP は `live-run` 指定で失敗）
- Cursor SDK 呼び出しで `CursorAgentError` が thrown された（`error.isRetryable` を Summary に記録）
- Cursor SDK の `result.status === "error"`（run は実行されたが失敗）
- post-verify で違反が検出された
- secret スキャナで Summary 出力に既知の secret パターンが残っている

## 13. 既存 workflow 活用方針（policy 引用）

Definition Run Harness は、更新系処理を直接実装せず、既存 workflow に委譲する。以下は **policy の引用** であり、本仕様書で新規に決めるものではない。

### 13.1 引用元

- [Commands設計書](../../00_共通/AIエージェント運用/Commands設計書.md) §4: 「Commandは Issue の起票・更新を起点とし、Projects同期やBranch作成などの後続処理は GitHub Actions workflow（仕様書で定義されたハーネス）に委譲する」
- 同 §10「Command実行時の補足」:
  - Agent は `gh project item-edit` 等で Projects を直接更新しない
  - Agent は `git push` のみで Branch 運用状態を確定しない
  - Issue 作成・更新後の同期結果は workflow 実行結果を確認する
- [Issue運用ルール](../../00_共通/プロジェクト管理/Issue運用ルール.md) §10 / §10.1: Issue 運用メタデータ形式（`###` 見出し）と初回 / 継続同期の分離
- [Projects運用ルール](../../00_共通/プロジェクト管理/Projects運用ルール.md) §6.1: 識別子単位 Epic は完了ゲート工程として原則 `07_開発・単体テスト`

### 13.2 既存 workflow 責務マッピング

Definition Run Harness が live-run で Issue を起票した後、以下の既存 workflow が責務を引き継ぐ。Harness は自身では同期処理を行わない。

| 更新系処理 | 委譲先 workflow | エージェント側の責務 |
| --- | --- | --- |
| Issue メタデータ → Project 同期 | `.github/workflows/issue-metadata-project-branch.yml` | Issue 本文に Issue 運用メタデータを正しく埋めて作成のみ |
| Issue → Branch 作成 | 同上 | Issue 本文 no-branch チェックを正しく設定 |
| PR 作成時 Status / Slack | `.github/workflows/pr-created-status-and-slack.yml` | PR 作成のみ。**完了後** `dispatch-review-pr-harness.cjs` で Harness 自動起動 |
| fix 完了後 Status / Slack | `.github/workflows/pr-ready-for-ai-review.yml` | **`publish-fix-complete-and-dispatch.cjs` で dispatch**（Fixer 実行）。**完了後** Harness 自動起動 |
| PR レビュー → Status | `.github/workflows/pr-review-status-sync.yml` | **`publish-ai-review-and-dispatch.cjs` で dispatch**（Agent 実行）。Harness live-run 後は post-verify で dispatch 忘れを検証 |
| PR merge → Done / Slack | `.github/workflows/pr-merged-done-and-slack.yml` | merge は人間判断（AI 不可） |
| 手動 Slack 通知 | `.github/workflows/slack-notify-manual.yml` | 必要時に `workflow_dispatch` |

### 13.3 例外

- **Slack → Definition Run のトリガ部分**（Slack → `repository_dispatch` または Slack → Bridge → Actions）は本方針の対象外。新規 workflow / Bridge を新設してよい（Phase C）。
- ただし、トリガ後に Harness が起動した時点から本方針が再び適用される。
- live-run 解禁時（Phase D）も、エージェントが起票した Issue / PR に対する後続処理は既存 workflow に流す。

## 14. 横展開チェックリスト

新規 Command を本 framework に乗せる際は、以下のみ実施する。

1. `.github/scripts/definition-run-prompt-builder.cjs` の `COMMAND_REGISTRY` に行を追加
   - `definition_type`（`epic` / `task` / `review` のいずれか）
   - `default_ref`（dry-run はリポジトリ既定で可、live-run 時は要設計）
   - `dry_run_supported` / `live_run_supported`
   - `output_section`（`.cursor/commands/<command>.md` の dry-run 出力セクション名）
2. `.cursor/commands/<command>.md` に「外部実行時の条件」節を複製
3. テスト（`definition-run-prompt-builder.test.cjs`）に許可 Command ケースを追加
4. 本仕様書 §2 の Command 一覧 / §4 の許可値に追記
5. workflow 本体・post-verify スクリプトは **改修しない**（許可リストはレジストリ参照のため）

live-run を解禁する場合のみ、`live_run_supported: true` 化 + 権限・ref 設計 + 承認ゲート（GitHub Environments approval）+ post-verify の許容ルール更新を別 PR で行う。

## 15. 動作確認手順（MVP 受入）

1. `secrets.CURSOR_API_KEY` を設定
2. Actions UI から `workflow_dispatch` で次を実行
   - `command=start-epic`, `definition=prompts/definitions/epics/scr-002-recommendation-input/epic.yaml`, `run_mode=dry-run`
3. Job Summary に `.cursor/commands/start-epic.md` の「dry-run 実行時」フォーマット相当が出ること
4. Actions log に `::group::cursor-stream` 配下でストリーミングイベントが折り畳まれて出ること
5. Job Summary の Guard Violations 欄が `None` であること
6. dry-run 出力（生成予定 Issue 本文）が以下の policy に整合していること
   - **Issue 運用メタデータ形式**（`###` 見出し単位）で出力されている（[Issue運用ルール](../../00_共通/プロジェクト管理/Issue運用ルール.md) §10）
   - 識別子単位 Epic の場合、`project.fields.phase` が `07_開発・単体テスト`、Milestone が `開発・単体テスト工程完了` になっている（[Projects運用ルール](../../00_共通/プロジェクト管理/Projects運用ルール.md) §6.1、[.cursor/commands/start-epic.md](../../../.cursor/commands/start-epic.md) §7）
7. `command=start-task` を指定したジョブが **必ず失敗** すること（MVP 未対応）
8. `run_mode=live-run` を指定したジョブが **必ず失敗** すること
9. 不許可 Command（例: `merge-pr`）や不正パスが **必ず失敗** すること
10. post-run 検証の発火確認: dry-run プロンプトを意図的に外して試験 Issue を作る再現テストで、Guard Violations に検出され job が失敗すること（受入時に手動で1回）
11. `CURSOR_API_KEY` や類似 secret が Job Summary / Actions log に出ていないこと

## 16. 関連ドキュメント

| ドキュメント | 役割 |
| --- | --- |
| [Commands設計書](../../00_共通/AIエージェント運用/Commands設計書.md) | Command 仕様（Definition Run 通称・外部トリガ節を含む） |
| [Task Definition設計書](../../00_共通/AIエージェント運用/Task%20Definition設計書.md) | Definition 構造 |
| [.cursor/commands/start-epic.md](../../../.cursor/commands/start-epic.md) | start-epic の手順（dry-run 出力フォーマット含む） |
| [Issue運用ルール](../../00_共通/プロジェクト管理/Issue運用ルール.md) | Issue 運用メタデータ / 初回・継続同期 |
| [Projects運用ルール](../../00_共通/プロジェクト管理/Projects運用ルール.md) | Phase / Milestone（識別子単位 Epic） |
| [Slack通知運用設計書](../../00_共通/AIエージェント運用/Slack通知運用設計書.md) | Slack 通知方針 |
| [README.md](./README.md) | github_actions 仕様書一覧 |
