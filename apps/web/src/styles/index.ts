export { colorTokens, radiiTokens, spacingTokens, typographyTokens } from "./tokens/index.js";
export type {
  ColorTokenName,
  RadiiTokenName,
  SpacingTokenName,
  TypographyTokenName,
} from "./tokens/index.js";
export { fontFamilyStacks, googleFontSources } from "./fonts.js";
export { buildCssVariables, buildCssVariablesBlock } from "./theme/css-variables.js";
export { tailwindThemeExtend } from "./theme/tailwind-theme.js";

/** Phase4b layout から読み込むグローバル CSS の相対パス */
export const globalsCssPath = "./globals.css";

/** Tailwind / PostCSS 設定の相対パス（apps/web ルートからの参照用） */
export const tailwindConfigPath = "./src/styles/tailwind.config.ts";
export const postcssConfigPath = "./src/styles/postcss.config.mjs";
