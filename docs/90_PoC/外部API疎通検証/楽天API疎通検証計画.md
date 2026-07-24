# 楽天 API 疎通検証計画（TV-001〜003・最小）

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 検証ID | TV-001 / TV-002 / TV-003（本 Task で一括） |
| 文書種別 | PoC 検証計画（最小） |
| 方針正本 | [TV-001](../計画/TV要件・実施方針/TV-001_楽天商品検索API実疎通.md) / [TV-002](../計画/TV要件・実施方針/TV-002_楽天ランキングAPI実疎通.md) / [TV-003](../計画/TV要件・実施方針/TV-003_楽天ジャンルAPI実疎通.md) |
| 関連 Epic / Task | [#1598](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1598) / [#1603](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1603) |
| 前提 | [#1601](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1601) `HttpRakutenApiClient` |
| Human 判断 | [2026-07-24 QPS/IP](../../../ai-logs/human-decisions/2026-07-24-rakuten-api-qps-ip-verify-policy.md) / [2026-07-25 常用QPS=2改訂](../../../ai-logs/human-decisions/2026-07-25-rakuten-operational-qps-revise-to-2.md) |
| 結果 | [楽天API疎通検証結果](./楽天API疎通検証結果.md) |

---

## 2. 目的と切り分け

| 項目 | 内容 |
| ---- | ---- |
| 目的 | genre / ranking / item_search の**最小 live 疎通**と主要レスポンス・エラー形式の観察 |
| client | `apps/batch` の `HttpRakutenApiClient`（明示 `--live-rakuten` のみ） |
| 実行場所 | **登録済み外部 IP を持つ WSL（local）のみ** |
| out of scope | CI 必須ゲート、production live、大量呼出、rate limit 意図的誘発、Object Storage / Embedding、正式 Batch 仕様の独断更新、本番 egress 設計 |

---

## 3. 制約（Human 決定・2026-07-24）

| 制約 | 方針 |
| ---- | ---- |
| 目標 QPS | **2**（常用。登録上限 10 はハードキャップ。実験により旧目標 8 から改訂） |
| 接続元 IP | 楽天側に登録した外部 IP からのみ。ハーネスで **照合必須** |
| CI live | **禁止**（GitHub-hosted は動的 IP） |
| Rate Limiter 本実装 | #1603 外。ハーネスは最小間隔のみ。`MOD-BATCH-008` は別 Task（設計入力 QPS=2） |

---

## 4. 計測設計

| 項目 | 方針 |
| ---- | ---- |
| ハーネス | `scripts/batch/rakuten_live_verify.py` |
| モード | 明示 `--live-rakuten` 必須。未指定時は HTTP 非実行（exit 3） |
| 事前ゲート | `RAKUTEN_EXPECTED_EGRESS_IP` 必須。観測 egress と不一致なら **楽天 HTTP せず中止**（exit 2） |
| 間隔 | 既定 `RAKUTEN_MAX_QPS=2` → 最小間隔 500ms。`RAKUTEN_MIN_INTERVAL_MS` で上書き可（ただし 100ms 未満＝10 QPS 超は拒否） |
| 件数 | genre 1 / ranking 1 / item_search page1+page2 / 任意で invalid genre 1 |
| 指標 | wall-clock（ms）、成功可否、top-level keys、代表 counts、エラー code、IP 照合結果（一致/不一致のみ。実 IP は成果物 docs に書かない） |
| secret | `RAKUTEN_APPLICATION_ID` / `RAKUTEN_ACCESS_KEY` は env のみ。成果物はマスク |
| CI | 通常 PR CI の必須ゲートにしない |

### 4.1 実行コマンド（local / WSL）

```bash
set -a && source .env && set +a
# .env に RAKUTEN_EXPECTED_EGRESS_IP / RAKUTEN_APPLICATION_ID / RAKUTEN_ACCESS_KEY を設定済みであること
cd apps/batch
uv run python ../../scripts/batch/rakuten_live_verify.py --live-rakuten --probe-invalid \
  --output-dir ../../scripts/batch/output-rakuten-live
```

出力（Git 管理外）: `report.json` / `summary.md`

---

## 5. 判定枠

| ラベル | 意味 |
| ------ | ---- |
| Go | IP 照合通過、かつ 3 API とも成功疎通。主要フィールド・エラー形式を説明可能。致命制約なし |
| Adjust | 疎通は可能だが認証必須項目・欠損・ページング等で設計調整が必要 |
| Block | IP 不一致・認証失敗・疎通不能、または成立を妨げる制約がある |

---

## 6. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-24 | 初版（#1603） |
| 2026-07-24 | Human 決定反映: 目標 QPS=8、egress IP 照合必須、本番 egress は Backlog |
| 2026-07-25 | 常用 QPS を実験結果に基づき **2** へ改訂（旧 8 は常用から外す） |
