# レコメンド実行 API契約仕様書

> 本書は **API-PUB-002** の契約面（Public I/F）正本である。
> 処理フロー・MOD-API 責務・内部 DTO マッピング・結合テスト観点は `API-PUB-002_レコメンド実行API実装仕様書.md`（別 Task）で定義する。
> OpenAPI 正本は `packages/contracts/openapi/public-api.yaml`（別 Contract Task）。

## 1. ドキュメント情報

| 項目           | 内容                                      |
| -------------- | ----------------------------------------- |
| ドキュメントID | `API-PUB-002-CONTRACT`                    |
| ドキュメント名 | レコメンド実行 API契約仕様書              |
| 対象システム   | Gift Recommendation Service MVP（Public） |
| MVP対象        | `○`                                       |
| 作成日         | 2026-06-02                                |
| 更新日         | 2026-06-04                                |

---

## 2. 概要

web（`apps/web`）から api（`apps/api`）へ、贈答条件に基づくギフト推薦実行を依頼する Public API である。api は内部で API-INT-002（Reco推薦実行）を呼び出すが、本書では **web↔api 間の HTTP 契約** のみを定義する。

---

## 3. 目的

- MVP 画面（レコメンド条件入力〜結果一覧）が利用する Request / Response / Error / Validation を確定する。
- 後続の OpenAPI Contract Task（`public-api.yaml`）および Contract Gate の入力とする。
- Recommendation Request / Result 定義書・API設計方針書・API一覧・エラーコード定義書と整合した契約面を提供する。

---

## 4. API基本情報

| 項目     | 内容                                              |
| -------- | ------------------------------------------------- |
| API ID   | `API-PUB-002`                                     |
| API名    | レコメンド実行                                    |
| API種別  | `Public API`                                      |
| Method   | `POST`                                            |
| Endpoint | `/api/v1/recommendations`                         |
| Base URL | 環境ごとに環境変数で定義（本書ではパスを正とする） |
| Version  | `v1`（URL パスに含む）                            |
| Provider | `apps/api`                                        |
| Consumer | `apps/web`                                        |
| 認証要否 | `false`（MVP は非認証。後続で Authorization 追加可） |
| 権限条件 | MVP ではなし                                      |
| 冪等性   | `非冪等`（同一条件の再実行は新規 Run として扱う） |
| MVP対象  | `○`                                               |

---

## 5. 利用シーン

### 5.1 利用タイミング

レコメンド条件入力画面（SCR-002）でユーザーが条件を入力し、「レコメンド実行」操作を行ったとき。

### 5.2 呼び出し元

- `apps/web`（レコメンド条件入力画面 / レコメンド実行中表示）

### 5.3 主なユースケース

- 贈答相手・用途・予算・好み・避けたい条件・NG 条件を送信し、推薦結果一覧を取得する。
- 候補 0 件の場合も HTTP 200 で空結果を受け取り、0 件結果画面へ遷移する。

### 5.4 内部 API 連携（契約上の前提のみ）

| 項目 | 内容 |
| ---- | ---- |
| 内部 API ID | `API-INT-002`（Reco推薦実行） |
| Method / Endpoint | `POST` `/internal/reco/v1/recommendations/run` |
| 呼び出し元 | `apps/api`（本 Public API の Provider） |
| 契約正本 | `docs/06_実装設計/api/API-INT-002_Reco推薦実行API契約仕様書.md` |
| 実装正本（参照のみ） | `docs/06_実装設計/api/API-INT-002_Reco推薦実行API実装仕様書.md` |
| 本書との境界 | Request/Response の **Public 向け表面**のみ本書で定義。api→reco 間の Request/Response 変換・モジュール責務は実装仕様書 Task で定義 |

---

## 6. Request仕様

### 6.1 Request Header

