import type { ErrorDetail, ErrorResponseBody, RequestMeta } from "./types.js";

/** OpenAPI ErrorResponse 形式の JSON body を組み立てる。内部詳細は含めない。 */
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
