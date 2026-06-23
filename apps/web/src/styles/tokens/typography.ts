/**
 * タイポグラフィトークン（正本: デザインルール.md §4.2）
 */
export const typographyTokens = {
  "text-display": { fontSize: "1.875rem", fontWeight: 600, lineHeight: 1.3 },
  "text-h1": { fontSize: "1.5rem", fontWeight: 600, lineHeight: 1.35 },
  "text-h2": { fontSize: "1.25rem", fontWeight: 600, lineHeight: 1.4 },
  "text-h3": { fontSize: "1.125rem", fontWeight: 600, lineHeight: 1.45 },
  "text-body": { fontSize: "1rem", fontWeight: 400, lineHeight: 1.8 },
  "text-small": { fontSize: "0.875rem", fontWeight: 400, lineHeight: 1.5 },
  "text-label": { fontSize: "0.875rem", fontWeight: 500, lineHeight: 1.4 },
} as const;

export type TypographyTokenName = keyof typeof typographyTokens;
