import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { RecommendationResultItem } from "@/features/recommendation-result/RecommendationResultItem";
import type { PublicRecommendationResultItem } from "@/generated/api/giftRecommendationServicePublicAPI.schemas";

const baseItem: PublicRecommendationResultItem = {
  recommendationResultItemId: "rii-1",
  itemId: "item-1",
  rank: 1,
  itemName: "サンプル商品",
  itemPrice: 4200,
  itemUrl: "https://example.com/item/1",
  itemCatchcopy: "上品な一品",
  reasonSummary: "バランスが良いため",
  reasonBadges: [{ label: "上品", code: "elegant" }],
  isFallback: false,
};

describe("RecommendationResultItem (SCR-004 / SCR-005)", () => {
  it("renders rank, name, price, badge and enables feedback", () => {
    render(<RecommendationResultItem item={baseItem} resultId="result-1" />);

    expect(screen.getByLabelText("順位 1")).toBeInTheDocument();
    expect(screen.getByText("サンプル商品")).toBeInTheDocument();
    expect(screen.getByText("¥4,200")).toBeInTheDocument();
    expect(screen.getByText("上品")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Feedback" })).toBeEnabled();
    expect(screen.queryByText("準備中")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "外部ECで見る" })).toHaveAttribute(
      "href",
      "https://example.com/item/1",
    );
    expect(screen.getByRole("link", { name: "商品詳細" })).toHaveAttribute(
      "href",
      "/items/item-1?fromResultId=result-1",
    );
  });

  it("does not render external EC link for unsafe URL", () => {
    render(
      <RecommendationResultItem
        item={{ ...baseItem, itemUrl: "javascript:alert(1)" }}
        resultId="result-1"
      />,
    );

    expect(
      screen.queryByRole("link", { name: "外部ECで見る" }),
    ).not.toBeInTheDocument();
  });

  it("toggles reason detail accordion", async () => {
    const user = userEvent.setup();
    render(<RecommendationResultItem item={baseItem} resultId="result-1" />);

    const toggle = screen.getByRole("button", { name: "▶ 理由の詳細" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");

    await user.click(toggle);

    expect(
      screen.getByRole("button", { name: "▼ 理由の詳細" }),
    ).toHaveAttribute("aria-expanded", "true");
    expect(
      screen.getByText(
        "詳細な説明文はありません。カード上の要約・バッジをご確認ください。",
      ),
    ).toBeInTheDocument();
  });

  it("shows reason points in accordion when provided", async () => {
    const user = userEvent.setup();
    render(
      <RecommendationResultItem
        item={{
          ...baseItem,
          reasonPoints: ["きちんと感がある"],
          reasonDetail: "詳細な説明です。",
        }}
        resultId="result-1"
      />,
    );

    await user.click(screen.getByRole("button", { name: "▶ 理由の詳細" }));

    expect(screen.getByText("きちんと感がある")).toBeInTheDocument();
    expect(screen.getByText("詳細な説明です。")).toBeInTheDocument();
    expect(
      screen.queryByText(
        "詳細な説明文はありません。カード上の要約・バッジをご確認ください。",
      ),
    ).not.toBeInTheDocument();
  });

  it("does not show shopName", () => {
    render(
      <RecommendationResultItem
        item={{ ...baseItem, shopName: "シークレットショップ" }}
        resultId="result-1"
      />,
    );

    expect(screen.queryByText("シークレットショップ")).not.toBeInTheDocument();
  });
});
