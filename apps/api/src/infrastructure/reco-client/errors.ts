/** Infrastructure-level reco client errors. */

export type RecoErrorCode =
  | "RECO_UNAVAILABLE"
  | "RECO_REQUEST_FAILED"
  | "RECO_INVALID_RESPONSE";

export class RecoError extends Error {
  readonly code: RecoErrorCode;
  readonly retryable: boolean;
  readonly statusCode?: number;
  readonly upstreamCode?: string;
  readonly cause?: unknown;

  constructor(input: {
    code: RecoErrorCode;
    message: string;
    retryable?: boolean;
    statusCode?: number;
    upstreamCode?: string;
    cause?: unknown;
  }) {
    super(input.message, { cause: input.cause });
    this.name = "RecoError";
    this.code = input.code;
    this.retryable = input.retryable ?? false;
    this.statusCode = input.statusCode;
    this.upstreamCode = input.upstreamCode;
    this.cause = input.cause;
  }
}

export function isRecoError(error: unknown): error is RecoError {
  return error instanceof RecoError;
}
