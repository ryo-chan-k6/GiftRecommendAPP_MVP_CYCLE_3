# Phase4a middleware scaffold

Phase4a `api-foundation`（A1）の middleware 骨格。validation / error / CORS の Express middleware 境界を定義する。

| サブディレクトリ | 責務（将来） |
| ---------------- | ------------ |
| `cors/` | `CORS_ALLOWED_ORIGINS` に基づく Origin 制御 |
| `error/` | `ApiError` と error handler（GRS 形式 Response） |
| `validation/` | Zod schema による body / query / params validation |

`request-meta.ts` は traceId / requestId を `res.locals.apiMeta` へ設定し、error handler の `meta` 生成に利用する。logger 連携は `logger-foundation` Task（A2）で拡張する。

正本ディレクトリ構成: `docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md` §6.3

## 登録順（推奨）

```text
requestMetaMiddleware
  ↓
createCorsMiddleware()
  ↓
routes / createValidationMiddleware(...)
  ↓
errorHandler   ← 必ず末尾
```

`registerFoundationMiddlewares` / `registerErrorMiddleware` を利用してもよい。

## 関連モジュール

- 共通 error response 組み立て: `apps/api/src/lib/error-response/`（A4）

## Phase4b 以降

- route 実装・認証 middleware は Phase4b 識別子 Epic で追加
