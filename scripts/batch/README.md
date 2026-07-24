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
| 出力 | `scripts/batch/output-rakuten-live/`（gitignored） |
| secret | env の `RAKUTEN_APPLICATION_ID` / `RAKUTEN_ACCESS_KEY`。値をログに出さない |

```bash
set -a && source .env && set +a
cd apps/batch
uv run python ../../scripts/batch/rakuten_live_verify.py --live-rakuten \
  --output-dir ../../scripts/batch/output-rakuten-live
```

## 配置予定（後続）

- ローカル dry-run 起動補助
- GitHub Actions workflow 連携メモ（Task ⑤）
