# Experiment: Reco性能フィジビリティ Phase2 live（#1513）

| 項目 | 内容 |
| ---- | ---- |
| 日付 | 2026-07-21 |
| Issue | #1513 / Epic #1512 |
| 目的 | live 実性能（ephemeral DB + OpenAI secrets）計測と Go/Adjust/Block 整理 |
| 正本結果 | `docs/90_PoC/性能フィジビリティ/Reco性能フィジビリティ検証結果_Phase2_live.md` |

## GHA runs

| Run | モード | 結論（要約） |
| --- | ------ | ------------ |
| [29829674333](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/29829674333) | live + secrets | TV-007 p95≈4529ms → Block |
| [29830051761](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/29830051761) | live + mock | TV-007 p95≈451ms → Go |
| [29829993205](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/actions/runs/29829993205) | skeleton | p95≈0.001ms（参考） |

## local（Docker 再実施）

| モード | 結果 |
| ------ | ---- |
| live + mock | TV-007 p95≈696ms → Go（success 20/20） |
| live + secrets | API key プレースホルダで 401。性能判定対象外（GHA secrets を正） |

secret 実値は本ログに記載しない。
