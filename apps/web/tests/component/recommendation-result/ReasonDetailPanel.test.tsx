import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  CAUTION_ALERT_TITLE,
  DETAIL_EMPTY_GUIDE,
  REASON_POINTS_LIST_LABEL,
} from "@/features/recommendation-result/constants";
import { ReasonDetailPanel } from "@/features/recommendation-result/ReasonDetailPanel";
import type { PublicRecommendationResultItem } from "@/generated/api/giftRecommendationServicePublicAPI.schemas";

const baseItem: PublicRecommendationResultItem = {
  recommendationResultItemId: "rii-1",
  itemId: "item-1",
  rank: 1,
  itemName: "サンプル商品",
  itemPrice: 4200,
  itemUrl: "https://example.com/item/1",
  reasonSummary: "バランスが良いため",
  reasonBadges: [{ label: "上品", code: "elegant" }],
};

describe("ReasonDetailPanel (SCR-005)", () => {
  it("renders points and detail without redisplaying summary when rich", () => {
    render(
      <ReasonDetailPanel
        item={{
          ...baseItem,
          reasonPoints: ["きちんと感がある", "安心感が高い", "レビューが安定"],
          reasonDetail: "上司へのお礼として失礼になりにくい候補です。",
        }}
        panelId="panel-rich"
      />,
    );

    expect(
      screen.getByRole("list", { name: REASON_POINTS_LIST_LABEL }),
    ).toBeInTheDocument();
    expect(screen.getByText("きちんと感がある")).toBeInTheDocument();
    expect(
      screen.getByText("上司へのお礼として失礼になりにくい候補です。"),
    ).toBeInTheDocument();
    expect(screen.queryByText(DETAIL_EMPTY_GUIDE)).not.toBeInTheDocument();
    // 展開内での要約再掲はしない（カード上は別コンポーネント）
    expect(screen.queryByText("バランスが良いため")).not.toBeInTheDocument();
  });

  it("limits points to three entries", () => {
    render(
      <ReasonDetailPanel
        item={{
          ...baseItem,
          reasonPoints: ["a", "b", "c", "d"],
        }}
        panelId="panel-points"
      />,
    );

    expect(screen.getByText("a")).toBeInTheDocument();
    expect(screen.getByText("c")).toBeInTheDocument();
    expect(screen.queryByText("d")).not.toBeInTheDocument();
  });

  it("shows caution alert when cautionNote is present", () => {
    render(
      <ReasonDetailPanel
        item={{
          ...baseItem,
          reasonPoints: ["ポイント1"],
          cautionNote: "価格帯が高めです。",
        }}
        panelId="panel-caution"
      />,
    );

    expect(screen.getByText(CAUTION_ALERT_TITLE)).toBeInTheDocument();
    expect(screen.getByText("価格帯が高めです。")).toBeInTheDocument();
  });

  it("redisplays summary and badges with guide when detail is thin", () => {
    render(
      <ReasonDetailPanel item={baseItem} panelId="panel-thin" />,
    );

    expect(screen.getByText("バランスが良いため")).toBeInTheDocument();
    expect(screen.getByText("上品")).toBeInTheDocument();
    expect(screen.getByText(DETAIL_EMPTY_GUIDE)).toBeInTheDocument();
  });

  it("shows only guide when all reason fields are empty", () => {
    render(
      <ReasonDetailPanel
        item={{
          ...baseItem,
          reasonSummary: undefined,
          reasonBadges: undefined,
          reasonPoints: undefined,
          reasonDetail: undefined,
          cautionNote: undefined,
        }}
        panelId="panel-empty"
      />,
    );

    expect(screen.getByText(DETAIL_EMPTY_GUIDE)).toBeInTheDocument();
  });
});
