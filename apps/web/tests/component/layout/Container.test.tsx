import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Container } from "@/components/layout/Container";

describe("Container (UI-002)", () => {
  it("renders children", () => {
    render(<Container>コンテンツ</Container>);

    expect(screen.getByText("コンテンツ")).toBeInTheDocument();
  });
});
