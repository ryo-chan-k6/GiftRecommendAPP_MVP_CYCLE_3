# error middleware

Express error handler 骨格。Response 形式は OpenAPI `ErrorResponse` / エラーコード定義書 §5 に整合する。

| コンポーネント | 役割 |
| -------------- | ---- |
| `ApiError` | 業務・Validation エラーを middleware 境界へ伝播 |
| `errorHandler` | 未知エラーを `GRS-COM-999` へマスクし JSON を返却 |

Response 組み立ては `apps/api/src/lib/error-response/`（A4）の `buildErrorResponseBody` を利用する。

内部 stack trace / SQL / secret は Response へ返さない（API設計方針 §10）。
