# 商品詳細取得 API契約仕様書

> 本書は **API-PUB-003** の契約面（Public I/F）正本である。
> Item 参照 Repository・MOD-API 責務・内部 DTO マッピング・結合テスト観点は `API-PUB-003_商品詳細取得API実装仕様書.md`（別 Task）で定義する。
> OpenAPI 正本は `packages/contracts/openapi/public-api.yaml`（別 Contract Task）。

## 1. ドキュメント情報

| 項目           | 内容                                      |
| -------------- | ----------------------------------------- |
| ドキュメントID | `API-PUB-003-CONTRACT`                    |
| ドキュメント名 | 商品詳細取得 API契約仕様書                |
| 対象システム   | Gift Recommendation Service MVP（Public） |
| MVP対象        | `○`                                       |
| 作成日         | 2026-06-05                                |
| 更新日         | 2026-06-05（Human Review #405 反映）      |

---

## 2. 概要

web（`apps/web`）から api（`apps/api`）へ、指定 `itemId` の商品詳細を取得する Public API である。関連リソースは **Item / Item Image / External Item Reference / Popularity Signal** であり、Response では商品詳細画面（SCR-006）およびレコメンド結果一覧画面向けの **表示用商品情報**（商品名、説明、キャッチコピー、価格、画像 URL、外部 EC URL、レビュー情報等）を返す（[API一覧](../../05_アプリケーション設計/アプリ/api/API一覧.md) §API-PUB-003）。

レコメンド結果一覧（API-PUB-002）の `items[]` に含まれる Snapshot 情報で足りる場合、本 API 呼び出しは省略可能（API一覧 §関連画面）。

---

## 3. 目的

- 商品詳細画面・外部 EC 遷移に必要な Request / Response / Error / Validation を確定する。
- 後続の OpenAPI Contract Task（`public-api.yaml`）および Contract Gate の入力とする。
- Item 系リソース正本定義・API設計方針書・API一覧・エラーコード定義書・API-PUB-002 `items[]` 表面フィールドと整合した契約面を提供する。

---

## 4. API基本情報

| 項目     | 内容                                              |
| -------- | ------------------------------------------------- |
| API ID   | `API-PUB-003`                                     |
| API名    | 商品詳細取得                                      |
| API種別  | `Public API`                                      |
| Method   | `GET`                                             |
| Endpoint | `/api/v1/items/{itemId}`                          |
| Base URL | 環境ごとに環境変数で定義（本書ではパスを正とする） |
| Version  | `v1`（URL パスに含む）                            |
| Provider | `apps/api`                                        |
| Consumer | `apps/web`                                        |
| 認証要否 | `false`（MVP は非認証。後続で Authorization 追加可） |
| 権限条件 | MVP ではなし                                      |
| 冪等性   | `冪等`（同一 `itemId` の GET は副作用なし）       |
| MVP対象  | `○`                                               |

---

## 5. 利用シーン

### 5.1 利用タイミング

- 商品詳細画面（SCR-006）表示時
- レコメンド結果一覧から商品詳細へ遷移する際（API-PUB-002 の Snapshot だけでは不足する場合）
- 外部 EC（楽天商品ページ等）への遷移前に最新の商品表示情報を確認する場合

### 5.2 呼び出し元

- `apps/web`（商品詳細画面 / レコメンド結果一覧画面）

### 5.3 主なユースケース

- `itemId` を指定して商品詳細を取得する。
- 商品が存在しない場合は HTTP **404** と `GRS-ITM-001` を返す（API一覧 §API-PUB-003）。
- 非 active 商品は HTTP **422** と `GRS-ITM-002` を返す（Human Review #405 で確定。§14.1 参照）。
- 画像がない場合は HTTP **200** の正常系とし、`itemImageUrl` を省略する（API-PUB-002 `items[]` と同方針。画面側プレースホルダ）。

### 5.4 API-PUB-002 との関係（契約上の前提のみ）

| 項目 | 内容 |
| ---- | ---- |
| 関連 Public API | `API-PUB-002`（レコメンド実行） |
| 連携キー | `itemId` |
| 契約正本 | [API-PUB-002_レコメンド実行API契約仕様書.md](./API-PUB-002_レコメンド実行API契約仕様書.md) §7.3.2 |
| 本書との境界 | 推薦結果 Snapshot に含まれる表面フィールド（`itemName` / `itemPrice` / `itemUrl` 等）は **同一命名・意味** を維持する。本 API は詳細画面向けに **追加フィールド**（説明文、複数画像、レビュー summary 等）を返却可能 |

