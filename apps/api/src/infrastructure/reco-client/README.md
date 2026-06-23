# Phase4a reco-client wrapper scaffold

Phase4a `api-foundation`（A5）の reco-client wrapper 骨格。Orval 生成物（`apps/api/src/generated/reco-client/`）を手編集せず、infrastructure 層で呼び出し境界と単体テスト可能な scaffold を定義する。

| ファイル | 責務 |
| -------- | ---- |
| `client.ts` | `RecoClient` 境界と `ScaffoldRecoClient` |
| `config.ts` | `RECO_BASE_URL` / `RECO_INTERNAL_API_KEY` 解決・URL 組み立て |
| `errors.ts` | infrastructure 層の `RecoError` |
| `types.ts` | Phase4a 参照用の request / response 型 |

Task Definition / Issue の `infrastructure/reco/**` は本ディレクトリ `infrastructure/reco-client/` を指す（正本: プロジェクトディレクトリ構成定義書 §7.2）。

## Phase4b 以降

- `getRecoHealth` / `runRecoRecommendation`（generated）を `RecoClient` 実装へ接続する
- `RECO_BASE_URL` を `buildRecoRequestUrl` 経由で fetch に適用する
- domain / route 層は本 wrapper 経由でのみ reco を呼び出す
