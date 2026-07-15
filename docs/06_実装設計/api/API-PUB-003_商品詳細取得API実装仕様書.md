# 商品詳細取得 API実装仕様書

> 本書は **API-PUB-003** の **実装面** 正本である。
> 契約面（Request / Response / Error / Validation の定義）は `API-PUB-003_商品詳細取得API契約仕様書.md` を正とし、本書では再掲しない。
> OpenAPI 正本は `packages/contracts/openapi/public-api.yaml`（#416 / PR #417 develop 反映済み）。generated / Orval / apps 実装の本格整備は後続 Task。本書は docs のみ。

## 1. ドキュメント情報

| 項目           | 内容                                      |
| -------------- | ----------------------------------------- |
| ドキュメントID | `API-PUB-003-IMPLEMENTATION`              |
| ドキュメント名 | 商品詳細取得 API実装仕様書                |
| 対象システム   | Gift Recommendation Service MVP（Public） |
| MVP対象        | `○`                                       |
| 作成日         | 2026-07-15                                |
| 更新日         | 2026-07-15                                |

---

## 2. 前提契約

| 項目 | 内容 |
| ---- | ---- |
| 対象API ID | `API-PUB-003` |
| API名 | 商品詳細取得 |
| Method / Endpoint | `GET` `/api/v1/items/{itemId}` |
| API契約仕様書 | `docs/06_実装設計/api/API-PUB-003_商品詳細取得API契約仕様書.md` |
| OpenAPI定義 | `packages/contracts/openapi/public-api.yaml`（`operationId: getItemDetail`） |
| テーブル定義 | `item` / `item_image` / `item_review_summary` / `item_popularity_signal` / `external_genre` / `ranking_snapshot` 各テーブル定義書 |
| Contract Gate | **契約仕様書確定済み**（#399 / PR #405）。**OpenAPI 断片反映済み**（#416 / PR #417 develop merge）。Orval / generated の全面追随は consumer（SCR-006 等）側 Task で確認 |

> 契約面の Request / Response schema、Validation、Error 一覧は契約仕様書を参照する。本書では実装判断に必要な処理フロー・論理モジュール責務・DB マッピング・エラー境界のみ記載する。

### 2.1 Contract Gate 確認結果（本 Task）

| No | チェック | 結果 |
| --: | -------- | ---- |
| 1 | 契約 #399 / PR #405 が develop 反映済み | 充足（契約仕様書が本 Branch に存在） |
| 2 | OpenAPI #416 / PR #417 が `public-api.yaml` に反映済み | 充足（`getItemDetail` / `ItemIdPath` / `PublicItemDetail` あり） |
| 3 | item 系テーブル定義（item / item_image / item_review_summary / item_popularity_signal） | 充足 |
| 4 | 本 Task は OpenAPI / apps / DB schema を変更しない | 充足（docs のみ） |

---

## 3. 実装方針

### 3.1 全体方針

| 観点 | 方針 |
| ---- | ---- |
| Provider | `apps/api`（`apps/api/src/app/items/**`） |
| Consumer | `apps/web`（SCR-006 商品詳細画面 / SCR-004 レコメンド結果一覧からの導線）。本 Task では実装しない |
| Web フレームワーク | **Express**（`apps/api` 既存スタック） |
| 担当モジュール（論理） | **Item Detail Controller** / **Item Detail Repository**（モジュール一覧に専用 MOD-ID 未記載。§11 参照） |
| 責務分離 | HTTP I/F（meta 解決・Path / Query 検証・Item 系読取・Response / Error 組立）のみ。推薦パイプライン（MOD-API-001〜006）および **Reco Client は呼び出さない** |
| 認証 | **MVP は非認証**（契約仕様書 §4）。`Authorization` 検証なし |
| 冪等性 | 副作用なし。同一 `itemId` の GET は繰り返し可（SELECT のみ） |
| Feature / Embedding | **Public Response に含めない**（`item_feature` / `item_embedding` / `item_meaning` 等は参照しない） |
| キャッシュ | **MVP 既定: 都度 SELECT**（プロセス内キャッシュは MVP 非導入） |

### 3.2 エンドポイント層の配置

