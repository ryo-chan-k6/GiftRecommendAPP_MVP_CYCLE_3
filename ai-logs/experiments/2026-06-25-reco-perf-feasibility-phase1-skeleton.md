# Reco性能フィジビリティ Phase1 skeleton 実測ログ

## 概要

| 項目 | 内容 |
| ---- | ---- |
| Epic | #759 |
| Task | #763 poc-report |
| モード | skeleton |
| 日付 | 2026-06-25 |

## local 実行

- コマンド: `reco_pipeline_bench.py --mode skeleton --iterations 100 --warmup 5`
- 出力: `scripts/perf/output-phase1-report/`（git 未追跡）
- `tv007_total` p95: **0.001ms**（sub-ms）

## GHA 実行

| Run ID | トリガ | iterations | 結果 |
| ------ | ------ | ---------- | ---- |
| 28147486256 | push | 50 | success |
| 28147511559 | workflow_dispatch | 10 | success |

- workflow: `perf-feasibility-reco.yml`
- artifact: `reco-perf-bench-<run_id>`

## 所見

- skeleton は scaffold 下限参考。本処理（DB / pgvector / AI）未計測。
- Phase1 暫定判定は試算ベース Go候補。最終判定は Phase2 live 後。

## 成果物

- `docs/90_PoC/性能フィジビリティ/Reco性能フィジビリティ検証結果_Phase1.md`
- `docs/90_PoC/性能フィジビリティ/設計反映メモ.md`
