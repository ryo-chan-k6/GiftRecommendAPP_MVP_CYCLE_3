import type {
  RecoHealthSuccessResponse,
  RecoRecommendationRunRequest,
  RecoRecommendationRunSuccessResponse,
} from "../../generated/reco-client/giftRecommendationServiceInternalRecoAPI.schemas.js";
import { getRecoHealth } from "../../generated/reco-client/reco-health/reco-health.js";
import { runRecoRecommendation } from "../../generated/reco-client/reco-recommendations/reco-recommendations.js";
import {
  assertRecoClientReady,
  mapRecoErrorResponse,
  mapRecoTransportError,
} from "./error-mapper.js";
import { parseRecoErrorResponse } from "./mapper.js";
import {
  runWithRecoFetchRuntime,
  type RecoFetch,
} from "./orval-mutator.js";
import type { RecoClientConfig, RecoTraceContext } from "./types.js";

export type { RecoFetch } from "./orval-mutator.js";

type RecoGeneratedCallOptions = {
  config: RecoClientConfig;
  trace?: RecoTraceContext;
  fetchImpl?: RecoFetch;
};

function createRecoFetchRuntime(
  options: RecoGeneratedCallOptions,
): {
  config: RecoClientConfig;
  trace?: RecoTraceContext;
  fetchImpl?: RecoFetch;
} {
  return {
    config: options.config,
    trace: options.trace,
    fetchImpl: options.fetchImpl,
  };
}

async function invokeGeneratedCall<T>(
  options: RecoGeneratedCallOptions,
  call: () => Promise<{ data: unknown; status: number }>,
): Promise<T> {
  assertRecoClientReady(options.config);

  try {
    const response = await runWithRecoFetchRuntime(
      createRecoFetchRuntime(options),
      call,
    );

    if (response.status !== 200) {
      throw mapRecoErrorResponse(
        response.status,
        parseRecoErrorResponse(response.data),
      );
    }

    return response.data as T;
  } catch (error) {
    throw mapRecoTransportError(error);
  }
}

/** Invoke API-INT-001 via generated reco-client with wrapper error mapping. */
export async function callGetRecoHealth(
  options: RecoGeneratedCallOptions,
): Promise<RecoHealthSuccessResponse> {
  return invokeGeneratedCall<RecoHealthSuccessResponse>(options, () =>
    getRecoHealth({
      headers: {
        Accept: "application/json",
      },
    }),
  );
}

/** Invoke API-INT-002 via generated reco-client with wrapper error mapping. */
export async function callRunRecoRecommendation(
  request: RecoRecommendationRunRequest,
  options: RecoGeneratedCallOptions,
): Promise<RecoRecommendationRunSuccessResponse> {
  return invokeGeneratedCall<RecoRecommendationRunSuccessResponse>(options, () =>
    runRecoRecommendation(request, {
      headers: {
        Accept: "application/json",
      },
    }),
  );
}
