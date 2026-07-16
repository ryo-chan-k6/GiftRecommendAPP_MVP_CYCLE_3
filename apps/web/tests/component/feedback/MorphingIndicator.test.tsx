import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MorphingIndicator } from "@/components/feedback/MorphingIndicator";

describe("MorphingIndicator", () => {
  it("renders full motion morphing indicator by default", () => {
    render(<MorphingIndicator reducedMotion={false} />);
    const indicator = screen.getByTestId("morphing-indicator");
    expect(indicator).toHaveAttribute("data-motion", "full");
    expect(indicator).toHaveAttribute("aria-hidden", "true");
  });

  it("falls back to static geometry when reduced motion is requested", () => {
    render(<MorphingIndicator reducedMotion />);
    const indicator = screen.getByTestId("morphing-indicator");
    expect(indicator).toHaveAttribute("data-motion", "reduced");
  });
});
