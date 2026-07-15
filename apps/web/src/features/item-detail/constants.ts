/** SCR-006 商品詳細向けの表示文言 */

export const PAGE_TITLE = "商品詳細";

export const LOADING_MESSAGE = "読み込み中…";

export const BACK_TO_RESULT_LABEL = "結果一覧へ戻る";

export const BACK_TO_INPUT_LABEL = "条件入力へ戻る";

export const INPUT_HREF = "/recommendations";

export const EXTERNAL_EC_LABEL = "外部ECで見る";

export const REASON_DETAIL_LABEL = "推薦理由詳細";

export const REASON_DETAIL_DISABLED_HINT = "準備中";

export const FEEDBACK_LABEL = "Feedback";

export const FEEDBACK_DISABLED_HINT = "準備中";

export const RETRY_LABEL = "再試行";

export const FALLBACK_REASON_HINT = "一般的な推薦理由を表示しています";

export const DESCRIPTION_TOGGLE_CLOSED = "説明をすべて表示";

export const DESCRIPTION_TOGGLE_OPEN = "説明を閉じる";

/** 商品説明の折りたたみ閾値（画面仕様 §22.1） */
export const DESCRIPTION_COLLAPSE_THRESHOLD = 400;

export const ERROR_TITLE_NOT_FOUND = "商品情報が見つかりません";

export const ERROR_MESSAGE_NOT_FOUND =
  "商品情報が見つかりません。結果一覧または条件入力へお戻りください。";

export const ERROR_TITLE_INACTIVE = "表示できません";

export const ERROR_MESSAGE_INACTIVE =
  "この商品は現在表示できません。";

export const ERROR_TITLE_BAD_REQUEST = "条件を確認してください";

export const ERROR_MESSAGE_BAD_REQUEST =
  "条件を確認してください。";

export const ERROR_TITLE_FETCH = "データ取得に失敗しました";

export const ERROR_MESSAGE_FETCH =
  "データ取得に失敗しました。時間をおいて再試行するか、戻ってください。";

export function buildResultListHref(fromResultId: string): string {
  return `/recommendations/${encodeURIComponent(fromResultId)}`;
}
