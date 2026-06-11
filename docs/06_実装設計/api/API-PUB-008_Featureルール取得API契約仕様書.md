# Featureルール取得 API契約仕様書

> 本書は **API-PUB-008** の契約面（Public I/F）正本である。
> Master Repository・MOD-API-011/012 責務・内部 DTO マッピング・結合テスト観点は `API-PUB-008_Featureルール取得API実装仕様書.md`（別 Task）で定義する。
> OpenAPI 正本は `packages/contracts/openapi/public-api.yaml`（別 Contract Task）。

## 1. ドキュメント情報

| 項目           | 内容                                      |
| -------------- | ----------------------------------------- |
| ドキュメントID | `API-PUB-008-CONTRACT`                    |
| ドキュメント名 | Featureルール取得 API契約仕様書           |
| 対象システム   | Gift Recommendation Service MVP（Public） |
| MVP対象        | `○`                                       |
| 作成日         | 2026-06-05                                |
| 更新日         | 2026-06-05                                |

---

## 2. 概要

web（`apps/web`）から api（`apps/api`）へ、レコメンド条件入力画面（SCR-002）初期表示時に利用する **Feature Rule 一覧** を取得する Public API である。現行 Semantic Config Version に紐づく Relationship Rule / Occasion Rule / Concept Feature Rule を返す（[API一覧](../../05_アプリケーション設計/アプリ/api/API一覧.md) §API-PUB-008、[Featureルール定義書](../../04_ドメインモデル設計/Featureルール定義書.md) §17）。

**Pair Rule**（Relationship × Occasion 組み合わせ補正）は Public API 応答に含めない（API一覧 §API-PUB-005 備考「Pair情報はPublic API応答に含めず」と同方針）。正規化パラメータ（`feature_normalization_version`）も含めない。

**Response 構成（MVP 確定）:** `baseValueRules[]`（Relationship / Occasion 等の基準値 Rule）と `conceptFeatureRules[]`（Concept 補正 Rule）の **2 グループ構成** とする（Human Review #408 確定）。

---

## 3. 目的

- MVP 画面が参照する Feature Rule 一覧の Request / Response / Error / Validation を確定する。
- 後続の OpenAPI Contract Task（`public-api.yaml`）および Contract Gate の入力とする。
- Feature Rule 正本定義・API設計方針書・API一覧・エラーコード定義書・API-PUB-005/006/007 との整合を提供する。

---

## 4. API基本情報

| 項目     | 内容                                              |
| -------- | ------------------------------------------------- |
| API ID   | `API-PUB-008`                                     |
| API名    | Featureルール取得                                 |
| API種別  | `Public API`                                      |
| Method   | `GET`                                             |
| Endpoint | `/api/v1/masters/feature-rules`                   |
| Base URL | 環境ごとに環境変数で定義（本書ではパスを正とする） |
| Version  | `v1`（URL パスに含む）                            |
| Provider | `apps/api`                                        |
| Consumer | `apps/web`                                        |
| 認証要否 | `false`（MVP は非認証）                           |
| 権限条件 | MVP ではなし（公開参照のみ）                      |
| 冪等性   | `冪等`                                            |
| MVP対象  | `○`                                               |

---

## 5. 利用シーン

### 5.1 利用タイミング

- レコメンド条件入力画面（SCR-002）初期表示時
- API-PUB-005〜007 と並列取得

### 5.2 呼び出し元

- `apps/web`（レコメンド条件入力画面）

### 5.3 主なユースケース

- 現行 Semantic Config Version に紐づく Feature Rule を一覧取得する。
- web が Relationship / Occasion コード（API-PUB-005/006）および Semantic Concept（API-PUB-007）と整合した Rule 参照に利用する。
- Pair Rule は Reco 内部で Relationship + Occasion 選択後に適用し、本 Public API では返却しない。

### 5.4 他 API との関係

