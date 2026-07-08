/**
 * フォント定義（正本: デザインルール.md §4.2）
 *
 * next/font による実読み込みは `src/lib/fonts.ts`（App Router layout）で行う。
 * 本ファイルは Tailwind theme とスタイルガイド向けのフォントスタック正本。
 */
export const fontFamilyStacks = {
  body: ['"Noto Serif JP"', '"Hiragino Mincho ProN"', "serif"],
  heading: ['"Shippori Mincho"', '"Hiragino Mincho ProN"', "serif"],
} as const;

/** Google Fonts 公開 URL（layout / next/font 接続用の参照値） */
export const googleFontSources = {
  notoSerifJp:
    "https://fonts.googleapis.com/css2?family=Noto+Serif+JP:wght@400;500;600;700&display=swap",
  shipporiMincho:
    "https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@400;500;600;700&display=swap",
} as const;
