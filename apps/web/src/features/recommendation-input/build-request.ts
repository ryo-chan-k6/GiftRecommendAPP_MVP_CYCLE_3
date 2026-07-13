import type { RecommendationRunRequest } from "@/generated/api/giftRecommendationServicePublicAPI.schemas";

import {
  DEFAULT_CANDIDATE_LIMIT,
  DEFAULT_TOP_K,
} from "./constants";
import type {
  MasterOption,
  RecommendationInputFormValues,
} from "./types";

function parseOptionalBudget(raw: string): number | undefined {
  const trimmed = raw.trim();
  if (trimmed === "") {
    return undefined;
  }
  return Number(trimmed);
}

export function buildRecommendationRunRequest(
  values: RecommendationInputFormValues,
  relationships: MasterOption[],
  occasions: MasterOption[],
): RecommendationRunRequest {
  const relationship = relationships.find(
    (item) => item.code === values.relationshipCode,
  );
  const occasion = occasions.find((item) => item.code === values.occasionCode);

  const budgetMin = parseOptionalBudget(values.budgetMin);
  const budgetMax = parseOptionalBudget(values.budgetMax);

  const preferredText = values.preferredText.trim();
  const nonPreferredText = values.nonPreferredText.trim();
  const ngText = values.ngText.trim();

  const topK =
    Number.isInteger(values.topK) && values.topK >= 1 && values.topK <= 50
      ? values.topK
      : DEFAULT_TOP_K;

  const request: RecommendationRunRequest = {
    relationship: {
      relationshipCode: values.relationshipCode,
      ...(relationship ? { relationshipLabel: relationship.label } : {}),
    },
    occasion: {
      occasionCode: values.occasionCode,
      ...(occasion ? { occasionLabel: occasion.label } : {}),
    },
    budget: {
      ...(budgetMin !== undefined ? { budgetMin } : {}),
      ...(budgetMax !== undefined ? { budgetMax } : {}),
      currency: "JPY",
      taxIncluded: true,
    },
    execution: {
      mode: "ui",
      topK,
      candidateLimit: DEFAULT_CANDIDATE_LIMIT,
      includeReason: true,
      includeDebugInfo: false,
    },
  };

  if (preferredText) {
    request.preferredCondition = { preferredText };
  }
  if (nonPreferredText) {
    request.nonPreferredCondition = { nonPreferredText };
  }
  if (ngText) {
    request.ngCondition = { ngText };
  }

  return request;
}
