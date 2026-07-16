# Reco推薦実行 API契約仕様書

> 本書は **API-INT-002** の契約面（Internal I/F）正本である。
> 処理フロー・内部 DTO マッピング・MOD-RECO パイプライン詳細・結合テスト観点は `API-INT-002_Reco推薦実行API実装仕様書.md`（別 Task）で定義する。
> OpenAPI 正本は `packages/contracts/openapi/internal-reco-api.yaml`（別 Contract Task）。

## 1. ドキュメント情報

| 項目           | 内容                                      |
| -------------- | ----------------------------------------- |
| ドキュメントID | `API-INT-002-CONTRACT`                    |
| ドキュメント名 | Reco推薦実行 API契約仕様書                |
| 対象システム   | Gift Recommendation Service MVP（Internal） |
| MVP対象        | `○`                                       |
| 作成日         | 2026-06-04                                |
| 更新日         | 2026-07-16（#1398 resultItems に reasonPoints / reasonDetail 任意追加） |

---

## 2. 概要

api（`apps/api`）から reco（`apps/reco` エンドポイント層）へ、正規化済み Recommendation Request に基づくギフト推薦パイプライン実行を依頼する Internal API である。reco は Recommendation Run / Result を生成し、api が Public API（API-PUB-002）向け Response に整形する。

本書では **api↔reco 間の HTTP 契約** のみを定義する。推薦パイプライン（MOD-RECO-001 等）の内部処理順序・モジュール責務は本書の scope 外とし、関連資料への参照に留める。

---

## 3. 目的

- api→reco 間の Request / Response / Error / Validation を確定し、Contract Gate および後続 OpenAPI Contract Task の入力とする。
- Recommendation Request / Result 定義書・API設計方針書・API一覧・エラーコード定義書と整合した Internal 契約面を提供する。
- Public API（API-PUB-002）が内部呼び出しする先の I/F 境界を明確にする（Public 表面仕様は `docs/06_実装設計/api/API-PUB-002_レコメンド実行API契約仕様書.md` を正とする）。

---

## 4. API基本情報

| 項目     | 内容                                              |
| -------- | ------------------------------------------------- |
| API ID   | `API-INT-002`                                     |
| API名    | Reco推薦実行                                      |
| API種別  | `Internal API`                                    |
| Method   | `POST`                                            |
| Endpoint | `/internal/reco/v1/recommendations/run`           |
| Base URL | 環境ごとに環境変数で定義（本書ではパスを正とする） |
| Version  | `v1`（URL パスに含む）                            |
| Provider | `apps/reco`（エンドポイント層）                   |
| Consumer | `apps/api`（MOD-API-005 Reco Client 等）          |
| 認証要否 | `true`（Internal API Key。詳細は §6.1）           |
| 権限条件 | サービス間呼び出しのみ。外部ユーザー直接利用不可  |
| 冪等性   | `非冪等`（同一 Request ID の再実行は新規 Run として扱う） |
| MVP対象  | `○`                                               |

---

## 5. 利用シーン

### 5.1 利用タイミング

api が Public API（API-PUB-002）で Recommendation Request を受け付け・検証・保存した後、推薦パイプライン実行を reco に委譲するとき。

### 5.2 呼び出し元

- `apps/api`（Recommendation Application Service / Reco Client）

### 5.3 主なユースケース

- 正規化済み推薦条件と `recommendationRequestId` を渡し、推薦 Run を実行して Recommendation Result（内部項目含む）を取得する。
- 候補 0 件の場合も HTTP 200 で空結果を返し、api 側で Public 向け Response に変換する。

### 5.4 関連モジュール（参照のみ）

| 項目 | 内容 |
| ---- | ---- |
| Consumer モジュール | `MOD-API-005`（Reco Client）— 本 API の呼び出し責務 |
| Provider 境界 | `apps/reco` エンドポイント層（HTTP I/F）。推薦ロジック本体は application 層 |
| 推薦パイプライン | `MOD-RECO-001`（Recommendation Orchestrator）等 — 契約上は「reco 内で実行される処理」として参照のみ。詳細は Recoモジュール一覧・モジュール仕様書を正とする |
| 上流 Public API | `API-PUB-002`（レコメンド実行）— 契約正本は `docs/06_実装設計/api/API-PUB-002_レコメンド実行API契約仕様書.md` |

### 5.5 Public API 連携（契約上の前提のみ）

| 項目 | 内容 |
| ---- | ---- |
| 上流 API ID | `API-PUB-002`（レコメンド実行） |
| Method / Endpoint | `POST` `/api/v1/recommendations` |
| 契約正本 | `docs/06_実装設計/api/API-PUB-002_レコメンド実行API契約仕様書.md` |
| 補足参照 | `docs/05_アプリケーション設計/アプリ/api/API一覧.md`（API-PUB-002 行）、`docs/05_アプリケーション設計/アプリ/api/API設計方針書.md` §21（Public / Internal 境界） |
| 本書との境界 | Request/Response の **Internal 向け I/F** のみ本書で定義。api による Public↔Internal 変換・エラー整形は実装仕様書 Task で定義 |

---

## 6. Request仕様

### 6.1 Request Header

| Header | 必須 | 内容 | 例 |
| ------ | ---- | ---- | -- |
| `Content-Type` | `true` | `application/json` | `application/json` |
| `Accept` | `true` | `application/json` | `application/json` |
| `X-Internal-Api-Key` | `true` | Internal API 保護用キー（値は環境変数。本書に実値を記載しない） | `***REDACTED***` |
| `X-Trace-Id` | `true` | 横断追跡 ID。Public API 側で生成または引き継ぎ | `550e8400-e29b-41d4-a716-446655440000` |
| `X-Request-Id` | `true` | API リクエスト ID（api 側で生成） | `req_01HZYX` |

reco 側は `X-Trace-Id` / `X-Request-Id` を Response `meta` へ反映する（API設計方針書 §12、ログ・Observability設計書）。

### 6.2 Path Parameters

| 項目 | 型 | 必須 | 内容 | 例 |
| ---- | -- | ---- | ---- | -- |
| - | - | - | なし | - |

### 6.3 Query Parameters

| 項目 | 型 | 必須 | 内容 | 制約 | 例 |
| ---- | -- | ---- | ---- | ---- | -- |
| - | - | - | なし | - | - |

### 6.4 Request Body

api が保存済みの Recommendation Request を **正規化済み JSON** として渡す。フィールド名は Internal I/F として **camelCase** とする（Orval / reco-client 生成を想定）。

#### 6.4.1 ルート項目

| 項目 | 型 | 必須 | 内容 | 制約 | 例 |
| ---- | -- | ---- | ---- | ---- | -- |
| `recommendationRequestId` | `string` | `true` | api が永続化した推薦リクエスト ID | 非空 | `request_001` |
| `recommendationRequest` | `object` | `true` | 検証済み推薦条件（§6.4.2） | Recommendation Request 定義書に整合 | 下記 Example |

#### 6.4.2 `recommendationRequest`（検証済み推薦条件）

