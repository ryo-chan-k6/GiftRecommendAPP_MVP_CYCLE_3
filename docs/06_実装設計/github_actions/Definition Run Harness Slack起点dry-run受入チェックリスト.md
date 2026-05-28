# Definition Run Harness Slack起点dry-run受入チェックリスト

## 1. 目的

本チェックリストは、`start-epic` の `dry-run` を対象に、Slack 起点で Definition Run を実行する運用導線（Slack -> `repository_dispatch` -> `definition-run.yml` -> Cursor Cloud Agent）を受け入れるための手順を定義する。

本ドキュメントは「受入観点と判定基準」を定義する。Harness 本体の仕様は [Definition Run Harnessワークフロー仕様書](./Definition%20Run%20Harness%E3%83%AF%E3%83%BC%E3%82%AF%E3%83%95%E3%83%AD%E3%83%BC%E4%BB%95%E6%A7%98%E6%9B%B8.md) を正本とする。

## 2. 対象範囲

| 項目 | 範囲 |
| ---- | ---- |
| Command | `start-epic` のみ |
| run_mode | `dry-run` のみ |
| トリガ | Slack から `repository_dispatch` 発火 |
| 出力保管 | Job Summary + Actions log のみ |

以下は本チェックリストの対象外とする。

- `start-task` など他 Command の横展開
- `live-run` の許容運用
- Slack UI/UX の最終デザイン

## 3. 事前準備

### 3.1 必須設定

| 設定 | 値 | 確認方法 |
| ---- | ---- | ---- |
| Repository Secret | `CURSOR_API_KEY` | Actions 実行で `missing_cursor_api_key` が出ない |
| Workflow ファイル | `.github/workflows/definition-run.yml` | default branch に存在 |
| 入力 Definition | `prompts/definitions/epics/scr-002-recommendation-input/epic.yaml` | ファイル実在 |

### 3.2 Slack 側の最低入力契約

Slack 側の Bridge から `repository_dispatch` に渡す payload は次を最低限満たす。

```json
{
  "event_type": "definition-run",
  "client_payload": {
    "command": "start-epic",
    "definition": "prompts/definitions/epics/scr-002-recommendation-input/epic.yaml",
    "run_mode": "dry-run",
    "request_issue": "123",
    "requested_by": "slack:UXXXXXXX"
  }
}
```

## 4. 受入チェック（本番前）

### 4.1 正常系

| No | 観点 | 操作 | 合格基準 |
| --- | --- | --- | --- |
| N-1 | Slack 起点実行 | Slack から dry-run 実行指示を送る | `definition-run.yml` が起動する |
| N-2 | 入力検証 | `command=start-epic` / 実在 definition / `run_mode=dry-run` | `Validate inputs and build prompt` ステップが成功する |
| N-3 | Agent 実行 | Cloud Agent 呼び出し | `Invoke Cursor Cloud Agent` が `status=finished` で終了 |
| N-4 | Summary | Job Summary を確認 | `Definition Run Result` が出力される |
| N-5 | Guard | post-run 検証を確認 | `Guard Violations` が `None` |
| N-6 | 出力整合 | dry-run 出力本文を確認 | Issue 運用メタデータが `###` 見出し形式で出る |
| N-7 | Phase/Milestone 整合 | dry-run 出力本文を確認 | 識別子単位 Epic の既定（`07_開発・単体テスト` / `開発・単体テスト工程完了`）と整合 |

### 4.2 禁止系（必ず失敗すべき）

| No | 観点 | 入力例 | 合格基準 |
| --- | --- | --- | --- |
| F-1 | 未許可 Command | `command=start-task` | `unsupported_command` で失敗 |
| F-2 | 未許可 run_mode | `run_mode=live-run` | `run_mode_disabled` で失敗 |
| F-3 | 不正 path | `definition=docs/some.yaml` | `invalid_definition_path` で失敗 |
| F-4 | 不在 definition | `prompts/definitions/epics/no-such/epic.yaml` | `definition_not_found` で失敗 |
| F-5 | type 不一致 | task definition を `start-epic` に渡す | `definition_type_mismatch` で失敗 |

### 4.3 ガード発火試験（受入時 1 回）

| No | 観点 | 操作 | 合格基準 |
| --- | --- | --- | --- |
| G-1 | post-run 検知 | dry-run 制約を意図的に崩して試験 Issue を作る | `Guard Violations` に検出され、job が失敗する |
| G-2 | 監査情報 | Summary の違反一覧 | 種別・識別子・actor・時刻が確認できる |

試験用 Issue は確認後に手動で close する。

## 5. 監査観点（毎回確認）

| 観点 | 確認内容 |
| ---- | ---- |
| 秘密情報 | `CURSOR_API_KEY` などの実値が Job Summary / Actions log に出ていない |
| 決定ログ | 各ステップの `decision:` 行が出ている |
| ストリーム可読性 | `::group::cursor-stream` で折り畳み表示される |
| 追跡性 | Actions run URL から実行結果と失敗点を遡れる |

## 6. 障害時の一次切り分け

| 症状 | 主な原因候補 | 先に見る場所 |
| ---- | ---- | ---- |
| Workflow が起動しない | Slack -> `repository_dispatch` 連携不備 | Bridge 側ログ、GitHub repository_dispatch 呼び出しログ |
| validate で失敗 | payload 値不正、definition path/type 不一致 | `Validate inputs and build prompt` の `::error::validation_failed` |
| SDK 起動失敗 | `CURSOR_API_KEY` 不備、認可不足、ネットワーク | `Invoke Cursor Cloud Agent` の `cursor_agent_error` |
| Guard で失敗 | 禁止書き込みの発生 | `Post-run verification` と Summary の `Guard Violations` |

## 7. 受入完了条件

以下を満たした時点で「Slack 起点 dry-run 導線が固まった」と判定する。

1. 正常系 N-1〜N-7 が連続で合格
2. 禁止系 F-1〜F-5 がすべて期待どおり失敗
3. ガード発火試験 G-1〜G-2 が合格
4. 監査観点（秘密情報非露出、決定ログ、追跡性）に問題なし

## 8. 関連ドキュメント

| ドキュメント | 役割 |
| ---- | ---- |
| [Definition Run Harnessワークフロー仕様書](./Definition%20Run%20Harness%E3%83%AF%E3%83%BC%E3%82%AF%E3%83%95%E3%83%AD%E3%83%BC%E4%BB%95%E6%A7%98%E6%9B%B8.md) | Harness 本体仕様 |
| [Commands設計書](../../00_共通/AIエージェント運用/Commands設計書.md) | Definition Run 通称、外部トリガ原則、委譲方針（§4 / §10 / §29） |
| [Issue運用ルール](../../00_共通/プロジェクト管理/Issue運用ルール.md) | Issue 運用メタデータ形式（`###` 見出し） |
| [Projects運用ルール](../../00_共通/プロジェクト管理/Projects運用ルール.md) | 識別子単位 Epic の `phase` / Milestone 既定 |
