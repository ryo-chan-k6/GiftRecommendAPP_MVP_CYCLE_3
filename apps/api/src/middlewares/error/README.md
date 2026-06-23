# error middleware

Express error handler 骨格。Response 形式は OpenAPI `ErrorResponse` / エラーコード定義書 §5 に整合する。

| コンポーネント | 役割 |
| -------------- | ---- |
| `ApiError` | 業務・Validation エラーを middleware 境界へ伝播 |
| `errorHandler` | 未知エラーを `GRS-COM-999` へマスクし JSON を返却 |
| `buildErrorResponseBody` | Phase4a 暫定 formatter（A4 で lib 移管予定） |

内部 stack trace / SQL / secret は Response へ返さない（API設計方針 §10）。
