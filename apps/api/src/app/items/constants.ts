/** API-PUB-003 商品詳細取得の定数（契約・実装仕様書準拠）。 */

export const ITEM_DETAIL_PATH = "/api/v1/items/:itemId" as const;

export const ITEM_DETAIL_METRICS = {
  REQUEST_COUNT: "item_detail_request_count",
  NOT_FOUND_COUNT: "item_not_found_count",
} as const;

export const ITEM_DETAIL_ERROR_CODES = {
  INVALID_REQUEST: "GRS-REQ-001",
  NOT_FOUND: "GRS-ITM-001",
  INACTIVE: "GRS-ITM-002",
  DB_UNAVAILABLE: "GRS-DB-001",
  DB_QUERY_FAILED: "GRS-DB-002",
  UNEXPECTED: "GRS-ITM-999",
  COMMON_UNEXPECTED: "GRS-COM-999",
} as const;

export const ITEM_DETAIL_ERROR_MESSAGES = {
  INVALID_REQUEST: "条件を確認してください。",
  NOT_FOUND: "商品情報が見つかりません。",
  INACTIVE: "この商品は現在表示できません。",
  DB_UNAVAILABLE: "データ処理に失敗しました。",
  DB_QUERY_FAILED: "データ取得に失敗しました。",
  UNEXPECTED: "商品情報の取得に失敗しました。",
  COMMON_UNEXPECTED:
    "予期しないエラーが発生しました。時間を置いて再度お試しください。",
} as const;

/** OpenAPI ItemIdPath と同一。 */
export const ITEM_ID_MAX_LENGTH = 64;
export const ITEM_ID_PATTERN = /^[A-Za-z0-9_-]+$/;

/** MVP 固定: popularityBadge ラベル。 */
export const POPULARITY_BADGE_LABEL = "ランキング入り" as const;

/** 最新 Snapshot 解決用（item_popularity_signal テーブル定義書 §5.7）。 */
export const POPULARITY_SNAPSHOT_SOURCE = "rakuten" as const;
export const POPULARITY_SNAPSHOT_PERIOD = "daily" as const;
