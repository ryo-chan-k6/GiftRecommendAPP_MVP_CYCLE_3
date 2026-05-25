# {{database.name}} 物理ER

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

{{database.summary}}

---

## 3. 目的

{{database.objective}}

---

## 4. 設計対象

| 項目 | 内容 |
| ---- | ---- |
| 対象DB | {{database.target_db}} |
| 対象スキーマ | `{{database.schema}}` |
| 対象テーブル群 | {{database.table_groups}} |
| 前提論理ER | `{{references.logical_er}}` |
| 前提テーブル一覧 | `{{references.table_list}}` |
| DB方針 | {{database.policy_summary}} |

---

## 5. 物理設計方針

| 観点 | 方針 |
| ---- | ---- |
| 主キー | {{policy.primary_key}} |
| 外部キー | {{policy.foreign_key}} |
| unique制約 | {{policy.unique_constraint}} |
| index | {{policy.index}} |
| JSON / JSONB | {{policy.json}} |
| timestamp | {{policy.timestamp}} |
| 論理削除 | {{policy.logical_delete}} |
| 履歴管理 | {{policy.history}} |
| partition | {{policy.partition}} |
| pgvector | {{policy.pgvector}} |

---

## 6. 全体物理ER図

```mermaid
erDiagram
{{er.overall}}
```

---

## 7. テーブル分類

| 分類 | 主なテーブル | 位置づけ | MVP対象 |
| ---- | ------------ | -------- | ------- |
{{#each table_groups}}
| {{name}} | {{tables}} | {{description}} | `{{mvp_scope}}` |
{{/each}}
{{#unless table_groups}}
| - | - | なし | - |
{{/unless}}

---

## 8. テーブル一覧

| テーブル名 | 論理名 | 分類 | 正本区分 | 主な更新主体 | MVP対象 |
| ---------- | ------ | ---- | -------- | ------------ | ------- |
{{#each tables}}
| `{{physical_name}}` | {{logical_name}} | {{category}} | {{canonical_type}} | {{owner}} | `{{mvp_scope}}` |
{{/each}}
{{#unless tables}}
| - | - | - | なし | - | - |
{{/unless}}

---

## 9. 関係定義

| From | To | 関係 | FK制約 | カーディナリティ | 備考 |
| ---- | -- | ---- | ------ | ---------------- | ---- |
{{#each relationships}}
| `{{from_table}}.{{from_column}}` | `{{to_table}}.{{to_column}}` | {{relation}} | `{{fk_constraint}}` | {{cardinality}} | {{note}} |
{{/each}}
{{#unless relationships}}
| - | - | なし | - | - | - |
{{/unless}}

---

## 10. Index設計

| テーブル | Index名 | 対象カラム | 種別 | 用途 | 備考 |
| -------- | ------- | ---------- | ---- | ---- | ---- |
{{#each indexes}}
| `{{table}}` | `{{name}}` | `{{columns}}` | {{type}} | {{purpose}} | {{note}} |
{{/each}}
{{#unless indexes}}
| - | - | - | なし | - | - |
{{/unless}}

---

## 11. 制約設計

| テーブル | 制約名 | 種別 | 対象 | 内容 | 備考 |
| -------- | ------ | ---- | ---- | ---- | ---- |
{{#each constraints}}
| `{{table}}` | `{{name}}` | {{type}} | `{{target}}` | {{description}} | {{note}} |
{{/each}}
{{#unless constraints}}
| - | - | - | - | なし | - |
{{/unless}}

---

## 12. 状態・enum連携

| 対象 | 状態 / enum | 定義元 | 利用テーブル | 備考 |
| ---- | ----------- | ------ | ------------ | ---- |
{{#each enum_links}}
| {{target}} | `{{enum_name}}` | `{{definition}}` | `{{tables}}` | {{note}} |
{{/each}}
{{#unless enum_links}}
| - | - | なし | - | - |
{{/unless}}

---

## 13. データ保持・削除

| テーブル群 | 保持期間 | 削除方式 | 削除条件 | 備考 |
| ---------- | -------- | -------- | -------- | ---- |
{{#each retention}}
| {{table_group}} | {{period}} | {{delete_type}} | {{condition}} | {{note}} |
{{/each}}
{{#unless retention}}
| - | - | なし | - | - |
{{/unless}}

---

## 14. セキュリティ・権限

| 観点 | 方針 |
| ---- | ---- |
| DB権限 | {{security.db_permission}} |
| secret取り扱い | {{security.secret_handling}} |
| 個人情報・機微情報 | {{security.personal_data}} |
| ログ出力制限 | {{security.logging_restriction}} |
| service role利用 | {{security.service_role}} |

---

## 15. Migration / DDL接続

| 項目 | 内容 |
| ---- | ---- |
| DDL作成単位 | {{migration.ddl_unit}} |
| migration命名 | {{migration.naming}} |
| 適用順序 | {{migration.apply_order}} |
| rollback方針 | {{migration.rollback_policy}} |
| 破壊的変更有無 | `{{migration.destructive_change}}` |
| Human Review必須事項 | {{migration.human_review_points}} |

---

## 16. 後続テーブル定義書への引き継ぎ

{{#each handoff_to_table_specs}}

- {{this}}
  {{/each}}

{{#unless handoff_to_table_specs}}

- なし
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

- 論理ER、テーブル一覧、正本定義と矛盾していない
- 主キー、外部キー、unique制約、index方針が後続DDLへ展開できる粒度である
- Online / Batch / Log / Metric の責務が混在していない
- migrationや破壊的DB変更がHuman Review事項として明示されている
- secretや`.env`実値が含まれていない
  {{/unless}}
