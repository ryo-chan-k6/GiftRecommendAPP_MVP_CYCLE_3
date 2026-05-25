# {{enum_group.name}} enum定義書

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

{{enum_group.summary}}

---

## 3. 目的

{{enum_group.objective}}

---

## 4. 定義方針

| 観点 | 方針 |
| ---- | ---- |
| 対象範囲 | {{policy.scope}} |
| 正本 | {{policy.canonical_source}} |
| 命名 | {{policy.naming}} |
| 値の追加 | {{policy.addition}} |
| 値の変更 | {{policy.change}} |
| 値の削除 | {{policy.deletion}} |
| DB / API / code連携 | {{policy.integration}} |

---

## 5. enum一覧

| enum名 | 物理名 | 分類 | 利用箇所 | MVP対象 | 備考 |
| ------ | ------ | ---- | -------- | ------- | ---- |
{{#each enums}}
| {{logical_name}} | `{{physical_name}}` | {{category}} | {{usage}} | `{{mvp_scope}}` | {{note}} |
{{/each}}
{{#unless enums}}
| - | - | - | なし | - | - |
{{/unless}}

---

## 6. enum値定義

{{#each enum_definitions}}

### 6.{{@index}} {{logical_name}} (`{{physical_name}}`)

| 値 | 表示名 | 意味 | 利用条件 | 有効 / 無効 | 備考 |
| -- | ------ | ---- | -------- | ----------- | ---- |
{{#each values}}
| `{{value}}` | {{label}} | {{meaning}} | {{condition}} | `{{enabled}}` | {{note}} |
{{/each}}

{{/each}}

{{#unless enum_definitions}}

なし

{{/unless}}

---

## 7. DB利用箇所

| テーブル | カラム | enum名 | 制約 | 備考 |
| -------- | ------ | ------ | ---- | ---- |
{{#each db_usages}}
| `{{table}}` | `{{column}}` | `{{enum_name}}` | {{constraint}} | {{note}} |
{{/each}}
{{#unless db_usages}}
| - | - | なし | - | - |
{{/unless}}

---

## 8. API利用箇所

| API | Request / Response | 項目 | enum名 | 備考 |
| --- | ------------------ | ---- | ------ | ---- |
{{#each api_usages}}
| `{{api_id}}` | {{direction}} | `{{field}}` | `{{enum_name}}` | {{note}} |
{{/each}}
{{#unless api_usages}}
| - | - | - | なし | - |
{{/unless}}

---

## 9. code利用箇所

| app / package | ファイル / モジュール | enum名 | 用途 | 備考 |
| ------------- | --------------------- | ------ | ---- | ---- |
{{#each code_usages}}
| `{{app}}` | `{{path}}` | `{{enum_name}}` | {{purpose}} | {{note}} |
{{/each}}
{{#unless code_usages}}
| - | - | なし | - | - |
{{/unless}}

---

## 10. 互換性・変更管理

| 変更種別 | 方針 | Human Review |
| -------- | ---- | ------------ |
| 値追加 | {{change_policy.add_value}} | `{{change_policy.add_value_human_review}}` |
| 値名変更 | {{change_policy.rename_value}} | `{{change_policy.rename_value_human_review}}` |
| 値削除 | {{change_policy.delete_value}} | `{{change_policy.delete_value_human_review}}` |
| 意味変更 | {{change_policy.meaning_change}} | `{{change_policy.meaning_change_human_review}}` |

### 10.1 API contract影響

APIのRequest / Responseで利用するenumのみ記載する。

| 項目 | 内容 |
| ---- | ---- |
| OpenAPI影響 | `{{contract_impact.openapi}}` |
| Orval影響 | `{{contract_impact.orval}}` |
| generated影響 | `{{contract_impact.generated}}` |
| Contract Task要否 | `{{contract_impact.contract_task_required}}` |
| 補足 | {{contract_impact.note}} |

---

## 11. テスト観点

|  No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
{{#each test_points}}
| {{no}} | {{name}} | {{description}} | {{type}} |
{{/each}}
{{#unless test_points}}
| 1 | DB制約 | {{default_test_points.db_constraint}} | migration |
| 2 | API schema | {{default_test_points.api_schema}} | contract |
| 3 | Type定義 | {{default_test_points.type_definition}} | typecheck |
| 4 | 表示名 | {{default_test_points.label}} | manual |
{{/unless}}

---

## 12. 未決事項

|  No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
{{#each open_questions}}
| {{@index}} | {{topic}} | {{reason}} | {{owner}} | {{due_date}} | {{note}} |
{{/each}}
{{#unless open_questions}}
| - | なし | - | - | - | - |
{{/unless}}

---

## 13. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
{{#each references}}
| {{type}} | `{{path}}` | {{purpose}} |
{{/each}}
{{#unless references}}
| - | - | なし |
{{/unless}}

---

## 14. レビュー観点

{{#each review_points}}

- {{this}}
  {{/each}}

{{#unless review_points}}

- DB / API / codeで同じenum値の意味が揺れていない
- 値追加、値削除、意味変更時の互換性影響が整理されている
- API利用箇所とAPI contract影響が明記されている
- 正本docsにない略称や独自値を導入していない
- secretや`.env`実値が含まれていない
  {{/unless}}
