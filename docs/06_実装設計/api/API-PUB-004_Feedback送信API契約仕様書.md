# Feedback送信 API契約仕様書

> 本書は **API-PUB-004** の契約面（Public I/F）正本である。
> 処理フロー・MOD-API-007〜010 責務・内部 DTO マッピング・結合テスト観点は `API-PUB-004_Feedback送信API実装仕様書.md`（別 Task）で定義する。
> OpenAPI 正本は `packages/contracts/openapi/public-api.yaml`（別 Contract Task）。

## 1. ドキュメント情報

| 項目           | 内容                                      |
| -------------- | ----------------------------------------- |
| ドキュメントID | `API-PUB-004-CONTRACT`                    |
| ドキュメント名 | Feedback送信 API契約仕様書                |
| 対象システム   | Gift Recommendation Service MVP（Public） |
| MVP対象        | `○`                                       |
| 作成日         | 2026-06-05                                |
| 更新日         | 2026-06-05（Human Review 指摘反映）       |

---

## 2. 概要

web（`apps/web`）から api（`apps/api`）へ、表示済みの Recommendation Result（または Result Item / Reason）に対するユーザー Feedback を登録する Public API である。Feedback は推薦品質改善・評価・分析の入力データとして蓄積する（[Recommendation Feedback定義書](../../04_ドメインモデル設計/RecommendationFeedback定義書.md)）。

---

## 3. 目的

- MVP 画面（Feedback入力表示 / レコメンド結果一覧 / 推薦理由詳細）が利用する Request / Response / Error / Validation を確定する。
- 後続の OpenAPI Contract Task（`public-api.yaml`）および Contract Gate の入力とする。
- Recommendation Feedback 定義書・API設計方針書・API一覧・エラーコード定義書と整合した契約面を提供する。

---

## 4. API基本情報

| 項目     | 内容                                                              |
| -------- | ----------------------------------------------------------------- |
| API ID   | `API-PUB-004`                                                     |
| API名    | Feedback送信                                                      |
| API種別  | `Public API`                                                      |
| Method   | `POST`                                                            |
| Endpoint | `/api/v1/recommendation-results/{resultId}/feedback`              |
| Base URL | 環境ごとに環境変数で定義（本書ではパスを正とする）                 |
| Version  | `v1`（URL パスに含む）                                            |
| Provider | `apps/api`                                                        |
| Consumer | `apps/web`                                                        |
| 認証要否 | `false`（MVP は匿名 Feedback。後続で Authorization 追加可）       |
| 権限条件 | MVP ではなし                                                      |
| 冪等性   | `条件付き`（`sessionId` + 同一対象 + 同一 `feedbackType` の再送は更新扱い。Recommendation Feedback 定義書 §13.2 準拠） |
| MVP対象  | `○`                                                               |

---

## 5. 利用シーン

### 5.1 利用タイミング

- レコメンド結果一覧画面または推薦理由詳細表示で、ユーザーが商品候補・推薦理由・結果全体に対する Feedback を送信したとき。
- Feedback入力モーダル（SCR-007）から送信したとき。

### 5.2 呼び出し元

- `apps/web`（Feedback入力表示 / レコメンド結果一覧画面 / 推薦理由詳細表示）

### 5.3 主なユースケース

- Result Item 単位で `item_good` / `item_bad` / `item_not_match` 等の Feedback を登録する。
- Reason 単位で `reason_good` / `reason_bad` 等の Feedback を登録する。
- Result 全体に対する `result_good` / `result_bad` または自由コメント（`comment`）を登録する。
- 登録成功時に Feedback 受付結果と `traceId` を受け取り、画面に完了表示する。

---

## 6. Request仕様

### 6.1 Request Header

