/** Phase4a reco-client wrapper types (aligned with Internal Reco API contract). */

export type RecoServiceStatus = "ok" | "unavailable";

export type RecoHealth = {
  isAvailable: boolean;
  status: RecoServiceStatus;
  backend: string;
};

export type RecoRecommendationRunInput = {
  recommendationRequestId: string;
  recommendationRequest: Record<string, unknown>;
};

export type RecoRecommendationRunResult = {
  recommendationRunId: string;
  recommendationResultId: string;
  recommendationRequestId: string;
  items: Array<Record<string, unknown>>;
};

export type RecoClientConfig = {
  baseUrl: string;
  apiKey?: string;
};
