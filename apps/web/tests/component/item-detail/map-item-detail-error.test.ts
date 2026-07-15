import { describe, expect, it } from "vitest";

import { mapItemDetailError } from "@/features/item-detail/map-item-detail-error";

describe("mapItemDetailError", () => {
  it("maps 404 / GRS-ITM-001 to not_found", () => {
    const byStatus = mapItemDetailError(404);
    expect(byStatus.kind).toBe("not_found");
    expect(byStatus.retryable).toBe(false);

    const byCode = mapItemDetailError(500, {
      error: { code: "GRS-ITM-001", message: "x" },
    });
    expect(byCode.kind).toBe("not_found");
  });

  it("maps 422 / GRS-ITM-002 to inactive", () => {
    expect(mapItemDetailError(422).kind).toBe("inactive");
  });

  it("maps 400 to bad_request", () => {
    expect(mapItemDetailError(400).kind).toBe("bad_request");
  });

  it("maps network failure (null status) as retryable fetch_failed", () => {
    const result = mapItemDetailError(null);
    expect(result.kind).toBe("fetch_failed");
    expect(result.retryable).toBe(true);
  });
});
