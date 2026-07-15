import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { storeRecommendationResult } from "@/features/recommendation-input/form-persistence";
import { RecommendationResultPage } from "@/features/recommendation-result/RecommendationResultPage";
import { ResultStatus } from "@/generated/api/giftRecommendationServicePublicAPI.schemas";

const useParamsMock = vi.fn();

vi.mock("next/navigation", () => ({
  useParams: () => useParamsMock(),
}));

describe("RecommendationResultPage (SCR-004)", () => {
  beforeEach(() => {
    sessionStorage.clear();
    useParamsMock.mockReturnValue({ resultId: "result-1" });
  });

  afterEach(() => {
    sessionStorage.clear();
    vi.clearAllMocks();
  });

  it("shows missing alert when sessionStorage has no result", async () => {
    render(<RecommendationResultPage />);

    await waitFor(() => {
      expect(screen.getByText("結果データがありません")).toBeInTheDocument();
    });
    expect(
      screen.getByRole("button", { name: "条件入力へ戻る" }),
    ).toBeInTheDocument();
  });

  it("shows missing alert when stored resultId mismatches route", async () => {
    storeRecommendationResult({
      recommendationResultId: "other-id",
      recommendationRequestId: "req-1",
      recommendationRunId: "run-1",
      resultStatus: ResultStatus.completed,
      topK: 10,
      resultItemCount: 1,
      fallbackUsed: false,
      items: [
        {
          recommendationResultItemId: "rii-1",
          itemId: "item-1",
          rank: 1,
          itemName: "別結果の商品",
          itemPrice: 1000,
          itemUrl: "https://example.com/a",
        },
      ],
    });

    render(<RecommendationResultPage />);

    await waitFor(() => {
      expect(screen.getByText("結果データがありません")).toBeInTheDocument();
    });
    expect(screen.queryByText("別結果の商品")).not.toBeInTheDocument();
  });

  it("renders stored items sorted by rank", async () => {
    storeRecommendationResult({
      recommendationResultId: "result-1",
      recommendationRequestId: "req-1",
      recommendationRunId: "run-1",
      resultStatus: ResultStatus.completed,
      topK: 10,
      resultItemCount: 2,
      fallbackUsed: false,
      displayMessage: "補足メッセージ",
      items: [
        {
          recommendationResultItemId: "rii-2",
          itemId: "item-2",
          rank: 2,
          itemName: "二位の商品",
          itemPrice: 2000,
          itemUrl: "https://example.com/2",
        },
        {
          recommendationResultItemId: "rii-1",
          itemId: "item-1",
          rank: 1,
          itemName: "一位の商品",
          itemPrice: 1000,
          itemUrl: "https://example.com/1",
          reasonSummary: "理由A",
        },
      ],
    });

    render(<RecommendationResultPage />);

    await waitFor(() => {
      expect(screen.getByText("一位の商品")).toBeInTheDocument();
    });
    expect(screen.getByText("二位の商品")).toBeInTheDocument();
    expect(screen.getByText("条件を変更して再検索")).toBeInTheDocument();
    expect(screen.getByText("補足メッセージ")).toBeInTheDocument();

    const names = screen.getAllByRole("heading", { level: 2 }).map((el) =>
      el.textContent,
    );
    expect(names[0]).toBe("一位の商品");
    expect(names[1]).toBe("二位の商品");
  });
});
