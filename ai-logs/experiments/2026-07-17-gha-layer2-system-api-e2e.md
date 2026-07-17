# Experiment: Layer2 system API E2E 有効化

| 項目 | 内容 |
| ---- | ---- |
| 日付 | 2026-07-17 |
| Epic | #1426 |
| Task | #1427 |
| PR | #1429 |
| 目的 | `test-system.yml` の既定を `skip_api_e2e=false` にし、health / PUB-002 系を GHA で検証する |

## 実施内容

1. `skip_api_e2e` 既定を `false` に変更
2. API E2E 有効時に `setup-uv` + `setup-python-reco.sh` を追加
3. health wait を最大約 3 分に延長
4. `redis-tools` 導入、失敗時の response / runtime log artifact 追加
5. api/reco 起動前に `.env` を `source`（`DATABASE_URL` 未注入が PUB-002 500 の主因だった）
6. `setup-uv` の cache を無効化（Post Install uv 失敗回避）
7. docs（テスト定義書 §9.5.3 / Layer2 dispatch / テスト環境設計書）を Phase4b 後方針に更新

## 結果（事実）

| 項目 | 値 |
| ---- | ---- |
| 検証 run（E2E pass 確認） | https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/29586379823 |
| E2E cases | **passed=7 / failed=0 / skipped=0** |
| `phase4bPending` | `false` |
| `skipApiE2e` | `false` |
| job conclusion（当該 run） | `failure`（原因は **Post Install uv** のみ。E2E step は success） |

### Case results（run 29586379823）

| id | status |
| ---- | ---- |
| fixture-manifest | passed |
| db-connectivity | passed |
| db-test-seed | passed |
| redis-connectivity | passed |
| api-health | passed |
| reco-health | passed |
| recommendation-run | passed（HTTP 200） |

### 失敗経緯（事実）

| run | 結果 | 備考 |
| ---- | ---- | ---- |
| 29585680448 | fail | redis-cli 未導入 + PUB-002 500 |
| 29586026057 | fail | redis pass。PUB-002 500 `GRS-REC-002`（api に `DATABASE_URL` 未注入） |
| 29586379823 | E2E pass / job fail | `.env` source 後に recommendation-run pass。Post Install uv で job failure |

## 次

- `enable-cache: false` 反映後に再 dispatch し、job conclusion=success を確認する
