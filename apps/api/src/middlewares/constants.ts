/**
 * Phase4a api-foundation middleware で参照する GRS コード定数。
 * 詳細な error response 組み立ては common-error-response Task（A4）で lib へ集約予定。
 */
export const SCAFFOLD_ERROR_CODES = {
  VALIDATION: "GRS-VAL-001",
  UNEXPECTED: "GRS-COM-999",
} as const;

export const DEFAULT_VALIDATION_MESSAGE = "入力内容を確認してください。";
export const DEFAULT_UNEXPECTED_MESSAGE =
  "一時的な問題が発生しました。時間をおいて再度お試しください。";

export const DEFAULT_CORS_ORIGIN = "http://localhost:3000";
