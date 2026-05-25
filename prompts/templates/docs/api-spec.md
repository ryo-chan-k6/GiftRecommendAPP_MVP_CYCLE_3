# {{api.name}} API仕様書

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

## 10. 処理概要

### 10.1 処理フロー

```mermaid
flowchart TD
{{process.flow}}
```

### 10.2 処理詳細

{{#each process.steps}}

- {{this}}
  {{/each}}

{{#unless process.steps}}

- なし
  {{/unless}}

---

## 11. データ項目マッピング

### 11.1 Request Mapping

| Request項目 | 内部項目 / DTO | 変換内容 | 備考 |
| ----------- | -------------- | -------- | ---- |

{{#each mapping.request}}
| `{{request_field}}` | `{{internal_field}}` | {{transform}} | {{note}} |
{{/each}}

{{#unless mapping.request}}
| - | - | なし | - |
{{/unless}}

### 11.2 Response Mapping

| 内部項目 / DTO | Response項目 | 変換内容 | 備考 |
| -------------- | ------------ | -------- | ---- |

{{#each mapping.response}}
| `{{internal_field}}` | `{{response_field}}` | {{transform}} | {{note}} |
{{/each}}

{{#unless mapping.response}}
| - | - | なし | - |
{{/unless}}

---

## 12. provider / consumer 影響

### 12.1 provider

| 項目     | 内容                                  |
| -------- | ------------------------------------- |
| provider | `{{provider.name}}`                   |
| 責務     | {{provider.responsibility}}           |
| 影響有無 | `{{provider.affected}}`               |
| 必要対応 | {{provider.required_changes_summary}} |

{{#each provider.required_changes}}

- {{this}}
  {{/each}}

{{#unless provider.required_changes}}

- なし
  {{/unless}}

### 12.2 consumer

| 項目     | 内容                                  |
| -------- | ------------------------------------- |
| consumer | `{{consumer.name}}`                   |
| 責務     | {{consumer.responsibility}}           |
| 影響有無 | `{{consumer.affected}}`               |
| 必要対応 | {{consumer.required_changes_summary}} |

{{#each consumer.required_changes}}

- {{this}}
  {{/each}}

{{#unless consumer.required_changes}}

- なし
  {{/unless}}

---

## 13. ログ・監視

| 種別           | 内容                   | 出力タイミング                | 備考                        |
| -------------- | ---------------------- | ----------------------------- | --------------------------- |
| API access log | {{logging.access_log}} | {{logging.access_log_timing}} | {{logging.access_log_note}} |
| error log      | {{logging.error_log}}  | {{logging.error_log_timing}}  | {{logging.error_log_note}}  |
| audit log      | {{logging.audit_log}}  | {{logging.audit_log_timing}}  | {{logging.audit_log_note}}  |
| metric         | {{logging.metric}}     | {{logging.metric_timing}}     | {{logging.metric_note}}     |

---

## 14. テスト観点

|  No | 観点                | 確認内容                          | 種別                   |
| --: | ------------------- | --------------------------------- | ---------------------- |
|   1 | 正常系              | {{test_points.normal}}            | contract / integration |
|   2 | validation error    | {{test_points.validation_error}}  | contract               |
|   3 | auth error          | {{test_points.auth_error}}        | contract               |
|   4 | permission error    | {{test_points.permission_error}}  | contract               |
|   5 | permission error    | {{test_points.permission_error}}  | contract               |
|   6 | unexpected error    | {{test_points.unexpected_error}}  | integration            |
|   7 | generated client    | {{test_points.generated_client}}  | typecheck              |
|   8 | provider / consumer | {{test_points.provider_consumer}} | manual                 |

---

## 15. 変更管理

### 15.1 変更履歴

| 日付 | 変更内容 | 関連Issue / PR |
| ---- | -------- | -------------- |

{{#each change_history}}
| {{date}} | {{description}} | {{reference}} |
{{/each}}

{{#unless change_history}}
| - | 初版 | - |
{{/unless}}

### 15.2 変更理由

{{change_management.reason}}

### 15.3 互換性メモ

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

### 15.4 rollout order

{{#each compatibility.rollout_order}}

- {{this}}
  {{/each}}

{{#unless compatibility.rollout_order}}

- なし
  {{/unless}}

---

## 16. 未決事項

|  No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |

{{#each open_questions}}
| {{@index}} | {{topic}} | {{reason}} | {{owner}} | {{due_date}} | {{note}} |
{{/each}}

{{#unless open_questions}}
| - | なし | - | - | - | - |
{{/unless}}

---

## 17. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |

{{#each references}}
| {{type}} | `{{path}}` | {{purpose}} |
{{/each}}

{{#unless references}}
| - | - | なし |
{{/unless}}

---

## 18. レビュー観点

{{#each review_points}}

- {{this}}
  {{/each}}

{{#unless review_points}}

- API仕様がAPI設計方針と整合している
- Request / Response / Error Response が明確である
- provider / consumer の影響が整理されている
- OpenAPI定義への反映要否が明確である
- 破壊的変更有無と後方互換性が明記されている
- secretや`.env`実値が含まれていない
  {{/unless}}

---

## 19. 備考

{{#each notes}}

- {{this}}
  {{/each}}

{{#unless notes}}

- なし
  {{/unless}}
