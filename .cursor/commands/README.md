# `.cursor/commands` 使い方

このディレクトリは、Cursor 上で AI Agent に依頼する **Command（作業手順）** の正本です。

人間は自然文だけでなく、次の形式で依頼します。

```text
/<command名> @<Task Definition または Review Definition のパス>
```

Command は「何をするか」、Definition は「何を対象に、どこまで、どの条件で行うか」を定義します。

---

## 1. クイックスタート

### 1.1 Cursor での呼び出し方

1. Cursor のチャット（Agent モード）を開く
2. 入力欄に Command と Definition を記載する
3. 送信する

```text
/start-task @prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml
```

`@` の後は、リポジトリ内の Definition ファイルパスを指定します（相対パスまたは絶対パス）。

### 1.2 Definition なし実行について

**原則禁止**です。作業対象・scope・完了条件が Definition に書かれている必要があります。

例外として、PR 番号などで対象が一意に特定できる Command は、補助引数を併記できます（例: `/review-pr`）。

```text
/review-pr @prompts/definitions/_examples/review-definition.example.yaml #123
```

### 1.3 最初に読むドキュメント

| 順序 | ドキュメント | 用途 |
| ---- | ------------ | ---- |
| 1 | [AGENTS.md](../../AGENTS.md) | リポジトリ全体の AI 運用入口 |
| 2 | [Commands設計書.md](../../docs/00_共通/AIエージェント運用/Commands設計書.md) | Command 設計の正本 |
| 3 | 各 Command の `.md`（本ディレクトリ） | 実行手順の詳細 |
| 4 | `prompts/definitions/**` | 個別 Task / Review の条件 |

---

## 2. Command 一覧

| Command | ファイル | 主担当 Agent | 主な用途 |
| ------- | -------- | ------------ | -------- |
| `/start-epic` | [start-epic.md](./start-epic.md) | Orchestrator AI | Epic 開始（Epic Issue 作成・Project 同期・Epic Branch 作成） |
| `/start-task` | [start-task.md](./start-task.md) | Orchestrator AI | Task 開始（Issue 作成・Project 同期・Branch 作成・引き継ぎ） |
| `/work-issue` | [work-issue.md](./work-issue.md) | Worker AI | 実作業（docs / コード / テスト等） |
| `/create-pr` | [create-pr.md](./create-pr.md) | Worker AI | PR 作成 |
| `/review-pr` | [review-pr.md](./review-pr.md) | Reviewer AI | PR の AI Review |
| `/fix-review-comments` | [fix-review-comments.md](./fix-review-comments.md) | Fixer AI | レビュー指摘の修正 |
| `/create-contract-task` | [create-contract-task.md](./create-contract-task.md) | Orchestrator AI / Contract AI | API 契約変更の専用 Task 起票 |
| `/summarize-work` | [summarize-work.md](./summarize-work.md) | Support AI 等 | 作業・レビュー結果の要約（Slack / PR 追記等） |

各ファイルの先頭に、目的・標準形式・処理手順・停止条件が記載されています。**実行時は該当 Command ファイルを Agent が参照します。**

---

## 3. 標準ワークフロー

### 3.1 AI 主導タスク（典型）

```text
/start-epic @<epic-definition.yaml>   # 親 Epic 未作成時
  ↓
/start-task @<task-definition.yaml>
  ↓
/work-issue @<task-definition.yaml>
  ↓
/create-pr @<task-definition.yaml>
  ↓
/review-pr @<review-definition.yaml> [#<pr番号>]
  ↓（修正が必要な場合）
/fix-review-comments @<task-definition.yaml> [#<pr番号>]
  ↓
/review-pr（再実行）
  ↓
Human Review → 人間による merge 判断
```

- `/start-task` は **実装そのものは行いません**（Issue・Branch・引き継ぎまで）。
- merge は **人間のみ**が行います（AI は merge 判断しません）。

### 3.2 人主導タスク（典型）

```text
人間が Issue 作成（原則 no-branch）
  ↓
着手タイミングで Branch 作成
  ↓
/work-issue @<task-definition.yaml>
  ↓
/create-pr → /review-pr → Human Review
```

### 3.3 契約変更が必要になったとき

通常 Task の途中で OpenAPI / Orval / generated の変更が必要になった場合は、本流に混ぜず分離します。

