# error/

`error_code` の機械可読正本は Phase4a `packages-foundation` Epic で整備する。

MVP DB 物理設計 Task（enum-code-definitions）では、error_code 全件の YAML 化は **out of scope** とする。

## 正本分担（Human Review 確定）

| レイヤ | 正本 | 担当 |
| ------ | ---- | ---- |
| 人間可読・設計 | `docs/05_アプリケーション設計/アプリ/エラーコード定義書.md` | 既存 docs 維持 |
| 機械可読 | `packages/code-definitions/error/*.yaml` | Phase4a packages-foundation |
| DB 物理 | `error_log.error_code` | テーブル定義 / DDL Task |

## DB 制約方針

- エラーコード全件の CHECK 列挙は **行わない**
- **`error_code` 形式 CHECK のみ** を付与する（例: `^GRS-[A-Z]{3}-[0-9]{3}$`）
- 意味・retryable・HTTP status・user message 等は Phase4a YAML + CI 整合で管理する

## Phase4a YAML に含める項目（方針）

- `code`, `domain`, `http_status`（API 向け）, `retryable`, `severity`, `user_message_key`, `internal_name`, `owner_types[]`, `mvp_scope`

## 参照

- `docs/06_実装設計/database/enum定義書.md` §10.2
