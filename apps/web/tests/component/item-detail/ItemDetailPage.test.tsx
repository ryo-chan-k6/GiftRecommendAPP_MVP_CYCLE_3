import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ItemDetailPage } from "@/features/item-detail/ItemDetailPage";
import type { PublicItemDetail } from "@/generated/api/giftRecommendationServicePublicAPI.schemas";

const fetchItemDetail = vi.fn();
const resolveRecommendationContext = vi.fn();

const navigationState = {
  itemId: "item-1",
  search: "fromResultId=result-1",
};

vi.mock("next/navigation", () => ({
  useParams: () => ({ itemId: navigationState.itemId }),
  useSearchParams: () => new URLSearchParams(navigationState.search),
}));

vi.mock("@/lib/api", () => ({
  fetchItemDetail: (...args: unknown[]) => fetchItemDetail(...args),
}));

vi.mock("@/features/item-detail/resolve-recommendation-context", () => ({
  resolveRecommendationContext: (...args: unknown[]) =>
    resolveRecommendationContext(...args),
}));

const sampleItem: PublicItemDetail = {
  itemId: "item-1",
  itemName: "上品な焼き菓子ギフトセット",
  itemPrice: 4320,
  itemUrl: "https://example.invalid/item/001",
  itemCatchcopy: "贈答向け",
  itemDescription: "説明文です。",
  genreName: "スイーツ",
  shopName: "非表示ショップ",
  isActive: true,
};

function successResponse(item: PublicItemDetail) {
  return {
    status: 200 as const,
    headers: new Headers(),
    data: {
      data: item,
      meta: { requestId: "req-1", traceId: "trace-1" },
    },
  };
}

describe("ItemDetailPage", () => {
  beforeEach(() => {
    navigationState.itemId = "item-1";
    navigationState.search = "fromResultId=result-1";
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders item detail on PUB-003 success", async () => {
    fetchItemDetail.mockResolvedValue(successResponse(sampleItem));
    resolveRecommendationContext.mockReturnValue(null);

    render(<ItemDetailPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: sampleItem.itemName }),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("贈答向け")).toBeInTheDocument();
    expect(screen.getByText("結果一覧へ戻る")).toBeInTheDocument();
    expect(screen.getByText("外部ECで見る")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "推薦理由詳細" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Feedback" })).toBeDisabled();
    expect(
      screen.getByText("結果一覧から開くと送信できます"),
    ).toBeInTheDocument();
    expect(screen.queryByText("非表示ショップ")).not.toBeInTheDocument();
  });

  it("shows not-found UX on 404", async () => {
    fetchItemDetail.mockResolvedValue({
      status: 404,
      headers: new Headers(),
      data: {
        error: { code: "GRS-ITM-001", message: "not found" },
        meta: { requestId: "r", traceId: "t" },
      },
    });
    resolveRecommendationContext.mockReturnValue(null);

    render(<ItemDetailPage />);

    await waitFor(() => {
      expect(
        screen.getByText(
          "商品情報が見つかりません。結果一覧または条件入力へお戻りください。",
        ),
      ).toBeInTheDocument();
    });
    expect(
      screen.queryByRole("button", { name: "再試行" }),
    ).not.toBeInTheDocument();
  });

  it("shows inactive UX on 422", async () => {
    fetchItemDetail.mockResolvedValue({
      status: 422,
      headers: new Headers(),
      data: {
        error: { code: "GRS-ITM-002", message: "inactive" },
        meta: { requestId: "r", traceId: "t" },
      },
    });
    resolveRecommendationContext.mockReturnValue(null);

    render(<ItemDetailPage />);

    await waitFor(() => {
      expect(
        screen.getByText("この商品は現在表示できません。"),
      ).toBeInTheDocument();
    });
    expect(
      screen.queryByRole("button", { name: "再試行" }),
    ).not.toBeInTheDocument();
  });

  it("links back to input when fromResultId is absent", async () => {
    navigationState.search = "";
    fetchItemDetail.mockResolvedValue(successResponse(sampleItem));
    resolveRecommendationContext.mockReturnValue(null);

    render(<ItemDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("条件入力へ戻る")).toBeInTheDocument();
    });
    expect(screen.queryByText("結果一覧へ戻る")).not.toBeInTheDocument();
  });

  it("shows recommendation context when session item matches", async () => {
    fetchItemDetail.mockResolvedValue(successResponse(sampleItem));
    resolveRecommendationContext.mockReturnValue({
      recommendationResultItemId: "ri-1",
      itemId: "item-1",
      rank: 2,
      itemName: sampleItem.itemName,
      itemPrice: sampleItem.itemPrice,
      itemUrl: sampleItem.itemUrl,
      reasonSummary: "上司へのお礼にふさわしい上品さ",
      reasonBadges: [{ label: "上品" }],
      isFallback: true,
    });

    render(<ItemDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("推薦順位: 2 位")).toBeInTheDocument();
    });
    expect(
      screen.getByText("上司へのお礼にふさわしい上品さ"),
    ).toBeInTheDocument();
    expect(screen.getByText("上品")).toBeInTheDocument();
    expect(
      screen.getByText("一般的な推薦理由を表示しています"),
    ).toBeInTheDocument();
  });

  it("allows retry on fetch failure", async () => {
    const user = userEvent.setup();
    fetchItemDetail
      .mockRejectedValueOnce(new Error("network"))
      .mockResolvedValueOnce(successResponse(sampleItem));
    resolveRecommendationContext.mockReturnValue(null);

    render(<ItemDetailPage />);

    await waitFor(() => {
      expect(
        screen.getByText(
          "データ取得に失敗しました。時間をおいて再試行するか、戻ってください。",
        ),
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "再試行" }));

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: sampleItem.itemName }),
      ).toBeInTheDocument();
    });
  });
});
