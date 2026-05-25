# {{batch.name}} バッチ仕様書

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

{{batch.summary}}

---

## 3. 目的

{{batch.objective}}

---

## 4. バッチ基本情報

| 項目           | 内容                         |
| -------------- | ---------------------------- |
| Batch ID       | `{{batch.id}}`               |
| Batch名        | {{batch.name}}               |
| 処理種別       | `{{batch.process_type}}`     |
| 実行基盤       | {{batch.runtime.platform}}   |
| 実装言語       | {{batch.runtime.language}}   |
| 起動方式       | {{batch.trigger.type}}       |
| 実行頻度       | {{batch.schedule.frequency}} |
| 想定実行時間   | {{batch.runtime.duration}}   |
| 冪等キー       | `{{batch.idempotency_key}}`  |
| 先行Batch      | {{batch.dependencies.before}} |
| 後続Batch      | {{batch.dependencies.after}} |
| MVP対象        | `{{batch.mvp_scope}}`        |

`Batch ID` は `BATCH-*` を使用する。処理構成上の分類IDである `BT-*` を Task / Issue / 成果物名の識別子として使用しない。

---

## 5. 実行条件

### 5.1 トリガー

| トリガー | 利用有無 | 条件 | 備考 |
| -------- | -------- | ---- | ---- |
| schedule | `{{trigger.schedule.enabled}}` | {{trigger.schedule.condition}} | {{trigger.schedule.note}} |
| workflow_dispatch | `{{trigger.workflow_dispatch.enabled}}` | {{trigger.workflow_dispatch.condition}} | {{trigger.workflow_dispatch.note}} |
| 先行Batch完了 | `{{trigger.after_batch.enabled}}` | {{trigger.after_batch.condition}} | {{trigger.after_batch.note}} |
| retry-failed | `{{trigger.retry_failed.enabled}}` | {{trigger.retry_failed.condition}} | {{trigger.retry_failed.note}} |

### 5.2 実行前提