Recommendation Request 定義書 **§6**（データ項目定義）および **§8.2**（値域チェック）に準拠。api 側で Public 入力を検証・正規化した後の確定値を渡す。物理名（snake_case）から Internal I/F 用 camelCase へマッピングする。

| 項目 | 型 | 必須 | 内容 | 制約 | 例 |
| ---- | -- | ---- | ---- | ---- | -- |
| `relationship` | `object` | `true` | 贈答相手（関係性） | `relationshipCode` 必須 | - |
| `relationship.relationshipCode` | `string` | `true` | 関係性コード | マスタコード体系に整合 | `boss` |
| `relationship.relationshipLabel` | `string` | `false` | 関係性表示名 | api 側で正規化済み | `上司` |
| `occasion` | `object` | `true` | ギフト用途 | `occasionCode` 必須 | - |
| `occasion.occasionCode` | `string` | `true` | 用途コード | マスタコード体系に整合 | `thanks` |
| `occasion.occasionLabel` | `string` | `false` | 用途表示名 | api 側で正規化済み | `お礼` |
| `budget` | `object` | `false` | 予算条件 | `budgetMin` / `budgetMax` は 0 以上。両方指定時は `budgetMin <= budgetMax` | - |
| `budget.budgetMin` | `integer` | `false` | 予算下限（JPY） | 0 以上 | `3000` |
| `budget.budgetMax` | `integer` | `false` | 予算上限（JPY） | 0 以上 | `5000` |
| `budget.currency` | `string` | `false` | 通貨 | MVP は `JPY` 固定想定 | `JPY` |
| `budget.taxIncluded` | `boolean` | `false` | 税込みフラグ | - | `true` |
| `preferredCondition` | `object` | `false` | 好み・期待する方向性 | - | - |
| `preferredCondition.preferredText` | `string` | `false` | 好みテキスト | api 側で正規化済み | `上品で感謝が伝わるもの` |
| `preferredCondition.preferredKeywords` | `array` | `false` | 好みキーワード | 要素は `string` | `["上品", "感謝"]` |
| `nonPreferredCondition` | `object` | `false` | 避けたい傾向 | - | - |
| `nonPreferredCondition.nonPreferredText` | `string` | `false` | 避けたい条件テキスト | api 側で正規化済み | `カジュアルすぎるものは避けたい` |
| `nonPreferredCondition.nonPreferredKeywords` | `array` | `false` | 避けたいキーワード | 要素は `string` | `["カジュアルすぎる"]` |
| `ngCondition` | `object` | `false` | 絶対 NG 条件 | - | - |
| `ngCondition.ngText` | `string` | `false` | NG テキスト | api 側で正規化済み | `アルコールはNG` |
| `ngCondition.ngKeywords` | `array` | `false` | NG キーワード | 要素は `string` | `["アルコール"]` |
| `ngCondition.ngCategories` | `array` | `false` | NG カテゴリ | 要素は `string` | `["alcohol"]` |
| `freeText` | `string` | `false` | 自由記述 | api 側で正規化済み | `退職する上司へのお礼` |
| `execution` | `object` | `true` | 実行条件 | `mode` 必須 | - |
| `execution.mode` | `string` | `true` | 実行モード | `ui` / `evaluation` / `batch` | `ui` |
| `execution.topK` | `integer` | `false` | 返却件数 | 1〜50。未指定時デフォルト **10**（ui） | `10` |
| `execution.candidateLimit` | `integer` | `false` | 候補抽出上限 | **`topK` 以上**（Recommendation Request §8.2）。未指定時デフォルト **50**（ui） | `50` |
| `execution.includeReason` | `boolean` | `false` | 推薦理由を含めるか | ui ではデフォルト **true** | `true` |
| `execution.includeDebugInfo` | `boolean` | `false` | デバッグ情報 | `evaluation` 等で **true** 可。ui では **false** 想定 | `false` |
| `execution.evalCaseId` | `string` | `false` | 評価ケース ID | `mode=evaluation` 時に使用 | - |
| `execution.configName` | `string` | `false` | Semantic Config 系列名 | evaluation / batch の version 再現用。`versionLabel` とセット指定 | `mvp-semantic-config` |
| `execution.versionLabel` | `string` | `false` | Version ラベル（semver） | evaluation / batch の version 再現用。`configName` とセット指定 | `v1.0.0` |
| `execution.modelVersionId` | `string` | `false` | Model Version | 評価・再現用 | - |

`recommendationRequestId` と `recommendationRequest` の内容が矛盾しないこと（同一 Request の確定ペイロードであること）を api 側で保証する。reco 側の再 Validation は契約上、必須項目・値域・矛盾の **受け入れ確認** に限定する（詳細ルールは §9）。

### 6.5 Request Example

```json
{
  "recommendationRequestId": "request_001",
  "recommendationRequest": {
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
}
```

### 6.6 Observability（契約露出範囲）

契約上、Request / Response に含める（または Header で往復する）識別子は以下とする。access_log / phase_log / error_log / metric の**実装・記録詳細**は実装仕様書 Task で扱う（ログ・Observability設計書を正本とする）。

| 項目 | 露出箇所 | 必須 | 内容 |
| ---- | -------- | ---- | ---- |
| `traceId` | Request Header `X-Trace-Id` / Response `meta.traceId` | `true` | 横断追跡 ID。api から reco へ引き継ぎ、Response で一致させる |
| `requestId` | Request Header `X-Request-Id` / Response `meta.requestId` | `true` | API リクエスト ID |
| `recommendationRunId` | Response `data.recommendationRunId` | `true`（成功時） | 推薦 Run 追跡。phase_log / metric の相関キー |
| `recommendationRequestId` | Request Body / Response `data.recommendationRequestId` | `true` | 推薦リクエスト ID |
| `recommendationResultId` | Response `data.recommendationResultId` | `true`（成功時） | 推薦結果 ID |
| phase / metric 詳細 | Response `metricSummary` 等（任意） | `false` | Run 単位サマリ。キー構造は §7.3.4〜§7.3.5。詳細記録はログ・Observability設計書を正本とする |

---

## 7. Response仕様

### 7.1 Response Header

| Header | 内容 | 例 |
| ------ | ---- | -- |
| `Content-Type` | `application/json` | `application/json` |

### 7.2 Status Code

| Status | 意味 | 利用条件 |
| -----: | ---- | -------- |
| 200 | 処理成功（推薦結果あり、または 0 件の正常系） | 推薦パイプラインが完了し Response を返却できる場合 |
| 400 | Request 不正 | 必須項目欠落・型不正・値域違反等 |
| 401 | 認証失敗 | `X-Internal-Api-Key` 不正または未指定 |
| 403 | 権限不足 | Internal API への不正アクセス・操作拒否（`GRS-AUTH-002` 等） |
| 422 | 業務的 Validation 失敗 | 未対応条件・実行不可な条件組み合わせ等 |
| 500 | 内部エラー | Reco パイプライン失敗（`GRS-REC-002` 等） |
| 502 | 外部依存エラー | LLM / Embedding / 外部 API 失敗 |
| 503 | 一時利用不可 | DB 接続失敗等（`GRS-COM-003`） |
| 504 | タイムアウト | 推薦処理タイムアウト（`GRS-REC-101`） |

