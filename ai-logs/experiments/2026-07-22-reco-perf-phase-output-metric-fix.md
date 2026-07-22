# phase_output 計測定義修正（response_built 除外）実験ログ

## 概要

| 項目 | 内容 |
| ---- | ---- |
| Epic | #1544 |
| Task | #1545 |
| 日付 | 2026-07-22 |
| 目的 | `phase_output` / `reason` 合算から `response_built`（累積壁時計）を除外し、Reason 寄与を正しく測る |

## 変更要点

| 項目 | 旧 | 新（#1545） |
| ---- | -- | ----------- |
| `phase_output` 合算 | `result_generated` + `reason_generated` + `response_built` | `result_generated` + `reason_generated` |
| `response_built` | reason step に合算 | `scopes.response_built`（診断専用） |
| Reason 込み E2E | 外側 wall-clock | 変更なし |

## local mock 再計測

| 項目 | 値 |
| ---- | -- |
| 環境 | local（WSL2） |
| openai_mode | mock |
| iterations / warmup | 20 / 2 |
| success | 20 / 20 |
| 出力（git 未追跡） | `scripts/perf/output-metric-fix-mock/` |

| 指標 | 旧（Phase3 local mock） | 新 |
| ---- | ----------------------- | -- |
| phase_output p95 (ms) | 1,355.0 | **105.1** |
| response_built p95 (ms) | （合算内） | **1,233.2** |
| Reason E2E p95 (ms) | 2,089.2 | 1,234.0（定義変更なし・実行差） |
| Ranking まで p95 (ms) | 709.4 | 685.1 |

## 所見

- 新定義で `phase_output` が旧合算の約 1/13 になり、Reason/Output 寄与と累積壁時計を分離できた。
- 案 A（soft 3s / hard 7s）は旧合算根拠のため、見直し要否は Human 判断（断定しない）。
- secrets 再計測は本 Task では未実施（Human 判断・コスト）。
- secret 実値は成果物に含めない。

## 成果物

- `scripts/perf/reco_pipeline_bench.py`
- `scripts/perf/README.md`
- `docs/90_PoC/性能フィジビリティ/Reco性能フィジビリティ検証結果_Phase3_reason_e2e.md` §3.3.1 / §3.3.2
- `docs/90_PoC/性能フィジビリティ/設計反映メモ.md`
- `docs/06_実装設計/reco/MOD-RECO-001_Recommendation Orchestratorモジュール仕様書.md` §13.2.5
