import { test } from "node:test";
import assert from "node:assert/strict";

import { colorTokens } from "./tokens/colors.js";
import { buildCssVariables } from "./theme/css-variables.js";
import { tailwindThemeExtend } from "./theme/tailwind-theme.js";

test("colorTokens includes LP primary color from design rules", () => {
  assert.equal(colorTokens["color-primary"], "#4A3728");
  assert.equal(colorTokens["color-bg"], "#FAF7F2");
});

test("buildCssVariables exposes semantic token names as CSS variable keys", () => {
  const variables = buildCssVariables();

  assert.equal(variables["color-primary"], "#4A3728");
  assert.equal(variables["space-4"], "16px");
  assert.equal(variables["radius-md"], "8px");
});

test("tailwindThemeExtend maps primary color to CSS variable reference", () => {
  const colors = tailwindThemeExtend?.colors as Record<string, string>;

  assert.equal(colors.primary, "var(--color-primary)");
  assert.equal(colors.bg, "var(--color-bg)");
});
