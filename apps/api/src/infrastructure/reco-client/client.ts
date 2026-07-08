import { RecoError } from "./errors.js";
import type {
  RecoHealth,
  RecoRecommendationRunInput,
  RecoRecommendationRunResult,
} from "./types.js";

export interface RecoClient {
  readonly backend: string;

  healthCheck(): Promise<RecoHealth>;

  runRecommendation(
    input: RecoRecommendationRunInput,
  ): Promise<RecoRecommendationRunResult>;
}

export type ScaffoldRecoClientOptions = {
  backend?: string;
  isAvailable?: boolean;
  healthStatus?: RecoHealth["status"];
  runResult?: RecoRecommendationRunResult;
};

/**
 * Phase4a placeholder client without calling generated reco-client or reco service.
 * Phase4b wires Orval-generated functions through this boundary.
 */
export class ScaffoldRecoClient implements RecoClient {
  readonly backend: string;
  private readonly isAvailable: boolean;
  private readonly healthStatus: RecoHealth["status"];
  private readonly runResult: RecoRecommendationRunResult;

  healthCheckCalls = 0;
  readonly runRecommendationCalls: RecoRecommendationRunInput[];

  constructor(options: ScaffoldRecoClientOptions = {}) {
    this.backend = options.backend ?? "scaffold";
    this.isAvailable = options.isAvailable ?? true;
    this.healthStatus = options.healthStatus ?? "ok";
    this.runResult = options.runResult ?? {
      recommendationRunId: "run-scaffold-1",
      recommendationResultId: "result-scaffold-1",
      recommendationRequestId: "request-scaffold-1",
      items: [],
    };
    this.runRecommendationCalls = [];
  }

  async healthCheck(): Promise<RecoHealth> {
    this.healthCheckCalls += 1;

    if (!this.isAvailable) {
      throw new RecoError({
        code: "RECO_UNAVAILABLE",
        message: "reco service is unavailable",
        retryable: true,
        statusCode: 503,
      });
    }

    return {
      isAvailable: this.healthStatus === "ok",
      status: this.healthStatus,
      backend: this.backend,
    };
  }

  async runRecommendation(
    input: RecoRecommendationRunInput,
  ): Promise<RecoRecommendationRunResult> {
    this.runRecommendationCalls.push(input);

    if (!this.isAvailable) {
      throw new RecoError({
        code: "RECO_UNAVAILABLE",
        message: "reco service is unavailable",
        retryable: true,
        statusCode: 503,
      });
    }

    if (input.recommendationRequestId.trim() === "") {
      throw new RecoError({
        code: "RECO_REQUEST_FAILED",
        message: "recommendationRequestId is required",
        retryable: false,
        statusCode: 400,
      });
    }

    return {
      ...this.runResult,
      recommendationRequestId: input.recommendationRequestId,
    };
  }
}
