/** API-PUB-002 Public Error / Result コード（契約仕様書・エラーコード定義書準拠）。 */

export const PUBLIC_ERROR_CODES = {
  INVALID_CONDITION: "GRS-REQ-001",
  RELATIONSHIP_REQUIRED: "GRS-REQ-004",
  OCCASION_REQUIRED: "GRS-REQ-005",
  REQUEST_SAVE_FAILED: "GRS-REQ-999",
  RECOMMENDATION_FAILED: "GRS-REC-002",
  RECO_TIMEOUT: "GRS-REC-101",
  NO_CANDIDATES: "GRS-REC-001",
} as const;

export const PUBLIC_ERROR_MESSAGES = {
  INVALID_CONDITION: "条件を確認してください。",
  RELATIONSHIP_REQUIRED: "贈る相手を選択してください。",
  OCCASION_REQUIRED: "ギフトの用途を選択してください。",
  REQUEST_SAVE_FAILED:
    "推薦条件の保存に失敗しました。時間を置いて再度お試しください。",
  RECOMMENDATION_FAILED:
    "レコメンド処理に失敗しました。時間を置いて再度お試しください。",
  RECO_TIMEOUT:
    "レコメンド処理に時間がかかっています。時間を置いて再度お試しください。",
} as const;

export const EMPTY_RESULT_DISPLAY_MESSAGE =
  "条件に合う商品が見つかりませんでした。条件を変更して再度お試しください。";

export const DEFAULT_EXECUTION = {
  mode: "ui" as const,
  topK: 10,
  candidateLimit: 50,
  includeReason: true,
  includeDebugInfo: false,
  currency: "JPY",
};
