import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RecommendationInputForm } from "@/features/recommendation-input/RecommendationInputForm";
import { createEmptyFormValues } from "@/features/recommendation-input/types";

const relationships = [
  { code: "boss", label: "上司", displayOrder: 1 },
];
const occasions = [
  { code: "thanks", label: "お礼", displayOrder: 1 },
];

describe("RecommendationInputForm", () => {
  it("disables selects while masters are loading", () => {
    render(
      <RecommendationInputForm
        values={createEmptyFormValues()}
        errors={{}}
        relationships={[]}
        occasions={[]}
        mastersLoading
        mastersEmpty={false}
        submitDisabled
        onChange={vi.fn()}
        onBlurField={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByLabelText(/贈る相手/)).toBeDisabled();
    expect(screen.getByLabelText(/用途/)).toBeDisabled();
    expect(screen.getByRole("button", { name: "レコメンドを実行" })).toBeDisabled();
  });

  it("shows field errors and calls onSubmit when enabled", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    const onChange = vi.fn();

    render(
      <RecommendationInputForm
        values={createEmptyFormValues({
          relationshipCode: "boss",
          occasionCode: "thanks",
          budgetMax: "5000",
        })}
        errors={{ budgetMax: "予算の上限を入力してください。" }}
        relationships={relationships}
        occasions={occasions}
        mastersLoading={false}
        mastersEmpty={false}
        submitDisabled={false}
        onChange={onChange}
        onBlurField={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    expect(
      screen.getByText("予算の上限を入力してください。"),
    ).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/贈る相手/), "boss");
    expect(onChange).toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "レコメンドを実行" }));
    expect(onSubmit).toHaveBeenCalledOnce();
  });

  it("disables CTA when masters are empty", () => {
    render(
      <RecommendationInputForm
        values={createEmptyFormValues()}
        errors={{}}
        relationships={[]}
        occasions={[]}
        mastersLoading={false}
        mastersEmpty
        submitDisabled
        onChange={vi.fn()}
        onBlurField={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "レコメンドを実行" })).toBeDisabled();
    expect(screen.getByLabelText(/贈る相手/)).toHaveTextContent(
      "選択肢がありません",
    );
  });
});
