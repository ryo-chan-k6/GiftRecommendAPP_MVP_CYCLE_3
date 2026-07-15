# Experiment: レーン1e alcohol NG 除外

| 項目 | 内容 |
| ---- | ---- |
| 日付 | 2026-07-15 |
| Issue | #1309 |
| Epic | #1308 |
| 目的 | `ngText: アルコールはNG` で seed item_003（ワイン）を候補から除外する |

## 実施内容

- Pre Hard Filter: ngText / attribute hard_filter から実効キーワード抽出（例: `アルコール`）
- InMemory: item_name / item_caption 照合を Postgres ILIKE に揃える
- UT / 手順書 §10.4.12

## 結果（事実）

| 項目 | 結果 |
| ---- | ---- |
| UT | candidate-retriever 30 passed（pre_hard_filter 12） |
| PUB-002 | HTTP **200**、resultItemCount=1、item_003 除外・item_001 のみ |

## 補足

- 現行 OpenAPI `NgCondition` は `ngText` のみ。MOD-RECO-012 の api 正本化は後続
- PostFilter の `alcohol_ng` / `ng_candidate` は本線にしない（Hard Filter 正本）

## 次（推論）

- OpenAPI/api での `ngKeywords` 正規化正本化
- 親レーン Epic #1263 クローズ判断
