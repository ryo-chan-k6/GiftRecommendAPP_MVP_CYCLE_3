import { readRecommendationResult } from "@/features/recommendation-input/form-persistence";
import type { PublicRecommendationResultItem } from "@/generated/api/giftRecommendationServicePublicAPI.schemas";

/**
 * fromResultId + sessionStorage から、route itemId と一致する推薦文脈を取得する。
 * 欠落・不一致時は null（invent しない / エラーにしない）。
 */
export function resolveRecommendationContext(
  itemId: string,
  fromResultId: string | null | undefined,
): PublicRecommendationResultItem | null {
  if (!fromResultId || !itemId) {
    return null;
  }
  const stored = readRecommendationResult(fromResultId);
  if (!stored || stored.recommendationResultId !== fromResultId) {
    return null;
  }
  return stored.items.find((item) => item.itemId === itemId) ?? null;
}
