import {
  FeedbackType,
  type FeedbackType as FeedbackTypeValue,
} from "@/generated/api/giftRecommendationServicePublicAPI.schemas";

export type FeedbackOption = {
  feedbackType: FeedbackTypeValue;
  label: string;
  rating: number;
};

/** 画面仕様書 §9.1 MVP item 粒度 */
export const ITEM_FEEDBACK_OPTIONS: FeedbackOption[] = [
  { feedbackType: FeedbackType.item_good, label: "良い", rating: 5 },
  { feedbackType: FeedbackType.item_bad, label: "微妙", rating: 2 },
  {
    feedbackType: FeedbackType.item_not_match,
    label: "贈答文脈に合わない",
    rating: 2,
  },
  {
    feedbackType: FeedbackType.item_ng_violation,
    label: "NG条件に反する",
    rating: 1,
  },
  {
    feedbackType: FeedbackType.item_avoid_match,
    label: "避けたい条件に近い",
    rating: 2,
  },
];

export function findItemFeedbackOption(
  feedbackType: FeedbackTypeValue,
): FeedbackOption | undefined {
  return ITEM_FEEDBACK_OPTIONS.find(
    (option) => option.feedbackType === feedbackType,
  );
}