| Header         | 必須    | 内容                         | 例                                   |
| -------------- | ------- | ---------------------------- | ------------------------------------ |
| `Content-Type` | `true`  | `application/json`           | `application/json`                   |
| `Accept`       | `true`  | `application/json`           | `application/json`                   |
| `X-Trace-Id`   | `false` | 横断追跡 ID。未指定時は api 側で生成 | `550e8400-e29b-41d4-a716-446655440000` |
| `X-Request-Id` | `false` | API リクエスト ID。未指定時は api 側で生成 | `req_01HZYX`                         |

MVP では `Authorization` は使用しない。

### 6.2 Path Parameters

| 項目       | 型       | 必須   | 内容                         | 例            |
| ---------- | -------- | ------ | ---------------------------- | ------------- |
| `resultId` | `string` | `true` | 対象 Recommendation Result ID | `result_001` |

Path の `resultId` は [API-PUB-002](./API-PUB-002_レコメンド実行API契約仕様書.md) Response の `data.recommendationResultId` と一致する。

### 6.3 Query Parameters

| 項目 | 型 | 必須 | 内容 | 制約 | 例 |
| ---- | -- | ---- | ---- | ---- | -- |
| -    | -  | -    | なし | -    | -  |

### 6.4 Request Body

Recommendation Feedback 定義書 §7.1 に準拠。フィールド名は API 外部 I/F として **camelCase** とする（[API一覧](../../05_アプリケーション設計/アプリ/api/API一覧.md) §API-PUB-004 の `resultItemId` / `feedbackType` / `rating` / `reasonFeedback` / `comment` 等を包含）。

| 項目 | 型 | 必須 | 内容 | 制約 | 例 |
| ---- | -- | ---- | ---- | ---- | -- |
| `feedbackTargetType` | `string` | `true` | Feedback 対象粒度 | enum: `result` / `item` / `reason` | `item` |
| `resultItemId` | `string` | 条件付き | 対象 Result Item ID | `feedbackTargetType` が `item` のとき **必須**。Path `resultId` に属する Item であること | `result_item_001` |
| `reasonId` | `string` | 条件付き | 対象 Reason ID | `feedbackTargetType` が `reason` のとき **必須** | `reason_001` |
| `feedbackType` | `string` | `true` | Feedback 種別 | MVP 許容値は §6.4.1 参照 | `item_good` |
| `feedbackValueType` | `string` | `false` | 値の形式 | enum: `boolean` / `rating` / `choice` / `text` / `event`。未指定時は `feedbackType` から推定 | `boolean` |
| `feedbackValue` | `boolean` / `number` / `string` | 条件付き | Feedback 値 | `feedbackValueType` に応じた型・範囲 | `true` |
| `feedbackChoiceCode` | `string` | 条件付き | 選択式 Feedback コード | `item_not_match` 等で使用。定義書 §7.2 の category と整合 | `too_casual` |
| `feedbackReasonCategory` | `string` | `false` | 不満・違和感の分類 | 定義書 §7.2 MVP category | `context_mismatch` |
| `rating` | `integer` | `true` | 1〜5 評価 | **1〜5** の整数（MVP 必須） | `4` |
| `comment` | `string` | `false` | 自由コメント（`feedback_text`） | 最大 **500** 文字 | `上司へのお礼としては少しカジュアルに見えます` |
| `sourcePage` | `string` | `false` | 入力元画面識別子 | SCR-007 等の画面 ID | `SCR-007` |
| `sessionId` | `string` | `false` | セッション識別子 | MVP 匿名 Feedback 用。個人情報を含めない | `sess_abc123` |

**命名対応（API一覧 ↔ 本契約）:**

| API一覧（概要列） | 本契約フィールド |
| ----------------- | ---------------- |
| `resultItemId`    | `resultItemId`   |
| `feedbackType`    | `feedbackType`   |
| `rating`          | `rating`         |
| `reasonFeedback`  | `feedbackType` が `reason_good` / `reason_bad` 等の Reason 向け種別、または `feedbackTargetType: reason` と組み合わせ |
| `comment`         | `comment`        |

#### 6.4.1 MVP で許容する `feedbackType`

