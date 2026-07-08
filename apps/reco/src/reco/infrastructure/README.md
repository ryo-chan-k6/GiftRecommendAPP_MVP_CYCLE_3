# Phase4a infrastructure scaffold

Phase4a `reco-foundation` の infrastructure 骨格。DB・vector store・外部AI・logger の技術境界を配置する。

| サブディレクトリ | 責務（将来） |
| ---------------- | ------------ |
| `db/` | PostgreSQL 接続・Repository 基盤 |
| `vector_store/` | pgvector / Embedding 検索 |
| `external_ai/` | Semantic / Embedding / Reason 向け外部 AI API |
| `logger/` | trace_id / run_id 連携・phase_log / error_log 出力 |

Phase4a では各モジュールに `Scaffold*` 実装を置き、単体テスト可能な Protocol 境界のみ定義する。
実接続・永続化・外部 API 呼び出しは Phase4b 以降。

正本ディレクトリ構成: `docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md` §7.3
