# cors middleware

`CORS_ALLOWED_ORIGINS`（環境設計書 §19.5、`.env.example` 既定 `http://localhost:3000`）を allowlist として扱う Phase4a 骨格。

- preflight (`OPTIONS`) は 204 で応答
- 許可 Origin のみ `Access-Control-Allow-Origin` を返す（`*` は使用しない）

Phase4b 以降、認証導入時は allowHeaders / credentials 方針を [認証・認可方針書](../../../../docs/05_アプリケーション設計/基盤/認証・認可方針書.md) に合わせて拡張する。