| 項目 | 内容 |
| ---- | ---- |
| API-PUB-005 | `relationshipCode` は本 API の `baseValueRules[]`（`ruleType: relationship`）と整合 |
| API-PUB-006 | `occasionCode` は本 API の `baseValueRules[]`（`ruleType: occasion`）と整合 |
| API-PUB-007 | `semanticConfigVersionId` および `conceptCode` が整合 |
| 非公開 | `pair_rule` 行は応答に含めない（Reco 内部完結） |

---

## 6. Request仕様

### 6.1 Request Header

| Header         | 必須    | 内容               | 例                                   |
| -------------- | ------- | ------------------ | ------------------------------------ |
| `Accept`       | `true`  | `application/json` | `application/json`                   |
| `X-Trace-Id`   | `false` | 横断追跡 ID        | `550e8400-e29b-41d4-a716-446655440000` |
| `X-Request-Id` | `false` | API リクエスト ID  | `req_01HZYX`                         |

### 6.2 Path Parameters

なし。

### 6.3 Query Parameters

| 項目 | 型 | 必須 | 内容 | 制約 | 例 |
| ---- | -- | ---- | ---- | ---- | -- |
| -    | -  | -    | なし | -    | -  |

### 6.4 Request Body

なし。

### 6.5 Request Example

```http
GET /api/v1/masters/feature-rules HTTP/1.1
Host: api.example.com
Accept: application/json
```

---

## 7. Response仕様

### 7.1 Response Header

| Header         | 内容               |
| -------------- | ------------------ |
| `Content-Type` | `application/json` |

### 7.2 Status Code

| Status | 意味 | 利用条件 |
| -----: | ---- | -------- |
| 200 | 処理成功 | Feature Rule 一覧を返却できる場合 |
| 400 | Request 不正 | 未知 Query 等（`GRS-REQ-001`） |
| 500 | 内部エラー | 設定未整備（`GRS-CFG-001` / `GRS-CFG-005`）、DB 障害（`GRS-DB-*` / `GRS-CFG-999`） |
| 503 | 一時利用不可 | DB 一時不可（`GRS-DB-001`） |

**空配列方針:** 各 Rule 配列が 0 件でも HTTP **200** とする（API一覧「マスタ未設定時は空配列等」）。current Version 未設定のみ `GRS-CFG-001`。

**active Rule のみ返却（MVP 確定）:** DB 上 `is_active = false` の Rule は応答に含めない。`isActive` フィールドは Public 応答に含めない（サーバ側で active のみ抽出）。

### 7.3 Response Body

#### 7.3.1 `data`

| 項目 | 型 | 必須 | 内容 | 備考 |
| ---- | -- | ---- | ---- | ---- |
| `semanticConfigVersionId` | `string` | `true` | 現行 Semantic Config Version ID | API-PUB-007 と一致 |
| `baseValueRules` | `array` | `true` | 基準値 Rule 一覧 | `relationship_rule` / `occasion_rule` 表面 |
| `baseValueRules[].ruleType` | `string` | `true` | Rule 種別 | enum: `relationship` / `occasion` |
| `baseValueRules[].relationshipCode` | `string` | 条件付き | Relationship コード | `ruleType: relationship` 時必須。API-PUB-005 と整合 |
| `baseValueRules[].occasionCode` | `string` | 条件付き | Occasion コード | `ruleType: occasion` 時必須。API-PUB-006 と整合 |
| `baseValueRules[].featureCode` | `string` | `true` | Feature コード | MVP 8 次元 |
| `baseValueRules[].featureBaseValue` | `number` | `true` | 基準値 | 0.0〜1.0（API設計方針書 §7.3、Human Review 確定） |
| `conceptFeatureRules` | `array` | `true` | Concept Feature Rule 一覧 | `concept_feature_rule` 表面 |
| `conceptFeatureRules[].conceptCode` | `string` | `true` | Semantic Concept コード | API-PUB-007 と整合 |
| `conceptFeatureRules[].featureCode` | `string` | `true` | Feature コード | - |
| `conceptFeatureRules[].featureDelta` | `number` | `true` | 補正値（delta） | 0.0〜1.0。方向は `polarity` で表現 |
| `conceptFeatureRules[].polarity` | `string` | `false` | 極性 | enum: `positive` / `negative` / `mixed` |

