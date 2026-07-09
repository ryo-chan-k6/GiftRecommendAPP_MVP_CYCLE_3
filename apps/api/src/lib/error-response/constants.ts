/**
 * Phase4a api-foundation で参照する GRS コード定数。
 * 正本: エラーコード定義書 / Phase4a packages/code-definitions（将来）。
 */
export const SCAFFOLD_ERROR_CODES = {
  VALIDATION: "GRS-VAL-001",
  UNEXPECTED: "GRS-COM-999",
} as const;

export const DEFAULT_VALIDATION_MESSAGE = "入力内容を確認してください。";
export const DEFAULT_UNEXPECTED_MESSAGE =
  "一時的な問題が発生しました。時間をおいて再度お試しください。";
