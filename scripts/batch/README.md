# scripts/batch/

Batch 手動実行・dry-run・再実行補助を配置するディレクトリ。

## 参照

| ドキュメント | 内容 |
| ------------ | ---- |
| [環境設計書 §19.7](../../docs/06_実装設計/cross_cutting/環境設計書.md) | Batch 環境変数 |
| [CI・CD方針書](../../docs/05_アプリケーション設計/共通/CI・CD方針書.md) | Batch は GitHub Actions 手動/定期実行を基本 |

## MVP（Task ③）

- README のみ
- 物理名正本: `RAKUTEN_APPLICATION_ID`, `OBJECT_STORAGE_*`（§19.7.1）

## ハーネス（明示 live のみ）

| スクリプト | 用途 |
| ---------- | ---- |
| `object_storage_live_verify.py` | Supabase Storage（S3 互換）put/get 疎通（#1617）。`--live-object-storage` 必須 |
| `rakuten_live_verify.py` | 楽天 API 疎通（E3）。親 Epic tip に存在する場合あり |

出力ディレクトリ `scripts/batch/output-*/` は Git 管理外。CI 既定 live は禁止。

## 配置予定（後続）

- ローカル dry-run 起動補助
- GitHub Actions workflow 連携メモ（Task ⑤）
