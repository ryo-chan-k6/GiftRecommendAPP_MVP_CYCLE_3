/**
 * 角丸・影・枠線トークン（正本: デザインルール.md §4.4）
 */
export const radiiTokens = {
  "radius-sm": "2px",
  "radius-md": "8px",
  "radius-lg": "12px",
  "shadow-sm": "0 4px 24px rgba(42, 31, 24, 0.08)",
  "shadow-md": "0 8px 40px rgba(42, 31, 24, 0.12)",
  "border-width": "1px",
} as const;

export type RadiiTokenName = keyof typeof radiiTokens;
