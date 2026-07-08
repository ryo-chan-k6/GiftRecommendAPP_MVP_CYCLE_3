/** Infrastructure-level reco client errors (Phase4a scaffold). */

export type RecoErrorCode =
  | "RECO_UNAVAILABLE"
  | "RECO_REQUEST_FAILED"
  | "RECO_INVALID_RESPONSE";

export class RecoError extends Error {
  readonly code: RecoErrorCode;
  readonly retryable: boolean;
  readonly statusCode?: number;
  readonly cause?: unknown;

  constructor(input: {
    code: RecoErrorCode;
    message: string;
    retryable?: boolean;
    statusCode?: number;
    cause?: unknown;
  }) {
    super(input.message, { cause: input.cause });
    this.name = "RecoError";
    this.code = input.code;
    this.retryable = input.retryable ?? false;
    this.statusCode = input.statusCode;
    this.cause = input.cause;
  }
}

export function isRecoError(error: unknown): error is RecoError {
  return error instanceof RecoError;
}
