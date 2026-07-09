# infra/

ホスティング・外部基盤向けの設定配置ディレクトリ（正本: [プロジェクトディレクトリ構成定義書](../docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md) §13）。

## 目的

- Web / API / Reco / Batch の **デプロイ関連設定** を環境別に整理する
- [環境設計書 §19.9](../docs/06_実装設計/cross_cutting/環境設計書.md) の設定先マトリクスと対応づける
- secret 実値は **リポジトリに含めない**（ホスティング Secret / GitHub Actions Secrets 経由）

## MVP 方針（Task ③ / Human 判断 2026-06-07）

| 項目 | 方針 |
| ---- | ---- |
| 本ディレクトリ | **README + プレースホルダ** のみ |
| 本番 deploy 設定 | Task ③ scope 外（後続フェーズで追加） |
| 環境変数名 | 正本は [環境設計書 §19](../docs/06_実装設計/cross_cutting/環境設計書.md) / [`.env.example`](../.env.example) |

## サブディレクトリ

| パス | 対象 | 主な env（§19 参照） |
| ---- | ---- | -------------------- |
| [`render/`](./render/) | API ホスティング | `DATABASE_URL`, `REDIS_URL`, `RECO_*`, `CORS_*` 等 |
| [`vercel/`](./vercel/) | Web ホスティング | `NEXT_PUBLIC_*` |
| [`fly/`](./fly/) | Reco ホスティング | `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, `RECO_INTERNAL_API_KEY` |
| [`supabase/`](./supabase/) | Supabase 採用時（任意） | `SUPABASE_*`（△。Neon 直結時は不要） |

## 環境分離

dev / stg / prod で Secret・接続先を混在させない（[環境設計書 §7–§8](../docs/06_実装設計/cross_cutting/環境設計書.md)）。
