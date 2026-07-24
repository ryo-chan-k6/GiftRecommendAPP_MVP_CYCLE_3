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

## live 疎通（#1603）

| 項目 | 内容 |
| ---- | ---- |
| スクリプト | `rakuten_live_verify.py` |
| 用途 | TV-001〜003 向けの最小 live 疎通（明示 `--live-rakuten` のみ） |
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

## 配置予定（後続）

- `MOD-BATCH-008` External API Rate Limiter 本実装（別 Task / T2c）
- ローカル dry-run 起動補助
- GitHub Actions workflow 連携メモ（Task ⑤）
- 本番 egress IP 設計（**Backlog: BL-RAKUTEN-EGRESS-PROD**・未検討）
