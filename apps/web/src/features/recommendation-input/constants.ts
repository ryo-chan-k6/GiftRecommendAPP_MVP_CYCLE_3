export const DEFAULT_TOP_K = 10;
export const DEFAULT_CANDIDATE_LIMIT = 50;

export const PREFERRED_TEXT_MAX = 500;
export const NON_PREFERRED_TEXT_MAX = 500;
export const NG_TEXT_MAX = 300;

/** クエリパラメータキー（短い条件の復元用） */
export const QUERY_KEYS = {
  relationshipCode: "relationshipCode",
  occasionCode: "occasionCode",
  budgetMin: "budgetMin",
  budgetMax: "budgetMax",
  topK: "topK",
} as const;

/** sessionStorage キー（長い自由記述の復元用） */
export const SESSION_KEYS = {
  preferredText: "scr002:preferredText",
  nonPreferredText: "scr002:nonPreferredText",
  ngText: "scr002:ngText",
  /** 実行結果の一時保管（SCR-004 未実装時の受け渡し） */
  lastResultPrefix: "scr002:lastResult:",
} as const;

export const VALIDATION_MESSAGES = {
  relationshipRequired: "贈る相手を選択してください。",
  occasionRequired: "用途を選択してください。",
  budgetMaxRequired: "予算の上限を入力してください。",
  budgetInvalid: "予算は0以上の数値で入力してください。",
  budgetRange: "予算の下限と上限を確認してください。",
  textTooLong: "入力文字数を短くしてください。",
  masterCodeInvalid: "選択項目を確認してください。",
} as const;

export const MASTERS_ERROR_MESSAGE = "選択項目の取得に失敗しました。";
export const MASTERS_EMPTY_MESSAGE =
  "選択肢がありません。しばらくしてから再度お試しください。";
export const RUNNING_MESSAGE = "条件に合うギフトを探しています";
export const EMPTY_RESULT_MESSAGE =
  "条件に合うギフトが見つかりませんでした。条件を変えて再度お試しください。";
/** SCR-008: 推薦実行失敗時の汎用メッセージ（ErrorResponse.message 欠落時） */
export const RUN_ERROR_FALLBACK_MESSAGE =
  "レコメンド実行に失敗しました。条件を変えて再度お試しください。";

/** SCR-008: PageLayout タイトル */
export const RUN_ERROR_PAGE_TITLE = "エラー";

/** SCR-008: Alert タイトル */
export const RUN_ERROR_ALERT_TITLE = "レコメンド実行に失敗しました";

/** SCR-008: 条件入力へ戻る */
export const RUN_ERROR_BACK_LABEL = "条件入力へ戻る";

/** SCR-008: 再実行（画面仕様 §6.2 は Human Review 採否待ちの提案。現状実装を維持） */
export const RUN_ERROR_RETRY_LABEL = "再実行";