| Header         | 必須   | 内容                         | 例                                   |
| -------------- | ------ | ---------------------------- | ------------------------------------ |
| `Content-Type` | `true` | `application/json`           | `application/json`                   |
| `Accept`       | `true` | `application/json`           | `application/json`                   |
| `X-Trace-Id`   | `false` | 横断追跡 ID。未指定時は api 側で生成 | `550e8400-e29b-41d4-a716-446655440000` |
| `X-Request-Id` | `false` | API リクエスト ID。未指定時は api 側で生成 | `req_01HZYX`                         |

MVP では `Authorization` は使用しない。

### 6.2 Path Parameters

| 項目 | 型 | 必須 | 内容 | 例 |
| ---- | -- | ---- | ---- | -- |
| -    | -  | -    | なし | -  |

### 6.3 Query Parameters

| 項目 | 型 | 必須 | 内容 | 制約 | 例 |
| ---- | -- | ---- | ---- | ---- | -- |
| -    | -  | -    | なし | -    | -  |

複雑な条件は Query ではなく Request Body で受け取る（API設計方針書 §7.4）。

### 6.4 Request Body

Recommendation Request 定義書 §7.1（UI 向け）に準拠。フィールド名は API 外部 I/F として **camelCase** とする。

| 項目 | 型 | 必須 | 内容 | 制約 | 例 |
| ---- | -- | ---- | ---- | ---- | -- |
| `relationship` | `object` | `true` | 贈答相手（関係性） | `relationshipCode` 必須。`relationshipLabel` は表示用で任意 | 下記 Example |
| `relationship.relationshipCode` | `string` | `true` | 関係性コード | マスタ（API-PUB-005）のコード体系に整合 | `boss` |
| `relationship.relationshipLabel` | `string` | `false` | 関係性表示名 | 最大 **50** 文字（マスタコードが正） | `上司` |
| `occasion` | `object` | `true` | ギフト用途 | `occasionCode` 必須 | - |
| `occasion.occasionCode` | `string` | `true` | 用途コード | マスタ（API-PUB-006）のコード体系に整合 | `thanks` |
| `occasion.occasionLabel` | `string` | `false` | 用途表示名 | 最大 **50** 文字（マスタコードが正） | `お礼` |
| `budget` | `object` | `false` | 予算条件 | `budgetMin` / `budgetMax` は 0 以上。両方指定時は `budgetMin <= budgetMax` | - |
| `budget.budgetMin` | `integer` | `false` | 予算下限（JPY） | 0 以上 | `3000` |
| `budget.budgetMax` | `integer` | `false` | 予算上限（JPY） | 0 以上 | `5000` |
| `budget.currency` | `string` | `false` | 通貨 | MVP は `JPY` 固定想定 | `JPY` |
| `budget.taxIncluded` | `boolean` | `false` | 税込みフラグ | - | `true` |
| `preferredCondition` | `object` | `false` | 好み・期待する方向性 | `preferredText` を含む | - |
| `preferredCondition.preferredText` | `string` | `false` | 好みテキスト | 最大 **500** 文字 | `上品で感謝が伝わるもの` |
| `nonPreferredCondition` | `object` | `false` | 避けたい傾向 | `nonPreferredText` を含む | - |
| `nonPreferredCondition.nonPreferredText` | `string` | `false` | 避けたい条件テキスト | 最大 **500** 文字 | `カジュアルすぎるものは避けたい` |
| `ngCondition` | `object` | `false` | 絶対 NG 条件 | `ngText` を含む | - |
| `ngCondition.ngText` | `string` | `false` | NG テキスト | 最大 **300** 文字 | `アルコールはNG` |
| `freeText` | `string` | `false` | 自由記述 | 最大 **800** 文字 | `退職する上司へのお礼` |
| `execution` | `object` | `true` | 実行条件 | `mode` 必須 | - |
| `execution.mode` | `string` | `true` | 実行モード | `ui` / `evaluation` / `batch`。Public MVP 画面は **`ui` のみ** | `ui` |
| `execution.topK` | `integer` | `false` | 画面返却件数 | 1〜50。未指定時デフォルト **10** | `10` |
| `execution.candidateLimit` | `integer` | `false` | 候補抽出上限 | `topK` 以上。未指定時デフォルト **50**（ui） | `50` |
| `execution.includeReason` | `boolean` | `false` | 推薦理由を含めるか | ui ではデフォルト **true** | `true` |
| `execution.includeDebugInfo` | `boolean` | `false` | デバッグ情報 | Public MVP では **false** 固定想定 | `false` |

