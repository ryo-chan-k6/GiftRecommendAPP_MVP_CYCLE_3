import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RecommendationEmptyPanel } from "@/features/recommendation-input/RecommendationEmptyPanel";
import { EMPTY_RESULT_MESSAGE } from "@/features/recommendation-input/constants";

describe("RecommendationEmptyPanel (SCR-009)", () => {
  it("shows empty title, EMPTY_RESULT_MESSAGE, and page title", () => {
    render(<RecommendationEmptyPanel onChangeConditions={() => undefined} />);

    expect(
      screen.getByRole("heading", { name: "おすすめが見つかりませんでした" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "条件に合うギフトがありません" }),
    ).toBeInTheDocument();
    expect(screen.getByText(EMPTY_RESULT_MESSAGE)).toBeInTheDocument();
  });

  it("calls onChangeConditions when 条件を変更する is clicked", async () => {
    const user = userEvent.setup();
    const onChangeConditions = vi.fn();

    render(
      <RecommendationEmptyPanel onChangeConditions={onChangeConditions} />,
    );

    await user.click(screen.getByRole("button", { name: "条件を変更する" }));
    expect(onChangeConditions).toHaveBeenCalledTimes(1);
  });

  it("renders トップへ戻る TextLink to /", () => {
    render(<RecommendationEmptyPanel onChangeConditions={() => undefined} />);

    const topLink = screen.getByRole("link", { name: "トップへ戻る" });
    expect(topLink).toHaveAttribute("href", "/");
  });

  it("does not render 再検索 CTA", () => {
    render(<RecommendationEmptyPanel onChangeConditions={() => undefined} />);

    expect(screen.queryByRole("button", { name: /再検索/ })).toBeNull();
    expect(screen.queryByRole("link", { name: /再検索/ })).toBeNull();
    expect(screen.queryByText("再検索")).toBeNull();
  });
});
