# packages/code-definitions

Gift Recommendation Service MVP のコード定義正本。

## 目的

- DB / API / アプリケーション / テストで共通利用する識別子・状態値を機械可読形式で管理する
- docs 上の enum 定義書（`docs/06_実装設計/database/enum定義書.md`）およびエラーコード定義書と整合させる
- TypeScript からロード・検証可能な骨格を提供する

## ディレクトリ構成

| パス | 役割 |
| ---- | ---- |
| `semantic/` | Feature / Semantic 関連コード |
| `application/` | recommendation mode、Feedback 対象、Log owner 等 |
| `state/` | Run / Batch / Item 等の状態コード |
| `batch/` | Batch フェーズ名・生成種別等 |
| `error/` | error_code カタログ（domain 別 YAML） |
| `src/` | ロード・検証ロジック（`@gift-recommendation/code-definitions`） |
| `tests/` | 単体テスト |

## ファイル形式

### enum / 状態コード（`code_definition`）

各 YAML は以下の共通構造とする。

```yaml
schema_version: "1.0"
definition_type: "code_definition"
code_definition:
  id: "<論理ID>"
  physical_name: "<DB列名>"
  logical_name: "<表示名>"
  category: "state | application | semantic | batch"
  mvp_scope: true
values:
  - value: "<物理値>"
    label: "<表示名>"
    meaning: "<意味>"
    terminal: true|false
    enabled: true
db_usages:
  - table: "<table>"
    column: "<column>"
    constraint: "<制約>"
```

### error_code（`error_catalog`）

domain 単位のカタログ YAML。詳細は `error/README.md` を参照。

## TypeScript パッケージ

```bash
cd packages/code-definitions
pnpm install
pnpm test
```

公開 API:

- `loadAllDefinitions()` — enum / error 定義を読み込む
- `validatePackageDefinitions()` — スキーマ・重複・形式を検証する

## 命名方針

- `code_definition.id` は snake_case の論理 ID とする（例: `recommendation_run_status`）
- 同一 physical 列名（`run_status` 等）で意味が異なる場合は **別 id** とする
- 値（`values[].value`）は snake_case、小文字英数字とアンダースコア
- error_code は `GRS-{DOMAIN}-{NUMBER}`（`error/error_code_format.yaml` 参照。DOMAIN 長 2〜4）

## 変更手順

1. 関連 docs 更新
2. 本ディレクトリ更新
3. `pnpm test`（packages/code-definitions）で整合性確認
4. 必要に応じて `supabase/seeds/masters/` 更新（後続 Task）
5. 実装・テスト参照箇所更新

正本: [DevOps方針書](../../docs/05_アプリケーション設計/共通/DevOps方針書.md) §8
