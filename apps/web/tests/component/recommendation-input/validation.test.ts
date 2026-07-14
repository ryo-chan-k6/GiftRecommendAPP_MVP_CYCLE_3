import { describe, expect, it } from "vitest";

import { buildRecommendationRunRequest } from "@/features/recommendation-input/build-request";
import { VALIDATION_MESSAGES } from "@/features/recommendation-input/constants";
import { createEmptyFormValues } from "@/features/recommendation-input/types";
import {
  hasFieldErrors,
  validateRecommendationInput,
} from "@/features/recommendation-input/validation";

const relationships = [
  { code: "boss", label: "上司", displayOrder: 1 },
  { code: "friend", label: "友人", displayOrder: 2 },
];
const occasions = [
  { code: "thanks", label: "お礼", displayOrder: 1 },
  { code: "birthday", label: "誕生日", displayOrder: 2 },
];

describe("validateRecommendationInput (SCR-002 §12)", () => {
  it("requires relationship, occasion, and budgetMax", () => {
    const errors = validateRecommendationInput(
      createEmptyFormValues(),
      relationships,
      occasions,
    );
    expect(errors.relationshipCode).toBe(
      VALIDATION_MESSAGES.relationshipRequired,
    );
    expect(errors.occasionCode).toBe(VALIDATION_MESSAGES.occasionRequired);
    expect(errors.budgetMax).toBe(VALIDATION_MESSAGES.budgetMaxRequired);
    expect(hasFieldErrors(errors)).toBe(true);
  });

  it("rejects negative or non-integer budget", () => {
    const errors = validateRecommendationInput(
      createEmptyFormValues({
        relationshipCode: "boss",
        occasionCode: "thanks",
        budgetMin: "-1",
        budgetMax: "1.5",
      }),
      relationships,
      occasions,
    );
    expect(errors.budgetMin).toBe(VALIDATION_MESSAGES.budgetInvalid);
    expect(errors.budgetMax).toBe(VALIDATION_MESSAGES.budgetInvalid);
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
    expect(errors.budgetMin).toBe(VALIDATION_MESSAGES.budgetRange);
    expect(errors.budgetMax).toBe(VALIDATION_MESSAGES.budgetRange);
  });

  it("rejects codes not in masters", () => {
    const errors = validateRecommendationInput(
      createEmptyFormValues({
        relationshipCode: "unknown",
        occasionCode: "thanks",
        budgetMax: "5000",
      }),
      relationships,
      occasions,
    );
    expect(errors.relationshipCode).toBe(VALIDATION_MESSAGES.masterCodeInvalid);
  });

  it("rejects text over max length", () => {
    const errors = validateRecommendationInput(
      createEmptyFormValues({
        relationshipCode: "boss",
        occasionCode: "thanks",
        budgetMax: "5000",
        preferredText: "あ".repeat(501),
        ngText: "い".repeat(301),
      }),
      relationships,
      occasions,
    );
    expect(errors.preferredText).toBe(VALIDATION_MESSAGES.textTooLong);
    expect(errors.ngText).toBe(VALIDATION_MESSAGES.textTooLong);
  });

  it("passes valid input", () => {
    const errors = validateRecommendationInput(
      createEmptyFormValues({
        relationshipCode: "boss",
        occasionCode: "thanks",
        budgetMin: "3000",
        budgetMax: "5000",
        preferredText: "上品",
      }),
      relationships,
      occasions,
    );
    expect(errors).toEqual({});
    expect(hasFieldErrors(errors)).toBe(false);
  });
});

describe("buildRecommendationRunRequest (SCR-002 §14)", () => {
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
    expect(request.nonPreferredCondition).toBeUndefined();
    expect(request.execution).toMatchObject({
      mode: "ui",
      topK: 10,
      candidateLimit: 50,
      includeReason: true,
      includeDebugInfo: false,
    });
    expect(request.freeText).toBeUndefined();
  });

  it("omits empty optional text and budgetMin", () => {
    const request = buildRecommendationRunRequest(
      createEmptyFormValues({
        relationshipCode: "friend",
        occasionCode: "birthday",
        budgetMax: "10000",
      }),
      relationships,
      occasions,
    );
    expect(request.budget?.budgetMin).toBeUndefined();
    expect(request.budget?.budgetMax).toBe(10000);
    expect(request.preferredCondition).toBeUndefined();
    expect(request.ngCondition).toBeUndefined();
  });
});
