# 楽天 API 設計反映メモ（TV-001〜003・最小）

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 用途 | Batch / Error 設計への**入力メモ**（正式 docs 更新は別 Task） |
| 関連結果 | [楽天API疎通検証結果](./楽天API疎通検証結果.md) |
| 関連 Epic / Task | [#1598](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1598) / [#1603](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1603) |
| Human 判断 | [2026-07-24](../../../ai-logs/human-decisions/2026-07-24-rakuten-api-qps-ip-verify-policy.md) / [2026-07-25 常用QPS=2](../../../ai-logs/human-decisions/2026-07-25-rakuten-operational-qps-revise-to-2.md) |

**注意:** 本メモは PoC 成果物である。正式 Batch / Error docs を独断更新しない。

---

## 2. 反映候補

| 反映先候補 | 示唆 | 優先 | 状態 |
| ---------- | ---- | ---- | ---- |
| HttpRakutenApiClient endpoint | 現行は `openapi.rakuten.co.jp`（genre=`ichibagt` / ranking=`ichibaranking` / item=`ichibams`）。旧 `app.rakuten.co.jp` は新 credential で `specify valid applicationId` | 高 | **正式反映済（#1606）** |
| Ranking `period` | ドメイン `daily` と楽天クエリ `period` は別物。現行 API へは `realtime` のみ送る。`daily` は送らない | 高 | **正式反映済（#1606 / BATCH-002）** |
| Genre adapter | 現行 Raw は `genre`（`current` ではない）。`ancestors` / `siblings` / `children` | 高 | **正式反映済（#1606）。adapter は `genre` のみ** |
| Item Search / Ranking adapter | formatVersion=2 相当の Item キーを live で確認。突合・欠損方針は別 Task | 中 | 観測済み。endpoint は正式反映済 |
| QPS / Rate Limiter | **常用 QPS=2**（実験改訂。旧目標 8 は常用外）。ハードキャップ 10。`MOD-BATCH-008` 本実装は T2c | 高 | **#1605 / #1608 完了** |
| egress IP | live は登録 IP のみ・ハーネス照合必須。**本番 egress は Backlog** | 高 | Human 決定済 |
| Error / GRS-EXT | 400 body の `error` / `error_description` 短文付与は有用。invalid genre は `genreId is a 6 digit integer, or 0` | 中 | client 実装済み。正式 Error docs は別 Task |
| 認証 | UUID `applicationId` + `pk_` `accessKey` 必須。`.env.example` に名を追記済み | 高 | 完了 |

---

## 3. TV-001〜003 との関係

| TV | 本 Task | 残作業 |
| -- | ------- | ------ |
| TV-001〜003 | live 成功疎通・形状・429・endpoint 移行を記録 | 正式 Batch / adapter 反映は **#1606** |
| S4 正式反映 | メモ → 正式 docs | **#1606 で反映** |

---

## 4. Human 確認事項

| No | 事項 | 状態 |
| -- | ---- | ---- |
| 1 | QPS / IP 必須 / Limiter 別 Task / 本番 egress Backlog | **決定済**（常用 QPS は 2026-07-25 に **2** へ改訂） |
| 2 | live 再実行（credential + 新 endpoint） | **実施済**（Adjust） |
| 3 | rate limit 意図的誘発 | 推奨: 現状不要（偶発 429 は記録済み） |
| 4 | 正式 Batch / adapter 反映 Task を起票するか | **起票済 #1606** |
| 5 | T2c `MOD-BATCH-008` 起票タイミング | **完了 #1605 / #1608** |

---

## 5. Backlog（未検討）

| ID | 内容 | 備考 |
| -- | ---- | ---- |
| BL-RAKUTEN-EGRESS-PROD | 本番（および将来の固定 egress 実行基盤）の接続元 IP 登録・NAT / self-hosted 等の設計 | 2026-07-24 Human: 検討しない |

---

## 6. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-24 | 初版（認証失敗時点） |
| 2026-07-24 | Human 決定反映（QPS / IP / Limiter / Backlog） |
| 2026-07-24 | endpoint 移行・成功疎通・Genre キー・Ranking period・429 を追記 |
| 2026-07-25 | 常用 QPS=2 改訂（実験 `2026-07-24-rakuten-qps-pattern`）を反映 |
| 2026-07-25 | #1606: 正式 Batch / 外部連携設計 / adapter 正本反映完了を記録 |