---

## 6. Request仕様

### 6.1 Request Header

| Header         | 必須    | 内容               | 例                                   |
| -------------- | ------- | ------------------ | ------------------------------------ |
| `Accept`       | `true`  | `application/json` | `application/json`                   |
| `X-Trace-Id`   | `false` | 横断追跡 ID        | `550e8400-e29b-41d4-a716-446655440000` |
| `X-Request-Id` | `false` | API リクエスト ID  | `req_01HZYX`                         |

MVP では `Authorization` は使用しない。GET のため `Content-Type` は不要。

### 6.2 Path Parameters

| 項目     | 型       | 必須   | 内容     | 例         |
| -------- | -------- | ------ | -------- | ---------- |
| `itemId` | `string` | `true` | 商品 ID  | `item_001` |

- 本サービス内部の Item 識別子（DB 上の item_id）を正とする。
- 空文字・空白のみは Validation エラー（`GRS-REQ-001`）。

### 6.3 Query Parameters

| 項目 | 型 | 必須 | 内容 | 制約 | 例 |
| ---- | -- | ---- | ---- | ---- | -- |
| -    | -  | -    | なし | -    | -  |

MVP では Query Parameter を定義しない。未定義 Query を受け付けた場合は HTTP **400** と `GRS-REQ-001` を返す（Human Review #405 で確定。§14.1 参照）。将来、表示言語や画像サイズ指定が必要になった場合は optional で追加可能（破壊的変更に該当しない追加のみ）。

### 6.4 Request Body

なし（GET では Request Body を使用しない。API設計方針書 §6）。

### 6.5 Request Example

```http
GET /api/v1/items/item_001 HTTP/1.1
Host: api.example.com
Accept: application/json
X-Trace-Id: 550e8400-e29b-41d4-a716-446655440000
```

---

## 7. Response仕様

### 7.1 Response Header

| Header         | 内容               | 例                |
| -------------- | ------------------ | ----------------- |
| `Content-Type` | `application/json` | `application/json` |

### 7.2 Status Code

| Status | 意味 | 利用条件 |
| -----: | ---- | -------- |
| 200 | 処理成功 | 商品が存在し、Public 表示可能な Item 詳細を返却できる場合 |
| 400 | Request 不正 | Path Parameter 形式不正等（`GRS-REQ-001`） |
| 404 | 商品なし | 指定 `itemId` が存在しない（`GRS-ITM-001`） |
| 422 | 業務的 Validation 失敗 | 非 active 商品等（`GRS-ITM-002`） |
| 500 | 内部エラー | DB 障害・想定外エラー（`GRS-DB-*` / `GRS-ITM-999`） |
| 503 | 一時利用不可 | DB 接続失敗等（`GRS-DB-001`） |

**画像なし:** HTTP **200** の正常系。`GRS-ITM-003` は Public 詳細取得では **HTTP エラーとして返却しない**（メトリクス `item_detail_request_count` で観測。API一覧 §観測メモ）。

### 7.3 Response Body

成功時は API設計方針書 §8.2 の **`data` + `meta`** 構造を基本とする。主データは **Item** リソースの Public 表面表現とする。

Public API では API設計方針書 §18.4 に従い、**Feature / Embedding / 内部スコア / 生の Popularity 計算値** は返却しない。

#### 7.3.1 `data`（Item 詳細）

