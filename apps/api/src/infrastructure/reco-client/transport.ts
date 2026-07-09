import type {
  RecoHealthSuccessResponse,
  RecoRecommendationRunRequest,
  RecoRecommendationRunSuccessResponse,
} from "../../generated/reco-client/giftRecommendationServiceInternalRecoAPI.schemas.js";
import {
  buildRecoFetchInit,
  buildRecoRequestUrl,
  resolveRecoRequestTimeoutMs,
} from "./config.js";
import {
  assertRecoClientReady,
  mapRecoErrorResponse,
  mapRecoTransportError,
} from "./error-mapper.js";
import { parseRecoErrorResponse } from "./mapper.js";
import {
  RECO_HEALTH_PATH,
  RECO_RECOMMENDATIONS_RUN_PATH,
} from "./paths.js";
import type { RecoClientConfig, RecoTraceContext } from "./types.js";

export type RecoFetch = typeof fetch;

type RecoGeneratedCallOptions = {
  config: RecoClientConfig;
  trace?: RecoTraceContext;
  fetchImpl?: RecoFetch;
};

async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number,
  fetchImpl: RecoFetch,
): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetchImpl(url, {
      ...init,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }
}

async function parseJsonBody<T>(response: Response): Promise<T> {
  const body = [204, 205, 304].includes(response.status)
    ? null
    : await response.text();

  return (body ? JSON.parse(body) : {}) as T;
}

/** Invoke API-INT-001 via generated-compatible path with wrapper fetch/header policy. */
export async function callGetRecoHealth(
  options: RecoGeneratedCallOptions,
): Promise<RecoHealthSuccessResponse> {
  assertRecoClientReady(options.config);

  const fetchImpl = options.fetchImpl ?? fetch;
  const timeoutMs = resolveRecoRequestTimeoutMs(options.config);
  const requestInit = buildRecoFetchInit(
    options.config,
    {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    },
    options.trace,
  );
  const url = buildRecoRequestUrl(options.config.baseUrl, RECO_HEALTH_PATH);

  try {
    const response = await fetchWithTimeout(
      url,
      requestInit,
      timeoutMs,
      fetchImpl,
    );
    const data = await parseJsonBody<RecoHealthSuccessResponse | unknown>(
      response,
    );

    if (response.status !== 200) {
      throw mapRecoErrorResponse(
        response.status,
        parseRecoErrorResponse(data),
      );
    }

    return data as RecoHealthSuccessResponse;
  } catch (error) {
    throw mapRecoTransportError(error);
  }
}

/** Invoke API-INT-002 via generated-compatible path with wrapper fetch/header policy. */
export async function callRunRecoRecommendation(
  request: RecoRecommendationRunRequest,
  options: RecoGeneratedCallOptions,
): Promise<RecoRecommendationRunSuccessResponse> {
  assertRecoClientReady(options.config);

  const fetchImpl = options.fetchImpl ?? fetch;
  const timeoutMs = resolveRecoRequestTimeoutMs(options.config);
  const requestInit = buildRecoFetchInit(
    options.config,
    {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
    options.trace,
  );
  const url = buildRecoRequestUrl(
    options.config.baseUrl,
    RECO_RECOMMENDATIONS_RUN_PATH,
  );

  try {
    const response = await fetchWithTimeout(
      url,
      requestInit,
      timeoutMs,
      fetchImpl,
    );
    const data = await parseJsonBody<RecoRecommendationRunSuccessResponse | unknown>(
      response,
    );

    if (response.status !== 200) {
      throw mapRecoErrorResponse(
        response.status,
        parseRecoErrorResponse(data),
      );
    }

    return data as RecoRecommendationRunSuccessResponse;
  } catch (error) {
    throw mapRecoTransportError(error);
  }
}
