import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RecommendationRunningPanel } from "@/features/recommendation-input/RecommendationRunningPanel";
import {
  RUNNING_MESSAGE,
  RUNNING_WAITING_MESSAGE,
} from "@/features/recommendation-input/constants";

describe("RecommendationRunningPanel (SCR-003)", () => {
  it("shows running title, messages, morphing indicator, and status a11y", () => {
    render(<RecommendationRunningPanel />);

    expect(
      screen.getByRole("heading", { name: "レコメンド実行中" }),
    ).toBeInTheDocument();
    expect(screen.getByText(RUNNING_MESSAGE)).toBeInTheDocument();
    expect(screen.getByText(RUNNING_WAITING_MESSAGE)).toBeInTheDocument();

    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-live", "polite");
    expect(status.querySelector('[data-testid="morphing-indicator"]')).not.toBeNull();
    expect(status.querySelector(".animate-spin")).toBeNull();
  });

  it("does not render cancel UI", () => {
    render(<RecommendationRunningPanel />);

    expect(screen.queryByRole("button", { name: /キャンセル/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /キャンセル/ })).toBeNull();
    expect(screen.queryByText("キャンセル")).toBeNull();
  });
});
