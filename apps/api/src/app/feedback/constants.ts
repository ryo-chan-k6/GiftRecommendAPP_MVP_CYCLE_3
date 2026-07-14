/** API-PUB-004 Feedback 送信の定数（契約仕様書・実装仕様書準拠）。 */

export const FEEDBACK_SUBMIT_PATH =
  "/api/v1/recommendation-results/:resultId/feedback" as const;

export const FEEDBACK_METRICS = {
  COUNT: "feedback_count",
  ERROR_COUNT: "feedback_error_count",
  POSITIVE_COUNT: "positive_feedback_count",
  NEGATIVE_COUNT: "negative_feedback_count",
} as const;

export const FEEDBACK_ERROR_CODES = {
  INVALID_CONTENT: "GRS-FDB-001",
  TARGET_NOT_FOUND: "GRS-FDB-002",
  COMMENT_TOO_LONG: "GRS-FDB-004",
  SAVE_FAILED: "GRS-FDB-005",
  UNEXPECTED: "GRS-FDB-999",
  INVALID_REQUEST: "GRS-REQ-001",
  DB_QUERY_FAILED: "GRS-DB-001",
} as const;

export const FEEDBACK_ERROR_MESSAGES = {
  INVALID_CONTENT: "フィードバック内容を確認してください。",
  TARGET_NOT_FOUND: "対象の推薦結果が見つかりません。",
  COMMENT_TOO_LONG: "コメントを短くしてください。",
  SAVE_FAILED:
    "フィードバックの送信に失敗しました。時間を置いて再度お試しください。",
  UNEXPECTED: "フィードバック処理でエラーが発生しました。",
  INVALID_REQUEST: "条件を確認してください。",
  DB_QUERY_FAILED: "データ処理に失敗しました。",
} as const;

export const FEEDBACK_SUCCESS_MESSAGES = {
  ACCEPTED: "フィードバックを受け付けました。",
  UPDATED: "フィードバックを更新しました。",
} as const;

export const FEEDBACK_TARGET_TYPES = ["result", "item", "reason"] as const;

export const FEEDBACK_TYPES = [
  "item_good",
  "item_bad",
  "item_not_match",
  "item_ng_violation",
  "item_avoid_match",
  "reason_good",
  "reason_bad",
  "result_good",
  "result_bad",
  "comment",
] as const;

export const FEEDBACK_VALUE_TYPES = [
  "boolean",
  "rating",
  "choice",
  "text",
  "event",
] as const;

export const MAX_COMMENT_LENGTH = 500;
export const MAX_USER_AGENT_LENGTH = 500;

/** feedbackType ごとに許容する feedbackTargetType。comment は任意粒度。 */
export const FEEDBACK_TYPE_ALLOWED_TARGETS: Record<
  (typeof FEEDBACK_TYPES)[number],
  readonly (typeof FEEDBACK_TARGET_TYPES)[number][] | "any"
> = {
  item_good: ["item"],
  item_bad: ["item"],
  item_not_match: ["item"],
  item_ng_violation: ["item"],
  item_avoid_match: ["item"],
  reason_good: ["reason"],
  reason_bad: ["reason"],
  result_good: ["result"],
  result_bad: ["result"],
  comment: "any",
};
