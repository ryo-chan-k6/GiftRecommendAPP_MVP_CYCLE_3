/** SCR-007 Feedback入力向けの表示文言 */

export const MODAL_TITLE = "Feedback";

export const PROMPT_TEXT = "この候補についてどう感じましたか？";

export const COMMENT_LABEL = "コメント（任意）";

export const COMMENT_PLACEHOLDER = "気になった点があれば記入してください";

export const SUBMIT_LABEL = "送信";

export const CANCEL_LABEL = "キャンセル";

export const RETRY_LABEL = "再試行";

export const SUCCESS_FALLBACK_MESSAGE = "フィードバックを受け付けました。";

export const SELECT_HINT = "評価を選択してください";

export const COMMENT_TOO_LONG = "コメントは500文字以内で入力してください";

export const FEEDBACK_UNAVAILABLE_HINT =
  "結果一覧から開くと送信できます";

export const ERROR_TITLE_VALIDATION = "入力内容を確認してください";

export const ERROR_MESSAGE_VALIDATION =
  "入力内容を確認してください。";

export const ERROR_TITLE_NOT_FOUND = "対象が見つかりません";

export const ERROR_MESSAGE_NOT_FOUND =
  "対象の推薦結果が見つかりません。";

export const ERROR_TITLE_FETCH = "送信に失敗しました";

export const ERROR_MESSAGE_FETCH =
  "Feedbackを送信できませんでした。時間をおいて再試行するか、閉じてください。";

export const COMMENT_MAX_LENGTH = 500;

export const SUCCESS_AUTO_CLOSE_MS = 1500;

export const SESSION_STORAGE_KEY = "grs.feedback.sessionId";
