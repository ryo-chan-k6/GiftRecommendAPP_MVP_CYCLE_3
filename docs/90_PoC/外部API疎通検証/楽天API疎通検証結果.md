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
| Human 判断 | [ai-logs/.../2026-07-24-rakuten-api-qps-ip-verify-policy.md](../../../ai-logs/human-decisions/2026-07-24-rakuten-api-qps-ip-verify-policy.md) |
| 判定 | **Adjust**（3 API 成功疎通。endpoint 移行・レスポンス形状・429 観察あり。正式仕様反映は別 Task） |

**注意:** secret / `.env` 実値 / 実 IP は本結果に含めていない。

---

## 2. 実施概要

| 項目 | 内容 |
| ---- | ---- |
| ハーネス | `scripts/batch/rakuten_live_verify.py` |
| client | `HttpRakutenApiClient`（endpoint を現行 `openapi.rakuten.co.jp` 系へ更新済み） |
| 環境 | local（WSL2・登録 egress IP） |
| live フラグ | `--live-rakuten` 明示 |
| credentials | `RAKUTEN_APPLICATION_ID`（UUID）+ `RAKUTEN_ACCESS_KEY`（`pk_`）両方設定 |
| 制約 | **常用 QPS=2**・egress IP 照合必須（不一致時は HTTP しない）。旧目標 8 は実験により常用外 |
| 最終成功計測 | genre / ranking / item_search×2 成功。invalid genre は期待どおり 400 |

### 2.1 TV 対応

| TV | API | endpoint（現行） | 本結果 |
| -- | --- | ---------------- | ------ |
| TV-003 | IchibaGenre/Search | `.../ichibagt/api/IchibaGenre/Search/20260701` | 成功 |
| TV-002 | IchibaItem/Ranking | `.../ichibaranking/api/IchibaItem/Ranking/20220601` | 成功（間隔不足時は 429） |
| TV-001 | IchibaItem/Search | `.../ichibams/api/IchibaItem/Search/20260701` | 成功（page 1 / 2） |

---

## 3. 結果サマリ（事実）

最終成功ラン（間隔 1500ms・クールダウン後）:

| name | ok | error_code | 観察（値なし） |
| ---- | -- | ---------- | -------------- |
| genre.fetch_genre_raw | true | — | top-level: `ancestors` / `genre` / `siblings` / `children` / `attributes`。`children`=39 |
| ranking.fetch_ranking_raw | true | — | `Items`=30。`lastBuildDate` / `title`。Item に `itemCode` 等 |
| item_search.fetch_item_search_raw | true | — | `Items`=3、`pageCount`=100、`hits`=3 |
| item_search.page2 | true | — | 同上（ページング継続） |
| genre.invalid_genre_id | false | GRS-EXT-105 | `genreId is a 6 digit integer, or 0`（認証エラーではない） |

**成功疎通:** genre / ranking / item_search 各 1 回以上。

### 3.1 初回失敗の原因（事実）

旧 endpoint（`app.rakuten.co.jp/services/api/...`）へ新形式 credential（UUID + `pk_`）を送ると、全 API が HTTP 400 / `specify valid applicationId`。

→ client の URL を現行 openapi 系へ差し替え後に解消。

### 3.2 429 観察（事実）

| 条件 | 結果 |
| ---- | ---- |
| 連続再実行 + 短い間隔（125〜500ms） | ranking が `GRS-EXT-102`（HTTP 429） |
| クールダウン後 + 呼出間隔 1500ms | ranking 成功 |
| ranking 単独（先行 sleep 2s） | genreId `0` / `100283` / `100371` いずれも成功 |

意図的な rate limit 誘発はしていない。短時間の連続 live 実行で 429 が出うる。

### 3.3 レスポンス形状メモ（事実）

| API | 主な観察 |
| --- | -------- |
| Genre | 現行は `genre`（旧メモの `current` ではない）。`ancestors` / `siblings` / `children` |
| Ranking | `Items` 配列。ドメイン `period=daily` は楽天クエリへ送らない（`realtime` のみ送る） |
| Item Search | `Items` / `pageCount` / `hits` / `count`。formatVersion=2 想定の flat Item キーを確認 |

---

## 4. 再現条件（成功）

1. WSL で登録 egress IP を `RAKUTEN_EXPECTED_EGRESS_IP` に設定
2. 有効な UUID `RAKUTEN_APPLICATION_ID` + `pk_` `RAKUTEN_ACCESS_KEY`
3. `HttpRakutenApiClient` が現行 openapi endpoint を使用
4. 直前の大量 live 呼出がない状態で、`--live-rakuten --probe-invalid` を実行

---

## 5. 判定

| ラベル | 採用 | 理由 |
| ------ | ---- | ---- |
| **Adjust** | ○ | 3 API 成功疎通。endpoint 移行・Genre キー名・Ranking period 扱い・429 耐性を正式 Batch / adapter へ反映する別 Task が必要 |
| Go | — | 正式仕様・adapter まで無修正で完了とは言えない |
| Block | — | 認証・IP による疎通不能は解消 |

---

## 6. secret チェック

| 確認 | 結果 |
| ---- | ---- |
| 結果 docs に実値なし | 遵守 |
| report/summary は gitignored。docs に実 IP なし | 遵守 |
| `--live-rakuten` なしで HTTP 非実行 | 遵守 |
| egress IP 不一致時に楽天 HTTP しない | 遵守 |

---

## 7. 改訂履歴

| 日付 | 内容 |
| ---- | ---- |
| 2026-07-24 | 初版。旧 endpoint により認証エラー → Block |
| 2026-07-24 | openapi endpoint 移行後に 3 API 成功。判定 Adjust |
| 2026-07-25 | 常用 QPS を 2 へ改訂（実験ログ参照）。本結果の成功計測は改訂前の検証を含む |
