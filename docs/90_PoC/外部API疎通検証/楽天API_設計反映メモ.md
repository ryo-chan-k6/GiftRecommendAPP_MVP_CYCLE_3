# 楽天 API 設計反映メモ（TV-001〜003・最小）

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 用途 | Batch / Error 設計への**入力メモ**（正式 docs 更新は別 Task） |
| 関連結果 | [楽天API疎通検証結果](./楽天API疎通検証結果.md) |
| 関連 Epic / Task | [#1598](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1598) / [#1603](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1603) |
| Human 判断 | [ai-logs/human-decisions/2026-07-24-rakuten-api-qps-ip-verify-policy.md](../../../ai-logs/human-decisions/2026-07-24-rakuten-api-qps-ip-verify-policy.md) |

**注意:** 本メモは PoC 成果物である。正式 Batch / Error docs を独断更新しない。

---

## 2. 反映候補（未確定）

| 反映先候補 | 示唆 | 優先 | 状態 |
| ---------- | ---- | ---- | ---- |
| Error / GRS-EXT | HTTP 400 body の `error` / `error_description` をログ短文に残す方針は有用。`HttpRakutenApiClient` へ最小実装済み | 高 | 正式 Error docs 反映は別 Task |
| Batch 認証設定 | `RAKUTEN_APPLICATION_ID` + `RAKUTEN_ACCESS_KEY` の両方が運用必須。`.env.example` に ACCESS_KEY 名を追記済み | 高 | 有効 credential は Human が local `.env` に設定 |
| QPS / Rate Limiter | 目標 QPS=**8**、ハードキャップ 10。`MOD-BATCH-008` 本実装は別 Task。#1603 はハーネス最小間隔のみ | 高 | Human 決定済（2026-07-24） |
| egress IP | live は登録 IP のみ。検証ハーネスで照合必須。**本番 egress 設計は Backlog（未検討）** | 高 | Human 決定済 |
| live 運用 | CI 既定 off・明示フラグのみ、は本検証でも妥当（動的 IP のため） | 中 | E3 方針維持 |
| 成功時 schema | 未観測。再計測後に Raw / adapter 突合 Task を検討 | 中 | credential 再投入後 |
| Retry / 429 | 本 Phase 未実施。意図的誘発は推奨しない | 低 | Human 承認後の候補 |

---

## 3. TV-001〜003 との関係

| TV | 本 Task | 残作業 |
| -- | ------- | ------ |
| TV-001〜003 方針 | ハーネス・失敗形式・再現条件を記録 | 成功疎通の再実行（IP / QPS 制約込み） |
| S4 正式反映 | メモのみ | 別 Task で Batch 仕様へ |

---

## 4. Human 確認事項

| No | 事項 | 状態 |
| -- | ---- | ---- |
| 1 | 目標 QPS / IP 必須 / Rate Limiter Task 切り / 本番 egress Backlog | **決定済**（上記 human-decision） |
| 2 | 有効 credential を local env に設定し、ハーネスを再実行するか | 未実施（Human） |
| 3 | rate limit 意図的誘発を追加で行うか | 推奨: 現状不要 |
| 4 | 成功疎通後に正式 Batch 仕様へ反映する別 Task を起票するか | 未判断 |
| 5 | `MOD-BATCH-008` Rate Limiter 本実装 Task の起票タイミング | 推奨: #1603 完了後すぐ |

---

## 5. Backlog（未検討）

| ID | 内容 | 備考 |
| -- | ---- | ---- |
| BL-RAKUTEN-EGRESS-PROD | 本番（および将来の固定 egress 実行基盤）の接続元 IP 登録・NAT / self-hosted 等の設計 | 2026-07-24 Human: 検討しない。ギャップ一覧にも Backlog として掲載 |

---

## 6. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-24 | 初版（#1603） |
| 2026-07-24 | Human 決定反映（QPS=8 / IP 必須 / Limiter 別 Task / 本番 egress Backlog） |
