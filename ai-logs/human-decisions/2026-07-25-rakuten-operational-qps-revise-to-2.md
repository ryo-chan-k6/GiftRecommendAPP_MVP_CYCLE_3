# Human Decision Log

## 1. 概要

| 項目 | 内容 |
| ---- | ---- |
| Log ID | `2026-07-25-rakuten-operational-qps-revise-to-2` |
| Log種別 | `human-decision` |
| 件名 | 楽天市場 API 常用 QPS を 8 から **2** へ改訂 |
| 発生日時 | 2026-07-25 |
| 記録日時 | 2026-07-25 |
| 関連Issue | #1603 |
| 関連PR | #1604 |
| 前提決定 | `ai-logs/human-decisions/2026-07-24-rakuten-api-qps-ip-verify-policy.md` |
| 実験根拠 | `ai-logs/experiments/2026-07-24-rakuten-qps-pattern.md` |
| 重要度 | `high` |
| 状態 | `decided` |

---

## 2. 結論

live QPS パターン実験の結果を受け、**常用（運用既定）QPS を 2 に改訂**する。

| 区分 | 改訂前 | 改訂後 |
| ---- | -----: | -----: |
| 常用 QPS（運用既定） | 8 | **2** |
| 安全側既定（長時間・連続再実行） | （未定義） | 1（推奨・任意） |
| ハードキャップ | 10 | **10**（変更なし） |
| egress IP 照合必須 | 必須 | **必須**（変更なし） |
| Rate Limiter 本実装 | 別 Task（T2c） | **別 Task（T2c）**。設計入力の目標 QPS も 2 |

---

## 3. 理由（要約）

- QPS 1–2 は連続 4 呼出で安定。QPS 3 以上で 429（`GRS-EXT-102`）が頻発
- 登録上限 10 / 旧目標 8 は sustained 常用値としては過大
- 偶発 429 に備え Rate Limiter + backoff は引き続き必須

---

## 4. 反映対象

| 対象 | 内容 |
| ---- | ---- |
| `scripts/batch/rakuten_live_verify.py` | 既定 `RAKUTEN_MAX_QPS` を 2 |
| `.env.example` | コメント既定を 2 / 間隔 500ms |
| PoC 計画・結果・設計反映メモ | 常用 QPS=2 に更新 |
| ギャップ一覧 | T2b/T2c / env 表を更新 |
| 本ログ | 改訂正本 |

---

## 5. 参照

- `ai-logs/experiments/2026-07-24-rakuten-qps-pattern.md`
- `ai-logs/human-decisions/2026-07-24-rakuten-api-qps-ip-verify-policy.md`