**0 件結果:** HTTP **200**。異常終了ではない（エラーコード定義書 `GRS-REC-001` 補足、API設計方針書 §9.2）。

### 7.3 Response Body

成功時は API設計方針書 §8.2 の **`data` + `meta`** 構造を基本とする。

#### 7.3.1 `data`（推薦成功・0 件共通）

| 項目 | 型 | 必須 | 内容 | 備考 |
| ---- | -- | ---- | ---- | ---- |
| `recommendationRunId` | `string` | `true` | 推薦実行 ID | reco 側で生成 |
| `recommendationResultId` | `string` | `true` | 推薦結果 ID | - |
| `recommendationRequestId` | `string` | `true` | 推薦リクエスト ID | Request と一致 |
| `resultStatus` | `string` | `true` | 結果状態 | Recommendation Result 定義書 §7 準拠。MVP 返却値: `completed` / `completed_with_fallback` / `partial`。0 件も `completed`（`resultItemCount: 0`） |
| `topK` | `integer` | `true` | 要求返却件数 | Request の `execution.topK` を反映 |
| `resultItemCount` | `integer` | `true` | 返却 Item 件数 | 0 件時は `0` |
| `fallbackUsed` | `boolean` | `true` | Fallback 利用有無 | MVP では原則 `false` |
| `displayMessage` | `string` | `false` | 画面向け補足（api 変換用） | 0 件時に設定可 |
| `candidateCounts` | `object` | `false` | フェーズ別候補数サマリ | API一覧 Response 概要に整合 |
| `candidateCounts.retrievalCount` | `integer` | `false` | Retrieval 候補数 | - |
| `candidateCounts.matchingCount` | `integer` | `false` | Matching 通過数 | - |
| `candidateCounts.rankingCount` | `integer` | `false` | Ranking 対象数 | - |
| `warnings` | `array` | `false` | 警告一覧 | 要素は `WarningItem`（§7.3.4）。MVP コードは §7.3.6 |
| `metricSummary` | `object` | `false` | Reco 品質メトリクス用サマリ | `MetricSummary`（§7.3.5）。任意 |
| `reasonData` | `object` | `false` | Reason 生成結果（内部・Run 単位） | `ReasonData`（§7.3.9）。`includeDebugInfo=true` または `mode=evaluation` 時は推奨。Public 非表面化 |
| `resultItems` | `array` | `true` | 推薦結果 Item 一覧 | API設計方針書 §21.3 の `resultItems`。0 件時は **空配列 `[]`** |
| `metadata` | `object` | `false` | バージョン・mode・debug 情報等 | `mode` は Request を反映。`debugPayload` は §7.3.8 参照 |

**Transient（永続化しない）:** `warnings` / `metricSummary` は **本 API Response に限る Transient フィールド**とする。Recommendation Result 定義書・DB には保存しない（観測・分析の正本はログ・Observability設計書および metric 集計）。api は Public Response へ渡さない（API設計方針書 §21.3）。

**`data.metadata`（Run 単位）**

| フィールド | 型 | 必須 | 内容 | 備考 |
| ---------- | -- | ---- | ---- | ---- |
| `mode` | `string` | `false` | Request の `execution.mode` | `ui` / `evaluation` / `batch` |
| `debugPayload` | `object` | `false` | 評価・デバッグ用 Run 単位情報 | Recommendation Result 定義書 `debug_payload` の API マッピング。§7.3.8 |

`debugPayload` は **open object**（追加キー許容）。MVP 推奨キー: `evalCaseId`, `configName`, `versionLabel`, `modelVersionId`, `rankingConfigVersionId`, `phaseSummary`。詳細スキーマ固定は OpenAPI / 実装 Task とする。

#### 7.3.2 `data.resultItems[]`（1 件あたり）

Internal API では API設計方針書 §21.3 に従い、Public より多くの内部項目を返してよい。

| 項目 | 型 | 必須 | 内容 | 備考 |
| ---- | -- | ---- | ---- | ---- |
| `recommendationResultItemId` | `string` | `true` | 結果明細 ID | - |
| `itemId` | `string` | `true` | 商品 ID | - |
| `rank` | `integer` | `true` | 表示順位 | 1 始まり |
| `itemName` | `string` | `true` | 商品名 | Snapshot |
| `itemPrice` | `integer` | `true` | 価格（JPY） | Snapshot |
| `itemUrl` | `string` | `true` | 外部 EC 商品 URL | Snapshot |
| `itemImageUrl` | `string` | `false` | 代表画像 URL | - |
| `itemCatchcopy` | `string` | `false` | キャッチコピー | - |
| `shopName` | `string` | `false` | 店舗名 | - |
| `contextScore` | `number` | `true` | 意味一致スコア | Public では非返却 |
| `socialMatch` | `number` | `false` | Social 軸一致度 | Recommendation Result 定義書 §6.2 |
| `symbolicMatch` | `number` | `false` | Symbolic 軸一致度 | 同上 |
| `popularityScore` | `number` | `false` | 人気補助スコア | - |
| `riskPenalty` | `number` | `false` | リスクペナルティ | - |
| `finalScore` | `number` | `true` | 最終スコア | Public では非返却 |
| `scoreBreakdown` | `object` | `false` | スコア内訳 | debug返却条件（§7.3.8）を満たすとき**推奨**（契約上必須ではない） |
| `reasonSummary` | `string` | 条件付き | 推薦理由（短文） | §7.3.2.1。`includeReason=true` かつ Item 存続時 **必須**（非空）。汎用 Reason（Reason生成定義書 §17.2）含む |
| `reasonPoints` | `array` | `false` | 箇条書き理由（`string[]`） | **任意**。Public へ透過可（#1398）。ui 経路で届けるため `resultItems[]` に載せる |
| `reasonDetail` | `string` | `false` | 詳細表示用短文 | **任意**。Public へ透過可（#1398）。ui 経路で届けるため `resultItems[]` に載せる |
| `recommendationReasonId` | `string` | `false` | 推薦理由 ID | `reasonStatus=completed` かつ Reason 永続化時は返却（推奨） |
| `reasonStatus` | `string` | 条件付き | Reason 生成状態 | §7.3.2.1。`includeReason=true` 時は返却。MVP 値域: `completed`（Item 存続時は Reason 失敗でも `completed`） |
| `reasonBadges` | `array` | `false` | 理由バッジ | `reasonStatus=completed` 時のみ任意 |
| `cautionNote` | `string` | `false` | 注意表示 | `reasonStatus=completed` 時のみ任意 |
| `isFallback` | `boolean` | `false` | Fallback 由来か | Ranking Fallback 候補（Recommendation Result §6.2）または Reason 汎用文注入（`isFallback: true`、MOD-RECO-001 §10.3） |

##### 7.3.2.1 Reason フィールドの必須条件（Internal）

