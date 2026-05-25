# {{openapi.name}} OpenAPI定義書

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

{{openapi.summary}}

---

## 3. 目的

{{openapi.objective}}

---

## 4. OpenAPI基本情報

| 項目 | 内容 |
| ---- | ---- |
| API ID | `{{api.id}}` |
| API名 | {{api.name}} |
| API種別 | `{{api.kind}}` |
| Method | `{{api.method}}` |
| Endpoint | `{{api.endpoint}}` |
| operationId | `{{openapi.operation_id}}` |
| OpenAPI定義ファイル | `{{openapi.path}}` |
| components schema | `{{openapi.schema_name}}` |
| Provider | `{{api.provider}}` |
| Consumer | `{{api.consumer}}` |

---

## 5. 対応するAPI仕様

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
{{#each references.api_specs}}
| {{type}} | `{{path}}` | {{purpose}} |
{{/each}}
{{#unless references.api_specs}}
| - | - | なし |
{{/unless}}

---

## 6. Path定義

```yaml
{{openapi.path_definition}}
```

---

## 7. Request Schema

### 7.1 Parameters

| 種別 | 項目 | 型 | 必須 | 制約 | 備考 |
| ---- | ---- | -- | ---- | ---- | ---- |
{{#each request.parameters}}
| {{in}} | `{{name}}` | `{{type}}` | `{{required}}` | {{validation}} | {{note}} |
{{/each}}
{{#unless request.parameters}}
| - | - | - | - | なし | - |
{{/unless}}

### 7.2 Request Body Schema

```yaml
{{request.body_schema}}
```

---

## 8. Response Schema

### 8.1 Status Code

| Status | Schema | 意味 | 備考 |
| -----: | ------ | ---- | ---- |
{{#each response.status_codes}}
| {{status}} | `{{schema}}` | {{meaning}} | {{note}} |
{{/each}}
{{#unless response.status_codes}}
| - | - | なし | - |
{{/unless}}

### 8.2 Response Body Schema

```yaml
{{response.body_schema}}
```

---

## 9. Error Schema

```yaml
{{error.schema}}
```

| Status | Error Code | 発生条件 | 備考 |
| -----: | ---------- | -------- | ---- |
{{#each error.items}}
| {{status}} | `{{code}}` | {{condition}} | {{note}} |
{{/each}}
{{#unless error.items}}
| - | - | なし | - |
{{/unless}}

---

## 10. Schema一覧

| Schema | 種別 | 用途 | 備考 |
| ------ | ---- | ---- | ---- |
{{#each schemas}}
| `{{name}}` | {{type}} | {{purpose}} | {{note}} |
{{/each}}
{{#unless schemas}}
| - | - | なし | - |
{{/unless}}

---

## 11. API仕様書との差分確認

| 確認項目 | 判定 | 補足 |
| -------- | ---- | ---- |
| Method / Endpointが一致 | `{{spec_check.method_endpoint}}` | {{spec_check.method_endpoint_note}} |
| Request項目が一致 | `{{spec_check.request}}` | {{spec_check.request_note}} |
| Response項目が一致 | `{{spec_check.response}}` | {{spec_check.response_note}} |
| Error Responseが一致 | `{{spec_check.error}}` | {{spec_check.error_note}} |
| 認証・認可が一致 | `{{spec_check.auth}}` | {{spec_check.auth_note}} |

---

## 12. Orval / generated 方針

| 項目 | 内容 |
| ---- | ---- |
| Orval設定ファイル | `{{orval.config_path}}` |
| generated出力先 | `{{generated.output_path}}` |
| generated手動編集 | `{{generated.manual_edit_allowed}}` |
| 再生成コマンド | `{{generated.regenerate_command}}` |
| 検証コマンド | `{{generated.verify_command}}` |

generatedファイルは手動編集しない。OpenAPI変更後は、定義された再生成コマンドで生成する。

---

## 13. provider / consumer 影響

### 13.1 provider

| Provider | 影響有無 | 必要対応 | 備考 |
| -------- | -------- | -------- | ---- |
{{#each provider_consumer.providers}}
| `{{name}}` | `{{affected}}` | {{required_changes}} | {{note}} |
{{/each}}
{{#unless provider_consumer.providers}}
| - | - | なし | - |
{{/unless}}

### 13.2 consumer

| Consumer | 影響有無 | 必要対応 | 備考 |
| -------- | -------- | -------- | ---- |
{{#each provider_consumer.consumers}}
| `{{name}}` | `{{affected}}` | {{required_changes}} | {{note}} |
{{/each}}
{{#unless provider_consumer.consumers}}
| - | - | なし | - |
{{/unless}}

---

## 14. 互換性

| 項目 | 内容 |
| ---- | ---- |
| 破壊的変更 | `{{compatibility.breaking_change}}` |
| 後方互換性 | {{compatibility.backward_compatibility}} |
| rollout順 | {{compatibility.rollout_order}} |
| Human Review事項 | {{compatibility.human_review_points}} |

---

## 15. テスト・検証

|  No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
{{#each test_points}}
| {{no}} | {{name}} | {{description}} | {{type}} |
{{/each}}
{{#unless test_points}}
| 1 | OpenAPI lint | {{default_test_points.openapi_lint}} | contract |
| 2 | Orval生成 | {{default_test_points.orval}} | generated |
| 3 | typecheck | {{default_test_points.typecheck}} | typecheck |
| 4 | provider / consumer | {{default_test_points.provider_consumer}} | integration |
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
{{#each references.items}}
| {{type}} | `{{path}}` | {{purpose}} |
{{/each}}
{{#unless references.items}}
| - | - | なし |
{{/unless}}

---

## 18. レビュー観点

{{#each review_points}}

- {{this}}
  {{/each}}

{{#unless review_points}}

- API仕様書、OpenAPI、Orval、generated、provider、consumerが整合している
- 破壊的変更有無と後方互換性が明記されている
- generatedファイルの手動編集を前提にしていない
- Contract Taskとして分離すべき影響が明示されている
- secretや`.env`実値が含まれていない
  {{/unless}}
