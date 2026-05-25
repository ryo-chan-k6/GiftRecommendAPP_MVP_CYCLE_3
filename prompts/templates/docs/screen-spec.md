# {{screen.name}} 画面仕様書

## 1. ドキュメント情報

| 項目      | 内容                    |
| --------- | ----------------------- |
| 画面ID    | `{{screen.id}}`         |
| 画面名    | {{screen.name}}         |
| 画面種別  | `{{screen.type}}`       |
| MVP対象   | `{{screen.mvp_scope}}`  |
| 作成日    | {{document.created_at}} |
| 更新日    | {{document.updated_at}} |

---

## 2. 概要

{{screen.summary}}

---

## 3. 目的

{{screen.objective}}

---

## 4. 対象ユーザー

| ユーザー種別 | 内容                       |
| ------------ | -------------------------- |
| 主利用者     | {{screen.users.primary}}   |
| 補助利用者   | {{screen.users.secondary}} |
| 管理者       | {{screen.users.admin}}     |

---

## 5. 画面表示条件

| 項目            | 内容                         |
| --------------- | ---------------------------- |
| 表示URL / Route | `{{screen.route}}`           |
| 遷移元          | {{screen.navigation.from}}   |
| 遷移先          | {{screen.navigation.to}}     |
| 認証要否        | `{{screen.auth.required}}`   |
| 権限条件        | {{screen.auth.permission}}   |
| 初期表示条件    | {{screen.initial_condition}} |

---

## 6. 画面遷移

```mermaid
flowchart TD
  A[{{screen.navigation.from}}] --> B[{{screen.name}}]
  B --> C[{{screen.navigation.to}}]
```

### 6.1 遷移一覧

|  No | 操作                  | 遷移先                     | 条件                     | 備考                |
| --: | --------------------- | -------------------------- | ------------------------ | ------------------- |
|   1 | {{navigation.action}} | {{navigation.destination}} | {{navigation.condition}} | {{navigation.note}} |

---

## 7. 画面レイアウト

### 7.1 レイアウト概要

{{layout.summary}}

### 7.2 ワイヤーフレーム簡易図

```text
{{layout.wireframe}}
```

### 7.3 画面領域

| 領域   | 内容              | 表示条件                    |
| ------ | ----------------- | --------------------------- |
| Header | {{layout.header}} | {{layout.header_condition}} |
| Main   | {{layout.main}}   | {{layout.main_condition}}   |
| Footer | {{layout.footer}} | {{layout.footer_condition}} |

---

## 8. 表示項目

|  No | 項目名                 | 物理名 / key            | 型                       | 表示形式                 | 必須                         | 表示条件                    | 備考                   |
| --: | ---------------------- | ----------------------- | ------------------------ | ------------------------ | ---------------------------- | --------------------------- | ---------------------- |
|   1 | {{display_items.name}} | `{{display_items.key}}` | `{{display_items.type}}` | {{display_items.format}} | `{{display_items.required}}` | {{display_items.condition}} | {{display_items.note}} |

---

## 9. 入力項目

入力項目がない場合は `なし` と記載する。

|  No | 項目名               | 物理名 / key          | 型                     | 入力形式                | 必須                       | 初期値                  | 入力制約                   | 備考                 |
| --: | -------------------- | --------------------- | ---------------------- | ----------------------- | -------------------------- | ----------------------- | -------------------------- | -------------------- |
|   1 | {{input_items.name}} | `{{input_items.key}}` | `{{input_items.type}}` | {{input_items.control}} | `{{input_items.required}}` | {{input_items.default}} | {{input_items.validation}} | {{input_items.note}} |

---

## 10. 操作仕様

|  No | 操作             | トリガー            | 処理内容            | 成功時                 | 失敗時               | 備考             |
| --: | ---------------- | ------------------- | ------------------- | ---------------------- | -------------------- | ---------------- |
|   1 | {{actions.name}} | {{actions.trigger}} | {{actions.process}} | {{actions.on_success}} | {{actions.on_error}} | {{actions.note}} |

---

## 11. 状態別表示仕様

### 11.1 初期表示

{{states.initial}}

### 11.2 Loading状態

{{states.loading}}

### 11.3 Empty状態

{{states.empty}}

### 11.4 Error状態

{{states.error}}

### 11.5 Success状態

{{states.success}}

---

## 12. バリデーション仕様

入力項目がない場合は `なし` と記載する。

|  No | 対象項目               | バリデーション内容   | エラーメッセージ        | 表示タイミング         |
| --: | ---------------------- | -------------------- | ----------------------- | ---------------------- |
|   1 | {{validations.target}} | {{validations.rule}} | {{validations.message}} | {{validations.timing}} |

---

## 13. エラー表示仕様

| エラー種別    | 発生条件                        | 表示内容                      | ユーザー操作                 | 備考                       |
| ------------- | ------------------------------- | ----------------------------- | ---------------------------- | -------------------------- |
| API通信エラー | {{errors.api.condition}}        | {{errors.api.message}}        | {{errors.api.action}}        | {{errors.api.note}}        |
| 認証エラー    | {{errors.auth.condition}}       | {{errors.auth.message}}       | {{errors.auth.action}}       | {{errors.auth.note}}       |
| 権限エラー    | {{errors.permission.condition}} | {{errors.permission.message}} | {{errors.permission.action}} | {{errors.permission.note}} |
| 入力エラー    | {{errors.validation.condition}} | {{errors.validation.message}} | {{errors.validation.action}} | {{errors.validation.note}} |
| 想定外エラー  | {{errors.unexpected.condition}} | {{errors.unexpected.message}} | {{errors.unexpected.action}} | {{errors.unexpected.note}} |