Recommendation Feedback 定義書 §5.2 に準拠。

| feedbackType        | 必須 `feedbackTargetType` | 概要                   |
| ------------------- | ------------------------- | ---------------------- |
| `item_good`         | `item`                    | 商品候補として良い     |
| `item_bad`          | `item`                    | 商品候補として微妙     |
| `item_not_match`    | `item`                    | 贈答文脈に合っていない |
| `item_ng_violation` | `item`                    | NG 条件に反している    |
| `item_avoid_match`  | `item`                    | 避けたい条件に近い     |
| `reason_good`       | `reason`                  | 理由に納得できた       |
| `reason_bad`        | `reason`                  | 理由に納得できない     |
| `result_good`       | `result`                  | 推薦全体が良い         |
| `result_bad`        | `result`                  | 推薦全体が微妙         |
| `comment`           | `result` / `item` / `reason` | 自由コメント        |

#### 6.4.2 `feedbackType` と `feedbackTargetType` の整合

Recommendation Feedback 定義書 §9.2 に準拠。不整合時は `GRS-FDB-001`（400）。

### 6.5 Request Example

#### 6.5.1 Result Item への Feedback（item_not_match）

```json
{
  "feedbackTargetType": "item",
  "resultItemId": "result_item_001",
  "feedbackType": "item_not_match",
  "feedbackValueType": "choice",
  "feedbackChoiceCode": "too_casual",
  "feedbackReasonCategory": "context_mismatch",
  "rating": 2,
  "comment": "上司へのお礼としては少しカジュアルに見えます",
  "sourcePage": "SCR-007",
  "sessionId": "sess_abc123"
}
```

#### 6.5.2 Reason への Feedback（reason_good）

