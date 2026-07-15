import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FeedbackInputModal } from "@/features/feedback-input/FeedbackInputModal";
import { FeedbackType } from "@/generated/api/giftRecommendationServicePublicAPI.schemas";

const submitFeedback = vi.fn();

vi.mock("@/lib/api", () => ({
  submitFeedback: (...args: unknown[]) => submitFeedback(...args),
}));

describe("FeedbackInputModal", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("submits item_good with mapped rating", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    submitFeedback.mockResolvedValue({
      status: 201,
      headers: new Headers(),
      data: {
        data: {
          recommendationFeedbackId: "fb-1",
          status: "accepted",
          message: "フィードバックを受け付けました。",
        },
        meta: { requestId: "r", traceId: "t" },
      },
    });

    render(
      <FeedbackInputModal
        open
        onClose={onClose}
        resultId="result-1"
        resultItemId="rii-1"
        itemName="サンプル"
        sourcePage="SCR-004"
      />,
    );

    await user.click(screen.getByRole("button", { name: "良い" }));
    await user.click(screen.getByRole("button", { name: "送信" }));

    await waitFor(() => {
      expect(submitFeedback).toHaveBeenCalledWith(
        "result-1",
        expect.objectContaining({
          feedbackTargetType: "item",
          resultItemId: "rii-1",
          feedbackType: FeedbackType.item_good,
          rating: 5,
          sourcePage: "SCR-004",
        }),
      );
    });

    expect(
      await screen.findByText("フィードバックを受け付けました。"),
    ).toBeInTheDocument();
  });

  it("keeps submit disabled until a type is selected", () => {
    render(
      <FeedbackInputModal
        open
        onClose={() => undefined}
        resultId="result-1"
        resultItemId="rii-1"
      />,
    );
    expect(screen.getByRole("button", { name: "送信" })).toBeDisabled();
  });

  it("shows retry on network failure", async () => {
    const user = userEvent.setup();
    submitFeedback.mockRejectedValueOnce(new Error("network"));

    render(
      <FeedbackInputModal
        open
        onClose={() => undefined}
        resultId="result-1"
        resultItemId="rii-1"
      />,
    );

    await user.click(screen.getByRole("button", { name: "微妙" }));
    await user.click(screen.getByRole("button", { name: "送信" }));

    expect(
      await screen.findByText(
        "Feedbackを送信できませんでした。時間をおいて再試行するか、閉じてください。",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "再試行" })).toBeInTheDocument();
  });
});
