/** API-PUB-005 Relationship マスタ取得の定数。 */

export const MASTERS_RELATIONSHIPS_PATH =
  "/api/v1/masters/relationships" as const;

export const MASTERS_RELATIONSHIPS_METRICS = {
  REQUEST_COUNT: "masters_relationships_request_count",
  ERROR_COUNT: "masters_relationships_error_count",
} as const;

export const MASTERS_RELATIONSHIPS_ERROR_CODES = {
  DB_READ_FAILED: "GRS-DB-002",
  MASTER_CONFIG_UNRESOLVED: "GRS-CFG-005",
  UNEXPECTED: "GRS-COM-999",
} as const;

export const MASTERS_RELATIONSHIPS_ERROR_MESSAGES = {
  DB_READ_FAILED: "データ取得に失敗しました。",
  MASTER_CONFIG_UNRESOLVED: "選択項目の取得に失敗しました。",
  UNEXPECTED:
    "予期しないエラーが発生しました。時間を置いて再度お試しください。",
} as const;