後続実装 Task の配置目安（現状 `apps/api/src/app/items/**` は未作成。本仕様書を正として新規追加する）:

```text
apps/api/src/app/items/
├── routes.ts                      # createItemsRouter(): GET /:itemId
├── controller.ts                  # Item Detail Controller（本 API 受付・Response 組立）
├── repository.ts                  # Item Detail Repository（item 系 JOIN 読取）
├── validator.ts                   # Path / Query 検証（任意。Controller 内包も可）
├── constants.ts                   # path / metric / error code 定数
├── types.ts                       # 内部 DTO（任意）
└── index.ts

apps/api/src/
├── middlewares/                   # request-meta / error 等（既存再利用）
├── infrastructure/db/             # DB client（既存）
└── ...
```

Router mount の目安: **`/api/v1/items`** 配下に Items Router を登録する（`GET /:itemId`）。既存 `masters` / `feedback` / `recommendations` Router と同列。

| 論理モジュール | 責務（本 API） |
| -------------- | -------------- |
| Item Detail Controller | `GET /:itemId` 受付、meta 解決、Path / Query 検証、Repository 呼び出し、active 判定後の Response / Error 組立、metric 境界 |
| Item Detail Repository | `item` をキーに `item_image` / `item_review_summary` / `item_popularity_signal`（最新 Snapshot 経由）/ `external_genre` を読取。内部行 DTO を返却 |

**MOD-ID（未確定）:** モジュール一覧に Item Detail 専用 ID が未記載のため、後続で **MOD-API-014（Item Detail Controller）/ MOD-API-015（Item Detail Repository）** を候補として割当可能（§11.2）。本書では論理名を正とし、正式 ID は Human 判断とする。

`apps/reco/**` / `apps/batch/**` / `apps/web/src/app/**` / `apps/web/src/features/**` は **変更しない**（親 Epic `forbidden_paths` 想定）。

### 3.3 DI / 依存

| 項目 | 方針 |
| ---- | ---- |
| request-meta | 既存 `resolveRequestMeta` を再利用（`masters` / `feedback` と同型）。Header 任意・未指定時はサーバ採番可 |
| DB | Postgres。`item` および子テーブルを SELECT。接続文字列実値をログ・Response に出さない |
| Reco Client / Recommendation Pipeline | **使用しない** |
| Masters API | **呼び出さない**（ジャンル名等は DB JOIN で解決） |
| 外部 EC API | **呼び出さない**（Batch 取込済み正本を参照） |

**Router DI パターン（参考）:** `feedback` / `masters` と同様、`createItemsRouter(deps?)` で Repository / Controller を注入可能とする。未指定時は `createDbSession()` から既定 Repository を構築する。

```typescript
// 配置イメージ（後続実装 Task）
export type ItemsRouterDeps = {
  repository?: ItemDetailRepository;
  logger?: ApiLogger;
  dbSession?: DbSession;
};
```

### 3.4 認証（実装面）

| 項目 | 方針 |
| ---- | ---- |
| 方式 | MVP 非認証。認証 middleware を本ルートに適用しない |
| `Authorization` | 無視（検証しない） |
| 後続 | 認証追加時は契約・OpenAPI 変更を伴う別 Task |

### 3.5 DB 読取（実装面）

| 項目 | 方針 |
| ---- | ---- |
| 主テーブル | `item`（PK / Path キー: `item_id`） |
| 子テーブル | `item_image`（1:N）、`item_review_summary`（1:0..1 LEFT JOIN）、`item_popularity_signal`（最新 Snapshot 経由 LEFT JOIN） |
| 補助 JOIN | `external_genre`（`item.external_genre_id` → `genre_name`）、`ranking_snapshot`（`popularityBadge` 解決用） |
| 読取操作 | **SELECT のみ**。api / reco の Online 推薦中更新禁止方針に従う |
| 存在確認 | `item_id` で 0 行 → **404 `GRS-ITM-001`**（`is_active` 判定前に実施） |
| active 判定 | 行は存在するが `is_active = false` → **422 `GRS-ITM-002`**（404 マスクしない） |
| 画像なし | `item_image` 0 行または `is_primary` 行なし → **HTTP 200**。`itemImageUrl` / `images` を省略（**`GRS-ITM-003` は HTTP エラーとして返却しない**） |
| Index 利用 | `item_pkey` / `idx_item_image_item_id` / `idx_item_review_summary_item_id` / `idx_ips_item_id` 等（各テーブル定義書 §9） |

