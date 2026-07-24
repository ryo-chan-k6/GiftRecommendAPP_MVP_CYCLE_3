# 楽天 API 疎通検証計画（TV-001〜003・最小）

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 検証ID | TV-001 / TV-002 / TV-003（本 Task で一括） |
| 文書種別 | PoC 検証計画（最小） |
| 方針正本 | [TV-001](../計画/TV要件・実施方針/TV-001_楽天商品検索API実疎通.md) / [TV-002](../計画/TV要件・実施方針/TV-002_楽天ランキングAPI実疎通.md) / [TV-003](../計画/TV要件・実施方針/TV-003_楽天ジャンルAPI実疎通.md) |
| 関連 Epic / Task | [#1598](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1598) / [#1603](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1603) |
| 前提 | [#1601](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1601) `HttpRakutenApiClient` |
| 結果 | [楽天API疎通検証結果](./楽天API疎通検証結果.md) |

---

## 2. 目的と切り分け

| 項目 | 内容 |
| ---- | ---- |
| 目的 | genre / ranking / item_search の**最小 live 疎通**と主要レスポンス・エラー形式の観察 |
| client | `apps/batch` の `HttpRakutenApiClient`（明示 `--live-rakuten` のみ） |
| out of scope | CI 必須ゲート、production live、大量呼出、rate limit 意図的誘発、Object Storage / Embedding、正式 Batch 仕様の独断更新 |

---

## 3. 計測設計

| 項目 | 方針 |
| ---- | ---- |
| ハーネス | `scripts/batch/rakuten_live_verify.py` |
| モード | 明示 `--live-rakuten` 必須。未指定時は HTTP 非実行（exit 3） |
| 件数 | genre 1 / ranking 1 / item_search page1+page2 / 任意で invalid genre 1 |
| 指標 | wall-clock（ms）、成功可否、top-level keys、代表 counts、エラー code |
| secret | `RAKUTEN_APPLICATION_ID` / `RAKUTEN_ACCESS_KEY` は env のみ。成果物はマスク |
| CI | 通常 PR CI の必須ゲートにしない |

### 3.1 実行コマンド（local）

```bash
set -a && source .env && set +a
cd apps/batch
uv run python ../../scripts/batch/rakuten_live_verify.py --live-rakuten --probe-invalid \
  --output-dir ../../scripts/batch/output-rakuten-live
```

出力（Git 管理外）: `report.json` / `summary.md`

---

## 4. 判定枠

| ラベル | 意味 |
| ------ | ---- |
| Go | 3 API とも成功疎通。主要フィールド・エラー形式を説明可能。致命制約なし |
| Adjust | 疎通は可能だが認証必須項目・欠損・ページング等で設計調整が必要 |
| Block | 疎通不能、または成立を妨げる制約（認証・料金・仕様）がある |

---

## 5. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-24 | 初版（#1603） |
