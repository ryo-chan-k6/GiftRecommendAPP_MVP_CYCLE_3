import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Text } from "@/components/display/Text";

describe("Text (UI-061)", () => {
  it("renders body text", () => {
    render(<Text>補足説明</Text>);

    expect(screen.getByText("補足説明")).toBeInTheDocument();
  });
});
