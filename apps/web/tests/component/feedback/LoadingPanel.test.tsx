import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { LoadingPanel } from "@/components/feedback/LoadingPanel";

describe("LoadingPanel", () => {
  it("uses morphing indicator instead of spin Spinner", () => {
    render(<LoadingPanel message="条件に合うギフトを探しています" />);

    const status = screen.getByRole("status");
    expect(status).toHaveAttribute("aria-live", "polite");
    expect(screen.getByText("条件に合うギフトを探しています")).toBeInTheDocument();
    expect(screen.getByTestId("morphing-indicator")).toBeInTheDocument();
    expect(status.querySelector(".animate-spin")).toBeNull();
  });
});