```text
/create-contract-task @<contract-definition.yaml>
  ↓
/work-issue → /create-pr → /review-pr
```

---

## 4. Command ごとの使い分け

### `/start-epic`

**いつ使うか**

- 新しい Epic（親 Issue + Epic Branch）を AI 主導で起票するとき
- 配下 Task の `parent.epic_*` に載せる親 Epic がまだないとき

**やること（概要）**

- Epic Definition（`definition_type: epic`）の妥当性確認
- Epic Issue 本文生成・作成
- Project 同期、Label 同期
- Epic Branch 作成（`branch.no_branch: false`、base/target は `develop`）
- 配下 Task は `/start-task` へ案内

**やらないこと**

- 子 Task Issue の作成、実装作業、Epic PR の merge

詳細: [start-epic.md](./start-epic.md)

---

### `/start-task`

**いつ使うか**

- 新しい AI 主導 Task を始めるとき
- Task Definition はあるが、まだ Issue / Branch がないとき

**やること（概要）**

- Task Definition・入力 docs の妥当性確認
- Issue 本文生成・Issue 作成（dry-run 指定時は未実施）
- Project 追加・フィールド同期の**更新意図**出力
- Label 同期（`issue.*` と `project.fields.priority` から導出）
- Branch 作成（`no-branch: false` の場合）
- Worker AI への引き継ぎ情報整理

**やらないこと**

- docs / コードの実装
- PR merge

詳細: [start-task.md](./start-task.md)

---

### `/work-issue`

**いつ使うか**

- Issue と Branch が既にある
- Definition の scope 内で成果物を作る・直す

**やること（概要）**

- scope 内の `docs/`・ソース・テスト等の作成・修正
- 完了条件・テスト方針に沿った検証

**やらないこと**

- Issue 新規作成（未作成なら `/start-task` へ）

詳細: [work-issue.md](./work-issue.md)

---

### `/create-pr`

**いつ使うか**

- 作業 Branch の変更が完了条件を満たした
- AI Review に進めたい

**やること（概要）**

- PR 本文テンプレートに沿った整理
- `gh pr create` 等による PR 作成（依頼時）
- Task PR は親 Epic Branch を target とする

詳細: [create-pr.md](./create-pr.md)

---

### `/review-pr`

**いつ使うか**

- PR 作成後、Human Review の前

**やること（概要）**

- Issue / Definition / PR 差分 / docs / テストの整合確認
- 結論: `Human Reviewへ進行可` / `修正後に再AI Review` / `Human判断待ち`

**やらないこと**

- 指摘内容の修正（→ `/fix-review-comments`）

Definition は **Review Definition**（`prompts/definitions/reviews/**`）を指定します。

詳細: [review-pr.md](./review-pr.md)

---

### `/fix-review-comments`

**いつ使うか**

- AI Review または Human Review で修正依頼があった

**やること（概要）**

- 同一 Branch 上で指摘対応
- 再レビュー前提の報告

詳細: [fix-review-comments.md](./fix-review-comments.md)

---

### `/create-contract-task`

**いつ使うか**

- OpenAPI / Orval / generated / API client に横断影響がある
- 通常 Task に契約変更を混在させたくない

詳細: [create-contract-task.md](./create-contract-task.md)

---

### `/summarize-work`

**いつ使うか**

- Slack 通知用サマリが欲しい
- PR / Issue 追記用の要約が欲しい
- 作業完了報告・判断依頼の整理

**やらないこと**

- 実装・docs 修正そのもの

詳細: [summarize-work.md](./summarize-work.md)

---

## 5. Definition の指定方法

### 5.1 Task Definition

```text
prompts/definitions/tasks/<識別子スラッグ>/<作業種別>.yaml
```

例:

```text
prompts/definitions/tasks/scr-002-recommendation-input/screen-spec.yaml
prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml
```

正本: [Task Definition設計書.md](../../docs/00_共通/AIエージェント運用/Task Definition設計書.md)、[Prompts運用ルール.md](../../docs/00_共通/AIエージェント運用/Prompts運用ルール.md)

### 5.2 Review Definition

```text
prompts/definitions/reviews/<識別子スラッグ>/pr-review.yaml
```

`/review-pr` で使用します。記入例は `prompts/definitions/_examples/review-definition.example.yaml`（`reviews/` 配下の実運用ファイルは識別子スラッグ単位で今後配置する）。