**`itemId` 表面 ID（実装注意）:**

| 観点 | 方針 |
| ---- | ---- |
| 契約 | Path `itemId` は **内部 Item 識別子**（DB `item_id`）を正とする |
| DB 型 | `item_id` は `uuid` |
| 実装 | Path 文字列を UUID として解釈し `item.item_id` で検索。OpenAPI `ItemIdPath` の `pattern` / `maxLength` に合致しない場合は **400 `GRS-REQ-001`**（Repository 到達前） |
| API-PUB-002 連携 | `items[].itemId` と **同一文字列表現** を維持する（Snapshot の `item_id` と同型） |

**`popularityBadge` 最新 Snapshot 解決（MVP）:** `item_popularity_signal_テーブル定義書` §5.7 / §12.4 を正とする。

| 観点 | 方針 |
| ---- | ---- |
| 対象ジャンル | 参照対象 Item の `external_genre_id` |
| period | MVP 固定 **`daily`** |
| source | MVP 固定 **`rakuten`** |
| 最新の定義 | 同一 `(source, external_genre_id, period)` で **`last_build_date` 最大** の `ranking_snapshot`（同値時 `fetched_at DESC`） |
| 明細 JOIN | 上記 `ranking_snapshot_id` かつ `item_id` 一致の `item_popularity_signal` 行があれば `popularityBadge` を組立 |
| 該当なし | `popularityBadge` オブジェクトごと **省略**（HTTP 200） |

**`shopName`（MVP）:** `item` テーブルは `shop_code` のみ保持し `shopName` 列はない（`item_テーブル定義書` §13）。MVP 実装では **外部ショップマスタ未整備のため省略を許容** し、解決手段が整った後続 Task で optional 返却を検討する（§11.2）。

---

## 4. 処理概要

### 4.1 処理フロー

```mermaid
flowchart TD
    START([GET /api/v1/items/{itemId}]) --> META[trace/request meta 解決<br/>Header任意・未指定時はサーバ採番可]
    META --> CTRL[Item Detail Controller]
    CTRL --> VAL[Path itemId 検証<br/>空・不正文字・maxLength 64]
    VAL -->|不正| E400[400 GRS-REQ-001]
    VAL --> QVAL{未知 Query あり?}
    QVAL -->|Yes| E400
    QVAL -->|No| REPO[Item Detail Repository<br/>item + 子テーブル読取]
    REPO -->|0行| E404[404 GRS-ITM-001]
    REPO -->|is_active=false| E422[422 GRS-ITM-002]
    REPO -->|active| ASM[Public Response 組立<br/>画像/レビュー/人気バッジ<br/>Feature/Embedding 除外]
    ASM --> OK200[200 data + meta]
    REPO -->|DB失敗| E500DB[500 GRS-DB-002 等]
    REPO -->|接続失敗| E503[503 GRS-DB-001]
    REPO -->|想定外| E999[500 GRS-ITM-999 / GRS-COM-999]
    OK200 --> METRIC[item_detail_request_count<br/>404時は item_not_found_count も]
    E400 --> METRIC
    E404 --> METRIC
    E422 --> METRIC
    E500DB --> METRIC
    E503 --> METRIC
    E999 --> METRIC
    METRIC --> END([完了])
```

### 4.2 処理詳細

