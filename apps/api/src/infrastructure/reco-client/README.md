# Phase4a reco-client wrapper scaffold

Phase4a `api-foundation`（A5）の reco-client wrapper 骨格。Orval 生成物（`apps/api/src/generated/reco-client/`）を手編集せず、infrastructure 層で呼び出し境界と単体テスト可能な scaffold を定義する。

| ファイル | 責務 |
| -------- | ---- |
| `client.ts` | `RecoClient` 境界、`ScaffoldRecoClient`、`GeneratedRecoClient` |
| `config.ts` | `RECO_BASE_URL` / `RECO_INTERNAL_API_KEY` / timeout 解決・Header 組み立て |
| `orval-mutator.ts` | Orval `recoFetch` mutator（base URL / 認証 / trace / timeout） |
| `transport.ts` | generated 関数（`getRecoHealth` / `runRecoRecommendation`）呼び出しと GRS-* エラー変換 |
| `mapper.ts` | generated schema ↔ infrastructure 型マッピング |
| `error-mapper.ts` | reco `GRS-*` / transport 失敗 → `RecoError` 変換 |
| `errors.ts` | infrastructure 層の `RecoError` |
| `types.ts` | wrapper request / response 型 |

Task Definition / Issue の `infrastructure/reco/**` は本ディレクトリ `infrastructure/reco-client/` を指す（正本: プロジェクトディレクトリ構成定義書 §7.2）。

## Phase1（API-INT-002 Orval NodeNext 整合）

- `internalRecoApi`（`orval.config.ts`）は `apps/api/tsconfig.orval.json`（NodeNext）と `recoFetch` mutator を利用する
- `GeneratedRecoClient` は generated endpoint 関数を `transport.ts` 経由で呼び出す
- `X-Internal-Api-Key` / `X-Trace-Id` / `X-Request-Id` は `orval-mutator.ts` → `buildRecoFetchInit` で付与する
- `apps/api/src/lib/reco-client/` の `createRecoClient` で DI / ファクトリを提供する
- domain / route 層は本 wrapper 経由でのみ reco を呼び出す
