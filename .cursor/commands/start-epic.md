# start-epic

## 目的

`/start-epic` は、Epic Definition（`definition_type: epic`）をもとに、Epic 単位の作業管理を開始する Command である。

主に、AI が以下を一連の流れで進める場合に利用する。

- Epic Definition の確認
- 入力 docs・参照ファイルの確認
- Issue 化可否の判断
- Epic Issue 本文の生成（`prompts/templates/issue/epic-issue.md`）
- Epic Issue の作成
- GitHub Projects への追加
- Project フィールド同期
- Label 同期（`issue.*` と `project.fields.priority` から導出）
- no-branch 判定（Issue 本文チェックボックス）
- Epic Branch 作成（`branch.no_branch: false` の場合。base / PR target は `develop`）
- Status 更新意図の出力
- 配下 Task 起票の案内（`/start-task`）
- 必要に応じた Slack 通知サマリ作成

本 Command は、配下 Task の実装・Epic PR の merge までは行わない。子 Task は `/start-task`、実作業は `/work-issue` に引き継ぐ。

---

## 標準形式

```text
/start-epic @<definition>
```

例：

```text
/start-epic @prompts/definitions/_examples/epic-definition.example.yaml
```

実運用の配置例: `prompts/definitions/epics/scr-002-recommendation-input/epic.yaml`

Definition なしでの実行は原則禁止する。

---

## 主担当Agent

| 項目   | Agent           |
| ------ | --------------- |
| 主担当 | Orchestrator AI |
| 補助   | Support AI      |
| 後続   | （配下 Task は `/start-task` → Worker AI） |

---

## 参照する定義・Rules

必要に応じて以下を参照する。

- `AGENTS.md`
- `.cursor/agents/orchestrator-ai.md`
- `.cursor/agents/support-ai.md`
- `.cursor/rules/project-operation.mdc`
- `.cursor/rules/github-operation.mdc`（Epic / Task の Branch・PR target）
- `.cursor/rules/docs-consistency.mdc`
- `.cursor/rules/terminology.mdc`
- `.cursor/rules/security.mdc`
- `.cursor/rules/worktree.mdc`
- [Commands設計書](../../docs/00_共通/AIエージェント運用/Commands設計書.md) §13
- [Task Definition設計書](../../docs/00_共通/AIエージェント運用/Task%20Definition設計書.md) §9.1・§15・§17・§21・§22
- [Issue運用ルール](../../docs/00_共通/プロジェクト管理/Issue運用ルール.md)
- [ブランチ運用ルール](../../docs/00_共通/プロジェクト管理/ブランチ運用ルール.md)

---

## 入力

| 入力                | 必須 | 内容                                                                 |
| ------------------- | ---- | -------------------------------------------------------------------- |
| Epic Definition     | 必須 | `definition_type: epic`。`prompts/definitions/epics/<識別子スラッグ>/epic.yaml`（記入例: `_examples/epic-definition.example.yaml`） |
| 関連 docs           | 必須 | Definition の `input.docs`                                           |
| templates           | 必須 | `prompts/templates/issue/epic-issue.md`                              |
| GitHub Projects情報 | 推奨 | Project 追加・Status・Phase・予定日等の同期                          |

親 Epic の実在確認は不要（本 Command が親 Epic を作成する）。

---

## 処理手順

### 1. Epic Definition を読み込む

- `schema_version` / `definition_type: epic` を確認する
- `epic.id` / `epic.title` / `epic.summary`（Epic 識別・タイトル・概要）
- トップレベル `work_mode` と `branch.no_branch` の整合（Task Definition設計書 §16.2）
- `scope` / `out_of_scope` / `input` / `acceptance_criteria`
- `issue.unit`（`epic`）/ `issue.type` / `issue.area`
- `project.fields.*`
- `branch.base` / `branch.target`（Epic は原則 `develop`）
- `epic_scope.artifact_id` / `epic_scope.allowed_paths` / `epic_scope.forbidden_paths`
- `dependencies.epics`
- `parallel_control` / `human_decision_points` / `stop_conditions`

`definition_type` が `task` の場合は停止し、`/start-task` を案内する。

### 1.5 Epic タイトル規約・識別子の実在を検証する

Task Definition設計書 §15.0 / [成果物一覧×Task Definition化方針書](../../docs/00_共通/AIエージェント運用/成果物一覧×Task%20Definition化方針書.md) §3.5 を参照し、以下を順に確認する。

