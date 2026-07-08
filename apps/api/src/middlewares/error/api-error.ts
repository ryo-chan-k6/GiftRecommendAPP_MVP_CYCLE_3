import type { ErrorDetail } from "../types.js";

/** middleware / usecase 境界で投げる業務・Validation エラー。 */
export class ApiError extends Error {
  readonly code: string;
  readonly httpStatus: number;
  readonly retryable: boolean;
  readonly details?: ErrorDetail[];

  constructor(input: {
    code: string;
    httpStatus: number;
    message: string;
    retryable?: boolean;
    details?: ErrorDetail[];
    cause?: unknown;
  }) {
    super(input.message, { cause: input.cause });
    this.name = "ApiError";
    this.code = input.code;
    this.httpStatus = input.httpStatus;
    this.retryable = input.retryable ?? false;
    this.details = input.details;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}
