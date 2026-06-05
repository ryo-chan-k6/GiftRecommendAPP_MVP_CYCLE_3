# Relationshipマスタ取得 API契約仕様書

> 本書は **API-PUB-005** の契約面（Public I/F）正本である。
> 処理フロー・MOD-API-011 / MOD-API-012 責務・内部 DTO マッピング・結合テスト観点は `API-PUB-005_Relationshipマスタ取得API実装仕様書.md`（別 Task）で定義する。
> OpenAPI 正本は `packages/contracts/openapi/public-api.yaml`（別 Contract Task）。

## 1. ドキュメント情報

| 項目           | 内容                                      |
| -------------- | ----------------------------------------- |
| ドキュメントID | `API-PUB-005-CONTRACT`                    |
| ドキュメント名 | Relationshipマスタ取得 API契約仕様書      |
| 対象システム   | Gift Recommendation Service MVP（Public） |
| MVP対象        | `○`                                       |
| 作成日         | 2026-06-05                                |
| 更新日         | 2026-06-05（Human Review #409 反映）       |

---

## 2. 概要

web（`apps/web`）から api（`apps/api`）へ、レコメンド条件入力画面（SCR-002）向けに **Relationship Master** の選択肢一覧を取得する Public API である。関連リソースは **Relationship Master / Relationship Rule** であり、Response では **relationship 選択肢一覧**（コード・表示名・並び順）を返す（[API一覧](../../05_アプリケーション設計/アプリ/api/API一覧.md) §API-PUB-005）。

Relationship × Occasion の **Pair 情報**（`pair_master` 等）は Public API 応答に含めない（API一覧 §API-PUB-005 備考）。Pair 利用は Reco 内部処理または Internal API 側で扱う。

---

## 3. 目的

- レコメンド条件入力画面が利用する Request / Response / Error を確定する。
- 後続の OpenAPI Contract Task（`public-api.yaml`）および Contract Gate の入力とする。
- API-PUB-002 の `relationship.relationshipCode` / `relationshipLabel` と整合したコード体系を提供する。
- API設計方針書・API一覧・エラーコード定義書・論理 ER（`relationship_master`）と整合した契約面を提供する。

---

## 4. API基本情報

| 項目     | 内容                                              |
| -------- | ------------------------------------------------- |
| API ID   | `API-PUB-005`                                     |
| API名    | Relationshipマスタ取得                            |
| API種別  | `Public API`                                      |
| Method   | `GET`                                             |
| Endpoint | `/api/v1/masters/relationships`                   |
| Base URL | 環境ごとに環境変数で定義（本書ではパスを正とする） |
| Version  | `v1`（URL パスに含む）                            |
| Provider | `apps/api`                                        |
| Consumer | `apps/web`（レコメンド条件入力画面 SCR-002）      |
| 認証要否 | `false`（MVP は非認証。後続で Authorization 追加可） |
| 権限条件 | MVP ではなし（公開参照のみ）                      |
| 冪等性   | `冪等`（同一 Request の繰り返しで副作用なし）     |
| MVP対象  | `○`                                               |

---

## 5. 利用シーン

### 5.1 利用タイミング

- レコメンド条件入力画面（SCR-002）の初期表示時
- 他マスタ API（API-PUB-006〜008）と **並列 GET** するタイミング（API一覧 §関連画面）

### 5.2 呼び出し元

- `apps/web`（レコメンド条件入力画面）

### 5.3 主なユースケース

- Relationship 選択肢（プルダウン等）を表示する。
- 取得した `relationshipCode` を API-PUB-002 Request の `relationship.relationshipCode` に利用する。
- 有効（`is_active=true`）なマスタのみを返却する（論理 ER §11.1。`is_active` 自体は Response に含めない）。
- 有効レコードが 0 件の場合は HTTP **200** かつ空配列を返す（API一覧 §エラー方針）。

### 5.4 API-PUB-002 との関係（契約上の前提のみ）

| 項目 | 内容 |
| ---- | ---- |
| 関連 Public API | `API-PUB-002`（レコメンド実行） |
| 連携キー | `relationshipCode` / `relationshipLabel` |
| 整合 | API-PUB-002 Request の `relationship` は本 API のコード体系に整合すること |

---

## 6. Request仕様

