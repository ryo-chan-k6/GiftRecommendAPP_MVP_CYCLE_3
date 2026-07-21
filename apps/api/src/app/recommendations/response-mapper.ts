import type { RecoRecommendationRunResult } from "../../infrastructure/reco-client/types.js";
import {
  EMPTY_RESULT_DISPLAY_MESSAGE,
  PUBLIC_ERROR_CODES,
} from "./constants.js";
import type {
  PublicRecommendationResultItem,
  RecommendationRunResponseData,
  RecommendationRunSuccessResponse,
} from "./types.js";

function mapResultItem(
  item: Record<string, unknown>,
): PublicRecommendationResultItem {
  const mapped: PublicRecommendationResultItem = {
    recommendationResultItemId: String(item.recommendationResultItemId),
    itemId: String(item.itemId),
    rank: Number(item.rank),
    itemName: String(item.itemName),
    itemPrice: Number(item.itemPrice),
    itemUrl: String(item.itemUrl),
  };

  if (typeof item.itemImageUrl === "string") {
    mapped.itemImageUrl = item.itemImageUrl;
  }
  if (typeof item.itemCatchcopy === "string") {
    mapped.itemCatchcopy = item.itemCatchcopy;
  }
  if (typeof item.shopName === "string") {
    mapped.shopName = item.shopName;
  }
  if (typeof item.reasonSummary === "string") {
    mapped.reasonSummary = item.reasonSummary;
  }
  if (
    Array.isArray(item.reasonPoints) &&
    item.reasonPoints.every((point) => typeof point === "string")
  ) {
    mapped.reasonPoints = item.reasonPoints as string[];
  }
  if (typeof item.reasonDetail === "string") {
    mapped.reasonDetail = item.reasonDetail;
  }
  if (Array.isArray(item.reasonBadges)) {
    mapped.reasonBadges =
      item.reasonBadges as PublicRecommendationResultItem["reasonBadges"];
  }
  if (typeof item.cautionNote === "string") {
    mapped.cautionNote = item.cautionNote;
  }
  if (typeof item.isFallback === "boolean") {
    mapped.isFallback = item.isFallback;
  }

  return mapped;
}

function resolvePublicResultStatus(
  itemCount: number,
  internalStatus?: string,
): RecommendationRunResponseData["resultStatus"] {
  if (itemCount === 0) {
    return "empty";
  }

  if (internalStatus === "partial") {
    return "partial";
  }

  return "completed";
}

/** MOD-API-006: Internal Result → Public data / meta（スコア系・debug 除外）。 */
export function mapRecoResultToPublicResponse(input: {
  recoResult: RecoRecommendationRunResult;
  recommendationRequestId: string;
  traceId: string;
  requestId: string;
  topK: number;
  fallbackUsed?: boolean;
  displayMessage?: string;
  generatedAt?: string;
}): RecommendationRunSuccessResponse {
  const items = input.recoResult.items.map((item) => mapResultItem(item));
  const resultItemCount =
    input.recoResult.resultItemCount ?? items.length;
  const resultStatus = resolvePublicResultStatus(
    resultItemCount,
    input.recoResult.resultStatus,
  );
  const isEmpty = resultStatus === "empty";
  const fallbackUsed =
    input.fallbackUsed ??
    items.some((item) => item.isFallback === true);

  const data: RecommendationRunResponseData = {
    recommendationResultId: input.recoResult.recommendationResultId,
    recommendationRequestId: input.recommendationRequestId,
    recommendationRunId: input.recoResult.recommendationRunId,
    resultStatus,
    topK: input.topK,
    resultItemCount,
    fallbackUsed,
    items,
  };

  if (isEmpty) {
    data.displayMessage = EMPTY_RESULT_DISPLAY_MESSAGE;
  } else if (input.displayMessage !== undefined) {
    data.displayMessage = input.displayMessage;
  }

  const meta = {
    traceId: input.traceId,
    requestId: input.requestId,
    generatedAt: input.generatedAt ?? new Date().toISOString(),
    ...(isEmpty ? { resultCode: PUBLIC_ERROR_CODES.NO_CANDIDATES } : {}),
  };

  return { data, meta };
}

export { mapResultItem as mapPublicRecommendationResultItemForTest };
