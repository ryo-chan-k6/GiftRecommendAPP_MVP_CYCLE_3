import { afterEach, describe, expect, it, vi } from "vitest";

import { resolveRecommendationContext } from "@/features/item-detail/resolve-recommendation-context";
import type { StoredRecommendationResult } from "@/features/recommendation-input/types";

const readRecommendationResult = vi.fn();

vi.mock("@/features/recommendation-input/form-persistence", () => ({
  readRecommendationResult: (...args: unknown[]) =>
    readRecommendationResult(...args),
}));

function sampleResult(
  overrides?: Partial<StoredRecommendationResult>,
): StoredRecommendationResult {
  return {
    recommendationResultId: "result-1",
    recommendationRequestId: "req-1",
    recommendationRunId: "run-1",
    resultStatus: "succeeded",
    topK: 3,
    resultItemCount: 1,
    fallbackUsed: false,
    items: [
      {
        recommendationResultItemId: "ri-1",
        itemId: "item-1",
        rank: 1,
        itemName: "サンプル",
        itemPrice: 1000,
        itemUrl: "https://example.invalid/1",
        reasonSummary: "理由です",
      },
    ],
    ...overrides,
  };
}

describe("resolveRecommendationContext", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("returns null when fromResultId is missing", () => {
    expect(resolveRecommendationContext("item-1", null)).toBeNull();
    expect(readRecommendationResult).not.toHaveBeenCalled();
  });

  it("returns matching item from sessionStorage", () => {
    readRecommendationResult.mockReturnValue(sampleResult());
    const item = resolveRecommendationContext("item-1", "result-1");
    expect(item?.rank).toBe(1);
    expect(item?.reasonSummary).toBe("理由です");
  });

  it("returns null when itemId is not in stored items", () => {
    readRecommendationResult.mockReturnValue(sampleResult());
    expect(resolveRecommendationContext("missing", "result-1")).toBeNull();
  });
});
