/**
 * スペーシングトークン（正本: デザインルール.md §4.3 / 4px ベース）
 */
export const spacingTokens = {
  "space-1": "4px",
  "space-2": "8px",
  "space-3": "12px",
  "space-4": "16px",
  "space-6": "24px",
  "space-8": "32px",
  "space-12": "48px",
  "space-16": "64px",
} as const;

export type SpacingTokenName = keyof typeof spacingTokens;
