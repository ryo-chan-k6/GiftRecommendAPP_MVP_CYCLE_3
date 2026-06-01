# {{api.name}} API実装仕様書

> このテンプレートは **Implementation Task** の成果物（API実装面）用である。
> 前提として、API契約は `api-contract-spec.md`（人間可読契約）および `openapi-spec.md` / `packages/contracts/openapi/*.yaml`（OpenAPI正本）で**確定済み（Contract Gate通過済み）**であること。
> 役割分担:
> - `api-contract-spec.md`: 確定済みのAPI契約（I/F）。本書の前提。
> - `openapi-spec.md`: OpenAPI定義（Orval生成入力）。
> - `api-implementation-spec.md`（本書）: 確定契約・generated client を前提とした内部実装仕様。

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

## 2. 前提契約

| 項目 | 内容 |
| ---- | ---- |
| 対象API ID | `{{api.id}}` |
| API名 | {{api.name}} |
| Method / Endpoint | `{{api.method}}` `{{api.endpoint}}` |
| API契約仕様書 | `{{contract.api_contract_spec_path}}` |
| OpenAPI定義 | `{{openapi.path}}`（正本: `packages/contracts/openapi/*.yaml`） |
| Contract Gate | `{{contract.gate_status}}`（契約確定の確認） |

> 契約面（Request / Response / Error / Validation の定義）は本書に再掲せず、`api-contract-spec.md` を正とする。

---

## 3. 実装方針

{{implementation.policy}}

---

## 4. 処理概要

### 4.1 処理フロー

```mermaid
flowchart TD
{{process.flow}}
```

### 4.2 処理詳細

{{#each process.steps}}

- {{this}}
  {{/each}}

{{#unless process.steps}}

- なし
  {{/unless}}

---

## 5. データ項目マッピング

### 5.1 Request Mapping

| Request項目 | 内部項目 / DTO | 変換内容 | 備考 |
| ----------- | -------------- | -------- | ---- |

{{#each mapping.request}}
| `{{request_field}}` | `{{internal_field}}` | {{transform}} | {{note}} |
{{/each}}

{{#unless mapping.request}}
| - | - | なし | - |
{{/unless}}

### 5.2 Response Mapping

| 内部項目 / DTO | Response項目 | 変換内容 | 備考 |
| -------------- | ------------ | -------- | ---- |

{{#each mapping.response}}
| `{{internal_field}}` | `{{response_field}}` | {{transform}} | {{note}} |
{{/each}}

{{#unless mapping.response}}
| - | - | なし | - |
{{/unless}}

---

## 6. generated client 利用方針

| 項目 | 内容 |
| ---- | ---- |
| generated出力先 | `{{generated.output_path}}` |
| client wrapper | `{{generated.wrapper_path}}`（手書きwrapperの配置） |
| 再生成コマンド | `{{generated.regenerate_command}}` |
| 検証コマンド | `{{generated.verify_command}}` |

generatedファイルは手動編集しない。利用側は wrapper を介して generated client を呼ぶ。

---

## 7. provider / consumer 実装影響

### 7.1 provider

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

### 7.2 consumer

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

## 8. ログ・監視

| 種別           | 内容                   | 出力タイミング                | 備考                        |
| -------------- | ---------------------- | ----------------------------- | --------------------------- |
| API access log | {{logging.access_log}} | {{logging.access_log_timing}} | {{logging.access_log_note}} |
| error log      | {{logging.error_log}}  | {{logging.error_log_timing}}  | {{logging.error_log_note}}  |
| audit log      | {{logging.audit_log}}  | {{logging.audit_log_timing}}  | {{logging.audit_log_note}}  |
| metric         | {{logging.metric}}     | {{logging.metric_timing}}     | {{logging.metric_note}}     |

---

## 9. 実装テスト観点

|  No | 観点                | 確認内容                          | 種別        |
| --: | ------------------- | --------------------------------- | ----------- |
|   1 | 正常系（結合）      | {{test_points.normal}}            | integration |
|   2 | unexpected error    | {{test_points.unexpected_error}}  | integration |
|   3 | 外部依存失敗        | {{test_points.dependency_error}}  | integration |
|   4 | generated client    | {{test_points.generated_client}}  | typecheck   |
|   5 | provider / consumer | {{test_points.provider_consumer}} | manual      |

> 契約面の単体テスト観点（validation / auth / Request・Response schema）は `api-contract-spec.md` に記載する。

---

## 10. 変更履歴

| 日付 | 変更内容 | 関連Issue / PR |
| ---- | -------- | -------------- |

{{#each change_history}}
| {{date}} | {{description}} | {{reference}} |
{{/each}}

{{#unless change_history}}
| - | 初版 | - |
{{/unless}}

---

## 11. 未決事項

|  No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |

{{#each open_questions}}
| {{@index}} | {{topic}} | {{reason}} | {{owner}} | {{due_date}} | {{note}} |
{{/each}}

{{#unless open_questions}}
| - | なし | - | - | - | - |
{{/unless}}

---

## 12. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |

{{#each references}}
| {{type}} | `{{path}}` | {{purpose}} |
{{/each}}

{{#unless references}}
| - | - | なし |
{{/unless}}

---

## 13. レビュー観点

{{#each review_points}}

- {{this}}
  {{/each}}

{{#unless review_points}}

- 確定済みAPI契約（`api-contract-spec.md` / OpenAPI）と実装が整合している
- 処理フロー・内部DTOマッピングが明確である
- generated client を手動編集せず wrapper 経由で利用している
- provider / consumer の実装影響が整理されている
- ログ・監視・テスト観点（結合）が整理されている
- secretや`.env`実値が含まれていない
  {{/unless}}

---

## 14. 備考

{{#each notes}}

- {{this}}
  {{/each}}

{{#unless notes}}

- なし
  {{/unless}}
