# tests/fixtures/

Layer2 システムテスト・レコメンド品質評価（Epic C C2）向け fixture 正本。

## 索引

`manifest.json` が C3/C4 workflow から参照するパス・固定 ID を定義する。

## ディレクトリ

| パス | 内容 |
| ---- | ---- |
| `api-input/` | Recommendation Run 入力（Public / Reco API 整合） |
| `external-api/rakuten/` | 楽天 API レスポンス mock |
| `external-api/openai/` | OpenAI Embedding / Chat Completion mock |
| `evaluation/` | レコメンド品質評価の固定ケース |
| `errors/` | 異常系・境界値リクエスト |

## DB 連携

商品 fixture ID（論理名 `item_001` 等）と DB UUID の対応は `manifest.json` の `items` を正とする。
test seed SQL は `supabase/seeds/test-data/` に配置し、`scripts/db/seed-test-data.sh` で master seed 適用後に投入する。

## OpenAI mock

Layer2 では **原則 fixture mock** を使用する。`workflow_dispatch` で実 API が必要な場合のみ GHA Secrets 注入（詳細はテスト定義書 §8.1）。
