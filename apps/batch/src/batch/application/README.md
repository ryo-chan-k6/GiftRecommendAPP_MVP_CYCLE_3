# Phase4a application scaffold

Phase4a `batch-foundation` の application 骨格。collector / transformer / loader の責務分離と job run 追跡の境界を配置する。

| サブディレクトリ | 責務（将来） |
| ---------------- | ------------ |
| `collector/`     | 外部データ取得ユースケース |
| `transformer/`   | Raw / 外部形式から Staging 形式への変換 |
| `loader/`        | Staging / 正本への反映 |
| `job_run/`       | `pipeline_job_run` 等の実行履歴追跡 |

Phase4a では `BatchJobRunner` が collector → transformer → loader を順に実行し、
infrastructure の `Scaffold*` 実装を通じて単体テスト可能な Protocol 境界のみ定義する。
実データ取得・永続化・本番接続は Phase4b 以降。

正本ディレクトリ構成: `docs/00_共通/ディレクトリ構成/プロジェクトディレクトリ構成定義書.md` §7.4

Orchestration 入口: `BatchJobRunner`（`runner.py`）
