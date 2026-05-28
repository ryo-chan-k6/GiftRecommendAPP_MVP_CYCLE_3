# Experiment Log: Definition Run Harness MVP ローカル検証 + 受入手順

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-05-28-definition-run-harness-mvp-smoke` |
| Log 種別 | `experiments` |
| 件名 | Definition Run Harness MVP の MVP 実装に対するローカル健全性検証と GitHub Actions 上での手動受入手順の記録 |
| 記録日時 | 2026-05-28 13:18 JST |
| 対象 | `.github/workflows/definition-run.yml`、`.github/scripts/definition-run-prompt-builder.cjs`、`.github/scripts/definition-run-post-verify.cjs` |
| 関連 plan | `definition_run_harness_mvp_9fad2999.plan.md` |
| 関連設計書 | [Definition Run Harness ワークフロー仕様書](../../docs/06_実装設計/github_actions/Definition%20Run%20Harness%E3%83%AF%E3%83%BC%E3%82%AF%E3%83%95%E3%83%AD%E3%83%BC%E4%BB%95%E6%A7%98%E6%9B%B8.md) |
| 状態 | ローカル健全性検証=完了 / GitHub Actions 受入確認=人間実施待ち |

---

## 2. experiments として記録する理由

Definition Run Harness は MVP として 1 Command パターン（`/start-epic` dry-run）で framework を確立する試行である。  
`secrets.CURSOR_API_KEY` 未設定の段階でも framework 自体の妥当性をローカルで確認できる範囲を記録し、設定後の GitHub Actions 上での受入確認手順を明示する。

通常作業ログを `ai-logs/` に保存しない方針（[project-operation.mdc](../../.cursor/rules/project-operation.mdc) §3.2）に従い、本ログは framework 試行記録としてのみ保持する。

---

## 3. ローカル健全性検証（Harness PR merge 前に AI Agent が実施済み）

### 3.1 単体テスト

| テスト対象 | コマンド | 結果 |
| ---------- | -------- | ---- |
| `definition-run-prompt-builder.cjs` | `node --test .github/scripts/definition-run-prompt-builder.test.cjs` | 18 / 18 pass |
| `definition-run-post-verify.cjs` | `node --test .github/scripts/definition-run-post-verify.test.cjs` | 11 / 11 pass |
| 両者の同時実行 | `node --test .github/scripts/definition-run-prompt-builder.test.cjs .github/scripts/definition-run-post-verify.test.cjs` | 29 / 29 pass |

### 3.2 実 Definition での正常系・禁止系シナリオ

`buildDefinitionRunRequest` を実 Definition に対して直接呼び出した結果。

| シナリオ | 入力 | 期待 | 結果 |
| -------- | ---- | ---- | ---- |
| 正常系 | `start-epic` + `prompts/definitions/epics/scr-002-recommendation-input/epic.yaml` + `dry-run` | プロンプト生成成功・`definition_type=epic`・`output_section=dry-run 実行時` | ok |
| 禁止系: live-run | `start-epic` + 同 Definition + `live-run` | `run_mode_disabled` で失敗 | ok |
| 禁止系: 未許可 Command | `start-task` + `screen-spec.yaml` + `dry-run` | `unsupported_command` で失敗 | ok |
| 禁止系: 不正パス | `start-epic` + `docs/some.yaml` + `dry-run` | `invalid_definition_path` で失敗 | ok |
| 禁止系: 不在ファイル | `start-epic` + `prompts/definitions/epics/no-such/epic.yaml` + `dry-run` | `definition_not_found` で失敗 | ok |
| 禁止系: definition_type 不一致 | `start-epic` + Task Definition + `dry-run` | `definition_type_mismatch` で失敗 | ok |

### 3.3 ワークフロー YAML 構文

| 検証 | コマンド | 結果 |
| ---- | -------- | ---- |
| `.github/workflows/definition-run.yml` のパース | `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/definition-run.yml','r',encoding='utf-8'))"` | パース成功・`jobs.definition-run.steps` に 8 ステップを確認（Checkout / Setup Node / Resolve inputs / Validate inputs and build prompt / Install Cursor SDK / Invoke Cursor Cloud Agent / Post-run verification / Write Job Summary） |
| Lint | ReadLints による静的検査 | エラーなし |

### 3.4 確認した事実

- prompt builder は正常系で `dry-run 実行時` セクション参照を含むプロンプトを生成する。
- 禁止系 5 種すべてが期待どおりに `ValidationError` で停止する。
- post-verify は `dry-run` 時に Issue / PR / Branch 由来 actor を区別せずすべて違反扱いとし、`live-run` 時は `automation` を許容するロジックを実装済み（Phase D 解禁時に有効化）。
- `CURSOR_API_KEY` を要する Cursor SDK 呼び出し（`Invoke Cursor Cloud Agent`）はローカル検証対象外。

---

## 4. GitHub Actions 上で必要な手動受入手順

`secrets.CURSOR_API_KEY` 設定後、Repository owner / Maintainer が以下を実施する。  
正本手順は [Definition Run Harness ワークフロー仕様書](../../docs/06_実装設計/github_actions/Definition%20Run%20Harness%E3%83%AF%E3%83%BC%E3%82%AF%E3%83%95%E3%83%AD%E3%83%BC%E4%BB%95%E6%A7%98%E6%9B%B8.md) §15 を参照する。

