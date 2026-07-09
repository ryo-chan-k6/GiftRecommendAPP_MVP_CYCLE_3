/** Phase4a reco-client wrapper types (aligned with Internal Reco API contract). */

export type RecoServiceStatus = "ok" | "unavailable";

export type RecoHealth = {
  isAvailable: boolean;
  status: RecoServiceStatus;
  backend: string;
};

export type RecoTraceContext = {
  traceId?: string;
  requestId?: string;
};

export type RecoRecommendationRunInput = {
  recommendationRequestId: string;
  recommendationRequest: Record<string, unknown>;
  traceId: string;
  requestId: string;
};

export type RecoRecommendationRunResult = {
  recommendationRunId: string;
  recommendationResultId: string;
  recommendationRequestId: string;
  items: Array<Record<string, unknown>>;
  resultStatus?: string;
  resultItemCount?: number;
  meta?: {
    traceId?: string;
    requestId?: string;
    resultCode?: string;
  };
};

export type RecoClientConfig = {
  baseUrl: string;
  apiKey?: string;
  timeoutMs?: number;
};