**`ruleType` ごとのコードフィールド:**

| `ruleType` | 必須コードフィールド | 整合先 API |
| ---------- | -------------------- | ---------- |
| `relationship` | `relationshipCode` | API-PUB-005 |
| `occasion` | `occasionCode` | API-PUB-006 |

**返却しない Rule 種別:** `pair_rule`、`input_type_rule`、`feature_integration_rule`（内部処理用）。

#### 7.3.2 `meta`

| 項目 | 型 | 必須 | 内容 |
| ---- | -- | ---- | ---- |
| `traceId` | `string` | `true` | 横断追跡 ID |
| `requestId` | `string` | `true` | API リクエスト ID |
| `generatedAt` | `string` | `false` | 応答生成日時（ISO 8601） |

### 7.4 Response Example

```json
{
  "data": {
    "semanticConfigVersionId": "semantic_config_v001",
    "baseValueRules": [
      {
        "ruleType": "relationship",
        "relationshipCode": "boss",
        "featureCode": "formality",
        "featureBaseValue": 0.85
      },
      {
        "ruleType": "occasion",
        "occasionCode": "thanks",
        "featureCode": "emotion",
        "featureBaseValue": 0.7
      }
    ],
    "conceptFeatureRules": [
      {
        "conceptCode": "formal_refined",
        "featureCode": "formality",
        "featureDelta": 0.15,
        "polarity": "positive"
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

---

## 8. Error Response仕様

### 8.1 Error Response形式

API-PUB-007 と同一構造（`error` + `meta`）。

### 8.2 Error一覧（代表）

| Status | Error Code | 発生条件 | ユーザー向け表示 |
| -----: | ---------- | -------- | ---------------- |
| 400 | `GRS-REQ-001` | 未知 Query 等 | 条件を確認してください。 |
| 500 | `GRS-CFG-001` | current Version 未設定 | 選択項目の取得に失敗しました。 |
| 500 | `GRS-CFG-005` | マスタ不足（Rule 参照不能） | 選択項目の取得に失敗しました。 |
| 500 | `GRS-DB-001` | DB 接続失敗 | データ処理に失敗しました。 |
| 500 | `GRS-DB-002` | DB 参照失敗 | データ取得に失敗しました。 |
| 500 | `GRS-CFG-999` | 設定系想定外 | 設定情報の処理に失敗しました。 |
| 503 | `GRS-DB-001` | DB 一時不可 | データ処理に失敗しました。 |

---

## 9. バリデーション仕様

| 対象項目 | ルール | エラーコード |
| -------- | ------ | ------------ |
| HTTP Method | `GET` のみ | - |
| Request Body | なし | - |
| 未知 Query | MVP では拒否 | `GRS-REQ-001` |
| `featureBaseValue` | 0.0〜1.0 | - |
| `featureDelta` | 0.0〜1.0 | - |
| `baseValueRules[].ruleType` | `relationship` / `occasion` | - |
| `baseValueRules[].relationshipCode` | `ruleType: relationship` 時必須 | - |
| `baseValueRules[].occasionCode` | `ruleType: occasion` 時必須 | - |
| inactive Rule | 応答に含めない（サーバ側フィルタ） | - |

---

## 10. OpenAPI / generated 反映方針

| 項目 | 内容 |
| ---- | ---- |
| OpenAPI正本 | `packages/contracts/openapi/public-api.yaml` |
| 操作 ID（案） | `getFeatureRuleMasters` |
| Path | `/api/v1/masters/feature-rules` |
| components schema | `FeatureRuleMastersResponse` / `BaseValueRuleMaster` / `ConceptFeatureRuleMaster` 等 |
| 条件付き必須 | `baseValueRules` は `ruleType` による `oneOf` / `discriminator` 表現を Contract Task で検討 |

本 Task では YAML / generated の実変更は行わない。

---

## 11. 互換性・破壊的変更

| 項目 | 内容 |
| ---- | ---- |
| 破壊的変更 | MVP 初版のためなし |
| 後方互換性 | optional フィールド追加を許容 |

---

## 12. 契約面テスト観点

|  No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | 正常系 | 200 + `baseValueRules` / `conceptFeatureRules` の 2 グループ | contract |
| 2 | Pair 非公開 | 応答に pair 関連フィールドがない | contract |
| 3 | コード整合 | `relationshipCode` / `occasionCode` / `conceptCode` が他マスタ API と一致 | contract |
| 4 | Version 整合 | `semanticConfigVersionId` が API-PUB-007 と一致 | contract |
| 5 | 空配列 | 各配列 0 件でも 200 | contract |
| 6 | 設定未整備 | current Version なしで 500 / `GRS-CFG-001` | contract |
| 7 | active のみ | inactive Rule が応答に含まれない | contract |
| 8 | 値域 | `featureBaseValue` / `featureDelta` が 0.0〜1.0 | contract |

---

## 13. 変更履歴

| 日付 | 変更内容 | 関連Issue / PR |
| ---- | -------- | -------------- |
| 2026-06-05 | 初版（Phase1 1a 契約面） | Issue #404 |
| 2026-06-05 | Human Review 反映（2 グループ構成・値域・active のみ・Pair Reco 内部完結） | PR #408 |
| 2026-06-11 | `concept_feature_rule` テーブル定義書 Human Review 決定を反映（polarity / feature_delta 値域 / semantic_concept_id FK） | Issue #476 |

---

## 14. Human Review 確定事項

|  No | 論点 | 確定内容 | 判断者 | 備考 |
| --: | ---- | -------- | ------ | ---- |
| 1 | Response 構成 | `baseValueRules[]` + `conceptFeatureRules[]` の 2 グループ | Human Review | 3 配列案・単一 `rules[]` 案は不採用 |
| 2 | 値域 | `featureBaseValue` / `featureDelta` は 0.0〜1.0 | Human Review | `featureDelta` の方向は `polarity` で表現 |
| 3 | inactive Rule | MVP は active Rule のみ返却 | Human Review | `isActive` は Public 応答に含めない |
| 4 | Pair Rule 公開方針 | Reco 内部完結。Public 化しない | Human Review | 現行非公開方針を維持 |

---

## 15. 関連資料

| 種別 | パス | 用途 |
| ---- | ---- | ---- |
| API一覧 | `docs/05_アプリケーション設計/アプリ/api/API一覧.md` | API-PUB-008 |
| Featureルール定義書 | `docs/04_ドメインモデル設計/Featureルール定義書.md` | Rule 物理項目 |
| テーブル一覧 | `docs/05_アプリケーション設計/アプリ/database/テーブル一覧.md` | feature_rule 分解 |
| テーブル定義 | `docs/06_実装設計/database/concept_feature_rule_テーブル定義書.md` | conceptFeatureRules DB 正本・§17.1 決定事項 |
| enum定義書 | `docs/06_実装設計/database/enum定義書.md` | §6.22 polarity |
| 関連契約 | `docs/06_実装設計/api/API-PUB-007_Semantic設定取得API契約仕様書.md` | Version / conceptCode 整合 |

---

## 16. レビュー観点

- Pair Rule が Public 応答に含まれていないこと
- `baseValueRules` / `conceptFeatureRules` の表面フィールドが Featureルール定義書 §17 と整合していること
- API-PUB-005/006/007 とのコード体系整合が明記されていること
- 実装詳細を含まず契約面に限定していること

---

## 17. 備考

- メトリクス: `masters_feature_rules_request_count` / `masters_feature_rules_error_count`
- Pair Rule は Reco（MOD-RECO-005 等）内部で Relationship + Occasion 選択後に適用する（Public 化しない）
