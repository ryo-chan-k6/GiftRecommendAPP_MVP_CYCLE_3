/** API-PUB-006 Occasion マスタ取得の公開エラーコード・メッセージ。 */
export const OCCASION_MASTERS_ERROR_CODES = {
  DB_READ_FAILED: "GRS-DB-002",
  CONFIG_UNRESOLVED: "GRS-CFG-005",
  UNEXPECTED: "GRS-COM-999",
} as const;

export const OCCASION_MASTERS_ERROR_MESSAGES = {
  DB_READ_FAILED: "データ取得に失敗しました。",
  CONFIG_UNRESOLVED: "選択項目の取得に失敗しました。",
  UNEXPECTED: "予期しないエラーが発生しました。",
} as const;

export const OCCASION_MASTERS_METRICS = {
  REQUEST_COUNT: "masters_occasions_request_count",
  ERROR_COUNT: "masters_occasions_error_count",
} as const;

export const OCCASION_MASTERS_PATH = "/api/v1/masters/occasions" as const;
