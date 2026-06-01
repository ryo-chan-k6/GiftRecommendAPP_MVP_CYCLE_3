# {{api.name}} API契約仕様書

> このテンプレートは **Contract Task** の成果物（API契約面）用である。
> 実装面（処理フロー・内部DTOマッピング・provider/consumer実装影響・ログ・テスト観点）は `api-implementation-spec.md` を、OpenAPI定義そのものは `openapi-spec.md` を使用する。
> 役割分担:
> - `api-contract-spec.md`（本書）: 人間可読の**API契約**（I/Fの確定面）。Contract Task で確定し、Implementation Task の前提（Contract Gate）となる。
> - `openapi-spec.md`: 機械可読の **OpenAPI定義**（Orval生成入力）。正本は `packages/contracts/openapi/*.yaml`。
> - `api-implementation-spec.md`: 確定済み契約・generated を前提とした**実装仕様**。

## 1. ドキュメント情報

| 項目           | 内容                     |
| -------------- | ------------------------ |
| ドキュメントID | `{{document.id}}`        |
| ドキュメント名 | {{document.title}}       |
| 対象システム   | {{document.system}}      |
| MVP対象        | `{{document.mvp_scope}}` |
| 作成日         | {{document.created_at}}  |
| 更新日         | {{document.updated_at}}  |

---

## 2. 概要

{{api.summary}}

---

## 3. 目的

{{api.objective}}

---

## 4. API基本情報

| 項目     | 内容                    |
| -------- | ----------------------- |
| API ID   | `{{api.id}}`            |
| API名    | {{api.name}}            |
| API種別  | `{{api.kind}}`          |
| Method   | `{{api.method}}`        |
| Endpoint | `{{api.endpoint}}`      |
| Base URL | `{{api.base_url}}`      |
| Version  | `{{api.version}}`       |
| Provider | `{{api.provider}}`      |
| Consumer | `{{api.consumer}}`      |
| 認証要否 | `{{api.auth.required}}` |
| 権限条件 | {{api.auth.permission}} |
| 冪等性   | `{{api.idempotency}}`   |
| MVP対象  | `{{api.mvp_scope}}`     |

---

## 5. 利用シーン

### 5.1 利用タイミング

{{api.usage_timing}}

### 5.2 呼び出し元

