# Experiment: レーン1e Result Item Postgres 配線

| 項目 | 内容 |
| ---- | ---- |
| 日付 | 2026-07-15 |
| Issue | #1294 |
| Epic | #1293 |
| 目的 | recommendation_result / recommendation_result_item の Postgres INSERT 確認 |

## 実施内容

- `PostgresRecommendationResultRepository`（MOD-RECO-021）
- `PostgresRecommendationResultItemRepository`（MOD-RECO-022）
- `build_production_ports` への注入（DEFAULT InMemory 維持）

## 結果（事実）

| 項目 | 結果 |
| ---- | ---- |
| UT | composition + result repo UT 通過（9 passed） |
| PUB-002 | HTTP **200** |
| recommendation_result | INSERT 確認（generated） |
| recommendation_result_item | INSERT 確認（2 行、price snapshot 正し） |

## 補足

- 初回失敗: `matching_config_id` NOT NULL（migration `20260702120000`）を INSERT 未含み → 列追加で解消
- DB 上の `item_price_snapshot` は正しい。API 応答の `itemPrice: 0` は別経路の残観測

## 次（推論）

- API 応答 itemPrice マッピング
- NG concept 除外
- Reason 永続
