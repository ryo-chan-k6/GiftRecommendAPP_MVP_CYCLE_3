import { afterEach, describe, expect, it, vi } from "vitest";

import { resolvePublicApiUrl } from "@/lib/api/base-url";

describe("resolvePublicApiUrl", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns relative path when NEXT_PUBLIC_API_BASE_URL is unset", () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");
    expect(resolvePublicApiUrl("/api/v1/masters/relationships")).toBe(
      "/api/v1/masters/relationships",
    );
  });

  it("prefixes base URL and strips trailing slash", () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8080/");
    expect(resolvePublicApiUrl("/api/v1/recommendations")).toBe(
      "http://localhost:8080/api/v1/recommendations",
    );
  });
});
