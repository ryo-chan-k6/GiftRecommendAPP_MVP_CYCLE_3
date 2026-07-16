import { describe, expect, it } from "vitest";

import { mapFeedbackSubmitError } from "@/features/feedback-input/map-feedback-error";

describe("mapFeedbackSubmitError", () => {
  it("maps 400 / GRS-FDB-001 to validation", () => {
    expect(mapFeedbackSubmitError(400).kind).toBe("validation");
    expect(
      mapFeedbackSubmitError(500, {
        error: { code: "GRS-FDB-001", message: "x" },
      }).kind,
    ).toBe("validation");
  });

  it("maps 404 to not_found", () => {
    expect(mapFeedbackSubmitError(404).kind).toBe("not_found");
  });

  it("maps network failure as retryable fetch_failed", () => {
    const result = mapFeedbackSubmitError(null);
    expect(result.kind).toBe("fetch_failed");
    expect(result.retryable).toBe(true);
  });
});
