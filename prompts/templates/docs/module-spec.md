# {{module.name}} モジュール仕様書

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

{{module.summary}}

---

## 3. 目的

{{module.objective}}

---

## 4. モジュール基本情報

| 項目 | 内容 |
| ---- | ---- |
| モジュールID | `{{module.id}}` |
| モジュール名 | {{module.name}} |
| 物理名 | `{{module.physical_name}}` |
| 分類 | {{module.category}} |
| 処理種別 | `{{module.process_type}}` |
| 配置予定 | `{{module.target_path}}` |
| 所属Epic | `{{module.epic}}` |
| MVP対象 | `{{module.mvp_scope}}` |
| 主な呼び出し元 | {{module.callers_summary}} |
| 主な呼び出し先 | {{module.callees_summary}} |

`MOD-API-*` / `MOD-RECO-*` / `MOD-BATCH-*` 配下のTaskでは、該当モジュールIDの責務範囲に変更を限定する。`MOD-RECO-*` では `apps/reco/src/app/**` のAPI-INTエンドポイント層を対象に含めない。エンドポイント層の変更が必要な場合は、該当する `API-INT-*` Epic配下Taskとして扱う。

---

## 5. 責務

### 5.1 主責務

{{#each responsibilities.primary}}

- {{this}}
  {{/each}}

{{#unless responsibilities.primary}}

- なし
  {{/unless}}

### 5.2 対象外責務

{{#each responsibilities.out_of_scope}}

- {{this}}
  {{/each}}

{{#unless responsibilities.out_of_scope}}

- なし
  {{/unless}}

---

## 6. 入出力

### 6.1 入力

| 入力 | 型 / 構造 | 必須 | 生成元 | 用途 | 備考 |
| ---- | --------- | ---- | ------ | ---- | ---- |
{{#each inputs}}
| `{{name}}` | `{{type}}` | `{{required}}` | {{source}} | {{purpose}} | {{note}} |
{{/each}}
{{#unless inputs}}
| - | - | - | - | なし | - |
{{/unless}}

### 6.2 出力

| 出力 | 型 / 構造 | 利用先 | 用途 | 備考 |
| ---- | --------- | ------ | ---- | ---- |
{{#each outputs}}
| `{{name}}` | `{{type}}` | {{consumer}} | {{purpose}} | {{note}} |
{{/each}}
{{#unless outputs}}
| - | - | - | なし | - |
{{/unless}}

---

## 7. 依存関係

### 7.1 依存モジュール

| 依存先 | 方向 | 用途 | 失敗時の扱い | 備考 |
| ------ | ---- | ---- | ------------ | ---- |
{{#each dependencies.modules}}
| `{{name}}` | `{{direction}}` | {{purpose}} | {{on_failure}} | {{note}} |
{{/each}}
{{#unless dependencies.modules}}
| - | - | なし | - | - |
{{/unless}}

### 7.2 参照データ

| データ | 参照元 | 用途 | version / config | 備考 |
| ------ | ------ | ---- | ---------------- | ---- |
{{#each dependencies.data}}
| `{{name}}` | {{source}} | {{purpose}} | `{{version}}` | {{note}} |
{{/each}}
{{#unless dependencies.data}}
| - | - | なし | - | - |
{{/unless}}

---

## 8. 処理仕様

### 8.1 処理フロー

```mermaid
flowchart TD
{{process.flow}}
```

### 8.2 処理ステップ

|  No | 処理 | 入力 | 出力 | 補足 |
| --: | ---- | ---- | ---- | ---- |
{{#each process.steps}}
| {{no}} | {{description}} | {{input}} | {{output}} | {{note}} |
{{/each}}
{{#unless process.steps}}
| - | なし | - | - | - |
{{/unless}}

### 8.3 アルゴリズム / 計算仕様

{{algorithm.summary}}

| 項目 | 内容 |
| ---- | ---- |
{{#each algorithm.parameters}}
| `{{name}}` | {{description}} |
{{/each}}
{{#unless algorithm.parameters}}
| - | なし |
{{/unless}}

---

## 9. データ項目マッピング

| 入力項目 | 内部項目 | 出力項目 | 変換内容 | 備考 |
| -------- | -------- | -------- | -------- | ---- |
{{#each mappings}}
| `{{input_field}}` | `{{internal_field}}` | `{{output_field}}` | {{transform}} | {{note}} |
{{/each}}
{{#unless mappings}}
| - | - | - | なし | - |
{{/unless}}

---

## 10. 状態・例外

### 10.1 状態

| 状態 | 意味 | 遷移条件 | 記録先 |
| ---- | ---- | -------- | ------ |
{{#each states}}
| `{{name}}` | {{meaning}} | {{condition}} | `{{recorded_in}}` |
{{/each}}
{{#unless states}}
| - | なし | - | - |
{{/unless}}

### 10.2 例外

| 例外 | Error Code | 発生条件 | 呼び出し元への返却 | ログ |
| ---- | ---------- | -------- | ------------------ | ---- |
{{#each errors}}
| {{name}} | `{{code}}` | {{condition}} | {{response}} | {{log_policy}} |
{{/each}}
{{#unless errors}}
| - | - | なし | - | - |
{{/unless}}

---

## 11. DB / 永続化

| テーブル | 操作 | 主な項目 | トランザクション | 備考 |
| -------- | ---- | -------- | ---------------- | ---- |
{{#each persistence.database}}
| `{{table}}` | {{operation}} | {{fields}} | {{transaction}} | {{note}} |
{{/each}}
{{#unless persistence.database}}
| - | - | なし | - | - |
{{/unless}}

---

## 12. ログ・メトリクス

| 種別 | 内容 | 出力タイミング | 保存先 | 備考 |
| ---- | ---- | -------------- | ------ | ---- |
{{#each observability.logs}}
| {{type}} | {{content}} | {{timing}} | `{{destination}}` | {{note}} |
{{/each}}
{{#unless observability.logs}}
| - | なし | - | - | - |
{{/unless}}

### 12.1 メトリクス

| Metric | 内容 | 集計単位 | 用途 |
| ------ | ---- | -------- | ---- |
{{#each observability.metrics}}
| `{{name}}` | {{description}} | {{aggregation}} | {{purpose}} |
{{/each}}
{{#unless observability.metrics}}
| - | なし | - | - |
{{/unless}}

---

## 13. 性能・非機能

| 観点 | 方針 |
| ---- | ---- |
| レイテンシ | {{non_functional.latency}} |
| 計算量 | {{non_functional.complexity}} |
| タイムアウト | {{non_functional.timeout}} |
| リトライ | {{non_functional.retry}} |
| キャッシュ | {{non_functional.cache}} |
| 並列実行 | {{non_functional.parallel_execution}} |

---

## 14. テスト観点

|  No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
{{#each test_points}}
| {{no}} | {{name}} | {{description}} | {{type}} |
{{/each}}
{{#unless test_points}}
| 1 | 正常系 | {{default_test_points.normal}} | unit |
| 2 | 境界値 | {{default_test_points.boundary}} | unit |
| 3 | 例外系 | {{default_test_points.error}} | unit |
| 4 | 依存モジュール失敗 | {{default_test_points.dependency_error}} | unit / integration |
| 5 | DB / ログ | {{default_test_points.persistence}} | integration |
{{/unless}}

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

- Recoモジュール一覧のモジュール名・物理名・分類と一致している
- 対象 `MOD-*` の責務範囲に収まり、API-INTエンドポイント層の変更を混在させていない
- 入力、出力、依存モジュール、例外、ログ、テスト観点が後続実装可能な粒度である
- 処理種別と呼び出し元・呼び出し先の責務境界が明確である
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
