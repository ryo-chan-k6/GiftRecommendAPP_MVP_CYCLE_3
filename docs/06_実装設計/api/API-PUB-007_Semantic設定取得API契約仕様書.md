# Semantic設定取得 API契約仕様書

> 本書は **API-PUB-007** の契約面（Public I/F）正本である。
> Master Repository・MOD-API-011/012 責務・内部 DTO マッピング・結合テスト観点は `API-PUB-007_Semantic設定取得API実装仕様書.md`（別 Task）で定義する。
> OpenAPI 正本は `packages/contracts/openapi/public-api.yaml`（別 Contract Task）。

## 1. ドキュメント情報

| 項目           | 内容                                      |
| -------------- | ----------------------------------------- |
| ドキュメントID | `API-PUB-007-CONTRACT`                    |
| ドキュメント名 | Semantic設定取得 API契約仕様書            |
| 対象システム   | Gift Recommendation Service MVP（Public） |
| MVP対象        | `○`                                       |
| 作成日         | 2026-06-05                                |
| 更新日         | 2026-06-10（composite 参照・semantic_config_version 定義書 §17.1 追随） |

---

## 2. 概要

web（`apps/web`）から api（`apps/api`）へ、レコメンド条件入力画面（SCR-002）初期表示時に利用する **Semantic Config のスナップショット** を取得する Public API である。現行の Semantic Config Version に紐づく Semantic Concept 定義および Feature Definition（8 次元）を返す（[API一覧](../../05_アプリケーション設計/アプリ/api/API一覧.md) §API-PUB-007）。

Relationship / Occasion マスタ（API-PUB-005 / 006）および Feature Rule（API-PUB-008）と並列取得される。Pair Rule や Semantic Rule の内部パターン・重みは Public 表面に含めない。

---

## 3. 目的

- MVP 画面が参照する Semantic Config スナップショットの Request / Response / Error / Validation を確定する。
- 後続の OpenAPI Contract Task（`public-api.yaml`）および Contract Gate の入力とする。
- Semantic Config / Semantic Concept / Feature Definition の正本定義・API設計方針書・API一覧・エラーコード定義書と整合した契約面を提供する。

---

## 4. API基本情報

| 項目     | 内容                                              |
| -------- | ------------------------------------------------- |
| API ID   | `API-PUB-007`                                     |
| API名    | Semantic設定取得                                  |
| API種別  | `Public API`                                      |
| Method   | `GET`                                             |
| Endpoint | `/api/v1/masters/semantic-configs`                |
| Base URL | 環境ごとに環境変数で定義（本書ではパスを正とする） |
| Version  | `v1`（URL パスに含む）                            |
| Provider | `apps/api`                                        |
| Consumer | `apps/web`                                        |
| 認証要否 | `false`（MVP は非認証。後続で Authorization 追加可） |
| 権限条件 | MVP ではなし（公開参照のみ）                      |
| 冪等性   | `冪等`（副作用なしの参照 API）                    |
| MVP対象  | `○`                                               |

---

## 5. 利用シーン

### 5.1 利用タイミング

- レコメンド条件入力画面（SCR-002）の初期表示時
- 他マスタ API（API-PUB-005〜006 / 008）と並列呼び出しされる

### 5.2 呼び出し元

- `apps/web`（レコメンド条件入力画面）

### 5.3 主なユースケース

- 現行（`is_current = true`）の Semantic Config Version を解決し、その Version に紐づく Semantic Concept / Feature Definition のスナップショットを取得する。
- web が Feature 軸名・Semantic Concept 表示ラベル等の参照に利用する（MVP では画面非表示でも、クライアント側バリデーション・デバッグ・将来 UI 拡張の前提データとする）。
- 設定未整備時は HTTP **500** と `GRS-CFG-001` を返す（マスタ不足の代表）。

### 5.4 他マスタ API との関係（契約上の前提のみ）

| 項目 | 内容 |
| ---- | ---- |
| 並列取得群 | API-PUB-005 / 006 / 007 / 008 |
| Version 整合 | 本 API の **`configName` + `versionLabel`**（composite）は API-PUB-008 と一致する前提 |
| 非公開情報 | `semantic_rule` のパターン・重み、`pair_rule`、正規化パラメータの詳細は本 API および API-PUB-008 の Public 応答に含めない |

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

なし。

### 6.3 Query Parameters

| 項目 | 型 | 必須 | 内容 | 制約 | 例 |
| ---- | -- | ---- | ---- | ---- | -- |
| -    | -  | -    | なし | -    | -  |

