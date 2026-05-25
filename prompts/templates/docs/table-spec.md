# {{table.logical_name}} テーブル定義書

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

{{table.summary}}

---

## 3. 目的

{{table.objective}}

---

## 4. テーブル基本情報

| 項目 | 内容 |
| ---- | ---- |
| 物理テーブル名 | `{{table.physical_name}}` |
| 論理テーブル名 | {{table.logical_name}} |
| 分類 | {{table.category}} |
| 正本区分 | {{table.canonical_type}} |
| 主な更新主体 | {{table.owner}} |
| 主な参照主体 | {{table.readers}} |
| MVP対象 | `{{table.mvp_scope}}` |
| 関連物理ER | `{{references.physical_er}}` |

---

## 5. 用途・責務

{{table.responsibility}}

### 5.1 対象外

{{#each table.out_of_scope}}

- {{this}}
  {{/each}}

{{#unless table.out_of_scope}}

- なし
  {{/unless}}

---

## 6. カラム定義

|  No | カラム名 | 論理名 | 型 | 必須 | PK | FK | Unique | Default | 説明 |
| --: | -------- | ------ | -- | ---- | -- | -- | ------ | ------- | ---- |
{{#each columns}}
| {{no}} | `{{physical_name}}` | {{logical_name}} | `{{type}}` | `{{required}}` | `{{primary_key}}` | `{{foreign_key}}` | `{{unique}}` | `{{default}}` | {{description}} |
{{/each}}
{{#unless columns}}
| - | - | - | - | - | - | - | - | - | なし |
{{/unless}}

---

## 7. 主キー・一意キー

| 種別 | 対象カラム | 方針 | 備考 |
| ---- | ---------- | ---- | ---- |
{{#each keys}}
| {{type}} | `{{columns}}` | {{policy}} | {{note}} |
{{/each}}
{{#unless keys}}
| - | - | なし | - |
{{/unless}}

---

## 8. 外部キー・参照関係

| カラム | 参照先 | FK制約 | 参照整合性 | 備考 |
| ------ | ------ | ------ | ---------- | ---- |
{{#each foreign_keys}}
| `{{column}}` | `{{reference_table}}.{{reference_column}}` | `{{constraint_enabled}}` | {{integrity_policy}} | {{note}} |
{{/each}}
{{#unless foreign_keys}}
| - | - | なし | - | - |
{{/unless}}

---

## 9. Index

| Index名 | 対象カラム | 種別 | 用途 | 備考 |
| ------- | ---------- | ---- | ---- | ---- |
{{#each indexes}}
| `{{name}}` | `{{columns}}` | {{type}} | {{purpose}} | {{note}} |
{{/each}}
{{#unless indexes}}
| - | - | なし | - | - |
{{/unless}}

---

## 10. 制約

| 制約名 | 種別 | 対象 | 内容 | 備考 |
| ------ | ---- | ---- | ---- | ---- |
{{#each constraints}}
| `{{name}}` | {{type}} | `{{target}}` | {{description}} | {{note}} |
{{/each}}
{{#unless constraints}}
| - | - | - | なし | - |
{{/unless}}

---

## 11. 状態・enum

| カラム | enum / code | 定義元 | 許容値 | 備考 |
| ------ | ----------- | ------ | ------ | ---- |
{{#each enums}}
| `{{column}}` | `{{name}}` | `{{definition}}` | {{values}} | {{note}} |
{{/each}}
{{#unless enums}}
| - | - | なし | - | - |
{{/unless}}

---

## 12. 更新仕様

| 操作 | 実行主体 | 条件 | 更新項目 | 冪等性 | 備考 |
| ---- | -------- | ---- | -------- | ------ | ---- |
{{#each operations}}
| {{operation}} | {{actor}} | {{condition}} | {{fields}} | {{idempotency}} | {{note}} |
{{/each}}
{{#unless operations}}
| - | - | なし | - | - | - |
{{/unless}}

---

## 13. データ保持・削除

| 観点 | 方針 |
| ---- | ---- |
| 保持期間 | {{retention.period}} |
| 削除方式 | {{retention.delete_type}} |
| 削除条件 | {{retention.condition}} |
| 論理削除 | {{retention.logical_delete}} |
| アーカイブ | {{retention.archive}} |

---

## 14. Migration / DDL

| 項目 | 内容 |
| ---- | ---- |
| DDL対象 | `{{ddl.target}}` |
| migration単位 | {{ddl.migration_unit}} |
| 適用順序 | {{ddl.apply_order}} |
| rollback方針 | {{ddl.rollback_policy}} |
| 破壊的変更有無 | `{{ddl.destructive_change}}` |

---

## 15. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| 読み取り権限 | {{security.read_permission}} |
| 書き込み権限 | {{security.write_permission}} |
| service role利用 | {{security.service_role}} |
| 個人情報・機微情報 | {{security.personal_data}} |
| ログ出力制限 | {{security.logging_restriction}} |

---

## 16. テスト観点

|  No | 観点 | 確認内容 | 種別 |
| --: | ---- | -------- | ---- |
{{#each test_points}}
| {{no}} | {{name}} | {{description}} | {{type}} |
{{/each}}
{{#unless test_points}}
| 1 | DDL適用 | {{default_test_points.ddl}} | migration |
| 2 | 制約 | {{default_test_points.constraints}} | unit / integration |
| 3 | Index | {{default_test_points.indexes}} | manual |
| 4 | CRUD | {{default_test_points.crud}} | integration |
| 5 | 権限 | {{default_test_points.permissions}} | manual |
{{/unless}}

---

## 17. 未決事項

|  No | 論点 | 判断が必要な理由 | 判断者 | 期限 | 備考 |
| --: | ---- | ---------------- | ------ | ---- | ---- |
{{#each open_questions}}
| {{@index}} | {{topic}} | {{reason}} | {{owner}} | {{due_date}} | {{note}} |
{{/each}}
{{#unless open_questions}}
| - | なし | - | - | - | - |
{{/unless}}

---

## 18. 関連資料

| 種別 | パス / URL | 用途 |
| ---- | ---------- | ---- |
{{#each references.items}}
| {{type}} | `{{path}}` | {{purpose}} |
{{/each}}
{{#unless references.items}}
| - | - | なし |
{{/unless}}

---

## 19. レビュー観点

{{#each review_points}}

- {{this}}
  {{/each}}

{{#unless review_points}}

- テーブル一覧、論理ER、物理ERと矛盾していない
- カラム、型、制約、Index、更新主体がDDLへ展開できる粒度である
- enum / code値の定義元が明確である
- 破壊的DB変更やmigration判断がHuman Review事項として明示されている
- secretや`.env`実値が含まれていない
  {{/unless}}
