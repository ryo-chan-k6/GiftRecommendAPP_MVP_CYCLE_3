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
| `rakuten_live_verify.py` | 楽天 API 疎通（#1603 / TV-001〜003）。`--live-rakuten` 必須 |
| `object_storage_live_verify.py` | Supabase Storage（S3 互換）put/get（#1617・リリース準備）。`--live-object-storage` 必須 |

出力ディレクトリ `scripts/batch/output-*/` は Git 管理外。CI 既定 live は禁止。

### 楽天 live（#1603）

| 項目 | 内容 |
| ---- | ---- |
| 実行場所 | 登録済み外部 IP を持つ **WSL（local）のみ**。CI live 禁止 |
| QPS | **常用 2**（ハードキャップ 10）。`RAKUTEN_MAX_QPS` / `RAKUTEN_MIN_INTERVAL_MS` |
| IP 照合 | `RAKUTEN_EXPECTED_EGRESS_IP` **必須**。不一致時は楽天 HTTP しない |
| 出力 | `scripts/batch/output-rakuten-live/`（gitignored） |
| secret | env の `RAKUTEN_APPLICATION_ID` / `RAKUTEN_ACCESS_KEY`。値をログに出さない |
| Human 判断 | `ai-logs/human-decisions/2026-07-25-rakuten-operational-qps-revise-to-2.md`（常用 QPS=2） |

```bash
set -a && source .env && set +a
cd apps/batch
uv run python ../../scripts/batch/rakuten_live_verify.py --live-rakuten \
  --output-dir ../../scripts/batch/output-rakuten-live
```

### Object Storage live（#1617・リリース準備）

手順正本: [ローカル開発手順書 §7.4](../../docs/06_実装設計/cross_cutting/ローカル開発手順書.md) / [PoC 計画](../../docs/90_PoC/外部API疎通検証/Supabase_Storage_S3互換疎通検証計画.md)

```bash
set -a && source .env && set +a
cd apps/batch
uv run python ../../scripts/batch/object_storage_live_verify.py \
  --live-object-storage --probe-missing \
  --output-dir ../../scripts/batch/output-object-storage-live
```

## 配置予定（後続）

| 対象 | 予定パス | 担当 |
| ---- | -------- | ---- |
| local日次親オーケストレータ | `local_daily_orchestrator.sh` | #1804（設計正本: [local薄いオーケストレータ設計・運用手順](../../docs/15_運用・改善/運用手順/local薄いオーケストレータ設計・運用手順.md)） |
| local週次親オーケストレータ | `local_weekly_orchestrator.sh` | #1804 |
| 共通（flock / Run ID） | `lib/local_orchestrator_common.sh` | #1804 |
| ローカル dry-run 起動補助 | 上記親シェルの `--dry-run` | #1804 |
| 本番 egress IP 設計 | — | **Backlog: #1607**・未検討（GHA楽天liveは禁止維持） |

設計・運用手順・crontab例（実登録はHuman）の正本は上記 docs。本READMEは実装後に起動例を追記する。
