import type { RecoClient } from "../../infrastructure/reco-client/client.js";
import type { ApiLogger } from "../../infrastructure/logger/logger.js";
import type { RecommendationRunRequest, RecommendationRunSuccessResponse } from "./types.js";
import { RecommendationRequestRepository } from "./request-repository.js";
import { mapRecoErrorToApiError } from "./reco-error-mapper.js";
import { mapRecoResultToPublicResponse } from "./response-mapper.js";

export type RecommendationApplicationServiceOptions = {
  recoClient: RecoClient;
  requestRepository: RecommendationRequestRepository;
  logger?: ApiLogger;
};

/** MOD-API-003: 永続化 → reco 呼び出し → Public Response 返却。 */
export class RecommendationApplicationService {
  private readonly recoClient: RecoClient;
  private readonly requestRepository: RecommendationRequestRepository;
  private readonly logger?: ApiLogger;

  constructor(options: RecommendationApplicationServiceOptions) {
    this.recoClient = options.recoClient;
    this.requestRepository = options.requestRepository;
    this.logger = options.logger;
  }

  async runRecommendation(input: {
    request: RecommendationRunRequest;
    traceId: string;
    requestId: string;
  }): Promise<RecommendationRunSuccessResponse> {
    let recommendationRequestId: string;

    try {
      const record = await this.requestRepository.insert({
        request: input.request,
        traceId: input.traceId,
      });
      recommendationRequestId = record.id;
    } catch (error) {
      throw mapRecoErrorToApiError(error);
    }

    this.logger?.info("recommendation_request_persisted", {
      recommendationRequestId,
      relationshipCode: input.request.relationship.relationshipCode,
      occasionCode: input.request.occasion.occasionCode,
    });

    try {
      const recoResult = await this.recoClient.runRecommendation({
        recommendationRequestId,
        recommendationRequest: input.request,
        traceId: input.traceId,
        requestId: input.requestId,
      });

      const response = mapRecoResultToPublicResponse({
        recoResult,
        recommendationRequestId,
        traceId: input.traceId,
        requestId: input.requestId,
        topK: input.request.execution.topK,
      });

      this.logger?.info("recommendation_run_completed", {
        recommendationRequestId,
        recommendationRunId: response.data.recommendationRunId,
        resultStatus: response.data.resultStatus,
        resultItemCount: response.data.resultItemCount,
        httpStatus: 200,
      });

      return response;
    } catch (error) {
      const apiError = mapRecoErrorToApiError(error);

      this.logger?.recordError({
        errorCode: apiError.code,
        errorMessage: apiError.message,
        severity: apiError.httpStatus >= 500 ? "error" : "warn",
        retryable: apiError.retryable,
        errorDetail: {
          recommendationRequestId,
          upstreamCode:
            error instanceof Error && "upstreamCode" in error
              ? (error as { upstreamCode?: string }).upstreamCode
              : undefined,
        },
      });

      throw apiError;
    }
  }
}

export function createRecommendationApplicationService(
  options: RecommendationApplicationServiceOptions,
): RecommendationApplicationService {
  return new RecommendationApplicationService(options);
}
