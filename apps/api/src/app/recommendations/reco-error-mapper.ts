import { ApiError } from "../../middlewares/error/api-error.js";
import {
  isRecoError,
  type RecoError,
} from "../../infrastructure/reco-client/errors.js";
import {
  PUBLIC_ERROR_CODES,
  PUBLIC_ERROR_MESSAGES,
} from "./constants.js";

const UPSTREAM_HTTP_STATUS: Record<string, number> = {
  "GRS-REQ-001": 400,
  "GRS-REQ-002": 422,
  "GRS-REQ-003": 400,
  "GRS-REQ-004": 400,
  "GRS-REQ-005": 400,
  "GRS-REQ-006": 422,
  "GRS-REC-002": 500,
  "GRS-REC-003": 500,
  "GRS-REC-004": 500,
  "GRS-REC-005": 500,
  "GRS-REC-006": 500,
  "GRS-REC-007": 500,
  "GRS-REC-008": 500,
  "GRS-REC-009": 500,
  "GRS-REC-010": 500,
  "GRS-REC-011": 500,
  "GRS-REC-012": 500,
  "GRS-REC-013": 500,
  "GRS-REC-101": 504,
  "GRS-REC-201": 409,
  "GRS-REC-999": 500,
  "GRS-DB-001": 503,
  "GRS-DB-002": 500,
  "GRS-LLM-001": 502,
  "GRS-LLM-002": 502,
};

const UPSTREAM_MESSAGES: Record<string, string> = {
  "GRS-REQ-001": "条件を確認してください。",
  "GRS-REQ-002": "この条件では現在レコメンドできません。条件を変更してください。",
  "GRS-REQ-006": "条件を少し広げて再度お試しください。",
};

function isAuthUpstreamCode(code: string | undefined): boolean {
  return code !== undefined && code.startsWith("GRS-AUTH-");
}

function resolveUpstreamHttpStatus(code: string): number {
  return UPSTREAM_HTTP_STATUS[code] ?? 500;
}

function resolveUpstreamMessage(code: string, fallback: string): string {
  return UPSTREAM_MESSAGES[code] ?? fallback;
}

function mapTransportRecoError(error: RecoError): ApiError {
  if (error.upstreamCode === PUBLIC_ERROR_CODES.RECO_TIMEOUT) {
    return new ApiError({
      code: PUBLIC_ERROR_CODES.RECO_TIMEOUT,
      httpStatus: 504,
      message: PUBLIC_ERROR_MESSAGES.RECO_TIMEOUT,
      retryable: true,
      cause: error,
    });
  }

  // 実装仕様書 §11 No.2: transport 失敗は 502 を推奨
  return new ApiError({
    code: PUBLIC_ERROR_CODES.RECOMMENDATION_FAILED,
    httpStatus: 502,
    message: PUBLIC_ERROR_MESSAGES.RECOMMENDATION_FAILED,
    retryable: true,
    cause: error,
  });
}

function mapUpstreamRecoError(error: RecoError, upstreamCode: string): ApiError {
  if (isAuthUpstreamCode(upstreamCode)) {
    return new ApiError({
      code: PUBLIC_ERROR_CODES.RECOMMENDATION_FAILED,
      httpStatus: 500,
      message: PUBLIC_ERROR_MESSAGES.RECOMMENDATION_FAILED,
      retryable: true,
      cause: error,
    });
  }

  if (upstreamCode.startsWith("GRS-REQ-")) {
    return new ApiError({
      code: upstreamCode,
      httpStatus: resolveUpstreamHttpStatus(upstreamCode),
      message: resolveUpstreamMessage(upstreamCode, error.message),
      retryable: false,
      cause: error,
    });
  }

  return new ApiError({
    code: upstreamCode,
    httpStatus: resolveUpstreamHttpStatus(upstreamCode),
    message: PUBLIC_ERROR_MESSAGES.RECOMMENDATION_FAILED,
    retryable: true,
    cause: error,
  });
}

/** reco / transport 失敗 → Public HTTP / GRS-*（実装仕様書 §7.3.2）。 */
export function mapRecoErrorToApiError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error;
  }

  if (!isRecoError(error)) {
    return new ApiError({
      code: PUBLIC_ERROR_CODES.RECOMMENDATION_FAILED,
      httpStatus: 500,
      message: PUBLIC_ERROR_MESSAGES.RECOMMENDATION_FAILED,
      retryable: true,
      cause: error,
    });
  }

  if (error.upstreamCode !== undefined) {
    return mapUpstreamRecoError(error, error.upstreamCode);
  }

  if (error.code === "RECO_UNAVAILABLE") {
    return mapTransportRecoError(error);
  }

  return new ApiError({
    code: PUBLIC_ERROR_CODES.RECOMMENDATION_FAILED,
    httpStatus: error.statusCode ?? 500,
    message: PUBLIC_ERROR_MESSAGES.RECOMMENDATION_FAILED,
    retryable: error.retryable,
    cause: error,
  });
}
