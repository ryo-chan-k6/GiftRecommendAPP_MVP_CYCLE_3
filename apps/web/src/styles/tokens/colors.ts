/**
 * セマンティックカラートークン（正本: デザインルール.md §4.1 / GiftRecommendAPP_LP :root）
 */
export const colorTokens = {
  "color-bg": "#FAF7F2",
  "color-surface": "#FFFFFF",
  "color-surface-muted": "#F2EDE3",
  "color-text": "#2A1F18",
  "color-text-secondary": "#8B6F5E",
  "color-text-muted": "#9A8F86",
  "color-primary": "#4A3728",
  "color-primary-hover": "#2A1F18",
  "color-on-primary": "#FAF7F2",
  "color-accent": "#C9A96E",
  "color-accent-light": "#E8D5B0",
  "color-border": "#D4CFC8",
  "color-success": "#7A8C6E",
  "color-warning": "#C9A96E",
  "color-error": "#C4857A",
  "color-focus": "#C9A96E",
} as const;

export type ColorTokenName = keyof typeof colorTokens;
