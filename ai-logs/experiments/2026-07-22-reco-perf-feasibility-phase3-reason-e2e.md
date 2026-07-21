# Reco性能フィジビリティ Phase3 Reason 込み E2E 実測ログ

## 概要

| 項目 | 内容 |
| ---- | ---- |
| Epic | #1535 |
| Task | #1536 poc-reason-e2e-verification |
| モード | live（Reason 込み主対象） |
| 日付 | 2026-07-22 |

## local 実行

| 経路 | 結果 |
| ---- | ---- |
| mock（iterations=20, warmup=2） | Reason E2E p95≈2,089ms **Go** / Ranking まで p95≈709ms **Go** / phase_output p95≈1,355ms |
| secrets | 未実施（local API key がプレースホルダ） |

出力ディレクトリ（git 未追跡）: `scripts/perf/output-phase3-local-mock/`

## GHA 実行

| Run ID | モード | iterations | 結果 | URL |
| ------ | ------ | ---------- | ---- | --- |
| 29854691042 | live + secrets | 20 | success（Reason E2E **Block**） | [Actions](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/29854691042) |
| 29855026956 | live + mock | 20 | success（Reason E2E **Go**） | [Actions](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/29855026956) |

- workflow: `perf-feasibility-reco.yml`
- artifact: `reco-perf-bench-<run_id>`
- secrets: embedding_calls=22 / llm_calls=22。secret 実値は成果物になし

## 所見

- Phase3 主対象（Reason 込み）を 6s/8s 枠で判定すると GHA secrets は **Block**（p95≈12.5s）。支配要因は User Meaning + Reason。
- mock は Ranking まで・Reason 込みとも **Go**。
- `phase_output` 当面 500ms は非現実的。案: soft 3s / hard 7s（Human 未確定）。
- 同一 Branch 同時 dispatch は concurrency で cancel されるため逐次実行が必要。

## 成果物

- `docs/90_PoC/性能フィジビリティ/Reco性能フィジビリティ検証結果_Phase3_reason_e2e.md`
- `docs/90_PoC/性能フィジビリティ/設計反映メモ.md`（Phase3 追記）
