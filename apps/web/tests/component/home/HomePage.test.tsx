import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HomePage } from "@/features/home/HomePage";
import {
  CTA_LABEL,
  PAGE_CATCHCOPY,
  PAGE_SERVICE_NAME,
  RECOMMENDATIONS_HREF,
} from "@/features/home/constants";

describe("HomePage (SCR-001)", () => {
  it("renders service name, catchcopy and CTA to recommendations", () => {
    render(<HomePage />);

    expect(
      screen.getByRole("heading", { level: 1, name: PAGE_SERVICE_NAME }),
    ).toBeInTheDocument();
    expect(screen.getByText(PAGE_CATCHCOPY)).toBeInTheDocument();

    const cta = screen.getByRole("link", { name: CTA_LABEL });
    expect(cta).toHaveAttribute("href", RECOMMENDATIONS_HREF);
  });
});
