import type { ErrorResponse } from "../../generated/reco-client/giftRecommendationServiceInternalRecoAPI.schemas.js";
import { RecoError } from "./errors.js";

const RETRYABLE_UPSTREAM_CODES = new Set([
  "GRS-REC-002",
  "GRS-REC-101",
  "GRS-REC-999",
  "GRS-DB-001",
  "GRS-DB-002",
  "GRS-LLM-001",
  "GRS-LLM-002",
]);

function isRetryableUpstreamCode(code: string | undefined): boolean {
  if (code === undefined) {
    return false;
  }

  return RETRYABLE_UPSTREAM_CODES.has(code);
}

function mapStatusToInfrastructureCode(status: number): RecoError["code"] {
  if (status === 503 || status === 502 || status === 504) {
    return "RECO_UNAVAILABLE";
  }

  if (status >= 500) {
    return "RECO_REQUEST_FAILED";
  }

  if (status >= 400) {
    return "RECO_REQUEST_FAILED";
  }

  return "RECO_INVALID_RESPONSE";
}

/** Map reco ErrorResponse envelope to infrastructure RecoError. */
export function mapRecoErrorResponse(
  status: number,
  body: ErrorResponse | undefined,
): RecoError {
  const upstreamCode = body?.error.code;
  const message =
    body?.error.message ??
    `reco request failed with status ${String(status)}`;

  return new RecoError({
    code: mapStatusToInfrastructureCode(status),
    message,
    retryable: isRetryableUpstreamCode(upstreamCode),
    statusCode: status,
    upstreamCode,
  });
}

/** Map network / timeout / unexpected failures to infrastructure RecoError. */
export function mapRecoTransportError(error: unknown): RecoError {
  if (error instanceof RecoError) {
    return error;
  }

  if (error instanceof Error && error.name === "AbortError") {
    return new RecoError({
      code: "RECO_UNAVAILABLE",
      message: "reco request timed out",
      retryable: true,
      statusCode: 504,
      upstreamCode: "GRS-REC-101",
      cause: error,
    });
  }

  return new RecoError({
    code: "RECO_UNAVAILABLE",
    message: "reco service is unavailable",
    retryable: true,
    statusCode: 503,
    cause: error,
  });
}

/** Validate required reco client configuration before HTTP calls. */
export function assertRecoClientReady(config: {
  baseUrl: string;
  apiKey?: string;
}): void {
  if (config.baseUrl.trim() === "") {
    throw new RecoError({
      code: "RECO_UNAVAILABLE",
      message: "RECO_BASE_URL is not configured",
      retryable: false,
      statusCode: 500,
      upstreamCode: "GRS-AUTH-004",
    });
  }

  if (config.apiKey === undefined) {
    throw new RecoError({
      code: "RECO_UNAVAILABLE",
      message: "RECO_INTERNAL_API_KEY is not configured",
      retryable: false,
      statusCode: 500,
      upstreamCode: "GRS-AUTH-004",
    });
  }
}
