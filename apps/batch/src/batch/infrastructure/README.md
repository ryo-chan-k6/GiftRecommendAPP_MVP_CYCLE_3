# Phase4a infrastructure scaffold

Phase4a `batch-foundation` の infrastructure 骨格。外部 API・DB・Object Storage・外部 AI・logger の技術境界を配置する。

| サブディレクトリ   | 責務（将来）                          |
| ------------------ | ------------------------------------- |
| `rakuten/`         | 楽天商品検索・ランキング・ジャンル API |
| `db/`              | PostgreSQL 書き込み・Repository 基盤  |
| `object_storage/`  | Raw JSON の保存・読取                 |
| `external_ai/`     | Embedding / LLM 向け外部 AI API       |
| `logger/`          | trace_id / job_run_id 連携・batch ログ |

Phase4a では各モジュールに `Scaffold*` 実装を置き、単体テスト可能な Protocol 境界のみ定義する。
実接続・永続化・外部 API 呼び出しは Phase4b 以降。

正本ディレクトリ構成: `docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md` §7.4
