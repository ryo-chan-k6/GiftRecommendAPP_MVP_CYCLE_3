import { describe, expect, it } from "vitest";

import { buildRecommendationRunRequest } from "@/features/recommendation-input/build-request";
import { createEmptyFormValues } from "@/features/recommendation-input/types";
import { validateRecommendationInput } from "@/features/recommendation-input/validation";

const relationships = [
  { code: "boss", label: "上司", displayOrder: 1 },
  { code: "friend", label: "友人", displayOrder: 2 },
];
const occasions = [
  { code: "thanks", label: "お礼", displayOrder: 1 },
  { code: "birthday", label: "誕生日", displayOrder: 2 },
];

describe("validateRecommendationInput", () => {
  it("requires relationship, occasion, and budgetMax", () => {
    const errors = validateRecommendationInput(
      createEmptyFormValues(),
      relationships,
      occasions,
    );
    expect(errors.relationshipCode).toBeTruthy();
    expect(errors.occasionCode).toBeTruthy();
    expect(errors.budgetMax).toBeTruthy();
  });

  it("rejects budgetMin greater than budgetMax", () => {
    const errors = validateRecommendationInput(
      createEmptyFormValues({
        relationshipCode: "boss",
        occasionCode: "thanks",
        budgetMin: "5000",
        budgetMax: "3000",
      }),
      relationships,
      occasions,
    );
    expect(errors.budgetMin).toBeTruthy();
    expect(errors.budgetMax).toBeTruthy();
  });

  it("passes valid input", () => {
    const errors = validateRecommendationInput(
      createEmptyFormValues({
        relationshipCode: "boss",
        occasionCode: "thanks",
        budgetMax: "5000",
        preferredText: "上品",
      }),
      relationships,
      occasions,
    );
    expect(errors).toEqual({});
  });
});

describe("buildRecommendationRunRequest", () => {
  it("maps form values to PUB-002 request with fixed execution fields", () => {
    const request = buildRecommendationRunRequest(
      createEmptyFormValues({
        relationshipCode: "boss",
        occasionCode: "thanks",
        budgetMin: "3000",
        budgetMax: "5000",
        preferredText: "上品で感謝が伝わるもの",
        ngText: "アルコールはNG",
      }),
      relationships,
      occasions,
    );

    expect(request.relationship).toEqual({
      relationshipCode: "boss",
      relationshipLabel: "上司",
    });
    expect(request.occasion).toEqual({
      occasionCode: "thanks",
      occasionLabel: "お礼",
    });
    expect(request.budget).toEqual({
      budgetMin: 3000,
      budgetMax: 5000,
      currency: "JPY",
      taxIncluded: true,
    });
    expect(request.preferredCondition).toEqual({
      preferredText: "上品で感謝が伝わるもの",
    });
    expect(request.ngCondition).toEqual({ ngText: "アルコールはNG" });
    expect(request.execution).toMatchObject({
      mode: "ui",
      topK: 10,
      includeDebugInfo: false,
    });
    expect(request.freeText).toBeUndefined();
  });
});
