import { afterEach, describe, expect, it, vi } from "vitest";

import { loadRecommendationMasters } from "@/features/recommendation-input/load-masters";

vi.mock("@/lib/api", () => ({
  fetchRelationshipMasters: vi.fn(),
  fetchOccasionMasters: vi.fn(),
  fetchSemanticConfigMasters: vi.fn(),
  fetchFeatureRuleMasters: vi.fn(),
}));

import {
  fetchFeatureRuleMasters,
  fetchOccasionMasters,
  fetchRelationshipMasters,
  fetchSemanticConfigMasters,
} from "@/lib/api";

const mockedRelationships = vi.mocked(fetchRelationshipMasters);
const mockedOccasions = vi.mocked(fetchOccasionMasters);
const mockedSemantic = vi.mocked(fetchSemanticConfigMasters);
const mockedFeatureRules = vi.mocked(fetchFeatureRuleMasters);

function successEnvelope<T>(data: T) {
  return {
    status: 200 as const,
    headers: new Headers(),
    data: {
      data,
      meta: { requestId: "req-1", traceId: "trace-1", generatedAt: "2026-07-13T00:00:00Z" },
    },
  };
}

describe("loadRecommendationMasters (PUB-005〜008)", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("loads relationship/occasion options and marks 007/008 as loaded", async () => {
    mockedRelationships.mockResolvedValue(
      successEnvelope({
        relationships: [
          {
            relationshipCode: "boss",
            relationshipLabel: "上司",
            displayOrder: 2,
          },
          {
            relationshipCode: "friend",
            relationshipLabel: "友人",
            displayOrder: 1,
          },
        ],
      }) as never,
    );
    mockedOccasions.mockResolvedValue(
      successEnvelope({
        occasions: [
          { occasionCode: "thanks", occasionLabel: "お礼", displayOrder: 1 },
        ],
      }) as never,
    );
    mockedSemantic.mockResolvedValue(
      successEnvelope({
        configName: "default",
        versionLabel: "v1",
        semanticConcepts: [],
        featureDefinitions: [],
      }) as never,
    );
    mockedFeatureRules.mockResolvedValue(
      successEnvelope({
        configName: "default",
        versionLabel: "v1",
        baseValueRules: [],
        conceptFeatureRules: [],
      }) as never,
    );

    const result = await loadRecommendationMasters();
    expect(result.status).toBe("success");
    if (result.status !== "success") {
      return;
    }
    expect(result.relationships.map((item) => item.code)).toEqual([
      "friend",
      "boss",
    ]);
    expect(result.occasions).toHaveLength(1);
    expect(result.semanticConfigLoaded).toBe(true);
    expect(result.featureRulesLoaded).toBe(true);
    expect(mockedSemantic).toHaveBeenCalledOnce();
    expect(mockedFeatureRules).toHaveBeenCalledOnce();
  });

  it("returns masters error when any of 005〜008 fails", async () => {
    mockedRelationships.mockResolvedValue(
      successEnvelope({ relationships: [] }) as never,
    );
    mockedOccasions.mockResolvedValue(
      successEnvelope({ occasions: [] }) as never,
    );
    mockedSemantic.mockResolvedValue({
      status: 503,
      headers: new Headers(),
      data: {
        error: { code: "GRS-CFG-001", message: "unavailable" },
        meta: {
          requestId: "req-err",
          traceId: "trace-err",
          generatedAt: "2026-07-13T00:00:00Z",
        },
      },
    } as never);
    mockedFeatureRules.mockResolvedValue(
      successEnvelope({
        configName: "default",
        versionLabel: "v1",
        baseValueRules: [],
        conceptFeatureRules: [],
      }) as never,
    );

    const result = await loadRecommendationMasters();
    expect(result.status).toBe("error");
    if (result.status !== "error") {
      return;
    }
    expect(result.message).toContain("選択項目の取得に失敗");
    expect(result.traceId).toBe("trace-err");
  });
});
