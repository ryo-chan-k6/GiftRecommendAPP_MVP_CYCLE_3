# error/

`error_code` の機械可読正本（Phase4a `packages-foundation`）。

人間可読正本: `docs/05_アプリケーション設計/アプリ/エラーコード定義書.md`

## 正本分担

| レイヤ | 正本 | 担当 |
| ------ | ---- | ---- |
| 人間可読・設計 | `docs/05_アプリケーション設計/アプリ/エラーコード定義書.md` | 既存 docs 維持 |
| 機械可読 | `packages/code-definitions/error/*.yaml` | Phase4a packages-foundation |
| DB 物理 | `error_log.error_code` | テーブル定義 / DDL Task |

## ファイル構成

| ファイル | 内容 |
| -------- | ---- |
| `error_code_format.yaml` | `GRS-{DOMAIN}-{NUMBER}` 形式定義 |
| `{domain}.yaml` | domain 別 error カタログ（例: `com.yaml`, `rec.yaml`） |

## YAML 形式（`error_catalog`）

```yaml
schema_version: "1.0"
definition_type: "error_catalog"
error_catalog:
  domain: "COM"
  domain_label: "Common"
  mvp_scope: true
  codes:
    - code: "GRS-COM-001"
      internal_name: "Bad Request"
      http_status: 400
      retryable: false
      severity: warn
      user_message_key: "error.com.001"
      owner_types: ["api_call"]
      mvp_scope: true
```

## DB 制約方針

- エラーコード全件の CHECK 列挙は **行わない**
- **`error_code` 形式 CHECK のみ** を付与する（`error_code_format.yaml` 参照）
- 意味・retryable・HTTP status・user message 等は本 YAML + CI 整合で管理する

## 参照

- `docs/06_実装設計/database/enum定義書.md` §10.2
- `pnpm test`（packages/code-definitions）でカタログ整合性を検証