1. **形式チェック**: `epic.title` が `{識別子}:{概要}` 形式か（識別子付き Epic の場合）。形式違反は停止
2. **識別子 prefix の判定**: 先頭 prefix（`API-PUB-*` / `API-INT-*` / `SCR-*` / `BATCH-*` / `MOD-API-*` / `MOD-RECO-*` / `MOD-BATCH-*`）を取得
3. **識別子の実在 grep**: 正本一覧に対して以下を実行し、`未検出` の場合は停止
   - `API-PUB-*` / `API-INT-*`: `rg -F '{識別子}' docs/05_アプリケーション設計/アプリ/api/API一覧.md`
   - `SCR-*`: `rg -F '{識別子}' docs/05_アプリケーション設計/アプリ/web/画面一覧.md`
   - `BATCH-*`: `rg -F '{識別子}' docs/05_アプリケーション設計/アプリ/batch/バッチ処理一覧.md`
   - `MOD-API-*` / `MOD-BATCH-*`: `rg -F '{識別子}' docs/05_アプリケーション設計/アプリ/モジュール一覧.md`
   - `MOD-RECO-*`: `rg -F '{識別子}' docs/05_アプリケーション設計/アプリ/モジュール一覧.md docs/05_アプリケーション設計/アプリ/reco/Recoモジュール一覧.md`
4. **`epic_scope.artifact_id` 一致**: `epic.title` 先頭識別子と `epic_scope.artifact_id` が一致するか
5. **`epic_scope.allowed_paths` 必須**: 空配列・未記載の場合は停止
6. **`dependencies.epics` の確認**: API-PUB / API-INT / SCR Epic では明示されているか（空配列でも可、未記載は停止）

機能・領域単位 Epic（例外）の場合は、`epic_scope.artifact_id: ""` を許容し、Issue 本文にその旨を明記する。

### 2. schema 妥当性を確認する

`prompts/definitions/_schemas/epic-definition.schema.md` および Task Definition設計書 §9.1・§10（Epic 追加必須項目）に沿って必須項目を確認する。

### 3. 入力 docs の存在を確認する

必須 `input.docs` が存在しない場合は Issue 化前フィードバックを返す。

### 4. Branch / PR 方針を確認する

| 項目 | Epic の標準 |
| ---- | ----------- |
| Branch base | `develop` |
| PR target | `develop` |
| 配下 Task PR target | 本 Epic Branch |

`branch.no_branch` と `work_mode` が §17.2 と矛盾する場合は、`human_decision_points` に理由がなければ停止する。

### 5. Issue 化可能か判断する

- scope / out_of_scope が明確
- 子 Task 候補または管理範囲が整理されている（任意だが推奨）
- OpenAPI / generated の横断変更を Epic に混在させていない（必要なら Contract Task を別途）
- secret・権限の不明点がない

### 6. 不足がある場合は Issue 化前フィードバックを返す

形式は `start-task.md` の Issue 化前フィードバックと同様とする。記録先は `ai-logs/intake/`（`operation_logging` に従う）。

### 7. Epic Issue 本文を生成する

- テンプレート: `prompts/templates/issue/epic-issue.md`
- Issue タイトル: `[Epic]` + `epic.title`（**直後に半角スペースを入れない**。Task Definition設計書 §15.0）
- Issue 本文に GitHub Label 一覧は**含めない**（`unit` / `type` / `area` / `priority` は本文分類と workflow 導出）
- Issue 本文の `Planned Start` / `Due Date` は、Issue作成時点のJST日付で明示的に埋める。`project.fields.planned_start` / `project.fields.due_date` に `{{issue_created_date}}` / `{{issue_created_date+2d}}` が指定されている場合、またはAI主導Epicで未指定の場合、テンプレートへプレースホルダを残さず以下の解決後値を入れる。

| 項目 | 解決値 | 形式 |
| ---- | ------ | ---- |
| `project.fields.planned_start` | Issue作成日（JST） | `YYYY-MM-DD` |
| `project.fields.due_date` | Issue作成日（JST） + 2日 | `YYYY-MM-DD` |

明示的な日付がDefinitionに指定されている場合はその値を使用する。ただし、AI主導Epicで標準値と異なる場合は、チャット出力のProject同期項目に「Definition明示値」として根拠を残す。日付計算に失敗した場合はIssue作成前に停止し、未解決プレースホルダをIssue本文へ出力しない。

### 8. Epic Issue を作成する

dry-run 指定時は作成せず、dry-run実行日のJST日付をIssue作成予定日として `Planned Start` / `Due Date` を解決し、生成予定本文と同期項目をチャットに出力する。実作成時は実行日のJST日付で再計算する。

### 8.5 実Issue番号を関連Definitionへ反映する

Epic Issue 作成に成功した場合、AI Agent は GitHub が返した**実 Issue 番号**を関連 Definition へ反映する。`branch.no_branch: false` の場合は、§13 で Epic Branch 作成に成功した後、確定した Epic Branch 名もあわせて反映する。

反映してよい値は、以下で実在確認できたものに限定する。

| 値 | 確認方法 |
| ---- | -------- |
| Epic Issue 番号 | `gh issue view <番号>` または Issue 作成結果 URL |
| Epic Branch 名 | `git branch -a` または `git ls-remote --heads origin <branch>` |

反映対象は以下。

| 対象Definition | 反映項目 |
| -------------- | -------- |
| 配下 Task Definition | `parent.epic_issue_number` / `parent.epic_branch` |
| 本 Epic に依存する Task / Epic Definition | `dependencies.epics` |
| 必要に応じた Review Definition | `target.parent_epic_issue` / `target.parent_epic_branch` |