### 5.3 Contract Definition

```text
prompts/definitions/cross-cutting/**/contract-task.yaml
```

`/create-contract-task` で使用します。

---

## 6. Projects Status との関係

Command 実行後の Status 更新は、**GitHub Actions または運用スクリプト**が行います。Command は主に**更新意図**を出力します。

| Command | 主な Status 影響（意図） |
| ------- | ------------------------ |
| `/start-epic` | `Todo` → `In Progress`（Epic Branch 作成後） |
| `/start-task` | `Todo` → `In Progress` |
| `/work-issue` | `In Progress` 維持 |
| `/create-pr` | `In Progress` → `AI Review` |
| `/review-pr` | `AI Review` → `Human Review`（または差戻し） |
| `/fix-review-comments` | 差戻し後 → 再 `AI Review` |

正本: [Projects運用ルール.md](../../docs/00_共通/プロジェクト管理/Projects運用ルール.md)

---

## 7. 共通ルール（要約）

Command 実行時、AI Agent は以下を守ります（詳細は `.cursor/rules/`）。

| 項目 | 内容 |
| ---- | ---- |
| 正本 | 作業計画=Issue、レビュー=PR、成果物=`docs/` |
| scope | Task Definition の `scope` / `out_of_scope` を超えない |
| Branch | Task PR は親 Epic Branch 向け（`develop` 直 PR 禁止） |
| generated | 手動編集しない |
| secret | 出力・commit しない |
| merge | AI は行わない（人間判断） |
| Label 出力 | `/start-task` のサマリは `unit` / `type` / `area` / `priority` のみ（`ai-agent` 等は出さない） |

---

## 8. よくある依頼例

```text
# 新規 Task 開始（dry-run の指示をチャットに書く場合）
/start-task @prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml
（※チャットで「dry-run」「Issue/Branch 作成はしない」と明示）

# 実装作業
/work-issue @prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml

# PR 作成
/create-pr @prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml

# AI Review
/review-pr @prompts/definitions/_examples/review-definition.example.yaml #456

# 指摘修正
/fix-review-comments @prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-spec.yaml #456
```

---

## 9. トラブルシューティング

| 症状 | 確認・対応 |
| ---- | ---------- |
| Agent が scope 外を編集する | Definition の `scope` / `out_of_scope` を確認。チャットで scope を再指定 |
| Branch が作られない | §5.1 の実在確認結果（`存在`/`未検出`/`未確認`）。未検出時は `/start-epic` または `parent.epic_issue_number` を実番号へ更新（`start-epic.md` / `start-task.md` §5.1） |
| Label が想定と違う | Issue 本文 §12（`issue.unit` / `type` / `area`）と `project.fields.priority` を確認 |
| PR target が `develop` になる | Task か Epic か、Branch 運用ルールを確認 |
| OpenAPI 変更が必要と出た | 通常 Task を止め、`/create-contract-task` を検討 |
| Command が見つからない | ファイル名は kebab-case。呼び出しは `/start-task` のように先頭 `/` 付き |

---

## 10. 関連リンク

| 種別 | パス |
| ---- | ---- |
| Command 設計正本 | [docs/00_共通/AIエージェント運用/Commands設計書.md](../../docs/00_共通/AIエージェント運用/Commands設計書.md) |
| Agent 責務 | [.cursor/agents/](../agents/) |
| 共通 Rule | [.cursor/rules/](../rules/) |
| Task Definition | [prompts/definitions/](../../prompts/definitions/) |
| テンプレート | [prompts/templates/](../../prompts/templates/) |
| Issue / Branch / PR 運用 | [Issue運用ルール.md](../../docs/00_共通/プロジェクト管理/Issue運用ルール.md)、[ブランチ運用ルール.md](../../docs/00_共通/プロジェクト管理/ブランチ運用ルール.md) |

---

## 11. この README の位置づけ

| ドキュメント | 役割 |
| ------------ | ---- |
| 本 README | **使い方の入口**（一覧・フロー・依頼例） |
| `Commands設計書.md` | 設計・責務・Status 連携の正本 |
| 各 `*.md` Command ファイル | 実行手順の詳細正本 |

設計変更は `Commands設計書.md` と Issue / PR で管理し、本 README は利用者向けに追随して更新します。