{{#each preconditions}}

- {{this}}
  {{/each}}

{{#unless preconditions}}

- なし
  {{/unless}}

---

## 6. 入力

### 6.1 入力データ

| 入力 | 種別 | 取得元 | 必須 | 用途 | 備考 |
| ---- | ---- | ------ | ---- | ---- | ---- |
{{#each inputs.data}}
| `{{name}}` | {{type}} | {{source}} | `{{required}}` | {{purpose}} | {{note}} |
{{/each}}
{{#unless inputs.data}}
| - | - | - | - | なし | - |
{{/unless}}

### 6.2 外部API

| API | 利用有無 | 用途 | Rate Limit / 制約 | 備考 |
| --- | -------- | ---- | ----------------- | ---- |
{{#each inputs.external_apis}}
| {{name}} | `{{enabled}}` | {{purpose}} | {{constraint}} | {{note}} |
{{/each}}
{{#unless inputs.external_apis}}
| - | - | なし | - | - |
{{/unless}}

### 6.3 環境変数

環境変数は名称のみ記載し、値は記載しない。

| 環境変数名 | 必須 | 用途 | secret区分 | 設定先 |
| ---------- | ---- | ---- | ---------- | ------ |
{{#each inputs.env_vars}}
| `{{name}}` | `{{required}}` | {{purpose}} | `{{secret_type}}` | {{configured_in}} |
{{/each}}
{{#unless inputs.env_vars}}
| - | - | なし | - | - |
{{/unless}}

---

## 7. 出力

### 7.1 出力データ

| 出力 | 種別 | 出力先 | 正本区分 | 用途 | 備考 |
| ---- | ---- | ------ | -------- | ---- | ---- |
{{#each outputs.data}}
| `{{name}}` | {{type}} | {{destination}} | {{canonical_type}} | {{purpose}} | {{note}} |
{{/each}}
{{#unless outputs.data}}
| - | - | - | - | なし | - |
{{/unless}}

### 7.2 更新リソース

| リソース | 操作 | 更新条件 | 冪等性 | 備考 |
| -------- | ---- | -------- | ------ | ---- |
{{#each outputs.updated_resources}}
| `{{resource}}` | {{operation}} | {{condition}} | {{idempotency}} | {{note}} |
{{/each}}
{{#unless outputs.updated_resources}}
| - | - | なし | - | - |
{{/unless}}

---

## 8. 処理フロー

### 8.1 全体フロー

```mermaid
flowchart TD
{{process.flow}}
```

### 8.2 処理ステップ

|  No | Phase | 処理 | 入力 | 出力 | 失敗時の扱い |
| --: | ----- | ---- | ---- | ---- | ------------ |
{{#each process.steps}}
| {{no}} | `{{phase}}` | {{description}} | {{input}} | {{output}} | {{on_error}} |
{{/each}}
{{#unless process.steps}}
| - | - | なし | - | - | - |
{{/unless}}

---

## 9. データ変換・マッピング

| 入力項目 | 内部項目 | 出力項目 | 変換内容 | 備考 |
| -------- | -------- | -------- | -------- | ---- |
{{#each mappings}}
| `{{input_field}}` | `{{internal_field}}` | `{{output_field}}` | {{transform}} | {{note}} |
{{/each}}
{{#unless mappings}}
| - | - | - | なし | - |
{{/unless}}

---

## 10. DB / Storage更新仕様

### 10.1 DB更新

| テーブル | 操作 | 主キー / 一意キー | 更新項目 | 競合時の扱い | 備考 |
| -------- | ---- | ----------------- | -------- | ------------ | ---- |
{{#each persistence.database}}
| `{{table}}` | {{operation}} | `{{key}}` | {{fields}} | {{on_conflict}} | {{note}} |
{{/each}}
{{#unless persistence.database}}
| - | - | - | なし | - | - |
{{/unless}}

### 10.2 Object Storage

| オブジェクト | 操作 | path / key 方針 | 保持方針 | 備考 |
| ------------ | ---- | --------------- | -------- | ---- |
{{#each persistence.storage}}
| `{{object}}` | {{operation}} | `{{path_policy}}` | {{retention}} | {{note}} |
{{/each}}
{{#unless persistence.storage}}
| - | - | - | なし | - |
{{/unless}}

---

## 11. 冪等性・再実行性

| 観点 | 方針 |
| ---- | ---- |
| 冪等キー | `{{idempotency.key}}` |
| 重複実行時の扱い | {{idempotency.duplicate_policy}} |
| 部分失敗時の再実行 | {{idempotency.partial_retry_policy}} |
| 成功済みデータのskip条件 | {{idempotency.skip_condition}} |
| rollback方針 | {{idempotency.rollback_policy}} |

---

## 12. 状態管理

| 対象 | 状態値 | 遷移条件 | 記録先 | 備考 |
| ---- | ------ | -------- | ------ | ---- |
{{#each state_management}}
| {{target}} | `{{state}}` | {{transition_condition}} | `{{recorded_in}}` | {{note}} |
{{/each}}
{{#unless state_management}}
| - | - | なし | - | - |
{{/unless}}

---

## 13. エラー・リトライ仕様

| エラー種別 | Error Code | 発生条件 | リトライ | 停止条件 | 備考 |
| ---------- | ---------- | -------- | -------- | -------- | ---- |
{{#each errors}}
| {{type}} | `{{code}}` | {{condition}} | {{retry_policy}} | {{stop_condition}} | {{note}} |
{{/each}}
{{#unless errors}}
| - | - | なし | - | - | - |
{{/unless}}

---

## 14. ログ・監視

| 種別 | 記録内容 | 出力タイミング | 保存先 | 備考 |
| ---- | -------- | -------------- | ------ | ---- |
{{#each observability.logs}}
| {{type}} | {{content}} | {{timing}} | `{{destination}}` | {{note}} |
{{/each}}
{{#unless observability.logs}}
| - | なし | - | - | - |
{{/unless}}

### 14.1 メトリクス

| Metric | 内容 | 集計単位 | 用途 |
| ------ | ---- | -------- | ---- |
{{#each observability.metrics}}
| `{{name}}` | {{description}} | {{aggregation}} | {{purpose}} |
{{/each}}
{{#unless observability.metrics}}
| - | なし | - | - |
{{/unless}}

---

## 15. セキュリティ・外部サービス利用

| 観点 | 方針 |
| ---- | ---- |
| secret取り扱い | {{security.secret_handling}} |
| 外部API key | {{security.external_api_key}} |
| ログ出力制限 | {{security.logging_restriction}} |
| 個人情報・機微情報 | {{security.personal_data}} |
| GitHub Actions permissions | {{security.github_actions_permissions}} |
| コスト・Rate Limit | {{security.cost_and_rate_limit}} |

---

## 16. テスト観点

|  No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
{{#each test_points}}
| {{no}} | {{name}} | {{description}} | {{type}} |
{{/each}}
{{#unless test_points}}
| 1 | 正常系 | {{default_test_points.normal}} | unit / integration |
| 2 | 外部API失敗 | {{default_test_points.external_api_error}} | integration |
| 3 | DB更新失敗 | {{default_test_points.db_error}} | integration |
| 4 | 冪等性 | {{default_test_points.idempotency}} | unit / integration |
| 5 | 再実行性 | {{default_test_points.retry}} | integration |
{{/unless}}

---

## 17. 変更管理

### 17.1 変更履歴

| 日付 | 変更内容 | 関連Issue / PR |
| ---- | -------- | -------------- |
{{#each change_history}}
| {{date}} | {{description}} | {{reference}} |
{{/each}}
{{#unless change_history}}
| - | 初版 | - |
{{/unless}}

---

## 18. 未決事項

|  No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
{{#each open_questions}}
| {{@index}} | {{topic}} | {{reason}} | {{owner}} | {{due_date}} | {{note}} |
{{/each}}
{{#unless open_questions}}
| - | なし | - | - | - | - |
{{/unless}}

---

## 19. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
{{#each references}}
| {{type}} | `{{path}}` | {{purpose}} |
{{/each}}
{{#unless references}}
| - | - | なし |
{{/unless}}

---

## 20. レビュー観点

{{#each review_points}}

- {{this}}
  {{/each}}

{{#unless review_points}}

- `BATCH-*` の識別子とバッチ処理一覧が一致している
- 入力、出力、更新リソース、冪等キーが明確である
- 外部API、DB、Object Storage、ログの責務が明確である
- 再実行時に重複登録や不整合が起きない方針になっている
- secretや`.env`実値が含まれていない
  {{/unless}}

---

## 21. 備考

{{#each notes}}

- {{this}}
  {{/each}}

{{#unless notes}}

- なし
  {{/unless}}
