import { colorTokens } from "../tokens/colors.js";
import { radiiTokens } from "../tokens/radii.js";
import { spacingTokens } from "../tokens/spacing.js";

/** デザイントークンを :root 用 CSS 変数へ展開する */
export function buildCssVariables(): Record<string, string> {
  return {
    ...colorTokens,
    ...spacingTokens,
    ...radiiTokens,
  };
}

/** globals.css 生成用の :root ブロック文字列 */
export function buildCssVariablesBlock(): string {
  const variables = buildCssVariables();
  const lines = Object.entries(variables).map(
    ([name, value]) => `  --${name}: ${value};`,
  );
  return `:root {\n${lines.join("\n")}\n}`;
}
