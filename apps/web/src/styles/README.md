# Phase4a styles-foundation scaffold（W3）

Phase4a `web-foundation`（W3）のスタイル基盤。デザインルールのセマンティックトークンを TypeScript / CSS 変数 / Tailwind theme へ集約する。

| パス | 責務 |
| ---- | ---- |
| `tokens/` | カラー・タイポ・余白・角丸の正本値（デザインルール §4） |
| `theme/tailwind-theme.ts` | トークン → `theme.extend` マッピング |
| `theme/css-variables.ts` | トークン → `:root` CSS 変数ヘルパ |
| `globals.css` | Tailwind エントリ + `:root` 変数 + base スタイル |
| `tailwind.config.ts` | Tailwind 設定（content は後続 W2/W4 向けに components/app を見越し） |
| `fonts.ts` | LP 準拠フォントスタック（next/font 接続は Phase4b） |
| `preview/` | スタイルガイド静的プレビュー（`pnpm preview:style-guide`） |

正本: `docs/05_アプリケーション設計/アプリ/web/デザインルール.md`

## スタイルガイドのプレビュー

```bash
cd apps/web && pnpm preview:style-guide
```

http://localhost:3099/style-guide.html でカラー・フォント・部品サンプルを確認できる。

## Phase4b 以降

- Next.js `layout.tsx` から `globals.css` を import する
- `next/font/google` で Noto Serif JP / Shippori Mincho を読み込む（§10.1 判断）
- W2 `common-ui-components` が本トークンを Tailwind クラスで利用する
