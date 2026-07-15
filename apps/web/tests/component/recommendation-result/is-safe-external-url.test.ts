import { describe, expect, it } from "vitest";

import { isSafeExternalUrl } from "@/features/recommendation-result/is-safe-external-url";

describe("isSafeExternalUrl (SCR-004)", () => {
  it("allows http and https URLs", () => {
    expect(isSafeExternalUrl("https://example.com/item/1")).toBe(true);
    expect(isSafeExternalUrl("http://example.com/item/1")).toBe(true);
  });

  it("rejects javascript: and invalid values", () => {
    expect(isSafeExternalUrl("javascript:alert(1)")).toBe(false);
    expect(isSafeExternalUrl("not-a-url")).toBe(false);
    expect(isSafeExternalUrl("")).toBe(false);
    expect(isSafeExternalUrl(undefined)).toBe(false);
  });
});
