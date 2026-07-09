import type {
  ErrorResponse,
  RecoHealthSuccessResponse,
  RecoRecommendationRunRequest,
  RecoRecommendationRunSuccessResponse,
} from "../../generated/reco-client/giftRecommendationServiceInternalRecoAPI.schemas.js";
import type {
  RecoHealth,
  RecoRecommendationRunInput,
  RecoRecommendationRunResult,
} from "./types.js";

export function toRecoRecommendationRunRequest(
  input: RecoRecommendationRunInput,
): RecoRecommendationRunRequest {
  return {
    recommendationRequestId: input.recommendationRequestId,
    recommendationRequest:
      input.recommendationRequest as unknown as RecoRecommendationRunRequest["recommendationRequest"],
  };
}

export function toRecoHealth(
  response: RecoHealthSuccessResponse,
  backend: string,
): RecoHealth {
  const status = response.data.status;

  return {
    isAvailable: status === "ok",
    status: status === "ok" ? "ok" : "unavailable",
    backend,
  };
}

export function toRecoRecommendationRunResult(
  response: RecoRecommendationRunSuccessResponse,
): RecoRecommendationRunResult {
  return {
    recommendationRunId: response.data.recommendationRunId,
    recommendationResultId: response.data.recommendationResultId,
    recommendationRequestId: response.data.recommendationRequestId,
    items: response.data.resultItems.map((item) => ({ ...item })),
    resultStatus: response.data.resultStatus,
    resultItemCount: response.data.resultItemCount,
    meta: {
      traceId: response.meta.traceId,
      requestId: response.meta.requestId,
      resultCode: response.meta.resultCode,
    },
  };
}

export function parseRecoErrorResponse(body: unknown): ErrorResponse | undefined {
  if (body === null || typeof body !== "object") {
    return undefined;
  }

  const candidate = body as Partial<ErrorResponse>;
  if (
    candidate.error === undefined ||
    typeof candidate.error.code !== "string" ||
    typeof candidate.error.message !== "string"
  ) {
    return undefined;
  }

  return candidate as ErrorResponse;
}
