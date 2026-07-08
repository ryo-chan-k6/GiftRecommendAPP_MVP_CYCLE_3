# Phase4a config scaffold

Phase4a `batch-foundation` の config / env 読取骨格。batch コンポーネントの設定値を型付きで読み込む。

| モジュール | 責務 |
| ---------- | ---- |
| `env.py` | `APP_ENV`（dev / stg / prod）の型 |
| `settings.py` | `BatchSettings` 値オブジェクト |
| `loader.py` | 環境変数から `BatchSettings` を構築 |

対象環境変数の正本は `docs/06_実装設計/cross_cutting/環境設計書.md` §19.3（共通）・§19.7（batch）。

Phase4a では secret 実値の検証や本番接続は行わない。`missing_required_secrets()` / `missing_required_config()` で MVP 必須項目の未設定を判定し、
`scaffold_batch_settings()` で単体テスト用の in-memory 設定を提供する。

正本ディレクトリ構成: `docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md` §7.4
