/** SCR-004 結果一覧向けの表示文言 */

export const PAGE_TITLE = "おすすめのギフト";

export const LOADING_MESSAGE = "読み込み中…";

export const MISSING_RESULT_TITLE = "結果データがありません";

export const MISSING_RESULT_MESSAGE =
  "sessionStorage に結果が見つかりませんでした。条件入力から再度実行してください。";

export const RESEARCH_LABEL = "条件を変更して再検索";

export const BACK_TO_INPUT_LABEL = "条件入力へ戻る";

export const FEEDBACK_LABEL = "Feedback";

export const DETAIL_TOGGLE_CLOSED = "▶ 理由の詳細";

export const DETAIL_TOGGLE_OPEN = "▼ 理由の詳細";

export const DETAIL_EMPTY_GUIDE =
  "詳細な説明文はありません。カード上の要約・バッジをご確認ください。";

export const FALLBACK_REASON_HINT = "一般的な推薦理由を表示しています";

export const ITEM_DETAIL_LABEL = "商品詳細";

export const EXTERNAL_EC_LABEL = "外部ECで見る";

export const RESEARCH_HREF = "/recommendations";

/** SCR-006 MVP スタブ。`fromResultId` は一覧へ戻るために付与する */
export function buildItemDetailHref(
  itemId: string,
  resultId: string,
): string {
  const params = new URLSearchParams({ fromResultId: resultId });
  return `/items/${encodeURIComponent(itemId)}?${params.toString()}`;
}

/** SCR-005 展開領域の高さ上限（画面仕様 §7.4 / §22.1） */
export const REASON_DETAIL_MAX_HEIGHT_CLASS = "max-h-[12rem]";
