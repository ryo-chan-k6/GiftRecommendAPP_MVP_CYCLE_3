import type { ErrorRequestHandler } from "express";

import {
  buildErrorResponseBody,
  DEFAULT_UNEXPECTED_MESSAGE,
  DEFAULT_VALIDATION_MESSAGE,
  SCAFFOLD_ERROR_CODES,
} from "../../lib/error-response/index.js";
import { resolveRequestMeta } from "../request-meta.js";
import { ApiError, isApiError } from "./api-error.js";

function toApiError(error: unknown): ApiError {
  if (isApiError(error)) {
    return error;
  }

  return new ApiError({
    code: SCAFFOLD_ERROR_CODES.UNEXPECTED,
    httpStatus: 500,
    message: DEFAULT_UNEXPECTED_MESSAGE,
    retryable: true,
    cause: error,
  });
}

/** Express 末尾配置用 error middleware。内部詳細は Response へ返さない。 */
export const errorHandler: ErrorRequestHandler = (error, _req, res, _next) => {
  const apiError = toApiError(error);
  const meta = resolveRequestMeta(res);

  // 未知エラーは Phase4b 以降 logger-foundation 経由で error_log へ記録する。

  const body = buildErrorResponseBody({
    code: apiError.code,
    message: apiError.message,
    retryable: apiError.retryable,
    meta,
    details: apiError.details,
  });

  if (res.headersSent) {
    return;
  }

  res.status(apiError.httpStatus).json(body);
};

export function createValidationApiError(details: {
  field: string;
  message: string;
}[]): ApiError {
  return new ApiError({
    code: SCAFFOLD_ERROR_CODES.VALIDATION,
    httpStatus: 400,
    message: DEFAULT_VALIDATION_MESSAGE,
    retryable: false,
    details,
  });
}

export { ApiError, isApiError };
