# Component tests (`apps/web/tests/component`)

Phase4a `web-foundation` W4 の component test 基盤。

## 実行

```bash
pnpm --filter @gift-recommendation/web test:component
```

## 配置方針

- テスト対象は `UIコンポーネント一覧.md` の MVP ○ コンポーネント
- ディレクトリは `src/components` のカテゴリ（`action` / `layout` / `form` 等）に合わせる
- render / 基本 interaction を Vitest + Testing Library で検証する

## 参照

- `docs/05_アプリケーション設計/アプリ/web/UIコンポーネント一覧.md` §7.2