`evaluation` / `batch` モード用フィールド（`evalCaseId`、`configName` + `versionLabel` 等）は MVP Public 画面では送信しない。Internal / 評価系は別契約（API-INT-002）で扱う。

### 6.5 Request Example

```json
{
  "relationship": {
    "relationshipCode": "boss",
    "relationshipLabel": "上司"
  },
  "occasion": {
    "occasionCode": "thanks",
    "occasionLabel": "お礼"
  },
  "budget": {
    "budgetMin": 3000,
    "budgetMax": 5000,
    "currency": "JPY",
    "taxIncluded": true
  },
  "preferredCondition": {
    "preferredText": "上品で、感謝が伝わるもの"
  },
  "nonPreferredCondition": {
    "nonPreferredText": "カジュアルすぎるものは避けたい"
  },
  "ngCondition": {
    "ngText": "アルコールはNG"
  },
  "freeText": "退職する上司に、お礼として失礼がなく、少し気の利いたものを贈りたい",
  "execution": {
    "mode": "ui",
    "topK": 10,
    "candidateLimit": 50,
    "includeReason": true,
    "includeDebugInfo": false
  }
}
```

---

## 7. Response仕様

### 7.1 Response Header

| Header         | 内容              | 例                |
| -------------- | ----------------- | ----------------- |
| `Content-Type` | `application/json` | `application/json` |

### 7.2 Status Code

| Status | 意味 | 利用条件 |
| -----: | ---- | -------- |
| 200 | 処理成功（推薦結果あり、または 0 件の正常系） | 推薦パイプラインが完了し Response を返却できる場合 |
| 400 | Request 不正 | Validation エラー（GRS-REQ-001 等） |
| 422 | 業務的 Validation 失敗 | 未対応条件・厳しすぎる条件等（GRS-REQ-002 / 006 等） |
| 409 | 競合 | Run 状態不整合（GRS-REC-201 等） |
| 500 | 内部エラー | 想定内の処理失敗（GRS-REC-002 等、GRS-REQ-999 等） |
| 502 | 外部依存エラー | Reco / LLM / 外部 API 失敗 |
| 503 | 一時利用不可 | DB 接続失敗等 |
| 504 | タイムアウト | Reco 内部 API タイムアウト（GRS-REC-101） |

**0 件結果:** HTTP **200**。異常終了ではない（API設計方針書 §9.2、エラーコード定義書 `GRS-REC-001` 補足）。

### 7.3 Response Body

成功時は API設計方針書 §8.2 の **`data` + `meta`** 構造を基本とする。

#### 7.3.1 `data`（推薦成功・0 件共通）

| 項目 | 型 | 必須 | 内容 | 備考 |
| ---- | -- | ---- | ---- | ---- |
| `recommendationResultId` | `string` | `true` | 推薦結果 ID | Feedback（API-PUB-004）の前提 |
| `recommendationRequestId` | `string` | `true` | 推薦リクエスト ID | - |
| `recommendationRunId` | `string` | `true` | 推薦実行 ID | - |
| `resultStatus` | `string` | `true` | 結果状態 | enum: `completed` / `empty` / `partial`（OpenAPI Task で固定） |
| `topK` | `integer` | `true` | 要求返却件数 | Request の `execution.topK` を反映 |
| `resultItemCount` | `integer` | `true` | 返却 Item 件数 | 0 件時は `0` |
| `fallbackUsed` | `boolean` | `true` | Fallback 利用有無 | MVP では原則 `false` |
| `displayMessage` | `string` | `false` | 画面向け補足メッセージ | 0 件時に表示文案を載せる場合 |
| `items` | `array` | `true` | 推薦結果 Item 一覧 | 0 件時は **空配列 `[]`** |