1. **meta 解決:** `X-Trace-Id` / `X-Request-Id` は任意。指定時は Response `meta` へ一致反映。未指定時はサーバ採番可。
2. **Controller:** 認証なし。Request Body は使用しない。HTTP Method が `GET` 以外はルーティング層で拒否（405 等）。
3. **Path 検証:** `itemId` は必須・非空・最大長 **64**・許可文字 **英数字・`_`・`-`**。違反時は Repository を呼ばず **400 `GRS-REQ-001`**。
4. **Query 検証:** MVP では定義 Query なし。**任意 Query キーが 1 つでもあれば 400 `GRS-REQ-001`**（無視しない。契約仕様書 §6.3 / §9）。
5. **Repository:** `item_id` で `item` を取得 → 不存在 404 → `is_active` 判定 → 子テーブル LEFT JOIN / 別 SELECT で画像・レビュー・人気バッジを読取。
6. **Response 組立:** 契約どおり `data`（Public 表面フィールドのみ）+ `meta`（`traceId` / `requestId` / optional `generatedAt`）。`isActive: true` のみ 200 正常系。
7. **画像なし:** 主画像行なしでも **200**。`itemImageUrl` / `images` を省略。access log または metric 付帯情報で「画像なし」を観測可能にする（API一覧 §観測メモ。HTTP エラーにしない）。
8. **失敗 Response:** 契約仕様書 §8 の Error 形式。stack trace・SQL・接続文字列・`normalized_hash`・Feature 値を Response / ログ本文に出さない。
9. **metric:** 処理完了時に `item_detail_request_count` を記録。404 時は `item_not_found_count` も記録（§8）。422 / 5xx は `item_detail_request_count` のログ属性（`httpStatus` / `code`）で区別する（専用 metric 名は API一覧に未定義）。

---

## 5. データ項目マッピング

### 5.1 Request Mapping

| Request項目 | 内部項目 / DTO | 変換内容 | 備考 |
| ----------- | -------------- | -------- | ---- |
| Path `itemId` | `item.item_id` | 文字列 → UUID 解釈・存在確認 | 契約・OpenAPI `ItemIdPath` |
| （Body） | — | なし | GET。Body 不使用 |
| `X-Trace-Id` | `meta.trace_id` | 任意。未指定時サーバ採番可 | Response と一致 |
| `X-Request-Id` | `meta.request_id` | 任意。未指定時サーバ採番可 | Response と一致 |
| `Accept` | — | `application/json` 想定 | 厳密検証は実装 Task 任意 |
| 未知 Query | — | **400 `GRS-REQ-001`** | MVP は Query 未定義 |

### 5.2 Response Mapping（成功・200）

| 内部項目 / DTO | Response項目 | 変換内容 | 備考 |
| -------------- | ------------ | -------- | ---- |
| `item_id` | `data.itemId` | UUID → 文字列 | Path と一致。必須 |
| `item_name` | `data.itemName` | そのまま | 必須 |
| `price` | `data.itemPrice` | integer | 必須 |
| `item_url` | `data.itemUrl` | そのまま | 必須 |
| `catchcopy` | `data.itemCatchcopy` | そのまま | optional。NULL 時省略 |
| `item_caption` | `data.itemDescription` | そのまま | optional |
| `shop_code` | `data.shopName` | **MVP は省略可** | `item` に名称列なし（§3.5） |
| `external_genre_id` | `data.genreId` | bigint → string | optional |
| `external_genre.genre_name` | `data.genreName` | JOIN 導出 | `genreId` とセットで optional |
| `item_image.image_url`（`is_primary=true`） | `data.itemImageUrl` | 代表画像 | なし時省略 |
| `item_image` 全行 | `data.images[]` | `url` / `kind` / `isPrimary` | `display_order` 昇順。0 行時省略 |
| `item_image.image_size_type` | `data.images[].kind` | `small` / `medium` | optional |
| `item_image.is_primary` | `data.images[].isPrimary` | boolean | optional |
| `item_review_summary.review_average` | `data.reviewSummary.average` | number | 行なし時 `reviewSummary` 省略 |
| `item_review_summary.review_count` | `data.reviewSummary.count` | integer | 同上 |
| `item_popularity_signal.rank` + 固定 label | `data.popularityBadge` | `label` 固定 **`ランキング入り`**、`rank` は DB 値 | 明細なし時省略（§13.1 テーブル定義書） |
| `is_active` | `data.isActive` | boolean | 200 時は常に `true` |
| — | `meta.traceId` | meta から | — |
| — | `meta.requestId` | meta から | — |
| サーバ時刻 | `meta.generatedAt` | ISO 8601 | optional |

**Response に含めない項目（実装で明示除外）:**