| 項目 | 型 | 必須 | 内容 | 備考 |
| ---- | -- | ---- | ---- | ---- |
| `itemId` | `string` | `true` | 商品 ID | Path と一致 |
| `itemName` | `string` | `true` | 商品名 | Item 正本（楽天商品検索 API 由来） |
| `itemPrice` | `integer` | `true` | 価格（JPY） | 税込表示前提は画面側方針に従う |
| `itemUrl` | `string` | `true` | 外部 EC 商品 URL | External Item Reference 表面。楽天商品ページ遷移用 |
| `itemImageUrl` | `string` | `false` | 代表画像 URL | Item Image 主画像。なしの場合は省略（UI プレースホルダ） |
| `itemCatchcopy` | `string` | `false` | キャッチコピー | API-PUB-002 `items[]` と同名 |
| `itemDescription` | `string` | `false` | 商品説明 | Item Caption 相当。詳細画面向け |
| `shopName` | `string` | `false` | 店舗名 | API-PUB-002 `items[]` と同名 |
| `genreId` | `string` | `false` | ジャンル ID | 表示補助。MVP Response に optional で含める（Human Review #405 確定）。Feature 推定の内部値は含めない |
| `genreName` | `string` | `false` | ジャンル名 | 表示補助。`genreId` とセットで optional 返却 |
| `reviewSummary` | `object` | `false` | レビュー概要 | Item Review Summary 表面 |
| `reviewSummary.average` | `number` | `false` | レビュー平均 | 例: `4.2` |
| `reviewSummary.count` | `integer` | `false` | レビュー件数 | 例: `128` |
| `images` | `array` | `false` | 画像 URL 一覧 | Item Image 複数枚。要素は下記 |
| `images[].url` | `string` | `true` | 画像 URL | `images` 指定時必須 |
| `images[].kind` | `string` | `false` | 画像種別 | enum 案: `medium` / `small`（OpenAPI Task で固定） |
| `images[].isPrimary` | `boolean` | `false` | 代表画像フラグ | 1 件を `true` とする |
| `popularityBadge` | `object` | `false` | 人気表示用バッジ | Popularity Signal の **表示用** 表面のみ。MVP Response に optional で含める（Human Review #405 確定） |
| `popularityBadge.label` | `string` | `false` | 表示ラベル | 例: `ランキング入り` |
| `popularityBadge.rank` | `integer` | `false` | ランキング順位 | 内部スコアは含めない |
| `isActive` | `boolean` | `true` | 推薦・表示対象か | `true` のみ 200 正常系（`false` は §7.2 の 422） |

**返却しない項目（契約上明示）:** `itemFeature`, `itemEmbedding`, `featureValues`, `embedding`, `popularityScore`, `finalScore`, `rawProductJson`, `contentHash`, `batchRunId`, `externalApiKey` 等。

#### 7.3.2 `meta`

| 項目 | 型 | 必須 | 内容 | 備考 |
| ---- | -- | ---- | ---- | ---- |
| `traceId` | `string` | `true` | 横断追跡 ID | Header `X-Trace-Id` を引き継ぎまたは生成 |
| `requestId` | `string` | `true` | API リクエスト ID | - |
| `generatedAt` | `string` | `false` | 応答生成日時（ISO 8601） | - |

### 7.4 Response Example

#### 7.4.1 正常系（200）

```json
{
  "data": {
    "itemId": "item_001",
    "itemName": "上品な焼き菓子ギフトセット",
    "itemPrice": 4320,
    "itemUrl": "https://example.com/item/001",
    "itemImageUrl": "https://example.com/item/001.jpg",
    "itemCatchcopy": "贈答にふさわしい上質な焼き菓子",
    "itemDescription": "厳選した素材を使用した、上品な味わいの焼き菓子詰め合わせです。",
    "shopName": "Example Shop",
    "genreId": "100227",
    "genreName": "スイーツ・お菓子",
    "reviewSummary": {
      "average": 4.2,
      "count": 128
    },
    "images": [
      {
        "url": "https://example.com/item/001.jpg",
        "kind": "medium",
        "isPrimary": true
      }
    ],
    "popularityBadge": {
      "label": "ランキング入り",
      "rank": 12
    },
    "isActive": true
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440000",
    "requestId": "req_01HZYX",
    "generatedAt": "2026-06-05T12:00:00+09:00"
  }
}
```

#### 7.4.2 画像なし正常系（200）

```json
{
  "data": {
    "itemId": "item_002",
    "itemName": "詰め合わせギフト",
    "itemPrice": 2980,
    "itemUrl": "https://example.com/item/002",
    "itemDescription": "手軽に贈れる詰め合わせギフトです。",
    "isActive": true
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440001",
    "requestId": "req_01HZYY"
  }
}
```

> `itemImageUrl` / `images` を省略し、HTTP 200 とする。画面側でプレースホルダ表示（API-PUB-002 §7.3.2 準拠）。

---

## 8. Error Response仕様

### 8.1 Error Response形式

エラー時も `meta.traceId` / `meta.requestId` を返す。`data` は返さないか `null` とする（OpenAPI Task で統一）。