`execution.includeReason`（Recommendation Request §8.2、本書 §6.2）に従う。

| 条件 | `reasonSummary` | `reasonStatus` | Item 存続 | Run `resultStatus` への影響 |
| ---- | --------------- | -------------- | --------- | --------------------------- |
| `includeReason=false` | 省略 | 省略 | — | — |
| `includeReason=true` かつ Reason 成功 | **必須**（非空） | `completed` | 存続 | — |
| `includeReason=true` かつ Reason **生成フェーズのみ**失敗 | **必須**（非空。Reason生成定義書 §17.2 汎用 Reason または MOD-RECO-001 Orchestrator 注入） | `completed` | **存続** | `isFallback: true`。他 Item が正常なら Run `completed` 可。複数 Item で一部 fallback のみなら `partial` 可 |

Ranking / Matching 等の先行フェーズ失敗で Item 自体が存在しない場合は、本節の Reason 失敗とは別扱いとする。

**Public API へ渡す際の非表面化:** api は `finalScore` / `scoreBreakdown` / `contextScore` / `socialMatch` / `symbolicMatch` / `reasonData` / `metadata.debugPayload` / `reasonBasis` / `reasonStatus` 等を Public Response から除外する。Public へ渡す Reason 関連は **`reasonSummary` / `reasonPoints` / `reasonDetail` / `reasonBadges` / `cautionNote` / `isFallback`**（`reasonPoints` / `reasonDetail` は任意。API-PUB-002 §7.3.2、#1398）。マッピング元は `resultItems[]`（`reasonData` 単独では ui 経路に届かない）。

#### 7.3.3 `meta`

| 項目 | 型 | 必須 | 内容 | 備考 |
| ---- | -- | ---- | ---- | ---- |
| `traceId` | `string` | `true` | 横断追跡 ID | Header `X-Trace-Id` と一致 |
| `requestId` | `string` | `true` | API リクエスト ID | Header `X-Request-Id` と一致 |
| `generatedAt` | `string` | `false` | 生成日時（ISO 8601） | - |
| `resultCode` | `string` | `false` | 業務結果コード | 0 件時は `GRS-REC-001`（§7.4.2） |

#### 7.3.4 `WarningItem`（`warnings[]` 要素）

| フィールド | 型 | 必須 | 内容 |
| ---------- | -- | ---- | ---- |
| `code` | `string` | `true` | 警告コード（`SCREAMING_SNAKE_CASE`）。MVP 一覧は §7.3.6 |
| `severity` | `string` | `false` | `info` / `warn`。未指定時は reco 実装で `warn` 想定 |
| `message` | `string` | `false` | 運用・デバッグ向け補足。Public へは渡さない |

**`warnings` と `meta.resultCode` の責務分離**

| 項目 | 役割 |
| ---- | ---- |
| `meta.resultCode`（例: `GRS-REC-001`） | 業務結果（0 件正常系など）。api が Public 変換時に参照 |
| `warnings[]` | パイプライン診断ヒント。HTTP 200 のまま返しうる。未知の `code` は api/reco とも処理継続（ログ・集計のみ） |

**拡張方針:** MVP 稼働後のコード追加は、(1) 本書 §7.3.6 への追記 (2) OpenAPI `WarningCode` enum の拡張（後方互換的追加）(3) 未知コードの tolerant 処理、とする。

#### 7.3.5 `MetricSummary`（`metricSummary`）

Run 単位の品質サマリ。API一覧（API-INT-002）のメトリクス列およびログ・Observability設計書 §11.2 に整合する。**`candidateCounts` はフェーズ別件数、`metricSummary` は時間・分布**と役割を分ける。

| フィールド | 型 | 必須 | 内容 |
| ---------- | -- | ---- | ---- |
| `recommendationLatencyMs` | `integer` | `false` | 推薦全体の処理時間（ms） |
| `phaseDurationMs` | `object` | `false` | フェーズ別処理時間（ms）。キー例: `retrieval`, `matching`, `ranking`, `reason` |
| `featureDistribution` | `object` | `false` | Feature 名 → `{ mean, p95 }`（数値 0〜1 想定）。分布 JSON 全体は載せない |

`phaseDurationMs` / `featureDistribution` のキーは MVP では上記を推奨とし、追加キーは optional で許容する（§11 後方互換）。

#### 7.3.6 MVP 警告コード一覧

| code | 発生条件（契約上） | severity | 備考 |
| ---- | ------------------ | -------- | ---- |
| `NO_CANDIDATES_AFTER_RETRIEVAL` | Retrieval 後に候補 0 → `resultItemCount: 0` | `warn` | §7.4.2 0 件例 |
| `LOW_CANDIDATES_AFTER_MATCHING` | Matching 後候補が閾値未満（件数は 1 以上） | `warn` | 閾値・発火条件は reco 実装 Task |
| `FEATURE_DISTRIBUTION_SKEW` | User / Item Feature 分布の偏り検知 | `warn` | Observability の分布異常 warn と対応。閾値は reco 実装 Task |

#### 7.3.7 内部コードと API `warnings.code` の対照

Retrieval 等の**モジュール内部** `error_code` と、本 API の `warnings[].code` は別体系とする。

| 内部（例） | API `warnings.code`（例） | 備考 |
| ---------- | ------------------------- | ---- |
| `RETRIEVAL_NO_CANDIDATES`（Retrieval定義書 §19） | `NO_CANDIDATES_AFTER_RETRIEVAL` | reco 実装でマッピング。契約上は API コードを正とする |

#### 7.3.8 `scoreBreakdown` / `debugPayload` 返却条件（#375 確定）

Recommendation Result 定義書 §9.2・§13.1 および Human 判断記録（`ai-logs/human-decisions/2026-06-05-api-int-002-score-breakdown-debug-return-policy.md`）に整合する。`debugPayload` 推奨キーの Semantic Config 参照は Task #463 にて `configName` + `versionLabel` composite に更新（旧 `semanticConfigVersionId` は不採用）。

**用語: debug返却条件**

以下のいずれかを満たす Request 条件。`batch` mode 単独では debug返却条件を満たさない（Offline Evaluation は `mode=evaluation` を使用。インターフェース一覧 IF-SHARED-004 参照）。

```text
execution.mode = evaluation
OR execution.includeDebugInfo = true
```

**返却条件マトリクス**

| mode | includeDebugInfo | `resultItems[].scoreBreakdown` | `data.metadata.debugPayload` |
| ---- | ---------------- | ------------------------------ | ---------------------------- |
| ui | false | 省略 | 省略 |
| ui | true | 推奨 | 推奨 |
| evaluation | false / true | 推奨 | 推奨 |
| batch | false | 省略 | 省略 |
| batch | true | 推奨 | 推奨 |

**必須度:** 上記「推奨」は契約上**必須ではない**。欠落しても HTTP **200** を維持する（Validation エラーにしない）。

**欠落時の tolerant 処理**