| 区分 | 内部列 / リソース | 備考 |
| ---- | ----------------- | ---- |
| Feature / Meaning | `item_feature` / `item_meaning` 等 | Public 非公開（契約 §7.3.1） |
| Embedding | `item_embedding` 等 | Public 非公開 |
| 内部スコア | `popularityScore` / `finalScore` / Ranking 内部値 | Reco 文脈のみ |
| Batch / Raw | `normalized_hash` / `raw_product_metadata` / `staging_*` | 監査・Batch 専用 |
| Item 内部 | `source` / `external_item_code` / `active_status` / `shop_code` | 表面 ID・`isActive` 以外は非公開 |
| Popularity 内部 | `ranking_snapshot_id` / `external_item_code`（signal 側）/ `period` / `last_build_date`（badge 以外） | `popularityBadge.label` / `rank` のみ公開 |

### 5.3 Error Mapping（実装面）

| 内部状況 | HTTP | Error Code | 備考 |
| -------- | ---: | ---------- | ---- |
| `itemId` 空・形式不正・maxLength 超過 | 400 | `GRS-REQ-001` | Path 検証 |
| 未知 Query Parameter | 400 | `GRS-REQ-001` | 無視しない |
| `item_id` 不存在 | 404 | `GRS-ITM-001` | `item_not_found_count` 対象 |
| `is_active = false`（`inactive` / `unavailable` / `excluded` 含む） | 422 | `GRS-ITM-002` | 404 マスクしない |
| 画像なし | **200** | （エラーではない） | **`GRS-ITM-003` は返却しない** |
| DB 読取失敗 | 500 | `GRS-DB-002` | クエリ例外 |
| DB 接続失敗 | 500 / 503 | `GRS-DB-001` | 契約 §7.2 に従い 503 も可 |
| DB 想定外 | 500 | `GRS-DB-999` | — |
| Item 処理想定外 | 500 | `GRS-ITM-999` | — |
| 共通想定外 | 500 | `GRS-COM-999` | stack 非公開 |

詳細メッセージ・ユーザー向け表示は契約仕様書 §8・エラーコード定義書を正とする。

---

## 6. generated client 利用方針

| 項目 | 内容 |
| ---- | ---- |
| generated出力先 | `apps/web/src/generated/api/`（Orval。本 Task では再生成しない） |
| operationId | `getItemDetail` |
| client wrapper | `apps/web/src/lib/**` 配下の手書き wrapper（SCR-006 実装 Task で利用。本 Task では変更しない） |
| 再生成コマンド | プロジェクト標準の Orval 再生成（本 Task では実行しない） |
| 検証コマンド | typecheck / contract test（本 Task では実行しない） |

generated ファイルは手動編集しない。利用側は wrapper を介して generated client を呼ぶ。

---

## 7. provider / consumer 実装影響

### 7.1 provider

| 項目     | 内容 |
| -------- | ---- |
| provider | `apps/api` |
| 責務     | Public Item 詳細 API の提供 |
| 影響有無 | `あり`（後続実装 Task） |
| 必要対応 | `apps/api/src/app/items/**` 新規、Router mount、Item 系 DB 読取、metric / error 配線 |

- Item Detail Controller / Item Detail Repository の実装
- `/api/v1/items` 配下への Router 登録
- `item` + 子テーブル SELECT（§3.5）
- Path / Query 検証、404 / 422 / 画像なし 200 境界
- Error / meta / metric の既存共通部品（`ApiError` / `resolveRequestMeta`）との整合

### 7.2 consumer

| 項目     | 内容 |
| -------- | ---- |
| consumer | `apps/web`（SCR-006 / SCR-004 導線） |
| 責務     | 商品詳細画面表示、外部 EC 遷移、一覧からの詳細遷移 |
| 影響有無 | `あり`（画面実装 Task。本 Task では対象外） |
| 必要対応 | generated client（`getItemDetail`）経由で本 API を呼び、表示用フィールドを UI に反映 |

- API-PUB-002 Snapshot だけで足りる場合は本 API 呼び出しを省略可能（契約 §5.4）
- 404 / 422 / 画像なし（プレースホルダ）の画面ハンドリングは画面仕様書 Task で定義
- Feature / Embedding / 内部スコアを consumer 側で期待しない

---

## 8. ログ・監視

