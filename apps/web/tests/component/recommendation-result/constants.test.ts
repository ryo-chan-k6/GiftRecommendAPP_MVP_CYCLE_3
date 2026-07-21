import { describe, expect, it } from "vitest";

import { buildItemDetailHref } from "@/features/recommendation-result/constants";

describe("buildItemDetailHref (SCR-004 / SCR-006 stub)", () => {
  it("builds stub item URL with fromResultId query", () => {
    expect(buildItemDetailHref("item-1", "result-9")).toBe(
      "/items/item-1?fromResultId=result-9",
    );
  });

  it("encodes itemId for path safety", () => {
    expect(buildItemDetailHref("a/b", "res")).toBe(
      "/items/a%2Fb?fromResultId=res",
    );
  });
});
