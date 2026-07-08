import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FormField } from "@/components/form/FormField";

describe("FormField (UI-025)", () => {
  it("associates label with input and shows helper text", () => {
    render(
      <FormField
        label="メールアドレス"
        htmlFor="email"
        helperText="半角英数字で入力してください"
      >
        <input id="email" type="email" />
      </FormField>,
    );

    expect(screen.getByLabelText("メールアドレス")).toBeInTheDocument();
    expect(
      screen.getByText("半角英数字で入力してください"),
    ).toBeInTheDocument();
  });

  it("shows error message instead of helper text", () => {
    render(
      <FormField label="メールアドレス" htmlFor="email" error="必須項目です">
        <input id="email" type="email" />
      </FormField>,
    );

    expect(screen.getByText("必須項目です")).toBeInTheDocument();
    expect(
      screen.queryByText("半角英数字で入力してください"),
    ).not.toBeInTheDocument();
  });
});
