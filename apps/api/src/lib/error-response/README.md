# Phase4a common error response scaffold

Phase4a `api-foundation`（A4）の共通 error response 骨格。OpenAPI `ErrorResponse` / エラーコード定義書 §5 に整合する JSON 形式を組み立てる。

| ファイル | 責務 |
| -------- | ---- |
| `types.ts` | `ErrorResponseBody` / `ErrorDetail` / `RequestMeta` 型 |
| `constants.ts` | Phase4a 参照用 GRS コード・既定メッセージ |
| `build-error-response.ts` | `buildErrorResponseBody` formatter |

`middlewares/error/` は Express 境界（`ApiError` / `errorHandler`）を担い、Response 組み立ては本モジュールへ委譲する。内部 stack trace / SQL / secret は Response へ返さない（API設計方針 §10）。

正本ディレクトリ構成: `docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md` §6.3

## Phase4b 以降

- `packages/code-definitions` の error_code 定義と機械可読マッピングを接続する
- route / domain 層は本 formatter 経由で統一 Response を返す