#### 7.3.2 `data.items[]`（1 件あたり）

Public API では API設計方針書 §18.4 に従い、**内部スコア・スコア内訳は原則返却しない**。

| 項目 | 型 | 必須 | 内容 | 備考 |
| ---- | -- | ---- | ---- | ---- |
| `recommendationResultItemId` | `string` | `true` | 結果明細 ID | - |
| `itemId` | `string` | `true` | 商品 ID | API-PUB-003 連携 |
| `rank` | `integer` | `true` | 表示順位 | 1 始まり |
| `itemName` | `string` | `true` | 商品名 | Snapshot |
| `itemPrice` | `integer` | `true` | 価格（JPY） | Snapshot |
| `itemUrl` | `string` | `true` | 外部 EC 商品 URL | Snapshot |
| `itemImageUrl` | `string` | `false` | 代表画像 URL | なしの場合は画面側でプレースホルダ |
| `itemCatchcopy` | `string` | `false` | キャッチコピー | - |
| `shopName` | `string` | `false` | 店舗名 | - |
| `reasonSummary` | `string` | 条件付き | 推薦理由（短文） | `includeReason=true` かつ Item 存続時 **必須**（非空）。Reason 失敗時は §17.2 汎用 Reason（MOD-RECO-001 §10.3 / API-INT-002 §7.3.2.1 参照） |
| `reasonBadges` | `array` | `false` | 理由バッジ | 画面仕様に合わせて任意 |
| `cautionNote` | `string` | `false` | 注意表示 | 任意 |
| `isFallback` | `boolean` | `false` | Reason 汎用文由来か | api が Internal の `isFallback` をマッピング。`true` 時は汎用 Reason 表示（§7.3.2.1） |

#### 7.3.2.1 Reason フィールド（Public）

正本: API-INT-002 §7.3.2.1、MOD-RECO-001 モジュール仕様書 §10.3。

| 条件 | `reasonSummary` | `isFallback` | Item 存続 |
| ---- | --------------- | ------------ | --------- |
| `includeReason=false` | 省略 | 省略 | — |
| `includeReason=true` かつ Reason 成功 | **必須**（非空） | `false`（通常） | 存続 |
| `includeReason=true` かつ Reason のみ失敗 | **必須**（非空。§17.2 汎用 Reason） | `true` | **存続**（レコメンド結果はユーザーに表示） |

**返却しない項目（契約上明示）:** `finalScore`, `contextScore`, `popularityScore`, `riskPenalty`, `scoreBreakdown`, `modelVersionId`, `configName`, `versionLabel`, `reasonBasis`, `reasonStatus`, `debugPayload`, `embedding` 等。

#### 7.3.3 `meta`

| 項目 | 型 | 必須 | 内容 | 備考 |
| ---- | -- | ---- | ---- | ---- |
| `traceId` | `string` | `true` | 横断追跡 ID | Header `X-Trace-Id` を引き継ぎまたは生成 |
| `requestId` | `string` | `true` | API リクエスト ID | - |
| `generatedAt` | `string` | `false` | 生成日時（ISO 8601） | - |
| `resultCode` | `string` | `false` | 業務結果コード | 0 件時は `GRS-REC-001`（§7.4.2） |

### 7.4 Response Example

#### 7.4.1 推薦結果あり（200）

```json
{
  "data": {
    "recommendationResultId": "result_001",
    "recommendationRequestId": "request_001",
    "recommendationRunId": "run_001",
    "resultStatus": "completed",
    "topK": 10,
    "resultItemCount": 2,
    "fallbackUsed": false,
    "items": [
      {
        "recommendationResultItemId": "result_item_001",
        "itemId": "item_001",
        "rank": 1,
        "itemName": "上品な焼き菓子ギフトセット",
        "itemPrice": 4320,
        "itemUrl": "https://example.com/item/001",
        "itemImageUrl": "https://example.com/item/001.jpg",
        "shopName": "Example Shop",
        "reasonSummary": "上司へのお礼として失礼がなく、上品さと感謝の伝わりやすさのバランスが良いため候補にしています。"
      }
    ]
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440000",
    "requestId": "req_01HZYX",
    "generatedAt": "2026-06-02T12:00:00+09:00"
  }
}
```