| 種別 | 内容 | 出力タイミング | 備考 |
| ---- | ---- | -------------- | ---- |
| API access log | method / path / status / latency / trace_id / itemId（表面 ID） | リクエスト完了時 | 個人情報・secret・SQL を含めない |
| error log | error.code / message（ユーザー向け以外の内部要約） / trace_id | 4xx / 5xx 発生時 | `normalized_hash`・Feature 値・接続文字列実値を出さない |
| audit log | なし | — | 参照のみ・非認証のため MVP では不要 |
| metric | `item_detail_request_count` | 成功・失敗とも処理完了時 | API一覧 §API-PUB-003 |
| metric | `item_not_found_count` | 404 `GRS-ITM-001` 時 | API一覧 §API-PUB-003 |
| 観測補助（ログ属性） | `httpStatus` / `code` / `hasPrimaryImage: false` 等 | 200 画像なし・422 inactive・5xx 時 | API一覧「商品なし、画像なしを観測」。専用 metric 名未定義のためログで補完 |

---

## 9. 実装テスト観点

|  No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | 正常系（active・画像あり） | 存在する active Item で 200。必須表面フィールド + optional（画像・レビュー・バッジ）が契約どおり | integration |
| 2 | 商品なし | 未知 `itemId` で 404 / `GRS-ITM-001`。`item_not_found_count` が増える | integration |
| 3 | 非 active | `is_active=false` で 422 / `GRS-ITM-002`（404 にならない） | integration |
| 4 | 画像なし | 画像行 0 件で 200。`itemImageUrl` / `images` 省略。`GRS-ITM-003` を返さない | integration |
| 5 | Path 検証 | 空 `itemId`・不正文字・maxLength 超過で 400 / `GRS-REQ-001` | integration |
| 6 | 未知 Query | `?foo=bar` で 400 / `GRS-REQ-001` | integration |
| 7 | 非公開列 | Response に Feature / Embedding / `normalized_hash` / 内部スコアが含まれない | integration |
| 8 | popularityBadge | 最新 Snapshot 明細あり時のみ `label=ランキング入り` + `rank`。なし時省略 | integration |
| 9 | DB 失敗 | 接続・クエリ失敗で 500 / 503 `GRS-DB-*` | integration |
| 10 | meta 伝播 | `X-Trace-Id` / `X-Request-Id` 指定時に Response meta と一致 | integration |
| 11 | metric | `item_detail_request_count` / `item_not_found_count` が記録境界どおり | unit / integration |
| 12 | generated client | `getItemDetail` 型と契約の整合（consumer Task） | typecheck |
| 13 | provider / consumer | SCR-006 が詳細表示に利用できること（画面 Task） | manual |

> 契約面の単体テスト観点（validation / auth / Request・Response schema）は契約仕様書を正とする。本 Task ではテストコードを追加しない。

---

## 10. 変更履歴

| 日付 | 変更内容 | 関連Issue / PR |
| ---- | -------- | -------------- |
| 2026-07-15 | 初版作成 | #1262 |

---

## 11. 未決事項

### 11.1 人間判断待ち

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
| 1 | Item Detail の MOD-ID 正式割当 | モジュール一覧に専用 ID が未記載。PUB-005 以降の番号体系と整合が必要 | Human | 実装 Task 前 | **推奨案:** MOD-API-014（Controller）/ MOD-API-015（Repository）。本書では論理名のみ使用 |
| 2 | `popularityBadge.label` の将来拡張 | MVP は固定文字列 `ランキング入り`（`item_popularity_signal_テーブル定義書` §13.1 / #504 確定）。period 別ラベル・閾値・多言語は未定 | Human | Post-MVP 検討可 | `rank` は DB 値をそのまま返す方針は確定 |
| 3 | `shopName` の導出元 | `item` は `shop_code` のみ。外部ショップマスタ DDL 未整備 | Human / 後続 Task | MVP 実装時 | MVP は **省略許容**。解決手段確定後に optional 返却 |

### 11.2 確定済み（本書へ反映済み・参考）

