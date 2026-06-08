# infra/supabase/

Supabase を採用する場合の設定を配置するディレクトリ。

## 参照

| ドキュメント | 内容 |
| ------------ | ---- |
| [環境設計書 §19.5 / §19.7](../../docs/06_実装設計/cross_cutting/環境設計書.md) | `SUPABASE_*`（△） |
| [基盤構成設計書 §10.1](../../docs/06_実装設計/cross_cutting/基盤構成設計書.md) | MVP は PostgreSQL (Neon) 想定 |

## MVP（Task ③）

- Neon 直結時は `DATABASE_URL` のみで可。本ディレクトリは **プレースホルダ**
- `SUPABASE_SERVICE_ROLE_KEY` は web へ公開禁止
- MVP では web から Supabase 直結しない（`.env.example` に `SUPABASE_ANON_KEY` なし）

## 配置予定（後続）

- Supabase プロジェクト設定の参照メモ（secret 実値は含めない）
- 採用判断後の migration / seed 連携手順へのリンク
