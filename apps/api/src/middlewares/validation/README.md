# validation middleware

Zod schema による request validation 骨格。失敗時は `GRS-VAL-001` の `ApiError` を生成する。

| source | 対象 |
| ------ | ---- |
| `body` | JSON request body |
| `query` | query string |
| `params` | path parameter |

Phase4b 以降、OpenAPI schema との二重定義を避けるため route 単位で schema を共有する方針を検討する（本 Task では骨格のみ）。