MVP では Query Parameter を定義しない。将来、特定 Version を指定する `configName` / `versionLabel` を optional で追加可能（破壊的変更に該当しない追加のみ）。

### 6.4 Request Body

なし（GET では Request Body を使用しない）。

### 6.5 Request Example

```http
GET /api/v1/masters/semantic-configs HTTP/1.1
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
| 200 | 処理成功 | Semantic Config スナップショットを返却できる場合 |
| 400 | Request 不正 | 未知 Query 等の Validation 失敗（`GRS-REQ-001`） |
| 500 | 内部エラー | current Semantic Config 未設定（`GRS-CFG-001`）、解決失敗（`GRS-CFG-002`）、有効 Feature Definition 0 件（`GRS-CFG-006`）、DB 障害（`GRS-DB-*` / `GRS-CFG-999`） |
| 503 | 一時利用不可 | DB 一時不可（`GRS-DB-001`） |

**空配列・不足方針（§14 決定事項）:**

| 条件 | HTTP Status | 扱い |
| ---- | ----------- | ---- |
| current Version 自体が存在しない | 500 | `GRS-CFG-001` |
| Version あり・Semantic Concept 0 件（`is_active = true`） | 200 | `semanticConcepts: []` |
| Version あり・有効 Feature Definition 0 件 | 500 | `GRS-CFG-006` |
| Version あり・Concept / Feature Definition ともに 1 件以上 | 200 | 通常応答 |

`is_active = false` の行は応答に含めない（§14 決定事項 No.1）。

### 7.3 Response Body

成功時は API設計方針書 §8.2 の **`data` + `meta`** 構造を基本とする。

#### 7.3.1 `data`（Semantic Config スナップショット）

| 項目 | 型 | 必須 | 内容 | 備考 |
| ---- | -- | ---- | ---- | ---- |
| `configName` | `string` | `true` | Semantic Config 系列名 | 親 `semantic_config.config_name`。api がアプリ層 JOIN で解決 |
| `versionLabel` | `string` | `true` | Version ラベル（semver） | `semantic_config_version.version_label`。例: `v1.0.0` |
| `semanticConcepts` | `array` | `true` | Semantic Concept 一覧 | `is_active = true` の行のみ（§14 決定事項 No.1） |
| `semanticConcepts[].conceptCode` | `string` | `true` | Concept コード | snake_case 物理名を API では camelCase キーで表現 |
| `semanticConcepts[].conceptLabel` | `string` | `true` | 表示ラベル | - |
| `semanticConcepts[].conceptDescription` | `string` | `false` | 説明 | - |
| `semanticConcepts[].isActive` | `boolean` | `true` | 有効フラグ | 応答に含める行は `true` |
| `featureDefinitions` | `array` | `true` | Feature Definition 一覧 | `is_active = true` の行のみ。MVP 8 次元固定（§14 決定事項 No.1） |
| `featureDefinitions[].featureCode` | `string` | `true` | Feature コード | `formality` 等（用語集・AGENTS.md 固定名） |
| `featureDefinitions[].featureLabel` | `string` | `true` | 表示ラベル | - |
| `featureDefinitions[].featureGroup` | `string` | `true` | 軸グループ | enum: `social` / `symbolic` |
| `featureDefinitions[].displayOrder` | `integer` | `false` | 表示順 | 1 始まり |
| `featureDefinitions[].isActive` | `boolean` | `true` | 有効フラグ | 応答に含める行は `true` |

**MVP 固定 Feature 名（契約上の許容値）:**

| featureGroup | featureCode |
| ------------ | ----------- |
| `social` | `formality`, `safety`, `brand_appropriateness` |
| `symbolic` | `emotion`, `novelty`, `intimacy`, `symbolic_identity`, `story_richness` |

**Public Version 参照:** `configName` + `versionLabel` の **composite** で現行 version を識別する。単一 `semanticConfigVersionId` 表面 ID は **返却しない**。内部 DB 主キー（`semantic_config_version_id` 等）も非公開。

**返却しない項目（契約上明示）:** `semanticConfigVersionId`、`semantic_rule` の `source_text_pattern` / `weight`、`pair_rule`、`normalization_rule` のパラメータ、`model_version_id`、内部 DB 主キー（`semantic_concept_id` 等）。Public 表面はコード体系（`conceptCode` / `featureCode` 等）のみとする（§14 決定事項 No.2）。

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
    "configName": "mvp-semantic-config",
    "versionLabel": "v1.0.0",
    "semanticConcepts": [
      {
        "conceptCode": "formal_refined",
        "conceptLabel": "フォーマルで上品",
        "conceptDescription": "贈答として格式があり、品のある印象",
        "isActive": true
      },
      {
        "conceptCode": "warm_gratitude",
        "conceptLabel": "感謝が伝わる",
        "isActive": true
      }
    ],
    "featureDefinitions": [
      {
        "featureCode": "formality",
        "featureLabel": "格式",
        "featureGroup": "social",
        "displayOrder": 1,
        "isActive": true
      },
      {
        "featureCode": "emotion",
        "featureLabel": "感情",
        "featureGroup": "symbolic",
        "displayOrder": 4,
        "isActive": true
      }
    ]
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440000",
    "requestId": "req_01HZYX",
    "generatedAt": "2026-06-05T12:00:00+09:00"
  }
}
```

