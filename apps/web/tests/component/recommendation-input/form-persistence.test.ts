import { afterEach, describe, expect, it } from "vitest";

import {
  persistFormValues,
  readFormValuesFromLocation,
  readRecommendationResult,
  storeRecommendationResult,
} from "@/features/recommendation-input/form-persistence";
import { createEmptyFormValues } from "@/features/recommendation-input/types";
import { ResultStatus } from "@/generated/api/giftRecommendationServicePublicAPI.schemas";

describe("form-persistence (SCR-002 §6.2)", () => {
  afterEach(() => {
    sessionStorage.clear();
    window.history.replaceState(null, "", "/recommendations");
  });

  it("restores short fields from query and long text from sessionStorage", () => {
    sessionStorage.setItem("scr002:preferredText", "上品なギフト");
    sessionStorage.setItem("scr002:ngText", "アルコールNG");

    const values = readFormValuesFromLocation(
      new URLSearchParams(
        "relationshipCode=boss&occasionCode=thanks&budgetMax=5000&budgetMin=3000",
      ),
    );

    expect(values.relationshipCode).toBe("boss");
    expect(values.occasionCode).toBe("thanks");
    expect(values.budgetMin).toBe("3000");
    expect(values.budgetMax).toBe("5000");
    expect(values.preferredText).toBe("上品なギフト");
    expect(values.ngText).toBe("アルコールNG");
    expect(values.nonPreferredText).toBe("");
  });

  it("persists query and sessionStorage on submit preparation", () => {
    persistFormValues(
      createEmptyFormValues({
        relationshipCode: "boss",
        occasionCode: "thanks",
        budgetMax: "8000",
        preferredText: "感謝",
        nonPreferredText: "派手",
        ngText: "酒",
      }),
    );

    expect(window.location.search).toContain("relationshipCode=boss");
    expect(window.location.search).toContain("budgetMax=8000");
    expect(sessionStorage.getItem("scr002:preferredText")).toBe("感謝");
    expect(sessionStorage.getItem("scr002:nonPreferredText")).toBe("派手");
    expect(sessionStorage.getItem("scr002:ngText")).toBe("酒");
  });

  it("stores and reads recommendation result by id", () => {
    storeRecommendationResult({
      recommendationResultId: "result-1",
      recommendationRequestId: "req-1",
      recommendationRunId: "run-1",
      resultStatus: ResultStatus.completed,
      topK: 10,
      resultItemCount: 1,
      fallbackUsed: false,
      items: [],
    });

    const stored = readRecommendationResult("result-1");
    expect(stored?.recommendationResultId).toBe("result-1");
    expect(stored?.resultStatus).toBe("completed");
  });
});