{{#each api.callers}}

- `{{this}}`
  {{/each}}

{{#unless api.callers}}

- なし
  {{/unless}}

### 5.3 主なユースケース

{{#each api.use_cases}}

- {{this}}
  {{/each}}

{{#unless api.use_cases}}

- なし
  {{/unless}}

---

## 6. Request仕様

### 6.1 Request Header

| Header | 必須 | 内容 | 例  |
| ------ | ---- | ---- | --- |

{{#each request.headers}}
| `{{name}}` | `{{required}}` | {{description}} | `{{example}}` |
{{/each}}

{{#unless request.headers}}
| - | - | なし | - |
{{/unless}}

### 6.2 Path Parameters

| 項目 | 型  | 必須 | 内容 | 例  |
| ---- | --- | ---- | ---- | --- |

{{#each request.path_params}}
| `{{name}}` | `{{type}}` | `{{required}}` | {{description}} | `{{example}}` |
{{/each}}

{{#unless request.path_params}}
| - | - | - | なし | - |
{{/unless}}

### 6.3 Query Parameters

| 項目 | 型  | 必須 | 内容 | 制約 | 例  |
| ---- | --- | ---- | ---- | ---- | --- |

{{#each request.query_params}}
| `{{name}}` | `{{type}}` | `{{required}}` | {{description}} | {{validation}} | `{{example}}` |
{{/each}}

{{#unless request.query_params}}
| - | - | - | なし | - | - |
{{/unless}}

### 6.4 Request Body

Request Bodyがない場合は `なし` と記載する。

| 項目 | 型  | 必須 | 内容 | 制約 | 例  |
| ---- | --- | ---- | ---- | ---- | --- |

{{#each request.body_fields}}
| `{{name}}` | `{{type}}` | `{{required}}` | {{description}} | {{validation}} | `{{example}}` |
{{/each}}

{{#unless request.body_fields}}
| - | - | - | なし | - | - |
{{/unless}}

### 6.5 Request Example

```json
{{request.example}}
```

---

## 7. Response仕様

### 7.1 Response Header

| Header | 内容 | 例  |
| ------ | ---- | --- |

{{#each response.headers}}
| `{{name}}` | {{description}} | `{{example}}` |
{{/each}}

{{#unless response.headers}}
| - | なし | - |
{{/unless}}

### 7.2 Status Code

| Status | 意味 | 利用条件 |
| -----: | ---- | -------- |

{{#each response.status_codes}}
| {{status}} | {{meaning}} | {{condition}} |
{{/each}}

{{#unless response.status_codes}}
| - | なし | - |
{{/unless}}

### 7.3 Response Body

| 項目 | 型  | 必須 | 内容 | 備考 |
| ---- | --- | ---- | ---- | ---- |

{{#each response.body_fields}}
| `{{name}}` | `{{type}}` | `{{required}}` | {{description}} | {{note}} |
{{/each}}

{{#unless response.body_fields}}
| - | - | - | なし | - |
{{/unless}}

### 7.4 Response Example

```json
{{response.example}}
```

---

## 8. Error Response仕様

### 8.1 Error Response形式

```json
{{error.common_example}}
```

### 8.2 Error一覧

| Status | Error Code | 発生条件 | Response概要 | ユーザー向け表示 |
| -----: | ---------- | -------- | ------------ | ---------------- |

{{#each error.items}}
| {{status}} | `{{code}}` | {{condition}} | {{response_summary}} | {{user_message}} |
{{/each}}

{{#unless error.items}}
| - | - | なし | - | - |
{{/unless}}

---

## 9. バリデーション仕様

| 対象項目 | ルール | エラーコード | エラーメッセージ |
| -------- | ------ | ------------ | ---------------- |

{{#each validations}}
| `{{field}}` | {{rule}} | `{{error_code}}` | {{message}} |
{{/each}}

{{#unless validations}}
| - | なし | - | - |
{{/unless}}

---

## 10. OpenAPI / generated 反映方針

| 項目 | 内容 |
| ---- | ---- |
| OpenAPI正本 | `{{openapi.path}}`（正本は `packages/contracts/openapi/*.yaml`） |
| components schema | `{{openapi.schema_name}}` |
| Orval設定 | `orval.config.ts` |
| generated出力先 | `{{generated.output_path}}`（web: `apps/web/src/generated/api/` / api: `apps/api/src/generated/reco-client/`） |
| OpenAPI定義書 | `openapi-spec.md`（機械可読定義） |

generatedファイルは手動編集しない。本契約が確定（Contract Gate通過）した後に Implementation Task を開始する。

---

## 11. 互換性・破壊的変更

| 項目       | 内容                                       |
| ---------- | ------------------------------------------ |
| 破壊的変更 | `{{compatibility.breaking_change}}`        |
| 後方互換性 | `{{compatibility.backward_compatibility}}` |
| 判断理由   | {{compatibility.reason}}                   |

{{#each compatibility.notes}}

- {{this}}
  {{/each}}

{{#unless compatibility.notes}}

- なし
  {{/unless}}

### 11.1 rollout order

{{#each compatibility.rollout_order}}

- {{this}}
  {{/each}}

{{#unless compatibility.rollout_order}}

- なし
  {{/unless}}

---

## 12. 契約面テスト観点

|  No | 観点             | 確認内容                         | 種別      |
| --: | ---------------- | -------------------------------- | --------- |
|   1 | 正常系           | {{test_points.normal}}           | contract  |
|   2 | validation error | {{test_points.validation_error}} | contract  |
|   3 | auth error       | {{test_points.auth_error}}       | contract  |
|   4 | permission error | {{test_points.permission_error}} | contract  |
|   5 | generated client | {{test_points.generated_client}} | typecheck |

> 実装結合・異常系の統合テスト観点は `api-implementation-spec.md` に記載する。

---

## 13. 変更履歴

| 日付 | 変更内容 | 関連Issue / PR |
| ---- | -------- | -------------- |

{{#each change_history}}
| {{date}} | {{description}} | {{reference}} |
{{/each}}

{{#unless change_history}}
| - | 初版 | - |
{{/unless}}

---

## 14. 未決事項

|  No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |

{{#each open_questions}}
| {{@index}} | {{topic}} | {{reason}} | {{owner}} | {{due_date}} | {{note}} |
{{/each}}

{{#unless open_questions}}
| - | なし | - | - | - | - |
{{/unless}}

---

## 15. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |

{{#each references}}
| {{type}} | `{{path}}` | {{purpose}} |
{{/each}}

{{#unless references}}
| - | - | なし |
{{/unless}}

---

## 16. レビュー観点

{{#each review_points}}

- {{this}}
  {{/each}}

{{#unless review_points}}

- API契約（Request / Response / Error / Validation）が明確で確定可能である
- API設計方針・API一覧と整合している
- OpenAPI（`packages/contracts/openapi/*.yaml`）への反映方針が明確である
- 破壊的変更有無と後方互換性が明記されている
- 実装詳細（内部DTO・処理フロー）を含めず契約面に限定している
- secretや`.env`実値が含まれていない
  {{/unless}}

---

## 17. 備考

{{#each notes}}

- {{this}}
  {{/each}}

{{#unless notes}}

- なし
  {{/unless}}