ガード条件:

- 実 Issue 番号を推測で記入しない。
- Issue タイトル検索で複数候補が出た場合は更新せず、人間確認へ回す。
- Epic Branch が未作成または未確認の場合、`parent.epic_branch` / `target.parent_epic_branch` は更新せず、人間確認へ回す。
- `dependencies.epics` に同じ Issue 番号を重複追加しない。
- 対象 Definition が特定できない場合は、チャットで「未反映項目」として明示する。
- dry-run では Definition を更新せず、反映予定の項目だけを出力する。
- `.env` 実値、token、secret を表示・保存しない。

### 9. Project へ追加する

### 10. Project フィールドを同期する

`project.fields` の更新意図を明示する。`planned_start` / `due_date` は §7 で解決した日付を同期対象とし、Issue本文・Project同期意図・dry-run出力で同じ値を使用する。成功時は `Todo` → `In Progress` へ進める意図を出す（Projects 正本は GitHub Projects）。

### 11. Label を同期する

付与予定は `unit` / `type` / `area` / `priority` の 4 種のみ。`no-branch` Label は付与しない（Issue運用ルール §15.1）。

### 12. no-branch を判定する

Issue 本文の no-branch チェックボックスに `branch.no_branch` を反映する。Branch 作成 workflow は**本文のチェックのみ**を参照する。

### 13. Epic Branch を作成する

`branch.no_branch: false` の場合:

- Branch 名は `issue.type` / `issue.unit` / Issue 番号 / `english-summary` から組み立て（ブランチ運用ルール）
- base / target は `develop`（Definition と一致すること）

`branch.no_branch: true` の場合は Branch 作成を行わない（人主導・未来着手 Epic）。

### 14. 後続作業を案内する

チャット出力に以下を含める。

- 作成した Epic Issue 番号・Epic Branch 名
- 配下 Task 起票: `/start-task @<task-definition>`（`parent.epic_issue_number` に**実番号**を反映した Task Definition を使用）
- Epic PR は配下 Task 完了後に `develop` 向け（本 Command では作成しない）

### 15. 必要に応じて Slack 通知を作成する

Slack通知運用設計書に従う。

---

## 出力

| 出力                    | 反映先                       |
| ----------------------- | ---------------------------- |
| Epic Issue 本文         | GitHub Issue                 |
| Project 同期項目        | GitHub Projects              |
| Label                   | GitHub Issue                 |
| Epic Branch             | Git Branch（`no_branch: false` 時） |
| 起票サマリ              | Slack / チャット             |
| Issue 化前フィードバック | チャット / `ai-logs/intake/` |

---

## 成功条件

- Epic Issue が作成されている
- Epic Issue が Project へ追加されている
- Project フィールドが同期意図どおり出力されている
- 必要な Label が付与されている（または付与予定が明示されている）
- `branch.no_branch: false` の場合、Epic Branch が `develop` から作成されている
- Branch base / PR target が `develop` であることが確認できる
- 配下 Task は `/start-task` で起票する旨が明示されている

---

## 失敗・停止条件

以下の場合は、Issue 作成前に停止する。

- Definition が存在しない、または `definition_type` が `epic` でない
- 必須項目・schema が不足している
- 入力 docs が存在しない
- scope / out_of_scope が曖昧
- 識別子付き Epic で `epic.title` が `{識別子}:{概要}` 形式でない
- `epic_scope.artifact_id` が正本一覧（API一覧 / 画面一覧 / バッチ処理一覧 / モジュール一覧 / Recoモジュール一覧）に**実在しない**
- `epic_scope.allowed_paths` が未記載または空配列
- `dependencies.epics` が API-PUB / API-INT / SCR Epic で未記載
- `work_mode` と `branch.no_branch` が §17.2 と矛盾し、`human_decision_points` に理由がない
- Branch base / target が Epic として `develop` でない（人間判断なしの例外を認めない）
- Issue本文の `Planned Start` / `Due Date` をJST日付へ解決できない、または `{{issue_created_date}}` / `{{issue_created_date+2d}}` が本文に残る
- 横断影響（OpenAPI / Orval / generated）を Epic に無断で混在させている
- secret や権限に関わる不明点がある

---

## やらないこと

- 子 Task Issue の作成（`/start-task` の責務）
- 成果物（docs / コード）の実装（`/work-issue` の責務）
- Task PR / Epic PR の作成（`/create-pr` の責務）
- PR merge 判断
- 親 Epic の実在確認（本 Command が親 Epic を新規作成する）

---

## 関連Command

| 後続 | 用途 |
| ---- | ---- |
| `/start-task` | 配下 Task の Issue / Branch 起票 |
| `/work-issue` | Task 実作業 |
| `/create-pr` | Task PR / Epic PR |
| `/review-pr` | PR レビュー |

正本: [Commands設計書](../../docs/00_共通/AIエージェント運用/Commands設計書.md)