```json
{
  "error": {
    "code": "GRS-ITM-001",
    "message": "商品情報が見つかりません。",
    "details": []
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440002",
    "requestId": "req_01HZYZ"
  }
}
```

### 8.2 Error一覧（本 API で想定する代表）

| Status | Error Code | 発生条件 | Response概要 | ユーザー向け表示 |
| -----: | ---------- | -------- | ------------ | ---------------- |
| 400 | `GRS-REQ-001` | `itemId` 形式不正（空・不正文字等） | Validation 失敗 | 条件を確認してください。 |
| 404 | `GRS-ITM-001` | 指定 `itemId` が存在しない | Item Not Found | 商品情報が見つかりません。 |
| 422 | `GRS-ITM-002` | 非 active 商品（表示対象外） | Item Inactive | この商品は現在表示できません。 |
| 500 | `GRS-DB-001` | DB 接続失敗 | 永続化基盤障害 | データ処理に失敗しました。 |
| 500 | `GRS-DB-002` | DB 参照失敗 | 読取失敗 | データ取得に失敗しました。 |
| 500 | `GRS-DB-999` | DB 想定外 | 内部エラー | データ処理で予期しないエラー。 |
| 500 | `GRS-ITM-999` | Item 処理想定外 | 内部エラー | 商品情報の処理でエラーが発生しました。 |
| 503 | `GRS-DB-001` | DB 一時不可 | サービス一時停止 | データ処理に失敗しました。 |

**Public 詳細取得で HTTP エラーとして返却しない代表:**

| Error Code | 理由 |
| ---------- | ---- |
| `GRS-ITM-003` | 画像なしは 200 正常系（optional フィールド省略） |
| `GRS-ITM-004`〜`006` | Feature / Embedding / Snapshot 不足は Reco / Batch 文脈。Public 詳細取得の契約 Error 一覧外 |

`GRS-REC-*` / `GRS-LLM-*` は本 Public Item API の契約 Error 一覧には含めない。

---

## 9. バリデーション仕様

| 対象項目 | ルール | エラーコード | エラーメッセージ |
| -------- | ------ | ------------ | ---------------- |
| HTTP Method | `GET` のみ許可 | - | ルーティング層で拒否（405 等は実装仕様書で定義） |
| `itemId` | 必須・非空・最大長 **64** | `GRS-REQ-001` | 条件を確認してください。 |
| `itemId` | 許可文字: 英数字・`_`・`-` | `GRS-REQ-001` | 条件を確認してください。 |
| Request Body | 送信しない | - | GET では Body なし |
| 未知 Query | MVP では未定義 Query を受け付けない（HTTP 400） | `GRS-REQ-001` | 条件を確認してください。 |

存在確認・active 判定は Repository 層で行い、HTTP Status / Error Code は §8.2 にマッピングする（実装詳細は api-implementation-spec Task）。

---

## 10. OpenAPI / generated 反映方針

| 項目 | 内容 |
| ---- | ---- |
| OpenAPI正本 | `packages/contracts/openapi/public-api.yaml` |
| 操作 ID（案） | `getItemDetail` または `getItemById`（OpenAPI Task で確定） |
| Path | `/api/v1/items/{itemId}` |
| Path parameter | `itemId`（required, string） |
| components schema | `ItemDetailResponse` / `ItemDetail` / `ItemReviewSummary` / `ItemImage` 等（OpenAPI Task で命名確定） |
| Orval設定 | リポジトリ正本 `orval.config.ts` |
| generated出力先（web） | `apps/web/src/generated/api/` |
| OpenAPI定義書 | `openapi-spec.md` テンプレ準拠の Contract Task 成果物 |

本 Task では YAML / generated の**実変更は行わない**。本契約仕様書を 1b OpenAPI Contract Task の入力正本とする。

Contract Gate 通過後に Implementation Task（`api-implementation-spec`）および apps 実装 Task を開始する。

---

## 11. 互換性・破壊的変更

| 項目       | 内容 |
| ---------- | ---- |
| 破壊的変更 | MVP 初版のためなし |
| 後方互換性 | `v1` パス固定。フィールド追加は optional で許容 |
| 判断理由   | 初回 Public Item Detail 契約確定 |

### 11.1 rollout order