---

## 14. API連携仕様

### 14.1 利用API一覧

|  No | API名         | Method            | Endpoint            | 利用タイミング  | 用途             |
| --: | ------------- | ----------------- | ------------------- | --------------- | ---------------- |
|   1 | {{apis.name}} | `{{apis.method}}` | `{{apis.endpoint}}` | {{apis.timing}} | {{apis.purpose}} |

### 14.2 Request

```json
{{api.request_example}}
```

### 14.3 Response

```json
{{api.response_example}}
```

### 14.4 画面項目とのマッピング

| 画面項目                    | API項目                     | 変換内容                  | 備考                 |
| --------------------------- | --------------------------- | ------------------------- | -------------------- |
| {{api_mapping.screen_item}} | `{{api_mapping.api_field}}` | {{api_mapping.transform}} | {{api_mapping.note}} |

---

## 15. データ取得・更新タイミング

| タイミング     | 処理                    | 対象API / 処理                 | 備考                         |
| -------------- | ----------------------- | ------------------------------ | ---------------------------- |
| 初期表示時     | {{data_flow.on_load}}   | {{data_flow.on_load_target}}   | {{data_flow.on_load_note}}   |
| ユーザー操作時 | {{data_flow.on_action}} | {{data_flow.on_action_target}} | {{data_flow.on_action_note}} |
| 再表示時       | {{data_flow.on_reload}} | {{data_flow.on_reload_target}} | {{data_flow.on_reload_note}} |

---

## 16. 非機能・UX観点

| 観点             | 方針                   |
| ---------------- | ---------------------- |
| レスポンシブ対応 | {{ux.responsive}}      |
| アクセシビリティ | {{ux.accessibility}}   |
| パフォーマンス   | {{ux.performance}}     |
| SEO              | {{ux.seo}}             |
| 多言語対応       | {{ux.i18n}}            |
| ブラウザ対応     | {{ux.browser_support}} |

---

## 17. セキュリティ観点

| 観点           | 方針                         |
| -------------- | ---------------------------- |
| 認証           | {{security.authentication}}  |
| 認可           | {{security.authorization}}   |
| 個人情報表示   | {{security.personal_data}}   |
| secret表示防止 | {{security.secret_handling}} |
| XSS対策        | {{security.xss}}             |
| CSRF対策       | {{security.csrf}}            |

---

## 18. ログ・計測

| 種別         | 内容                  | 出力タイミング               | 備考                       |
| ------------ | --------------------- | ---------------------------- | -------------------------- |
| 画面表示ログ | {{logging.page_view}} | {{logging.page_view_timing}} | {{logging.page_view_note}} |
| 操作ログ     | {{logging.action}}    | {{logging.action_timing}}    | {{logging.action_note}}    |
| エラーログ   | {{logging.error}}     | {{logging.error_timing}}     | {{logging.error_note}}     |
| メトリクス   | {{logging.metrics}}   | {{logging.metrics_timing}}   | {{logging.metrics_note}}   |

---

## 19. MVP対象範囲

### 19.1 MVP対象

{{#each mvp.in_scope}}

- {{this}}
  {{/each}}

### 19.2 MVP対象外

{{#each mvp.out_of_scope}}

- {{this}}
  {{/each}}

---

## 20. テスト観点

|  No | 観点         | 確認内容                   | 種別        |
| --: | ------------ | -------------------------- | ----------- |
|   1 | 初期表示     | {{test_points.initial}}    | manual      |
|   2 | Loading状態  | {{test_points.loading}}    | manual      |
|   3 | Empty状態    | {{test_points.empty}}      | manual      |
|   4 | Error状態    | {{test_points.error}}      | manual      |
|   5 | API連携      | {{test_points.api}}        | integration |
|   6 | レスポンシブ | {{test_points.responsive}} | manual      |

---

## 21. レビュー観点

{{#each review_points}}

- {{this}}
  {{/each}}

---

## 22. 未決事項

|  No | 論点                     | 判断が必要な理由          | 判断者                   | 期限                        | 備考                    |
| --: | ------------------------ | ------------------------- | ------------------------ | --------------------------- | ----------------------- |
|   1 | {{open_questions.topic}} | {{open_questions.reason}} | {{open_questions.owner}} | {{open_questions.due_date}} | {{open_questions.note}} |

---

## 23. 関連資料

| 種別       | パス / URL                   | 用途                               |
| ---------- | ---------------------------- | ---------------------------------- |
| input docs | `{{references.input_doc}}`   | {{references.input_doc_purpose}}   |
| API仕様書  | `{{references.api_spec}}`    | {{references.api_spec_purpose}}    |
| 画面一覧   | `{{references.screen_list}}` | {{references.screen_list_purpose}} |
| 画面遷移図 | `{{references.screen_flow}}` | {{references.screen_flow_purpose}} |
| Figma      | `{{references.figma}}`       | {{references.figma_purpose}}       |

---

## 24. 備考

{{#each notes}}

- {{this}}
  {{/each}}
