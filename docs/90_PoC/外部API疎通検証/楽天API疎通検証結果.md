# 楽天 API 疎通検証結果（TV-001〜003）

## 1. 文書情報

| 項目 | 内容 |
| ---- | ---- |
| 文書種別 | PoC 検証結果 |
| 検証ID | TV-001（item_search）/ TV-002（ranking）/ TV-003（genre） |
| 計画 | [楽天API疎通検証計画](./楽天API疎通検証計画.md) |
| 関連 Epic / Task | [#1598](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1598) / [#1603](https://github.com/ryo-chan-k6/GiftRecommendAPP_MVP_CYCLE_3/issues/1603) |
| 計測日 | 2026-07-24（JST） |
| 設計反映メモ | [楽天API_設計反映メモ](./楽天API_設計反映メモ.md) |
| 暫定判定 | **Block**（認証パラメータ不正により成功疎通なし） |

**注意:** secret / `.env` 実値は本結果に含めていない。

---

## 2. 実施概要

| 項目 | 内容 |
| ---- | ---- |
| ハーネス | `scripts/batch/rakuten_live_verify.py` |
| client | `HttpRakutenApiClient` |
| 環境 | local（WSL2） |
| live フラグ | `--live-rakuten` 明示。未指定時は exit 3（HTTP 非実行）を確認済み |
| credentials | `RAKUTEN_APPLICATION_ID` は env に存在。`RAKUTEN_ACCESS_KEY` は **未設定** |
| 呼出数 | 5（genre / ranking / item_search×2 / invalid genre） |
| apps 変更 | エラー本文の短文付与（secret マスク）を client に最小追加 |

### 2.1 TV 対応

| TV | API | 本結果での呼出 |
| -- | --- | -------------- |
| TV-003 | IchibaGenre/Search | `fetch_genre_raw` |
| TV-002 | IchibaItem/Ranking | `fetch_ranking_raw` |
| TV-001 | IchibaItem/Search | `fetch_item_search_raw`（page 1 / 2） |

---

## 3. 結果サマリ（事実）

| name | ok | elapsed_ms | error_code | 観察 |
| ---- | -- | ---------- | ---------- | ---- |
| genre.fetch_genre_raw | false | ≈373 | GRS-EXT-105 | HTTP 400 |
| ranking.fetch_ranking_raw | false | ≈110 | GRS-EXT-105 | HTTP 400 |
| item_search.fetch_item_search_raw | false | ≈105 | GRS-EXT-105 | HTTP 400 |
| item_search.page2 | false | ≈102 | GRS-EXT-105 | HTTP 400 |
| genre.invalid_genre_id | false | ≈104 | GRS-EXT-105 | HTTP 400（認証エラーが先） |

**成功疎通:** 0 / 5

### 3.1 エラー形式（事実）

楽天 API の HTTP 400 body（全 API 共通の観測）:

| フィールド | 値 |
| ---------- | -- |
| `error` | `wrong_parameter` |
| `error_description` | `specify valid applicationId` |

`HttpRakutenApiClient` はこれを `GRS-EXT-105` にマップし、メッセージへ短文付与する（secret マスク済み）。

### 3.2 認証まわり（事実）

| 項目 | 状態 |
| ---- | ---- |
| `RAKUTEN_APPLICATION_ID` | env に設定あり（値は記録しない）。API は **valid ではない** と応答 |
| `RAKUTEN_ACCESS_KEY` | local `.env` に **未設定**。Batch 仕様上は必須 |
| accessKey 空送信 | 実施。応答は依然 `specify valid applicationId`（accessKey 不足の明示ではない） |

### 3.3 未実施（本計測）

| 項目 | 理由 |
| ---- | ---- |
| 成功時の主要フィールド・欠損観察 | 認証失敗のためレスポンス本体未取得 |
| ページング成功時の pageCount 等 | 同上 |
| rate limit（429）実誘発 | Human 承認なし・本 Task out of scope |

---

## 4. 再現条件（事実）

1. local で `RAKUTEN_APPLICATION_ID` のみ設定（`RAKUTEN_ACCESS_KEY` なし）
2. `uv run python scripts/batch/rakuten_live_verify.py --live-rakuten --probe-invalid`
3. genre / ranking / item_search いずれも HTTP 400 / `wrong_parameter` / `specify valid applicationId`

**推論:** 現 local の applicationId は楽天側で無効（誤値・失効・別環境用）。ACCESS_KEY 未設定も仕様上の欠落だが、今回のエラーメッセージは applicationId 側を指している。

---

## 5. 判定

| ラベル | 採用 |
| ------ | ---- |
| **Block** | 成功疎通なし。有効な `RAKUTEN_APPLICATION_ID` / `RAKUTEN_ACCESS_KEY` の用意が必要 |

Go 判定には、Human が有効 credential を local env に設定したうえで本ハーネスを再実行する必要がある。

---

## 6. secret チェック

| 確認 | 結果 |
| ---- | ---- |
| 結果 docs に実値なし | 遵守 |
| report/summary に実値なし（マスク） | 遵守 |
| `--live-rakuten` なしで HTTP 非実行 | 遵守 |

---

## 7. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-24 | 初版（#1603）。認証失敗により Block |
