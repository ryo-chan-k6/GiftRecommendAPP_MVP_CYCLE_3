# packages/shared-types

Gift Recommendation Service MVP の TypeScript 横断型パッケージ。

## 目的

- `apps/web` / `apps/api` 等で共通利用する TypeScript 型・検証ユーティリティを提供する
- `packages/code-definitions/` を正本とし、同一 `code_definition.id` をキーに value 集合を参照する
- enum定義書（`docs/06_実装設計/database/enum定義書.md`）の DB / API / code 連携方針に整合する

## 責務分担

| パッケージ | 役割 |
| ---------- | ---- |
| `code-definitions` | YAML 正本、ロード・スキーマ検証 |
| `shared-types` | TypeScript 向けカタログ型、runtime ガード |
| `shared-logic` | reco / batch 共通ドメインロジック（Python） |

## ディレクトリ構成

| パス | 役割 |
| ---- | ---- |
| `src/types.ts` | `CodeValueCatalog` 等の共通型 |
| `src/catalog.ts` | code-definitions からカタログを構築 |
| `src/guards.ts` | value / error_code の runtime 検証 |
| `src/tests/` | 単体テスト |

## 利用例

```typescript
import {
  isCodeDefinitionValue,
  loadMvpSharedTypeCatalog,
} from "@gift-recommendation/shared-types";

const { codeValues } = await loadMvpSharedTypeCatalog();

if (isCodeDefinitionValue(codeValues, "recommendation_run_status", status)) {
  // status は catalog 上の有効値
}
```

## 開発

```bash
cd packages/shared-types
pnpm install
pnpm test
```

`pnpm test` は `@gift-recommendation/code-definitions` の build を先行実行する。

## 変更手順

1. 関連 docs（enum定義書等）更新
2. `packages/code-definitions/` 更新
3. 本パッケージのカタログ / ガード整合確認（`pnpm test`）
4. 利用側 apps 更新（後続 Task）

正本: [DevOps方針書](../../docs/05_アプリケーション設計/共通/DevOps方針書.md) §5.5 / §8
