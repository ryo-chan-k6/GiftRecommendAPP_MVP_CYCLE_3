import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { DESCRIPTION_COLLAPSE_THRESHOLD } from "@/features/item-detail/constants";
import { ItemDetailView } from "@/features/item-detail/ItemDetailView";
import type { PublicItemDetail } from "@/generated/api/giftRecommendationServicePublicAPI.schemas";

const baseItem: PublicItemDetail = {
  itemId: "item-1",
  itemName: "テスト商品",
  itemPrice: 1500,
  itemUrl: "https://example.invalid/ok",
  isActive: true,
};

describe("ItemDetailView", () => {
  it("shows image placeholder when itemImageUrl is absent", () => {
    render(<ItemDetailView item={baseItem} context={null} />);
    expect(screen.getByRole("img", { name: "画像なし" })).toBeInTheDocument();
  });

  it("hides external EC link for unsafe URL", () => {
    render(
      <ItemDetailView
        item={{ ...baseItem, itemUrl: "javascript:alert(1)" }}
        context={null}
      />,
    );
    expect(screen.queryByText("外部ECで見る")).not.toBeInTheDocument();
  });

  it("toggles long description", async () => {
    const user = userEvent.setup();
    const longDescription = "あ".repeat(DESCRIPTION_COLLAPSE_THRESHOLD + 10);
    render(
      <ItemDetailView
        item={{ ...baseItem, itemDescription: longDescription }}
        context={null}
      />,
    );

    expect(screen.getByText("説明をすべて表示")).toBeInTheDocument();
    await user.click(screen.getByText("説明をすべて表示"));
    expect(screen.getByText("説明を閉じる")).toBeInTheDocument();
  });

  it("renders review summary and popularity badge when present", () => {
    render(
      <ItemDetailView
        item={{
          ...baseItem,
          reviewSummary: { average: 4.2, count: 128 },
          popularityBadge: { label: "ランキング入り", rank: 12 },
        }}
        context={null}
      />,
    );
    expect(screen.getByText("レビュー 4.2（128件）")).toBeInTheDocument();
    expect(screen.getByText("ランキング入り")).toBeInTheDocument();
  });
});
