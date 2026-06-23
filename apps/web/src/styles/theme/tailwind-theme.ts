import type { Config } from "tailwindcss";

import { colorTokens } from "../tokens/colors.js";
import { radiiTokens } from "../tokens/radii.js";
import { spacingTokens } from "../tokens/spacing.js";
import { typographyTokens } from "../tokens/typography.js";
import { fontFamilyStacks } from "../fonts.js";

const tailwindColors = Object.fromEntries(
  Object.keys(colorTokens).map((token) => [
    token.replace(/^color-/, ""),
    `var(--${token})`,
  ]),
);

const tailwindSpacing = Object.fromEntries(
  Object.entries(spacingTokens).map(([token, value]) => [
    token.replace(/^space-/, ""),
    value,
  ]),
);

const tailwindFontSize = Object.fromEntries(
  Object.entries(typographyTokens).map(([token, spec]) => [
    token.replace(/^text-/, ""),
    [
      spec.fontSize,
      {
        lineHeight: String(spec.lineHeight),
        fontWeight: spec.fontWeight,
      },
    ] as [string, { lineHeight: string; fontWeight: number }],
  ]),
);

/** Tailwind theme.extend（正本トークンを CSS 変数経由で参照） */
export const tailwindThemeExtend = {
  colors: tailwindColors,
  spacing: tailwindSpacing,
  fontSize: tailwindFontSize,
  fontFamily: {
    body: [...fontFamilyStacks.body],
    heading: [...fontFamilyStacks.heading],
  },
  borderRadius: {
    sm: radiiTokens["radius-sm"],
    md: radiiTokens["radius-md"],
    lg: radiiTokens["radius-lg"],
  },
  boxShadow: {
    sm: radiiTokens["shadow-sm"],
    md: radiiTokens["shadow-md"],
  },
  borderWidth: {
    DEFAULT: radiiTokens["border-width"],
  },
} satisfies NonNullable<Config["theme"]>["extend"];
