# infra/vercel/

Web アプリ（`apps/web`）の Vercel 向け設定を配置するディレクトリ。

## 参照

| ドキュメント | 内容 |
| ------------ | ---- |
| [基盤構成設計書 §5.1](../../docs/06_実装設計/cross_cutting/基盤構成設計書.md) | Web 基盤 |
| [環境設計書 §19.4](../../docs/06_実装設計/cross_cutting/環境設計書.md) | Web 環境変数 |
| [認証・認可方針書 §17.2](../../docs/05_アプリケーション設計/基盤/認証・認可方針書.md) | Web は server-side secret を保持しない |

## MVP（Task ③）

- `vercel.json` 等の deploy 設定は **未配置**（README のみ）
- client 公開可: `NEXT_PUBLIC_*` のみ（§19.4）
- Secret を `NEXT_PUBLIC_*` に含めない

## 主な Environment Variables（例）

| 変数 | 区分 | 備考 |
| ---- | ---- | ---- |
| `NEXT_PUBLIC_API_BASE_URL` | public-config | 必須 |
| `API_BASE_URL` | config | Server Component 用（ローカル `.env` 中心） |