### 4.1 事前準備

1. `secrets.CURSOR_API_KEY` を Repository Secret に設定
2. Definition Run Harness の workflow が `default branch` または `workflow_dispatch` 対象 branch に存在することを確認

### 4.2 正常系試験

| # | 操作 | 入力 | 合格基準 |
| - | ---- | ---- | -------- |
| 1 | Actions UI から `Definition Run Harness` を `workflow_dispatch` で実行 | `command=start-epic` / `definition=prompts/definitions/epics/scr-002-recommendation-input/epic.yaml` / `run_mode=dry-run` | job 成功 |
| 2 | Job Summary を確認 | - | `Definition Run Result` ヘッダと表が出ている。`status=finished`、`Guard Violations` 欄が `None` |
| 3 | dry-run 出力本文を確認 | - | [Issue運用ルール](../../docs/00_共通/プロジェクト管理/Issue運用ルール.md) §10 の `###` 見出し形式 |
| 4 | 識別子単位 Epic の既定値を確認 | - | `project.fields.phase=07_開発・単体テスト` / Milestone=`開発・単体テスト工程完了`（[Projects運用ルール](../../docs/00_共通/プロジェクト管理/Projects運用ルール.md) §6.1 と一致） |
| 5 | Actions log を確認 | - | `::group::cursor-stream` 配下でストリーミングイベントが折り畳まれている。`CURSOR_API_KEY` 実値が log / Summary に出ていない |

### 4.3 禁止系試験

| # | 操作 | 入力 | 合格基準 |
| - | ---- | ---- | -------- |
| 6 | `workflow_dispatch` で MVP 未対応 Command を指定 | `command=start-task` | job 失敗（`unsupported_command` log） |
| 7 | `workflow_dispatch` で `live-run` を指定 | `run_mode=live-run` | job 失敗（`run_mode_disabled` log） |
| 8 | `workflow_dispatch` で不正パスを指定 | `definition=docs/some.yaml` | job 失敗（`invalid_definition_path` log） |
| 9 | `workflow_dispatch` で存在しない definition を指定 | `definition=prompts/definitions/epics/no-such/epic.yaml` | job 失敗（`definition_not_found` log） |

### 4.4 post-run 検証の発火確認

| # | 操作 | 合格基準 |
| - | ---- | -------- |
| 10 | プロンプト禁止条項を意図的に外して dry-run を起こし、試験用 Issue を 1 件作る | post-verify が違反検知し job が失敗。Job Summary の `Guard Violations` 欄に試験 Issue が列挙される |
| 10b | 後始末 | 試験用 Issue は確認後に手動 close。`ai-logs/incidents/` への記録は不要（再現テストのため） |

### 4.5 横展開準備の確認

| # | 操作 | 合格基準 |
| - | ---- | -------- |
| 11 | `.github/scripts/definition-run-prompt-builder.cjs` の `COMMAND_REGISTRY` を確認 | `start-epic` のみ登録。横展開時はここに追記するだけで workflow / post-verify は改修不要であることを確認 |

---

## 5. 未確認事項

- `npm install --no-save @cursor/sdk` の網羅的な接続可能性（GitHub Actions runner 上のネットワーク制約）。ローカルでは npm registry への到達確認まで未実施。
- Cursor Cloud Agent から本リポジトリの clone 成功（`secrets.CURSOR_API_KEY` 設定後にのみ確認可）。
- ストリーミングイベントの実フォーマット（`assistant` 以外の event type の頻度）。実 SDK 呼び出し時のみ確認可。

---

## 6. リスク

- `@cursor/sdk` のバージョン固定をしていないため、minor バージョン上昇による破壊的変更を受ける可能性。MVP 後に `package.json` 化を検討。
- Cursor Cloud Agent VM が `gh` CLI による write 系操作を試行した場合、`GITHUB_TOKEN` 権限は read のみだが、Cloud Agent が独自に認証して書き込みを試みる可能性は post-verify で検知する設計。

---

## 7. 推奨対応

- §4.1〜§4.5 を Repository owner が 1 回通して実施する
- §4.4 (post-verify 発火確認) は受入時 1 回で十分。日常運用では実施しない
- 結果に問題があれば本ログを更新するか、`ai-logs/incidents/` に新規ログを起票する

---

## 8. 正本参照

| 種別 | 参照先 |
| ---- | ------ |
| 関連 plan | `definition_run_harness_mvp_9fad2999.plan.md` |
| 関連設計書 | [Definition Run Harness ワークフロー仕様書](../../docs/06_実装設計/github_actions/Definition%20Run%20Harness%E3%83%AF%E3%83%BC%E3%82%AF%E3%83%95%E3%83%AD%E3%83%BC%E4%BB%95%E6%A7%98%E6%9B%B8.md) |
| 関連 Command | [.cursor/commands/start-epic.md](../../.cursor/commands/start-epic.md) |
| 関連 policy | [Commands設計書](../../docs/00_共通/AIエージェント運用/Commands設計書.md) §4 / §10 / §29 |

---

## 9. 備考

- 本ログは MVP framework 試行記録であり、通常作業の詳細ログではない（[project-operation.mdc](../../.cursor/rules/project-operation.mdc) §3.2）。
- §4 の手動受入手順は設計書 §15 と同期している。設計書側の更新があった場合は本ログも更新する。
