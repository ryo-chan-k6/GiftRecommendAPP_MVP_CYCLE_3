# Experiment: レーン1e 候補 Retrieval Postgres 配線

| 項目 | 内容 |
| ---- | ---- |
| 日付 | 2026-07-15 |
| Issue | #1278 |
| Epic | #1277 |
| 目的 | GRS-REC-012（ranked_items / item not found）解消と items≥1 確認 |

## 実施内容

- `PostgresItemRepository`（MOD-RECO-012）
- `PostgresPostFilterItemRepository`（MOD-RECO-013）
- `PostgresItemFeatureRepository` / `PostgresFeatureNormalizationRepository`（MOD-RECO-014）
- `PostgresItemSnapshotReadRepository`（MOD-RECO-022 ItemSnapshotReadPort）
- `build_production_ports` への注入
- test-data `item_semantic` seed 補完

## 結果（事実）

| 項目 | 結果 |
| ---- | ---- |
| UT | composition + catalog repo UT 通過（11 passed） |
| PUB-002 | HTTP **200** |
| resultItemCount | **2**（items≥1） |
| 旧 GRS-REC-012（ranked_items / item not found） | 解消 |
| recommendation_result_item Postgres INSERT | 未実施（InMemory） |

## 補足

- Snapshot 読取未配線時は seed UUID 候補到達後に `item not found` で GRS-REC-012 となっていた
- 応答の `itemPrice: 0` と alcohol NG 候補（item_003）返却は残観測（本 Task では items≥1 を完了条件とする）

## 次 Blocker / 後続（推論）

- `recommendation_result_item` Postgres 永続
- NG concept 除外の精査
- itemPrice 応答マッピング確認