| No | 論点 | 確定内容 | 反映箇所 |
| --: | ---- | -------- | -------- |
| 1 | 非 active の HTTP Status | **422** + `GRS-ITM-002`（404 マスクしない） | §4.1 / §5.3 |
| 2 | 画像なし | **200** + `itemImageUrl` 省略。`GRS-ITM-003` は HTTP エラーにしない | §3.5 / §4.2 / §5.3 |
| 3 | 未知 Query | **400** + `GRS-REQ-001`（無視しない） | §3.5 / §4.2 |
| 4 | Feature / Embedding 非公開 | Response / Repository から除外 | §3.1 / §5.2 |
| 5 | Reco 非呼び出し | 読取専用。推薦パイプライン不使用 | §3.1 / §3.3 |

---

## 12. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| 契約仕様書 | `docs/06_実装設計/api/API-PUB-003_商品詳細取得API契約仕様書.md` | 前提契約 |
| テーブル定義 | `docs/06_実装設計/database/item_テーブル定義書.md` | Item 正本・active 判定 |
| テーブル定義 | `docs/06_実装設計/database/item_image_テーブル定義書.md` | 画像 URL・主画像 |
| テーブル定義 | `docs/06_実装設計/database/item_review_summary_テーブル定義書.md` | レビュー要約 |
| テーブル定義 | `docs/06_実装設計/database/item_popularity_signal_テーブル定義書.md` | popularityBadge・最新 Snapshot |
| テーブル定義 | `docs/06_実装設計/database/external_genre_テーブル定義書.md` | genreName JOIN |
| テーブル定義 | `docs/06_実装設計/database/ranking_snapshot_テーブル定義書.md` | 最新 Snapshot ヘッダ |
| OpenAPI | `packages/contracts/openapi/public-api.yaml` | `getItemDetail` |
| API一覧 | `docs/05_アプリケーション設計/アプリ/api/API一覧.md` | metric / 関連画面 |
| モジュール一覧 | `docs/05_アプリケーション設計/アプリ/モジュール一覧.md` | MOD-ID 割当（未記載） |
| エラーコード定義書 | `docs/05_アプリケーション設計/アプリ/エラーコード定義書.md` | GRS-ITM-* / GRS-DB-* |
| ログ設計書 | `docs/05_アプリケーション設計/アプリ/ログ・Observability設計書.md` | trace / metric |
| スタイル参考 | `docs/06_実装設計/api/API-PUB-005_Relationshipマスタ取得API実装仕様書.md` | GET 実装面 |
| スタイル参考 | `docs/06_実装設計/api/API-PUB-004_Feedback送信API実装仕様書.md` | DI / Router パターン |
| Task Definition | `prompts/definitions/tasks/api-pub-003-item-detail/api-implementation-spec.yaml` | 本 Task 条件 |
| 親 Epic | #385 | 作業管理 |

---

## 13. レビュー観点

- 確定済み API 契約（契約仕様書 / OpenAPI）と実装方針が整合している
- 実装面に限定され、Request / Response schema の契約再掲がない
- 処理フロー・Item Detail Controller / Repository・内部 DTO マッピングが明確である
- 404 `GRS-ITM-001` / 422 `GRS-ITM-002` / 画像なし 200 / 未知 Query 400 が契約と一致している
- Feature / Embedding / 内部スコアの非公開が明記されている
- `item_detail_request_count` / `item_not_found_count` が API一覧と一致している
- generated client を手動編集せず、本 Task ではファイル変更していない
- provider / consumer の実装影響が整理されている
- ログ・監視・結合テスト観点（§9）が整理されている
- MOD-ID 未確定が §11 に明示され、Human 判断事項が漏れていない
- secret や `.env` 実値が含まれていない

---

## 14. 備考

- 本 Task は Phase4b 縦串の 1/3（実装面仕様書）。後続は apps/api 実装 → 単体テスト → Epic PR → develop。
- Task PR target は親 Epic Branch `feature/epic-385-pub-003-item-detail`。
- API-PUB-002 `items[]` との表面フィールド命名整合は契約正本。本 API は詳細画面向け追加フィールド（説明・複数画像・レビュー summary 等）を optional で返却する。
- PUB-005 実装仕様書を GET 読取・metric スタイルの参考とした。DI パターンは `feedback` / `masters` の `create*Router(deps?)` に合わせる。
