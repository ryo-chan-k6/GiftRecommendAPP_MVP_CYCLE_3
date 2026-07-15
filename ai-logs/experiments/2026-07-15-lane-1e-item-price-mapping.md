# Experiment: レーン1e itemPrice 応答マッピング

| 項目 | 内容 |
| ---- | ---- |
| 日付 | 2026-07-15 |
| Issue | #1301 |
| Epic | #1300 |
| 目的 | INT-002 / PUB-002 応答の `itemPrice` を Snapshot 価格と一致させる |

## 実施内容

- Snapshot executor: `version_info` に `item_price_snapshot` / `item_url_snapshot` を追記
- `response_mapper._map_result_item`: 上記キーを読み取り `itemPrice` / `itemUrl` へ反映
- UT: response mapping / snapshot smoke

## 結果（事実）

| 項目 | 結果 |
| ---- | ---- |
| UT | response mapping 8 passed / snapshot smoke 6 passed |
| PUB-002 | HTTP **200**、`itemPrice`=4320 / 4500（seed 一致）、`itemUrl` も Snapshot URL |

## 補足

- 欠落時は従来どおり `itemPrice=0` / stub URL（後方互換）
- OpenAPI / api / web / migration は変更なし
- スモークは Task worktree の reco を port 8000 で起動して実施

## 次（推論）

- NG concept 除外（item_003 alcohol）
- Reason 永続
- 親レーン Epic #1263 クローズ判断