| 項目 | 方針 |
| ---- | ---- |
| HTTP Status | 200 維持 |
| 内部記録 | Recommendation Result 定義書 §13.1 `SCORE_BREAKDOWN_MISSING` 相当を **phase_log / error_log** に記録 |
| `warnings[]` | **載せない**（§7.3.4 のパイプライン品質診断用途と分離） |

**ドメイン ↔ API マッピング**

| ドメイン（Recommendation Result） | Internal API |
| ----------------------------------- | ------------ |
| `score_breakdown`（Item 単位） | `data.resultItems[].scoreBreakdown` |
| `debug_payload`（Run 単位） | `data.metadata.debugPayload` |

`scoreBreakdown` の JSON 内部キー詳細は Ranking 定義書・実装 Task で確定する（本契約では open object として扱う）。

#### 7.3.9 `ReasonData` / `ReasonDataItem`（`reasonData`）（#376 確定）

Run レベルの内部 Reason 詳細。`resultItems[]` の表示用フィールド（`reasonSummary` 等）と **役割を分離**する。

| 項目 | 方針 |
| ---- | ---- |
| 必須度 | **任意**（`data.reasonData` 自体は必須ではない） |
| 返却推奨 | `includeReason=true` かつ（`includeDebugInfo=true` **または** `execution.mode=evaluation`） |
| 対応 | 各 `ReasonDataItem.recommendationResultItemId` が `resultItems[].recommendationResultItemId` と一致すること |

**`ReasonData` 構造**

| フィールド | 型 | 必須 | 内容 |
| ---------- | -- | ---- | ---- |
| `items` | `array` | `true` | `ReasonDataItem[]` |

**`ReasonDataItem` 構造**（Reason生成定義書 §5 / §14 / §15.1 の camelCase 対応）

| フィールド | 型 | 必須 | 内容 |
| ---------- | -- | ---- | ---- |
| `recommendationResultItemId` | `string` | `true` | 対応する Result Item ID |
| `itemId` | `string` | `true` | 商品 ID |
| `reasonStatus` | `string` | `true` | `completed`（Item 存続時。Reason fallback 時も `completed`） |
| `reasonSummary` | `string` | 条件付き | Item 存続かつ `includeReason=true` 時 **必須**（非空。汎用 Reason 含む） |
| `isFallback` | `boolean` | `false` | Reason 汎用文由来（§7.3.2.1） |
| `reasonDetail` | `string` | `false` | 詳細表示用。`resultItems[]` にも任意で載せ Public へ透過可（#1398） |
| `reasonPoints` | `array` | `false` | 箇条書き理由（string 要素）。`resultItems[]` にも任意で載せ Public へ透過可（#1398） |
| `reasonBadges` | `array` | `false` | 表示ラベル（Reason生成定義書 §5） |
| `cautionNote` | `string` | `false` | 注意・補足 |
| `reasonBasis` | `object` | `false` | 根拠 JSON（Reason生成定義書 §14.2 相当）。debug / evaluation 時は **推奨** |
| `generationMethod` | `string` | `false` | `template` / `llm_refined` / `hybrid` |
| `modelVersionId` | `string` | `false` | Reason 生成ロジックバージョン |

OpenAPI（`internal-reco-api.yaml`）への機械可読反映は **別 Contract Task** とする。

### 7.4 Response Example

#### 7.4.1 推薦結果あり（200）

```json
{
  "data": {
    "recommendationRunId": "run_001",
    "recommendationResultId": "result_001",
    "recommendationRequestId": "request_001",
    "resultStatus": "completed",
    "topK": 10,
    "resultItemCount": 2,
    "fallbackUsed": false,
    "candidateCounts": {
      "retrievalCount": 120,
      "matchingCount": 45,
      "rankingCount": 10
    },
    "warnings": [],
    "metricSummary": {
      "recommendationLatencyMs": 842,
      "phaseDurationMs": {
        "retrieval": 120,
        "matching": 210,
        "ranking": 95,
        "reason": 380
      },
      "featureDistribution": {
        "formality": { "mean": 0.62, "p95": 0.88 },
        "emotion": { "mean": 0.55, "p95": 0.79 }
      }
    },
    "resultItems": [
      {
        "recommendationResultItemId": "result_item_001",
        "itemId": "item_001",
        "rank": 1,
        "itemName": "上品な焼き菓子ギフトセット",
        "itemPrice": 4320,
        "itemUrl": "https://example.com/item/001",
        "itemImageUrl": "https://example.com/item/001.jpg",
        "shopName": "Example Shop",
        "contextScore": 0.82,
        "socialMatch": 0.86,
        "symbolicMatch": 0.76,
        "popularityScore": 0.64,
        "riskPenalty": 0.08,
        "finalScore": 0.78,
        "isFallback": false,
        "reasonSummary": "上司へのお礼として失礼がなく、上品さと感謝の伝わりやすさのバランスが良いため候補にしています。",
        "reasonStatus": "completed"
      }
    ],
    "metadata": {
      "mode": "ui"
    }
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440000",
    "requestId": "req_01HZYX",
    "generatedAt": "2026-06-04T12:00:00+09:00"
  }
}
```

#### 7.4.2 0 件結果（200）

```json
{
  "data": {
    "recommendationRunId": "run_002",
    "recommendationResultId": "result_002",
    "recommendationRequestId": "request_002",
    "resultStatus": "completed",
    "topK": 10,
    "resultItemCount": 0,
    "fallbackUsed": false,
    "displayMessage": "条件に合う商品が見つかりませんでした。",
    "candidateCounts": {
      "retrievalCount": 0,
      "matchingCount": 0,
      "rankingCount": 0
    },
    "warnings": [
      {
        "code": "NO_CANDIDATES_AFTER_RETRIEVAL",
        "severity": "warn"
      }
    ],
    "metricSummary": {
      "recommendationLatencyMs": 310,
      "phaseDurationMs": {
        "retrieval": 95,
        "matching": 0,
        "ranking": 0,
        "reason": 0
      }
    },
    "resultItems": []
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440001",
    "requestId": "req_01HZYY",
    "generatedAt": "2026-06-04T12:01:00+09:00",
    "resultCode": "GRS-REC-001"
  }
}
```

> 0 件時は `data.resultStatus: "completed"`、`data.resultItemCount: 0`、`data.resultItems: []`、`meta.resultCode: "GRS-REC-001"` を組み合わせる。HTTP Status は常に 200（`empty` は Result Status 値として使用しない）。

#### 7.4.3 Reason 生成のみ失敗（200・Item 存続）

1 件目は Reason 成功、2 件目は Reason 生成フェーズのみ失敗した例。

