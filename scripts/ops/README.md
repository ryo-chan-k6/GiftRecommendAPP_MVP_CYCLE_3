# scripts/ops/

運用確認・health check・post deploy check 補助を配置するディレクトリ。

## 参照

| ドキュメント | 内容 |
| ------------ | ---- |
| [環境設計書 §19](../../docs/06_実装設計/cross_cutting/環境設計書.md) | 環境識別 `APP_ENV` |
| [基盤構成設計書](../../docs/06_実装設計/cross_cutting/基盤構成設計書.md) | 監視・Observability |
| [UI E2E required 昇格方針](../../ai-logs/human-decisions/2026-07-20-ui-e2e-required-promotion-plan.md) | soak 基準の正本 |
| [UI E2E soak 進捗ログ](../../ai-logs/experiments/2026-07-20-ui-e2e-required-soak.md) | soak 観測の記録 |

## 配置済み

| スクリプト | 用途 |
| ---------- | ---- |
| `summarize-ui-e2e-soak.sh` | `test-ui-e2e.yml` の実行を集計し、required 昇格前 soak（2週間・10PR・flake0）の進捗を表示する |

```bash
./scripts/ops/summarize-ui-e2e-soak.sh
./scripts/ops/summarize-ui-e2e-soak.sh --markdown
```

## 配置予定（後続）

- 各 app health エンドポイント疎通チェック
- post deploy smoke test 補助
