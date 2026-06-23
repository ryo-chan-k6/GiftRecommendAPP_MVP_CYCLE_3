import type { ErrorDetail, ErrorResponseBody, RequestMeta } from "../types.js";

/** Phase4a 骨格。A4 common-error-response Task で apps/api/src/lib へ移管予定。 */
export function buildErrorResponseBody(input: {
  code: string;
  message: string;
  retryable: boolean;
  meta: RequestMeta;
  details?: ErrorDetail[];
}): ErrorResponseBody {
  const body: ErrorResponseBody = {
    error: {
      code: input.code,
      message: input.message,
      retryable: input.retryable,
    },
    meta: input.meta,
  };

  if (input.details !== undefined && input.details.length > 0) {
    body.error.details = input.details;
  }

  return body;
}