#### 7.4.2 0 件結果（200）

```json
{
  "data": {
    "recommendationResultId": "result_002",
    "recommendationRequestId": "request_002",
    "recommendationRunId": "run_002",
    "resultStatus": "empty",
    "topK": 10,
    "resultItemCount": 0,
    "fallbackUsed": false,
    "displayMessage": "条件に合う商品が見つかりませんでした。条件を変更して再度お試しください。",
    "items": []
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440001",
    "requestId": "req_01HZYY",
    "generatedAt": "2026-06-02T12:01:00+09:00",
    "resultCode": "GRS-REC-001"
  }
}
```

> 0 件時は `data.resultStatus: "empty"`、`data.displayMessage`、`meta.resultCode: "GRS-REC-001"` を組み合わせて表現する（§14.1 No.2）。HTTP Status は常に 200 とする。

---

## 8. Error Response仕様

### 8.1 Error Response形式

エラー時も `meta.traceId` / `meta.requestId` を返す。`data` は返さないか `null` とする（OpenAPI Task で統一）。

```json
{
  "error": {
    "code": "GRS-REQ-004",
    "message": "贈る相手を選択してください。",
    "details": [
      {
        "field": "relationship.relationshipCode",
        "message": "relationshipCode is required"
      }
    ]
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
| 400 | `GRS-REQ-001` | 推薦条件が不正（型・形式・文字数超過等） | Validation 失敗 | 条件を確認してください。 |
| 400 | `GRS-REQ-004` | 関係性未指定 | 必須項目不足 | 贈る相手を選択してください。 |
| 400 | `GRS-REQ-005` | 用途未指定 | 必須項目不足 | ギフトの用途を選択してください。 |
| 422 | `GRS-REQ-002` | 未対応の条件組み合わせ | 業務 Validation | この条件では現在レコメンドできません。 |
| 422 | `GRS-REQ-006` | 条件が厳しすぎる | 業務 Validation | 条件を少し広げて再度お試しください。 |
| 500 | `GRS-REQ-999` | Request 保存失敗 | 内部エラー | 推薦条件の保存に失敗しました。 |
| 500 | `GRS-REC-002` | 推薦実行失敗 | Reco パイプライン失敗 | レコメンド処理に失敗しました。 |
| 500 | `GRS-REC-003`〜`013` | 各フェーズ失敗 | Reco 内部処理失敗 | レコメンド処理に失敗しました。 |
| 504 | `GRS-REC-101` | Reco タイムアウト | タイムアウト | レコメンド処理に時間がかかっています。 |
| 409 | `GRS-REC-201` | Run 状態不整合 | 競合 | レコメンド処理の状態が不正です。 |
| 500 | `GRS-REC-999` | Reco 想定外エラー | 内部エラー | 予期しないエラーが発生しました。 |
| 500 | `GRS-DB-001`〜`006` | DB 障害 | 永続化失敗 | データ処理に失敗しました。 |
| 500 | `GRS-DB-999` | DB 想定外 | 内部エラー | データ処理で予期しないエラー。 |
| 502 | `GRS-LLM-100`〜`104` | LLM / Embedding 失敗 | 外部依存 | レコメンド処理に失敗しました。 |
| 504 | `GRS-LLM-101` | LLM タイムアウト | タイムアウト | 処理に時間がかかっています。 |

`GRS-REC-001` は **HTTP 200** の正常系（0 件）として扱い、§7.4.2 を参照。エラー Response 一覧には含めない。

---

## 9. バリデーション仕様

| 対象項目 | ルール | エラーコード | エラーメッセージ |
| -------- | ------ | ------------ | ---------------- |
| `relationship.relationshipCode` | 必須・非空 | `GRS-REQ-004` | 贈る相手を選択してください。 |
| `occasion.occasionCode` | 必須・非空 | `GRS-REQ-005` | ギフトの用途を選択してください。 |
| `execution.mode` | 必須。Public MVP は `ui` のみ許可 | `GRS-REQ-001` | 条件を確認してください。 |
| `execution.topK` | 指定時 1〜50 | `GRS-REQ-001` | 条件を確認してください。 |
| `budget.budgetMin` / `budget.budgetMax` | 指定時 0 以上、かつ min ≤ max | `GRS-REQ-001` | 条件を確認してください。 |
| `execution.candidateLimit` | 指定時 `topK` 以上 | `GRS-REQ-001` | 条件を確認してください。 |
| テキスト最大長 | §6.4 の `maxLength` を超過しないこと | `GRS-REQ-001` | 条件を確認してください。 |
| JSON 形式 | パース可能であること | `GRS-REQ-001` | 条件を確認してください。 |

`budget` は業務必須としない（Human Review #359 反映）。`GRS-REQ-003`（予算未指定）は本 API では返却しない。

ドメイン定義書 §8.3 の条件矛盾（preferred と NG の競合等）は、api 側で **警告または NG 優先** とする。HTTP 422 / `GRS-REQ-006` への落とし込みは実装仕様書 Task で詳細化する。

---

## 10. OpenAPI / generated 反映方針

| 項目 | 内容 |
| ---- | ---- |
| OpenAPI正本 | `packages/contracts/openapi/public-api.yaml` |
| 操作 ID（案） | `createRecommendation` または `runRecommendation`（OpenAPI Task で確定） |
| Path | `/api/v1/recommendations` |
| components schema | `RecommendationRunRequest` / `RecommendationRunResponse` 等（OpenAPI Task で命名確定） |
| Orval設定 | リポジトリ正本 `orval.config.ts` |
| generated出力先（web） | `apps/web/src/generated/api/` |
| generated出力先（api→reco） | `apps/api/src/generated/reco-client/`（Internal は別 YAML） |
| OpenAPI定義書 | `openapi-spec.md` テンプレ準拠の Contract Task 成果物 |

本 Task では YAML / generated の**実変更は行わない**。本契約仕様書を 1b OpenAPI Contract Task の入力正本とする。

Contract Gate 通過後に Implementation Task（`api-implementation-spec`）および apps 実装 Task を開始する。

---

## 11. 互換性・破壊的変更

| 項目       | 内容 |
| ---------- | ---- |
| 破壊的変更 | MVP 初版のためなし |
| 後方互換性 | `v1` パス固定。フィールド追加は optional で許容 |
| 判断理由   | 初回 Public 契約確定 |

### 11.1 rollout order

- 本契約確定 → `public-api.yaml` 更新 → Orval 再生成 → web api-client 更新 → api 実装

---

## 12. 契約面テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | 正常系 | 必須項目のみで 200、`items` が 1 件以上 | contract |
| 2 | 0 件正常系 | 200、`items: []`、`resultItemCount: 0` | contract |
| 3 | validation error | 関係性・用途欠落で 400 + `GRS-REQ-004` / `005` | contract |
| 4 | 予算矛盾 | min > max で 400 + `GRS-REQ-001` | contract |
| 5 | trace 伝播 | `X-Trace-Id` 指定時に `meta.traceId` が一致 | contract |
| 6 | generated client | OpenAPI 生成後、型が Request/Response と一致 | typecheck |

実装結合・Reco 障害シミュレーションは実装仕様書・単体テスト Task で扱う。

---

## 13. 変更履歴

| 日付 | 変更内容 | 関連Issue / PR |
| ---- | -------- | -------------- |
| 2026-06-02 | 初版（契約面のみ。Task #358 / 分離後モデル） | #358 |
| 2026-06-04 | Human Review #359 反映（maxLength / 0件表現 / reasonSummary / resultStatus enum / 予算任意化） | #359 |
| 2026-06-25 | MOD-RECO-001 §10.3 整合：Reason 失敗時も非空 `reasonSummary` + `isFallback`（§7.3.2.1、§14.1 No.3 更新） | #764 |

---

## 14. 未決事項

現時点の未決事項はなし（Human Review #359 で §14.1 の論点を確定済み）。

### 14.1 Human Review 反映済み判断（PR #359）

| No | 論点 | 確定内容 | 備考 |
| --: | ---- | -------- | ---- |
| 1 | 自由入力・好み/NG テキストの最大文字数 | `preferredText` / `nonPreferredText`: **500**、`ngText`: **300**、`freeText`: **800**、`relationshipLabel` / `occasionLabel`: **50** | §6.4・§9。OpenAPI `maxLength` に反映 |
| 2 | 0 件時の `GRS-REC-001` の載せ方 | `meta.resultCode: "GRS-REC-001"` + `data.resultStatus: "empty"` + `data.displayMessage` | §7.4.2。HTTP Status は 200 |
| 3 | `reasonSummary` の必須/任意 | `includeReason=true` かつ Item 存続時は**必須**（非空）。Reason のみ失敗時は §17.2 汎用 Reason を返し `isFallback: true`。レコメンド結果はユーザーに表示する（#764 / MOD-RECO-001 §10.3 で #359 方針を更新） | §7.3.2.1 |
| 4 | `resultStatus` enum 値 | `completed` / `empty` / `partial` | OpenAPI enum で固定 |
| 5 | 予算の業務必須化 | **業務必須化しない**。`GRS-REQ-003` は本 API の Error 一覧から除外 | `budget` は Request 上 optional のまま |

---

## 15. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| API一覧 | `docs/05_アプリケーション設計/アプリ/api/API一覧.md` | API-PUB-002 行 |
| API設計方針書 | `docs/05_アプリケーション設計/アプリ/api/API設計方針書.md` | Request/Response/0件/非表示項目 |
| エラーコード定義書 | `docs/05_アプリケーション設計/アプリ/エラーコード定義書.md` | GRS-* |
| Recommendation Request | `docs/04_ドメインモデル設計/RecommendationRequest定義書.md` | Request Body |
| Recommendation Result | `docs/04_ドメインモデル設計/RecommendationResult定義書.md` | Response 項目のドメイン根拠 |
| 内部 API（参照） | `docs/06_実装設計/api/API-INT-002_Reco推薦実行API契約仕様書.md` | api→reco 間の Internal 契約 |
| Task Definition | `prompts/definitions/tasks/api-pub-002-recommendation-run/api-contract-spec.yaml` | #358 scope |
| 実装仕様（別Task） | `prompts/definitions/tasks/api-pub-002-recommendation-run/api-implementation-spec.yaml` | Phase4 |

---

## 16. レビュー観点

- API契約（Request / Response / Error / Validation）が明確で、OpenAPI Task の入力として十分か
- API設計方針書 §18（Public 非表示スコア）と矛盾していないか
- API一覧の API-PUB-002（endpoint / Method / Provider / Consumer / 0件方針）と一致しているか
- 実装面（MOD-API フロー等）を含んでいないか
- secret / `.env` 実値が含まれていないか

### 16.1 Human Review で確認してほしいこと

- 正式 Endpoint（`POST /api/v1/recommendations`）と MVP 非認証方針の最終確認
- OpenAPI Contract Task への分離方針の確認
- §14.1 の Human Review 反映内容が意図どおりか（再レビュー時）

---

## 17. 備考

- 本書は `prompts/templates/docs/api-contract-spec.md` に準拠した Phase1 ①（1a）成果物である。
- API-INT-002 への内部呼び出し契約は別文書。本書では web↔api の境界のみを正とする。
- ログ・Observability（access_log / phase_log / metric）の実装記録方針は実装仕様書で扱う。契約上は `traceId` の往復を必須とする。