```json
{
  "data": {
    "recommendationRunId": "run_003",
    "recommendationResultId": "result_003",
    "recommendationRequestId": "request_003",
    "resultStatus": "partial",
    "topK": 10,
    "resultItemCount": 2,
    "fallbackUsed": false,
    "resultItems": [
      {
        "recommendationResultItemId": "result_item_001",
        "itemId": "item_001",
        "rank": 1,
        "itemName": "上品な焼き菓子ギフトセット",
        "itemPrice": 4320,
        "itemUrl": "https://example.com/item/001",
        "contextScore": 0.82,
        "finalScore": 0.78,
        "reasonSummary": "上司へのお礼として失礼がなく、上品さと感謝の伝わりやすさのバランスが良いため候補にしています。",
        "reasonStatus": "completed",
        "recommendationReasonId": "reason_001"
      },
      {
        "recommendationResultItemId": "result_item_002",
        "itemId": "item_002",
        "rank": 2,
        "itemName": "詰め合わせギフト",
        "itemPrice": 5400,
        "itemUrl": "https://example.com/item/002",
        "contextScore": 0.75,
        "finalScore": 0.71,
        "reasonSummary": "今回の条件に対して、候補商品の中でも比較的バランスの良い商品です。",
        "reasonStatus": "completed",
        "isFallback": true,
        "recommendationReasonId": "reason_002"
      }
    ]
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440003",
    "requestId": "req_01HZZ0"
  }
}
```

> 2 件目は Reason 生成フェーズのみ失敗し、§17.2 汎用 Reason を注入して `reasonStatus: completed` / `isFallback: true` で返す。Item は Ranking 結果として存続する（MOD-RECO-001 §10.3）。

---

## 8. Error Response仕様

### 8.1 Error Response形式

エラー時も `meta.traceId` / `meta.requestId` を返す。`data` は返さないか `null` とする（OpenAPI Task で統一）。

```json
{
  "error": {
    "code": "GRS-REC-002",
    "message": "レコメンド処理に失敗しました。時間を置いて再度お試しください。",
    "details": []
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440002",
    "requestId": "req_01HZYZ"
  }
}
```

### 8.2 Error一覧（本 API で想定する代表）

Public 向け Error Response の契約正本は `docs/06_実装設計/api/API-PUB-002_レコメンド実行API契約仕様書.md` §8 とする。

| Status | Error Code | 発生条件 | Response概要 | Public 向けマップ（API-PUB-002） |
| -----: | ---------- | -------- | ------------ | -------------------------------- |
| 401 | `GRS-AUTH-001` | Internal API Key 不正 | 認証失敗 | §8.2.1 参照（500 + `GRS-REC-002`） |
| 401 | `GRS-AUTH-004` | 内部認証情報なし | 認証情報不足 | §8.2.1 参照（500 + `GRS-REC-002`） |
| 403 | `GRS-AUTH-002` | 許可されない操作 | 権限不足 | §8.2.1 参照（500 + `GRS-REC-002`） |
| 403 | `GRS-AUTH-003` | Public 向け API への不正アクセス相当 | 操作不可 | §8.2.1 参照（500 + `GRS-REC-002`） |
| 403 | `GRS-AUTH-005` | Batch 操作の外部実行 | 操作不可 | §8.2.1 参照（500 + `GRS-REC-002`） |
| 400 | `GRS-REQ-001` | 正規化済み Request の契約違反 | Validation 失敗 | Public `GRS-REQ-001` 等へ変換 |
| 422 | `GRS-REQ-002` | 未対応の条件組み合わせ | 業務 Validation | Public 422 へ伝播可 |
| 422 | `GRS-REQ-006` | 条件が厳しすぎる | 業務 Validation | 同上 |
| 500 | `GRS-REC-002` | 推薦実行失敗 | パイプライン失敗 | Public `GRS-REC-002` |
| 500 | `GRS-REC-003`〜`013` | 各フェーズ失敗 | フェーズ別失敗 | Public 向けメッセージへ集約可 |
| 504 | `GRS-REC-101` | 推薦タイムアウト | タイムアウト | Public `GRS-REC-101` |
| 409 | `GRS-REC-201` | Run 状態不整合 | 競合 | 稀。実装仕様書で詳細化 |
| 500 | `GRS-REC-999` | Reco 想定外エラー | 内部エラー | Public 500 |
| 500 | `GRS-DB-001`〜`006` | DB 障害 | 永続化失敗 | Public 500 |
| 502 | `GRS-LLM-100`〜`104` | LLM / Embedding 失敗 | 外部依存 | Public 502 |
| 504 | `GRS-LLM-101` | LLM タイムアウト | タイムアウト | Public 504 |
| 503 | `GRS-COM-003` | 一時的利用不可（DB 接続失敗等） | サービス一時停止 | Public 503 へ集約可 |

### 8.2.1 Internal 認証・認可エラーの Public マップ（確定 #374）

api（`apps/api`）が reco（API-INT-002）呼び出しで受け取る `GRS-AUTH-*` は、**Public API（API-PUB-002）へそのまま返却しない**。MVP では Public API は匿名利用のため、エンドユーザー向け HTTP 401 / `GRS-AUTH-*` は定義しない（後続の会員認証導入時は API-AUT 系で別途定義）。

| Internal（reco→api） | Internal HTTP | Public（api→web）HTTP | Public `error.code` | Public `error.message` |
| -------------------- | ------------- | --------------------- | ------------------- | ---------------------- |
| `GRS-AUTH-001` | 401 | 500 | `GRS-REC-002` | エラーコード定義書の `GRS-REC-002` ユーザー向け文言 |
| `GRS-AUTH-004` | 401 | 500 | `GRS-REC-002` | 同上 |
| `GRS-AUTH-002` | 403 | 500 | `GRS-REC-002` | 同上 |
| `GRS-AUTH-003` | 403 | 500 | `GRS-REC-002` | 同上 |
| `GRS-AUTH-005` | 403 | 500 | `GRS-REC-002` | 同上 |

| 方針 | 内容 |
| ---- | ---- |
| `meta.traceId` / `meta.requestId` | Public 応答でも維持（§8.1） |
| error_log（内部） | 原文の `GRS-AUTH-*`・Internal HTTP Status・`upstream=reco`（または api 側事前検証時は `upstream=api`）を記録 |
| api 事前検証 | reco 呼び出し前に Internal API Key（環境変数）未設定時は reco を呼ばず、Public は上表と同じ 500 + `GRS-REC-002`。error_log には `GRS-AUTH-004` 相当を記録 |
| Secret | `X-Internal-Api-Key` 実値は Response・ログに含めない |

実装詳細（MOD-API-013 Error Handler、reco-client 例外変換、単体テスト）は API-INT-002 実装仕様書 Task で定義する。判断記録は `ai-logs/human-decisions/2026-06-05-api-int-002-internal-401-public-map-policy.md` を参照。

`GRS-REC-001` は **HTTP 200** の正常系（0 件）として扱い、§7.4.2 および `API-PUB-002_レコメンド実行API契約仕様書.md` §7.4.2 を参照。エラー Response 一覧には含めない。

`GRS-REQ-003`（予算未指定）・`GRS-REQ-004` / `005`（関係性・用途未指定）は、api 側 Public Validation で解消済みのため、本 API では原則返却しない。

---

## 9. バリデーション仕様