### 6.1 Request Header

| Header         | 必須    | 内容               | 例                                   |
| -------------- | ------- | ------------------ | ------------------------------------ |
| `Accept`       | `false` | `application/json` | `application/json`                   |
| `X-Trace-Id`   | `false` | 横断追跡 ID        | `550e8400-e29b-41d4-a716-446655440000` |
| `X-Request-Id` | `false` | API リクエスト ID  | `req_01HZYX`                         |

MVP では `Authorization` は使用しない。`Content-Type` は Request Body がないため不要。

### 6.2 Path Parameters

| 項目 | 型 | 必須 | 内容 | 例 |
| ---- | -- | ---- | ---- | -- |
| -    | -  | -    | なし | -  |

### 6.3 Query Parameters

| 項目 | 型 | 必須 | 内容 | 制約 | 例 |
| ---- | -- | ---- | ---- | ---- | -- |
| -    | -  | -    | なし | -    | -  |

MVP では Query パラメータは定義しない。locale / version 等の多言語対応用 Query も**想定しない**（Human Review #409 確定）。

### 6.4 Request Body

なし（GET では Request Body を使用しない。API設計方針書 §6）。

### 6.5 Request Example

Request Body なし。例:

```http
GET /api/v1/masters/relationships HTTP/1.1
Host: api.example.com
Accept: application/json
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
| 200 | 処理成功 | マスタ参照に成功し、選択肢一覧（0 件含む）を返却できる場合 |
| 500 | 内部エラー | DB 参照失敗（`GRS-DB-002` 等）または設定解決不能（`GRS-CFG-005` 等） |
| 503 | 一時利用不可 | api / DB が一時的に応答不能（`GRS-COM-003`） |
| 504 | タイムアウト | 内部処理タイムアウト（`GRS-COM-002`） |

**契約上の正常系:** HTTP **200**。有効レコード 0 件も正常系（空配列。API一覧 §エラー方針）。

### 7.3 Response Body

成功時は API設計方針書 §8.2 の **`data` + `meta`** 構造を基本とする。主データは **Relationship 選択肢一覧** とする。

#### 7.3.1 `data`

| 項目 | 型 | 必須 | 内容 | 備考 |
| ---- | -- | ---- | ---- | ---- |
| `relationships` | `array` | `true` | Relationship 選択肢の配列 | 0 件可。`displayOrder` 昇順（同順位は `relationshipCode` 昇順）で並べる |

#### 7.3.2 `data.relationships[]` 要素

論理 ER（`relationship_master`）および API-PUB-002 `RelationshipInput` に整合。外部 I/F は **camelCase**。

| 項目 | 型 | 必須 | 内容 | 制約 | 例 |
| ---- | -- | ---- | ---- | ---- | ---- |
| `relationshipCode` | `string` | `true` | 関係性コード | 非空。`relationship_master.relationship_code` に対応 | `boss` |
| `relationshipLabel` | `string` | `true` | 表示名 | 非空。最大 **50** 文字（API-PUB-002 と同上限）。DB 正本列は `relationship_master.relationship_label`（日本語 UI 表示用） | `上司` |
| `displayOrder` | `integer` | `false` | 表示順 | 0 以上。未指定時は api 側で `relationshipCode` 辞書順等にフォールバック可（実装仕様書で確定） | `10` |

**Response に含めない項目（MVP 契約面）:**

| 項目 | 理由 |
| ---- | ---- |
| `relationshipLabelJp` 等の DB 物理名そのもの | 表示は `relationshipLabel` に集約（`relationship_label` からマップ。§14.1 No.1） |
| `isActive` | サーバ側で `is_active=true` のみ返却。クライアントへ状態を露出しない |
| Pair / Rule 詳細 | Public API 非公開（API一覧 備考） |
| `relationshipRule` / Feature 補正値 | Reco / Internal 側の責務 |

#### 7.3.3 `meta`

| 項目 | 型 | 必須 | 内容 | 備考 |
| ---- | -- | ---- | ---- | ---- |
| `traceId` | `string` | `false` | 横断追跡 ID | Header を引き継ぎまたは生成 |
| `requestId` | `string` | `false` | API リクエスト ID | 未指定時は api 側で生成可 |
| `generatedAt` | `string` | `false` | 生成日時（ISO 8601） | - |
| `count` | `integer` | `false` | 返却件数 | `relationships.length` と一致 |

### 7.4 Response Example

#### 7.4.1 正常系（200・複数件）

```json
{
  "data": {
    "relationships": [
      {
        "relationshipCode": "boss",
        "relationshipLabel": "上司",
        "displayOrder": 10
      },
      {
        "relationshipCode": "colleague",
        "relationshipLabel": "同僚",
        "displayOrder": 20
      }
    ]
  },
  "meta": {
    "traceId": "550e8400-e29b-41d4-a716-446655440000",
    "requestId": "req_01HZYX",
    "generatedAt": "2026-06-05T09:00:00+09:00",
    "count": 2
  }
}
```

#### 7.4.2 正常系（200・0 件）

```json
{
  "data": {
    "relationships": []
  },
  "meta": {
    "generatedAt": "2026-06-05T09:00:00+09:00",
    "count": 0
  }
}
```

---

## 8. Error Response仕様

### 8.1 Error Response形式

エラー時は API設計方針書 §8.3 に準拠する。

```json
{
  "error": {
    "code": "GRS-DB-002",
    "message": "データ取得に失敗しました。",
    "details": []
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
| 500 | `GRS-DB-002` | `relationship_master` 参照失敗 | DB 読取失敗 | データ取得に失敗しました。 |
| 500 | `GRS-CFG-005` | マスタ設定が解決不能（seed 未投入等で参照不能） | マスタ不足 | 選択項目の取得に失敗しました。 |
| 500 | `GRS-CFG-999` | 設定系想定外エラー | 設定処理失敗 | 設定情報の処理に失敗しました。 |
| 500 | `GRS-COM-999` | 想定外内部エラー | 内部エラー | 予期しないエラーが発生しました。時間を置いて再度お試しください。 |
| 503 | `GRS-COM-003` | 一時的利用不可 | サービス一時停止 | 現在サービスを利用できません。時間を置いて再度お試しください。 |
| 504 | `GRS-COM-002` | タイムアウト | タイムアウト | 処理に時間がかかっています。時間を置いて再度お試しください。 |

**空配列とエラーの境界:** 有効レコード 0 件は **200 + 空配列**（API一覧）。参照処理不能（設定不備等）は **500 + `GRS-CFG-005`**（Human Review #409 確定。§14.1 No.3）。

本 API では Request Body を持たないため、`GRS-REQ-*` は原則発生しない。

---

## 9. バリデーション仕様

| 対象項目 | ルール | エラーコード | エラーメッセージ |
| -------- | ------ | ------------ | ---------------- |
| HTTP Method | `GET` のみ許可 | - | ルーティング層で拒否（405 等は実装仕様書で定義） |
| Request Body | 送信しない | - | GET では Body なし |
| Path / Query | 本 API ではパラメータなし | - | 未知 Query は無視（locale 等の Query は定義しない。§14.1 No.2） |

---

## 10. OpenAPI / generated 反映方針

| 項目 | 内容 |
| ---- | ---- |
| OpenAPI正本 | `packages/contracts/openapi/public-api.yaml` |
| 操作 ID（案） | `getMastersRelationships` または `listRelationships`（OpenAPI Task で確定） |
| Path | `/api/v1/masters/relationships` |
| components schema | `RelationshipMasterItem` / `RelationshipMastersResponse` 等（OpenAPI Task で命名確定） |
| 既存 schema 連携 | `RelationshipInput`（API-PUB-002）の `relationshipCode` / `relationshipLabel` と整合 |
| Orval設定 | リポジトリ正本 `orval.config.ts` |
| generated出力先（web） | `apps/web/src/generated/api/` |
| OpenAPI定義書 | `openapi-spec.md` テンプレ準拠の Contract Task 成果物 |

本 Task では YAML / generated の**実変更は行わない**。本契約仕様書を 1b OpenAPI Contract Task の入力正本とする。

---

## 11. 互換性・破壊的変更

| 項目       | 内容 |
| ---------- | ---- |
| 破壊的変更 | MVP 初版のためなし |
| 後方互換性 | `v1` パス固定。フィールド追加は optional で許容 |
| 判断理由   | 初回 Public Masters 契約確定 |

### 11.1 rollout order

- 本契約確定 → `public-api.yaml` 更新 → Orval 再生成 → web api-client 更新 → api 実装

---

## 12. 契約面テスト観点

| No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
| 1 | 正常系 | GET で 200、`data.relationships` が配列 | contract |
| 2 | 0 件 | 有効レコード 0 件で 200 + 空配列 | contract |
| 3 | 並び順 | `displayOrder` 昇順（同順位 tie-break） | contract |
| 4 | 必須フィールド | 各要素に `relationshipCode` / `relationshipLabel` | contract |
| 5 | Pair 非露出 | Response に Pair / Rule 詳細が含まれない | contract |
| 6 | API-PUB-002 整合 | 返却 `relationshipCode` が PUB-002 Validation で受理可能 | contract |
| 7 | エラー系 | 500 + `GRS-DB-002` 形式 | contract |
| 8 | generated client | OpenAPI 生成後、型が Response と一致 | typecheck |

実装結合・DB 障害シミュレーションは実装仕様書・単体テスト Task で扱う。

---

## 13. 変更履歴

| 日付 | 変更内容 | 関連Issue / PR |
| ---- | -------- | -------------- |
| 2026-06-05 | 初版（契約面のみ。Phase1 Wave2 C2 batch3） | Issue #401 |
| 2026-06-05 | Human Review #409 反映（`relationshipLabel` 正本列 / Query 非対応 / 空配列 vs `GRS-CFG-005` 境界） | #409 |

---

## 14. 未決事項

現時点の未決事項はなし（Human Review #409 で §14.1 の論点を確定済み）。

### 14.1 Human Review 反映済み判断（PR #409）

| No | 論点 | 確定内容 | 備考 |
| --: | ---- | -------- | ---- |
| 1 | `relationshipLabel` の正本列 | UI 表示用 `relationship_master.relationship_label`（日本語）を `relationshipLabel` にマップ | §7.3.2。`relationship_label_jp` は Response に露出しない |
| 2 | Query パラメータ（locale 等） | MVP では Query なし。**多言語対応は想定不要** | §6.3・§9 |
| 3 | `GRS-CFG-005` と空配列の境界 | 有効レコード 0 件は **200 + 空配列**。参照処理不能は **500 + `GRS-CFG-005`** | §7.2・§8.2 |

---

## 15. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
| API一覧 | `docs/05_アプリケーション設計/アプリ/api/API一覧.md` | API-PUB-005 行 |
| API設計方針書 | `docs/05_アプリケーション設計/アプリ/api/API設計方針書.md` | Request/Response/Error 形式 |
| エラーコード定義書 | `docs/05_アプリケーション設計/アプリ/エラーコード定義書.md` | GRS-CFG-* / GRS-DB-* |
| 論理 ER | `docs/05_アプリケーション設計/アプリ/database/論理ER.md` | `relationship_master` |
| API-PUB-002 契約 | `docs/06_実装設計/api/API-PUB-002_レコメンド実行API契約仕様書.md` | `relationship` 連携 |
| 認証・認可方針書 | `docs/05_アプリケーション設計/基盤/認証・認可方針書.md` | 公開参照 |
| Task Definition | `prompts/definitions/tasks/api-pub-005-relationship-masters/api-contract-spec.yaml` | Epic #387 配下 scope |

---

## 16. レビュー観点

- API 契約（Request / Response / Error）が明確で確定可能である
- API一覧 §API-PUB-005 と endpoint / Method / MVP / Pair 非露出が整合している
- API-PUB-002 の `relationshipCode` 体系と整合している
- OpenAPI 反映方針が明確である
- 実装詳細（MOD-API-011/012 フロー）を含めず契約面に限定している
- secret や `.env` 実値が含まれていない

### 16.1 Human Review で確認してほしいこと

- 正式 Endpoint（`GET /api/v1/masters/relationships`）と MVP 非認証方針の最終確認
- OpenAPI Contract Task への分離方針の確認
- §14.1 の Human Review 反映内容が意図どおりか（再レビュー時）

---

## 17. 備考

- 入力画面初期表示では API-PUB-006〜008 と並列取得する（API一覧 §関連画面）。
- metric: `masters_relationships_request_count` / `masters_relationships_error_count`（API一覧）。