#### 7.4.2 Semantic Concept 空配列正常系（200）

Version あり・有効 Feature Definition 1 件以上の場合。Concept 0 件は 200 とする。

```json
{
  "data": {
    "configName": "mvp-semantic-config",
    "versionLabel": "v1.0.0",
    "semanticConcepts": [],
    "featureDefinitions": [
      {
        "featureCode": "formality",
        "featureLabel": "格式",
        "featureGroup": "social",
        "displayOrder": 1,
        "isActive": true
      }
    ]
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440001",
    "requestId": "req_01HZYY"
  }
}
```

#### 7.4.3 Feature Definition 不足（500）

Version あり・有効 Feature Definition 0 件の場合。

```json
{
  "error": {
    "code": "GRS-CFG-006",
    "message": "選択項目の取得に失敗しました。",
    "details": []
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440003",
    "requestId": "req_01HZYZ"
  }
}
```

---

## 8. Error Response仕様

### 8.1 Error Response形式

```json
{
  "error": {
    "code": "GRS-CFG-001",
    "message": "選択項目の取得に失敗しました。",
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
| -----: | ---------- | -------- | -------------- | ---------------- |
| 400 | `GRS-REQ-001` | 未知 Query Parameter 等 | Validation 失敗 | 条件を確認してください。 |
| 500 | `GRS-CFG-001` | current Semantic Config / Version 未設定 | Current Config Not Found | 選択項目の取得に失敗しました。 |
| 500 | `GRS-CFG-002` | `semantic_config_version` 解決失敗 | Semantic Config Resolve Failed | 選択項目の取得に失敗しました。 |
| 500 | `GRS-CFG-006` | Feature Definition 不足（有効定義 0 件等） | Feature Definition Missing | 選択項目の取得に失敗しました。 |
| 500 | `GRS-DB-001` | DB 接続失敗 | 永続化基盤障害 | データ処理に失敗しました。 |
| 500 | `GRS-DB-002` | DB 参照失敗 | 読取失敗 | データ取得に失敗しました。 |
| 500 | `GRS-CFG-999` | 設定系想定外 | Config Unexpected Error | 設定情報の処理に失敗しました。 |
| 503 | `GRS-DB-001` | DB 一時不可 | サービス一時停止 | データ処理に失敗しました。 |

---

## 9. バリデーション仕様

| 対象項目 | ルール | エラーコード | エラーメッセージ |
| -------- | ------ | ------------ | ---------------- |
| HTTP Method | `GET` のみ許可 | - | ルーティング層で拒否 |
| Request Body | 送信しない | - | GET では Body なし |
| 未知 Query | MVP では未定義 Query を受け付けない（400 で拒否。§14 決定事項 No.4） | `GRS-REQ-001` | 条件を確認してください。 |

---

## 10. OpenAPI / generated 反映方針

| 項目 | 内容 |
| ---- | ---- |
| OpenAPI正本 | `packages/contracts/openapi/public-api.yaml` |
| 操作 ID（案） | `getSemanticConfigMasters` |
| Path | `/api/v1/masters/semantic-configs` |
| components schema | `SemanticConfigMastersResponse` / `SemanticConceptMaster` / `FeatureDefinitionMaster` 等 |
| Orval設定 | リポジトリ正本 `orval.config.ts` |
| generated出力先（web） | `apps/web/src/generated/api/` |

本 Task では YAML / generated の**実変更は行わない**。

---

## 11. 互換性・破壊的変更

| 項目       | 内容 |
| ---------- | ---- |
| 破壊的変更 | MVP 初版のためなし |
| 後方互換性 | `v1` パス固定。フィールド追加は optional で許容 |
| 判断理由   | 初回 Public Semantic Config マスタ契約確定 |

### 11.1 rollout order

- 本契約確定 → `public-api.yaml` 更新 → Orval 再生成 → web api-client 更新 → api 実装

---

## 12. 契約面テスト観点

|  No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | 正常系 | current Version 存在時 200、`configName` + `versionLabel` と配列が返る | contract |
| 2 | Concept 空配列 | Version あり・Concept 0 件で 200 + `semanticConcepts: []` | contract |
| 3 | 設定未整備 | current Version なしで 500 / `GRS-CFG-001` | contract |
| 4 | Feature 不足 | 有効 Feature Definition 0 件で 500 / `GRS-CFG-006` | contract |
| 5 | validation | 未知 Query で 400 / `GRS-REQ-001` | contract |
| 6 | version 整合 | API-PUB-008 と同一 `configName` + `versionLabel` | contract |
| 7 | generated client | OpenAPI 確定後、Orval 生成型と schema 一致 | typecheck |

---

## 13. 変更履歴

| 日付 | 変更内容 | 関連Issue / PR |
| ---- | -------- | -------------- |
| 2026-06-05 | 初版（Phase1 1a 契約面） | Issue #403 |
| 2026-06-05 | Human Review 指摘反映（§14 決定事項確定・空配列方針整合） | PR #407 |
| 2026-06-10 | Public Version 参照を `configName` + `versionLabel` composite に変更（`semanticConfigVersionId` 表面 ID 廃止） | Task #463 / `semantic_config_version_テーブル定義書` §17.1 |

---

## 14. 決定事項（Human Review 確定）

|  No | 論点 | 決定内容 | 判断者 | 関連 |
| --: | ---- | -------- | ------ | ---- |
| 1 | 応答に `is_active = false` の行を含めるか | **含めない**。`is_active = true` の行のみ返却する | Human | §7.3.1 |
| 2 | DB 主キー（`semantic_concept_id` 等）を Public に含めるか | **含めない**。コード体系（`conceptCode` / `featureCode` 等）のみ | Human | §7.3.1 |
| 3 | Concept / Definition 0 件の HTTP Status | **Version あり・Concept 0 件は 200**、**Version あり・有効 Feature Definition 0 件は 500（`GRS-CFG-006`）** | Human | §7.2 / §7.4.2 / §7.4.3 |
| 4 | 未知 Query を 400 とするか無視するか | **400（`GRS-REQ-001`）で拒否** | Human | §6.3 / §9 |
| 5 | Public Version 参照キー | **`configName` + `versionLabel` composite**（両方必須）。`semanticConfigVersionId` 表面 ID は不採用 | Human | `semantic_config_version_テーブル定義書` §17.1 |

---

## 15. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| API一覧 | `docs/05_アプリケーション設計/アプリ/api/API一覧.md` | API-PUB-007 行 |
| API設計方針書 | `docs/05_アプリケーション設計/アプリ/api/API設計方針書.md` | URL / Error / data+meta |
| エラーコード定義書 | `docs/05_アプリケーション設計/アプリ/エラーコード定義書.md` | GRS-CFG-* / GRS-DB-* |
| 正本定義表 | `docs/05_アプリケーション設計/アプリ/database/正本定義表.md` | Semantic Config 正本 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | semantic_config / semantic_concept / feature_definition |
| インターフェース一覧 | `docs/05_アプリケーション設計/アプリ/インターフェース一覧.md` | IF-PUB-007 |
| 関連契約 | `docs/06_実装設計/api/API-PUB-008_Featureルール取得API契約仕様書.md` | Version 整合 |
| 契約テンプレ | `prompts/templates/docs/api-contract-spec.md` | 章構成 |

---

## 16. レビュー観点

- API契約（Request / Response / Error / Validation）が明確で確定可能である
- API設計方針書・API一覧と整合している
- Semantic Config / Concept / Feature Definition の Public 表面のみを返却している
- 内部 Rule（semantic_rule / pair_rule / normalization）を含まない
- API-PUB-008 との `configName` + `versionLabel` composite 整合が明記されている
- OpenAPI 反映方針が明確である
- 実装詳細（Repository / MOD-API フロー）を含めず契約面に限定している

---

## 17. 備考

- メトリクス: `masters_semantic_configs_request_count` / `masters_semantic_configs_error_count`（API一覧 §API-PUB-007）
- trace_id: 任意（API一覧 §trace_id対象）
- マスタ参照 API では `configName` + `versionLabel` を返却し、レコメンド結果 Response には含めない（API設計方針書 §18.4）