| 対象項目 | ルール | エラーコード | エラーメッセージ |
| -------- | ------ | ------------ | ---------------- |
| `recommendationRequestId` | 必須・非空 | `GRS-REQ-001` | リクエスト ID が不正です。 |
| `recommendationRequest` | 必須オブジェクト | `GRS-REQ-001` | 推薦条件が不正です。 |
| `recommendationRequest.relationship.relationshipCode` | 必須・非空 | `GRS-REQ-001` | 推薦条件が不正です。 |
| `recommendationRequest.occasion.occasionCode` | 必須・非空 | `GRS-REQ-001` | 推薦条件が不正です。 |
| `recommendationRequest.execution.mode` | 必須。enum 整合 | `GRS-REQ-001` | 実行モードが不正です。 |
| `recommendationRequest.execution.topK` | 指定時 1〜50 | `GRS-REQ-001` | 返却件数が不正です。 |
| `recommendationRequest.execution.candidateLimit` | 指定時 **`topK` 以上**（Recommendation Request §8.2） | `GRS-REQ-001` | 候補抽出上限が不正です。 |
| `recommendationRequest.budget.*` | 指定時 0 以上、min ≤ max | `GRS-REQ-001` | 予算条件が不正です。 |
| `execution.configName` / `execution.versionLabel` | 片方のみ指定は不可。両方指定または両方省略 | `GRS-REQ-001` | Semantic Config 指定が不正です。 |
| `execution.versionLabel` | 指定時 semver 形式（`^v[0-9]+\.[0-9]+\.[0-9]+$`） | `GRS-REQ-001` | Version ラベルが不正です。 |
| `X-Internal-Api-Key` | 必須・検証成功 | `GRS-AUTH-001` / `GRS-AUTH-004` | 認証に失敗しました。 |
| `X-Trace-Id` / `X-Request-Id` | 必須・非空 | `GRS-REQ-001` | 追跡 ID が不正です。 |
| JSON 形式 | パース可能 | `GRS-REQ-001` | リクエスト形式が不正です。 |

api 側で実施済みの業務 Validation（未対応組み合わせ等）を reco が再検出した場合は `GRS-REQ-002` / `GRS-REQ-006`（422）とする。

---

## 10. OpenAPI / generated 反映方針

| 項目 | 内容 |
| ---- | ---- |
| OpenAPI正本 | `packages/contracts/openapi/internal-reco-api.yaml`（正本は `packages/contracts/openapi/*.yaml`） |
| 操作 ID（案） | `runRecoRecommendation` または `createRecoRecommendationRun`（OpenAPI Task で確定） |
| Path | `/internal/reco/v1/recommendations/run` |
| components schema | `RecoRecommendationRunRequest` / `RecoRecommendationRunResponse` 等（OpenAPI Task で命名確定） |
| Orval設定 | リポジトリ正本 `orval.config.ts` |
| generated出力先（api→reco） | `apps/api/src/generated/reco-client/`（**Consumer は apps/api のみ**。`apps/web` は Internal API 非利用のため generated 対象外） |
| OpenAPI定義書 | `openapi-spec.md` テンプレ準拠の Contract Task 成果物 |

本 Task では YAML / generated の**実変更は行わない**。本契約仕様書を OpenAPI（internal）Contract Task の入力正本とする。

OpenAPI Contract Task で反映する差分（#373 確定分）:

- `WarningItem` schema、`warnings` を `WarningItem[]` に変更
- `MetricSummary` の固定 properties（`recommendationLatencyMs` / `phaseDurationMs` / `featureDistribution`）
- 0 件例: `resultStatus: completed`（`empty` は 0 件正規系に使わない）、`warnings` をオブジェクト配列に合わせる

OpenAPI Contract Task で反映する差分（#375 確定分・本 Task では YAML 未変更）:

- `metadata.debugPayload`（open object・optional）
- `scoreBreakdown` の返却条件を description で §7.3.8 参照

OpenAPI Contract Task で反映する差分（#376 確定分）:

- `ReasonData` / `ReasonDataItem` schema（§7.3.9）
- `resultItems[].reasonStatus` enum（MVP は Item 存続時 `completed` のみ。OpenAPI Contract Task で `failed` 削除または非推奨化を検討）
- `reasonSummary` の条件付き required（OpenAPI `required` または description で表現）

Contract Gate 通過後に Implementation Task（`api-implementation-spec`）および apps/reco・apps/api 実装 Task を開始する。

---

## 11. 互換性・破壊的変更

| 項目       | 内容 |
| ---------- | ---- |
| 破壊的変更 | MVP 初版のためなし |
| 後方互換性 | `v1` パス固定。フィールド追加は optional で許容 |
| 判断理由   | 初回 Internal 契約確定 |

### 11.1 rollout order

- 本契約確定 → `internal-reco-api.yaml` 更新 → Orval 再生成（reco-client）→ apps/api Reco Client 更新 → apps/reco エンドポイント実装 → API-PUB-002 結合

---

## 12. 契約面テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | 正常系 | 必須 Header + Body で 200、`resultItems` が 1 件以上、内部スコア項目（`contextScore` / `socialMatch` 等）あり | contract |
| 2 | 0 件正常系 | 200、`resultItems: []`、`resultItemCount: 0`、`resultStatus: completed`、`warnings[].code`（例: `NO_CANDIDATES_AFTER_RETRIEVAL`）、`meta.resultCode: GRS-REC-001` | contract |
| 8 | warnings / metricSummary | `WarningItem` 形式、`metricSummary` の mean/p95（任意項目） | contract |
| 9 | scoreBreakdown / debugPayload | debug返却条件（§7.3.8）を満たす Request で `scoreBreakdown` / `metadata.debugPayload` が推奨返却。欠落時も 200、`warnings` 非追加 | contract |
| 3 | validation error | `recommendationRequestId` 欠落で 400 | contract |
| 4 | auth error | `X-Internal-Api-Key` 欠落・不正で 401 | contract |
| 5 | permission error | 権限不足相当で 403（`GRS-AUTH-002` 等） | contract |
| 6 | trace 伝播 | `X-Trace-Id` 指定時に `meta.traceId` が一致 | contract |
| 7 | generated client | OpenAPI 生成後、型が Request/Response と一致（`apps/api` reco-client） | typecheck |

実装結合・パイプライン障害シミュレーションは実装仕様書・単体テスト Task で扱う。

---

## 13. 変更履歴

| 日付 | 変更内容 | 関連Issue / PR |
| ---- | -------- | -------------- |
| 2026-06-04 | 初版（契約面のみ。Task #368 / 分離後モデル） | #368 |
| 2026-06-04 | AI Review 指摘反映（`resultItems` / Result Status / Error / Validation / Observability 等） | #368 / #369 |
| 2026-06-04 | Human Review 指摘対応：§14 未決事項を個別 Issue 化（#373〜#376） | #368 / #372 |
| 2026-06-05 | §14 No.1 確定：`warnings`（`WarningItem`）/ `metricSummary`（mean・p95）、Transient 注記、MVP 警告コード 3 件 | #373 |
| 2026-06-05 | §14 No.2 確定：Internal 認証エラーの Public マップ（§8.2.1、#374） | #374 |
| 2026-06-05 | §14 No.3 確定：`scoreBreakdown` / `debugPayload` 返却条件、§7.3.8、`metadata.debugPayload` マッピング | #375 |
| 2026-06-05 | §14 No.4 確定：`reasonSummary` / `reasonData` 必須範囲（§7.3.2.1、§7.3.9、#376） | #376 |
| 2026-06-10 | evaluation / batch 用 Semantic Config 指定を `execution.configName` + `execution.versionLabel` composite に変更。`debugPayload` 推奨キーも追随 | Task #463 |
| 2026-06-25 | MOD-RECO-001 §10.3 整合：Reason 失敗時も非空 `reasonSummary` + `isFallback: true` + `reasonStatus: completed`（§7.3.2.1、§14.1 No.4 更新） | #764 |
| 2026-07-16 | `resultItems[]` に `reasonPoints` / `reasonDetail` を任意追加。Public 表面化注記を更新（#1398） | #1398 |

