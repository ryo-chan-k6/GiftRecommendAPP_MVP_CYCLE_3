# scripts/ops/

運用確認・health check・post deploy check 補助を配置するディレクトリ。

## 参照

| ドキュメント | 内容 |
| ------------ | ---- |
| [環境設計書 §19](../../docs/06_実装設計/cross_cutting/環境設計書.md) | 環境識別 `APP_ENV` |
| [基盤構成設計書](../../docs/06_実装設計/cross_cutting/基盤構成設計書.md) | 監視・Observability |

## MVP（Task ③）

- README のみ
- 本番 deploy 後チェックは infra / CI 整備後に追加

## 配置予定（後続）

- 各 app health エンドポイント疎通チェック
- post deploy smoke test 補助
