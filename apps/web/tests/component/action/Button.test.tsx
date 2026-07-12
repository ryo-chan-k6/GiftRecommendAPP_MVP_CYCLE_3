import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Button } from "@/components/action/Button";

describe("Button (UI-020)", () => {
  it("renders label and responds to click", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(<Button onClick={onClick}>送信</Button>);

    const button = screen.getByRole("button", { name: "送信" });
    await user.click(button);

    expect(onClick).toHaveBeenCalledOnce();
  });

  it("does not fire click when loading", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();

    render(
      <Button loading onClick={onClick}>
        送信
      </Button>,
    );

    const button = screen.getByRole("button", { name: /送信/ });
    expect(button).toBeDisabled();

    await user.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });
});