- 本契約確定 → `public-api.yaml` 更新 → Orval 再生成 → web api-client 更新 → api 実装

---

## 12. 契約面テスト観点

|  No | 観点             | 確認内容 | 種別 |
| --: | ---------------- | -------- | ---- |
|   1 | 正常系           | 存在する active Item で 200、`data.itemId` / 必須表面フィールドが返る | contract |
|   2 | 商品なし         | 未知 `itemId` で 404 / `GRS-ITM-001` | contract |
|   3 | 非 active        | 非 active Item で 422 / `GRS-ITM-002` | contract |
|   4 | 画像なし         | 画像なし Item で 200、`itemImageUrl` 省略 | contract |
|   5 | validation error | 空 `itemId` で 400 / `GRS-REQ-001` | contract |
|   6 | auth error       | MVP 非認証のため N/A（将来 Authorization 追加時に再定義） | contract |
|   7 | generated client | OpenAPI 確定後、Orval 生成型と Response schema 一致 | typecheck |

> 実装結合・Repository 異常系の統合テスト観点は `api-implementation-spec.md` に記載する。

---

## 13. 変更履歴

| 日付 | 変更内容 | 関連Issue / PR |
| ---- | -------- | -------------- |
| 2026-06-05 | 初版（Phase1 1a 契約面） | Issue #399 |
| 2026-06-05 | Human Review #405 反映（非 active 422 / optional フィールド / itemId 制約 / 未知 Query 400） | PR #405 |

---

## 14. 未決事項

現時点の未決事項はなし（Human Review #405 で §14.1 の論点を確定済み）。

### 14.1 Human Review 反映済み判断（PR #405）

| No | 論点 | 確定内容 | 備考 |
| --: | ---- | -------- | ---- |
| 1 | 非 active 商品の HTTP Status | HTTP **422** + `GRS-ITM-002`（404 マスクは採用しない） | §5.3・§7.2・§8.2 |
| 2 | `popularityBadge` / `genreId` を MVP Response に含めるか | **optional で含める**（データがない場合は省略） | §7.3.1 |
| 3 | `itemId` 最大長・許可文字 | 最大長 **64**、許可文字 **英数字・`_`・`-`** | §9。OpenAPI `maxLength` / `pattern` に反映 |
| 4 | 未知 Query Parameter の扱い | HTTP **400** + `GRS-REQ-001`（無視しない） | §6.3・§9 |

---

## 15. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| API一覧 | `docs/05_アプリケーション設計/アプリ/api/API一覧.md` | API-PUB-003 行 |
| API設計方針書 | `docs/05_アプリケーション設計/アプリ/api/API設計方針書.md` | URL / Error / data+meta |
| エラーコード定義書 | `docs/05_アプリケーション設計/アプリ/エラーコード定義書.md` | GRS-ITM-* / GRS-DB-* |
| 正本定義表 | `docs/05_アプリケーション設計/アプリ/database/正本定義表.md` | Item 系正本 |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-PUB-003 |
| 関連契約 | `docs/06_実装設計/api/API-PUB-002_レコメンド実行API契約仕様書.md` | items[] 表面整合 |
| 契約テンプレ | `prompts/templates/docs/api-contract-spec.md` | 章構成 |

---

## 16. レビュー観点

### 16.1 Human Review で確認してほしいこと

- §14.1 の Human Review 反映内容が意図どおりか（再レビュー時）

### 16.2 一般レビュー観点

- API契約（Request / Response / Error / Validation）が明確で確定可能である
- API設計方針書・API一覧と整合している
- Item 系リソースの Public 表面のみを返却し、Feature / Embedding を含まない
- API-PUB-002 `items[]` とのフィールド命名整合が明記されている
- 商品不存在 404（`GRS-ITM-001`）方針が明記されている
- OpenAPI（`packages/contracts/openapi/*.yaml`）への反映方針が明確である
- 破壊的変更有無と後方互換性が明記されている
- 実装詳細（Repository / MOD-API フロー）を含めず契約面に限定している
- secret や `.env` 実値が含まれていない

---

## 17. 備考

- メトリクス: `item_detail_request_count` / `item_not_found_count`（API一覧 §API-PUB-003）
- trace_id: 必須（API一覧 §trace_id対象）
- 楽天商品ページへの外部遷移に必要な情報（`itemUrl` 等）を Response に含める（API一覧 備考）
