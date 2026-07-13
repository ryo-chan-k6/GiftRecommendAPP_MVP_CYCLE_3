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

/** API-PUB-007 Semantic 設定取得の公開エラーコード・メッセージ。 */
export const SEMANTIC_CONFIG_MASTERS_ERROR_CODES = {
  INVALID_REQUEST: "GRS-REQ-001",
  CURRENT_NOT_FOUND: "GRS-CFG-001",
  RESOLVE_FAILED: "GRS-CFG-002",
  FEATURE_MISSING: "GRS-CFG-006",
  DB_READ_FAILED: "GRS-DB-002",
  UNEXPECTED: "GRS-COM-999",
} as const;

export const SEMANTIC_CONFIG_MASTERS_ERROR_MESSAGES = {
  INVALID_REQUEST: "条件を確認してください。",
  CURRENT_NOT_FOUND: "選択項目の取得に失敗しました。",
  RESOLVE_FAILED: "選択項目の取得に失敗しました。",
  FEATURE_MISSING: "選択項目の取得に失敗しました。",
  DB_READ_FAILED: "データ取得に失敗しました。",
  UNEXPECTED: "予期しないエラーが発生しました。",
} as const;

export const SEMANTIC_CONFIG_MASTERS_METRICS = {
  REQUEST_COUNT: "masters_semantic_configs_request_count",
  ERROR_COUNT: "masters_semantic_configs_error_count",
} as const;

export const SEMANTIC_CONFIG_MASTERS_PATH =
  "/api/v1/masters/semantic-configs" as const;

/** API-PUB-008 Feature ルール取得の公開エラーコード・メッセージ。 */
export const FEATURE_RULE_MASTERS_ERROR_CODES = {
  INVALID_REQUEST: "GRS-REQ-001",
  CURRENT_NOT_FOUND: "GRS-CFG-001",
  RESOLVE_FAILED: "GRS-CFG-002",
  CONFIG_UNRESOLVED: "GRS-CFG-005",
  DB_READ_FAILED: "GRS-DB-002",
  UNEXPECTED: "GRS-COM-999",
} as const;

export const FEATURE_RULE_MASTERS_ERROR_MESSAGES = {
  INVALID_REQUEST: "条件を確認してください。",
  CURRENT_NOT_FOUND: "選択項目の取得に失敗しました。",
  RESOLVE_FAILED: "選択項目の取得に失敗しました。",
  CONFIG_UNRESOLVED: "選択項目の取得に失敗しました。",
  DB_READ_FAILED: "データ取得に失敗しました。",
  UNEXPECTED: "予期しないエラーが発生しました。",
} as const;

export const FEATURE_RULE_MASTERS_METRICS = {
  REQUEST_COUNT: "masters_feature_rules_request_count",
  ERROR_COUNT: "masters_feature_rules_error_count",
} as const;

export const FEATURE_RULE_MASTERS_PATH =
  "/api/v1/masters/feature-rules" as const;
