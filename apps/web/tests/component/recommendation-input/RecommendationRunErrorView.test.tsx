import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  RUN_ERROR_ALERT_TITLE,
  RUN_ERROR_BACK_LABEL,
  RUN_ERROR_PAGE_TITLE,
  RUN_ERROR_RETRY_LABEL,
} from "@/features/recommendation-input/constants";
import { RecommendationRunErrorView } from "@/features/recommendation-input/RecommendationRunErrorView";

describe("RecommendationRunErrorView (SCR-008)", () => {
  it("shows alert title, message, code, and traceId", () => {
    render(
      <RecommendationRunErrorView
        error={{
          message: "条件を確認してください。",
          code: "GRS-REQ-001",
          traceId: "trace-scr008-001",
        }}
        onBackToForm={vi.fn()}
        onRetry={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("heading", { name: RUN_ERROR_PAGE_TITLE }),
    ).toBeInTheDocument();
    expect(screen.getByText(RUN_ERROR_ALERT_TITLE)).toBeInTheDocument();
    expect(screen.getByText("条件を確認してください。")).toBeInTheDocument();
    expect(screen.getByText("code: GRS-REQ-001")).toBeInTheDocument();
    expect(screen.getByText("traceId: trace-scr008-001")).toBeInTheDocument();
  });

  it("hides code and traceId when absent", () => {
    render(
      <RecommendationRunErrorView
        error={{ message: "レコメンド実行に失敗しました。" }}
        onBackToForm={vi.fn()}
        onRetry={vi.fn()}
      />,
    );

    expect(screen.queryByText(/code:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/traceId:/)).not.toBeInTheDocument();
  });

  it("calls onBackToForm and onRetry", async () => {
    const user = userEvent.setup();
    const onBackToForm = vi.fn();
    const onRetry = vi.fn();

    render(
      <RecommendationRunErrorView
        error={{ message: "通信に失敗しました。" }}
        onBackToForm={onBackToForm}
        onRetry={onRetry}
      />,
    );

    await user.click(
      screen.getByRole("button", { name: RUN_ERROR_BACK_LABEL }),
    );
    await user.click(
      screen.getByRole("button", { name: RUN_ERROR_RETRY_LABEL }),
    );

    expect(onBackToForm).toHaveBeenCalledTimes(1);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
