# Experiment: Layer2 system API E2E 有効化

| 項目 | 内容 |
| ---- | ---- |
| 日付 | 2026-07-17 |
| Epic | #1426 |
| Task | #1427 |
| 目的 | `test-system.yml` の既定を `skip_api_e2e=false` にし、health / PUB-002 系を GHA で検証する |

## 実施内容

1. `skip_api_e2e` 既定を `false` に変更
2. API E2E 有効時に `setup-uv` + `setup-python-reco.sh` を追加
3. health wait を最大約 3 分に延長
4. `tests/e2e/run-system-tests.sh` の既定 skip を `false` に変更
5. テスト定義書 §9.5.3 / Layer2 dispatch / テスト環境設計書を Phase4b 後方針に更新
6. Task branch へ push 後、`workflow_dispatch`（`skip_api_e2e=false`）で検証

## 結果（事実）

| 項目 | 値 |
| ---- | ---- |
| 検証状態 | **pending**（push 後に GHA run を記録する） |
| workflow | `Test System (Layer2)` / `test-system.yml` |
| 入力 | `skip_api_e2e=false` |
| run URL | （追記予定） |
| conclusion | （追記予定） |

## 次

- GHA run 完了後、本ログに artifact 要約（passed/failed/skipped / phase4bPending）を追記する