```json
{
  "feedbackTargetType": "reason",
  "reasonId": "reason_001",
  "resultItemId": "result_item_001",
  "feedbackType": "reason_good",
  "feedbackValueType": "boolean",
  "feedbackValue": true,
  "rating": 5,
  "sourcePage": "SCR-007"
}
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
| 201 | Feedback 作成成功 | 新規 Feedback を受け付け保存した場合（API設計方針書 §9.1 準拠） |
| 200 | Feedback 更新成功 | `sessionId` + 同一対象 + 同一 `feedbackType` の既存 Feedback を更新した場合（Recommendation Feedback 定義書 §13.2 準拠） |
| 400 | Request 不正 | Validation エラー（`GRS-FDB-001` / `GRS-FDB-004` / `GRS-REQ-001` 等） |
| 404 | 対象なし | 対象 Result / Item / Reason が存在しない（`GRS-FDB-002`） |
| 500 | 内部エラー | Feedback 保存失敗等（`GRS-FDB-005` / `GRS-FDB-999` / `GRS-DB-*`） |

MVP では認証未導入のため **401 / 403** は返却しない。

### 7.3 Response Body

成功時は API設計方針書 §8.2 の **`data` + `meta`** 構造を基本とする。

#### 7.3.1 `data`（Feedback 受付成功）

| 項目 | 型 | 必須 | 内容 | 備考 |
| ---- | -- | ---- | ---- | ---- |
| `recommendationFeedbackId` | `string` | `true` | 登録された Feedback ID | 内部 ID の表面化。UUID 形式想定 |
| `status` | `string` | `true` | 受付状態 | 新規作成時は `accepted`、更新時は `updated` |
| `message` | `string` | `false` | 画面向け補足メッセージ | 例: 受付完了の短文 |

#### 7.3.2 `meta`

| 項目 | 型 | 必須 | 内容 | 備考 |
| ---- | -- | ---- | ---- | ---- |
| `traceId` | `string` | `true` | 横断追跡 ID | Header `X-Trace-Id` を引き継ぎまたは生成（[API一覧](../../05_アプリケーション設計/アプリ/api/API一覧.md) §API-PUB-004） |
| `requestId` | `string` | `true` | API リクエスト ID | - |
| `acceptedAt` | `string` | `false` | 受付日時（ISO 8601） | - |

**返却しない項目（契約上明示）:** DB 内部の `anonymous_user_id` 実値、`user_agent` 原文、保存先テーブル名、MOD-API 内部処理情報。

### 7.4 Response Example

#### 7.4.1 Feedback 新規作成成功（201）

```json
{
  "data": {
    "recommendationFeedbackId": "feedback_001",
    "status": "accepted",
    "message": "フィードバックを受け付けました。"
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440000",
    "requestId": "req_01HZYX",
    "acceptedAt": "2026-06-05T12:00:00+09:00"
  }
}
```

#### 7.4.2 Feedback 更新成功（200）

`sessionId` + 同一対象 + 同一 `feedbackType` の既存 Feedback がある場合、新しい内容で更新し **200** を返す。

```json
{
  "data": {
    "recommendationFeedbackId": "feedback_001",
    "status": "updated",
    "message": "フィードバックを更新しました。"
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440000",
    "requestId": "req_01HZYX",
    "acceptedAt": "2026-06-05T12:05:00+09:00"
  }
}
```

---

## 8. Error Response仕様

### 8.1 Error Response形式

エラー時も `meta.traceId` / `meta.requestId` を返す。`data` は返さないか `null` とする（OpenAPI Task で統一）。

```json
{
  "error": {
    "code": "GRS-FDB-001",
    "message": "フィードバック内容を確認してください。",
    "details": [
      {
        "field": "feedbackType",
        "message": "feedbackType is not allowed for feedbackTargetType item"
      }
    ]
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440001",
    "requestId": "req_01HZYY"
  }
}
```

### 8.2 Error一覧（本 API で想定する代表）

| Status | Error Code | 発生条件 | Response概要 | ユーザー向け表示 |
| -----: | ---------- | -------- | ------------ | ---------------- |
| 400 | `GRS-FDB-001` | Feedback 内容不正（type / target 不整合、必須値不足、enum 外等） | Validation 失敗 | フィードバック内容を確認してください。 |
| 400 | `GRS-FDB-004` | コメント文字数超過 | `comment` が最大長超過 | コメントを短くしてください。 |
| 400 | `GRS-REQ-001` | Request JSON 形式不正・型不正 | 共通 Validation | 条件を確認してください。 |
| 404 | `GRS-FDB-002` | 対象 Result / Item / Reason なし | 対象不存在 | 対象の推薦結果が見つかりません。 |
| 500 | `GRS-FDB-005` | Feedback 保存失敗 | DB 書き込み失敗 | フィードバックの送信に失敗しました。時間を置いて再度お試しください。 |
| 500 | `GRS-FDB-999` | Feedback 想定外エラー | 内部エラー | フィードバック処理でエラーが発生しました。 |
| 500 | `GRS-DB-001`〜`006` | DB 障害 | 永続化失敗 | データ処理に失敗しました。 |
| 500 | `GRS-DB-999` | DB 想定外 | 内部エラー | データ処理で予期しないエラー。 |

重複判定キー（`sessionId` + 同一対象 + 同一 `feedbackType`）に一致する既存 Feedback がある場合、**409 ではなく 200 + 更新扱い**とする（Recommendation Feedback 定義書 §13.2、Human Review #406 確定）。`GRS-FDB-003` は本 API の MVP 契約では返却しない。

---

## 9. バリデーション仕様

| 対象項目 | ルール | エラーコード | エラーメッセージ |
| -------- | ------ | ------------ | ---------------- |
| `resultId`（Path） | 必須・非空・存在する Result であること | `GRS-FDB-002` | 対象の推薦結果が見つかりません。 |
| `feedbackTargetType` | 必須。`result` / `item` / `reason` のいずれか | `GRS-FDB-001` | フィードバック内容を確認してください。 |
| `feedbackType` | 必須。§6.4.1 の MVP 許容 enum | `GRS-FDB-001` | フィードバック内容を確認してください。 |
| `feedbackType` × `feedbackTargetType` | §6.4.2 の整合 | `GRS-FDB-001` | フィードバック内容を確認してください。 |
| `resultItemId` | `feedbackTargetType=item` 時は必須。Path `resultId` に属すること | `GRS-FDB-001` / `GRS-FDB-002` | 内容確認 / 対象なし |
| `reasonId` | `feedbackTargetType=reason` 時は必須 | `GRS-FDB-001` / `GRS-FDB-002` | 内容確認 / 対象なし |
| `rating` | 必須。**1〜5** の整数 | `GRS-FDB-001` | フィードバック内容を確認してください。 |
| `comment` | 指定時は最大 **500** 文字 | `GRS-FDB-004` | コメントを短くしてください。 |
| 重複（更新） | `sessionId` + 同一対象 + 同一 `feedbackType` の既存 Feedback がある場合は更新し **200** を返す | - | - |
| JSON 形式 | パース可能であること | `GRS-REQ-001` | 条件を確認してください。 |

匿名 Feedback のため、MVP ではユーザー ID による厳密な重複排除は行わない（Recommendation Feedback 定義書 §9.3）。更新判定キーは `sessionId` + 同一対象 + 同一 `feedbackType` とし、一致時は新規作成（201）ではなく更新（200）とする。判定の詳細は実装仕様書 Task で詳細化する。

---

## 10. OpenAPI / generated 反映方針

| 項目 | 内容 |
| ---- | ---- |
| OpenAPI正本 | `packages/contracts/openapi/public-api.yaml` |
| 操作 ID（案） | `submitRecommendationFeedback`（OpenAPI Task で確定） |
| Path | `/api/v1/recommendation-results/{resultId}/feedback` |
| components schema | `RecommendationFeedbackSubmitRequest` / `RecommendationFeedbackSubmitResponse` 等（OpenAPI Task で命名確定） |
| Orval設定 | リポジトリ正本 `orval.config.ts` |
| generated出力先（web） | `apps/web/src/generated/api/` |
| OpenAPI定義書 | `openapi-spec.md` テンプレ準拠の Contract Task 成果物 |

本 Task では YAML / generated の**実変更は行わない**。本契約仕様書を 1b OpenAPI Contract Task の入力正本とする。

Contract Gate 通過後に Implementation Task（`api-implementation-spec`）および apps 実装 Task を開始する。横断 Epic [Epic]API-CONTRACT-ORVAL（#367）の成果供給タイミングは Epic #386 の運用に従う。

---

## 11. 互換性・破壊的変更

| 項目       | 内容 |
| ---------- | ---- |
| 破壊的変更 | MVP 初版のためなし |
| 後方互換性 | `v1` パス固定。フィールド追加は optional で許容 |
| 判断理由   | 初回 Public Feedback 契約確定 |

### 11.1 rollout order

- 本契約確定 → `public-api.yaml` 更新 → Orval 再生成 → web api-client 更新 → api 実装（MOD-API-007〜010）

---

## 12. 契約面テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | 正常系（item・新規） | `item_good` + 必須項目（`rating` 含む）で 201 + `data.status: accepted` | contract |
| 2 | 正常系（reason・新規） | `reason_good` + `reasonId` + `rating` で 201 + `data.status: accepted` | contract |
| 3 | validation error | `feedbackTargetType` と `feedbackType` 不整合で 400 + `GRS-FDB-001` | contract |
| 4 | 対象なし | 存在しない `resultId` で 404 + `GRS-FDB-002` | contract |
| 5 | 重複更新 | `sessionId` + 同一対象 + 同一 type の再送で 200 + `data.status: updated` | contract |
| 6 | rating 未指定 | `rating` 欠落で 400 + `GRS-FDB-001` | contract |
| 7 | comment 超過 | 501 文字以上で 400 + `GRS-FDB-004` | contract |
| 8 | trace 伝播 | `X-Trace-Id` 指定時に `meta.traceId` が一致 | contract |
| 9 | generated client | OpenAPI 生成後、型が Request/Response と一致 | typecheck |

実装結合・DB 障害シミュレーションは実装仕様書・単体テスト Task で扱う。

---

## 13. 変更履歴

| 日付 | 変更内容 | 関連Issue / PR |
| ---- | -------- | -------------- |
| 2026-06-05 | 初版（契約面のみ。Task #400 / 分離後モデル） | #400 |
| 2026-06-05 | Human Review 指摘反映（201 確定、重複は更新 200、`comment` 500 文字、`rating` 必須） | #406 |

---

## 14. Human Review 確定事項

PR #406 Human Review にて以下を確定した。

| No | 論点 | 確定内容 |
| --: | ---- | -------- |
| 1 | Feedback 成功時の HTTP Status | 新規作成は **201**。更新は **200** |
| 2 | 重複 Feedback の応答 | **更新扱い（200 + `data.status: updated`）**。409 は返却しない |
| 3 | `comment` 最大文字数 | **500 文字** |
| 4 | `rating` の MVP 必須化 | **必須**（1〜5 の整数） |

---

## 15. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| API一覧 | `docs/05_アプリケーション設計/アプリ/api/API一覧.md` | API-PUB-004 行 |
| API設計方針書 | `docs/05_アプリケーション設計/アプリ/api/API設計方針書.md` | Feedback API 方針 §20 |
| エラーコード定義書 | `docs/05_アプリケーション設計/アプリ/エラーコード定義書.md` | GRS-FDB-* |
| Recommendation Feedback | `docs/04_ドメインモデル設計/RecommendationFeedback定義書.md` | Request Body |
| Recommendation Result | `docs/04_ドメインモデル設計/RecommendationResult定義書.md` | 対象 Result / Item |
| API-PUB-002（前提） | `docs/06_実装設計/api/API-PUB-002_レコメンド実行API契約仕様書.md` | `recommendationResultId` |
| Task Definition | `prompts/definitions/tasks/api-pub-004-feedback-submit/api-contract-spec.yaml` | #400 scope |
| 実装仕様（別Task） | `prompts/definitions/tasks/api-pub-004-feedback-submit/api-implementation-spec.yaml` | Phase4（未作成） |

---

## 16. レビュー観点

- API契約（Request / Response / Error / Validation）が明確で、OpenAPI Task の入力として十分か
- API設計方針書 §20（Feedback API）と矛盾していないか
- API一覧の API-PUB-004（endpoint / Method / Provider / Consumer / 匿名 Feedback）と一致しているか（重複応答は本契約で更新 200 に確定。API一覧の 409 候補表記との差異は OpenAPI Contract Task 前に確認）
- Recommendation Feedback 定義書の MVP feedback_type と整合しているか
- 実装面（MOD-API-007〜010 フロー等）を含んでいないか
- secret / `.env` 実値が含まれていないか

### 16.1 Human Review で確認してほしいこと

- 正式 Endpoint と MVP 非認証（匿名 Feedback）方針の最終確認
- §14 の確定事項（201/200 使い分け、重複更新、`comment` 500 文字、`rating` 必須）の妥当性
- API一覧 §API-PUB-004 の重複 409 候補表記と本契約（更新 200）の整合方針
- OpenAPI Contract Task への分離方針の確認

---

## 17. 備考

- 本書は `prompts/templates/docs/api-contract-spec.md` に準拠した Phase1 ①（1a）成果物である。
- Feedback は即時に Ranking へ自動反映しない（Recommendation Feedback 定義書 §10.3）。契約上も非同期分析用途の登録 API として扱う。
- ログ・Observability（`feedback_count` / `feedback_error_count` / `positive_feedback_count` / `negative_feedback_count`）の実装記録方針は実装仕様書で扱う。契約上は `traceId` の往復を必須とする。
