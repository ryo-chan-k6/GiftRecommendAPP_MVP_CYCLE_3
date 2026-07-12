import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Heading } from "@/components/display/Heading";

describe("Heading (UI-060)", () => {
  it("renders the requested heading level", () => {
    render(<Heading level={1}>ページタイトル</Heading>);

    const heading = screen.getByRole("heading", {
      level: 1,
      name: "ページタイトル",
    });
    expect(heading).toBeInTheDocument();
  });
});