---

## 14. 未決事項

本節の論点は **人間判断待ち** として個別 Issue で管理する（作業計画の正本は Issue。契約仕様書は論点の参照先）。

### 14.1 確定済み（本書へ反映済み）

| No | 論点 | 確定内容 | 反映箇所 | 追跡 Issue |
| --: | ---- | -------- | -------- | ---------- |
| 1 | `warnings` / `metricSummary` のスキーマ詳細 | `warnings`: `WarningItem[]`（`code` 必須）。`metricSummary`: `recommendationLatencyMs` / `phaseDurationMs` / `featureDistribution`（`mean`, `p95` のみ）。Transient（DB 非永続）。0 件は `resultStatus: completed` | §7.3.4〜§7.3.7 | #373 |
| 2 | Internal 401/403（`GRS-AUTH-*`）の Public マップ方針 | `GRS-AUTH-*` は Public 非露出。api→web は **500 + `GRS-REC-002`**。内部は error_log に原文保持 | §8.2.1 | #374 |
| 3 | `scoreBreakdown` / `debug_payload` の返却条件 | debug返却条件 = `mode=evaluation` OR `includeDebugInfo=true`。両フィールドは**推奨**（必須ではない）。`debug_payload` → `data.metadata.debugPayload`。欠落時はログのみ・200 継続。`batch`+`includeDebugInfo=false` は省略 | §7.3.8 | #375 |
| 4 | `reasonSummary` / `reasonData` の必須/任意（Internal） | Item: `includeReason=true` かつ Item 存続時 `reasonSummary` 必須（非空）。Reason のみ失敗時は §17.2 汎用 Reason 注入＋`isFallback: true`＋`reasonStatus: completed`（#376 確定を #764 / MOD-RECO-001 §10.3 で更新）。Run: `reasonData` 任意、debug/evaluation 時推奨（§7.3.9） | §7.3.2.1、§7.3.9 | #376, #764 |

OpenAPI（`internal-reco-api.yaml`）への機械可読反映は **別 Contract Task** とする。

### 14.2 未決（人間判断待ち）

| No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 | 追跡 Issue |
| --: | ---- | ---------------- | ------ | ---- | ---- | ---------- |

（現時点、未決事項なし）

---

## 15. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| API一覧 | `docs/05_アプリケーション設計/アプリ/api/API一覧.md` | API-INT-002 行 |
| API設計方針書 | `docs/05_アプリケーション設計/アプリ/api/API設計方針書.md` | Internal API / Reco Internal API §21 |
| エラーコード定義書 | `docs/05_アプリケーション設計/アプリ/エラーコード定義書.md` | GRS-* |
| 認証・認可方針書 | `docs/05_アプリケーション設計/基盤/認証・認可方針書.md` | Internal API Key |
| ログ・Observability設計書 | `docs/05_アプリケーション設計/アプリ/ログ・Observability設計書.md` | trace / phase / metric |
| Recommendation Request | `docs/04_ドメインモデル設計/RecommendationRequest定義書.md` | Request Body |
| Recommendation Result | `docs/04_ドメインモデル設計/RecommendationResult定義書.md` | Response 項目 |
| Reason生成 | `docs/04_ドメインモデル設計/Reason生成定義書.md` | reason 項目 |
| Recoモジュール一覧 | `docs/05_アプリケーション設計/アプリ/reco/Recoモジュール一覧.md` | MOD-RECO-001 参照 |
| 機能×モジュール対応表 | `docs/05_アプリケーション設計/アプリ/機能×モジュール対応表.md` | MOD-API-005 / MOD-RECO-001 |
| 上流 Public API（参照） | `docs/06_実装設計/api/API-PUB-002_レコメンド実行API契約仕様書.md` | web↔api 間の Public 契約 |
| Task Definition | `prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-contract-spec.yaml` | #368 scope |
| 実装仕様（別Task） | `prompts/definitions/tasks/api-int-002-reco-recommendation-run/api-implementation-spec.yaml`（予定） | Phase4 |

---

## 16. レビュー観点

- API契約（Request / Response / Error / Validation）が明確で、OpenAPI（internal）Task の入力として十分か
- API一覧の API-INT-002（endpoint / Method / Internal / Provider reco・Consumer api / MVP）と一致しているか
- API設計方針書 §21（Reco Internal API）および §11.3（Internal 保護）と矛盾していないか
- Provider（apps/reco エンドポイント層）/ Consumer（apps/api）の I/F 境界が明確か
- Public API（API-PUB-002）との責務分離（スコア表面化・認証差）が明記されているか
- 処理フロー・MOD-RECO 実装詳細を含んでいないか
- `packages/contracts/openapi/internal-reco-api.yaml` への反映方針が明確か（本 Task でファイル未変更）
- secret / `.env` 実値が含まれていないか

### 16.1 Human Review で確認してほしいこと

- 正式 Endpoint（`POST /internal/reco/v1/recommendations/run`）と api→reco I/F 境界
- Request Body に `recommendationRequestId` + 正規化済み `recommendationRequest` を含める方針
- Internal Response の `warnings` / `metricSummary` が §7.3.4〜§7.3.7 と一致しているか（#373 確定分）
- `scoreBreakdown` / `metadata.debugPayload` の返却条件が §7.3.8 と human-decisions で一致しているか（#375 確定分）
- `reasonSummary` / `reasonData` が §7.3.2.1 / §7.3.9 と一致しているか（#376 確定分）
- OpenAPI Contract Task への分離方針（`internal-reco-api.yaml`）
- 上流 API-PUB-002 契約仕様書との整合（0 件・reason・予算任意化）

---

## 17. 備考

- 本書は `prompts/templates/docs/api-contract-spec.md` に準拠した Phase1 ①（1a）成果物である。
- ログ・Observability（access_log / phase_log / error_log / metric）の**実装**記録方針は実装仕様書で扱う。契約上は `traceId` / `requestId` / `recommendationRunId` の往復を必須とする。
- MOD-RECO-001（Recommendation Orchestrator）は本 API の**呼び出し先処理**として参照するのみ。パイプライン内部のモジュール順序・エラー伝播の詳細は Reco モジュール仕様・実装仕様書を正とする。
