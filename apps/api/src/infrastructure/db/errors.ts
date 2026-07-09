/** Infrastructure-level database errors (Phase4a scaffold). */

export type DbErrorCode =
  | "DB_UNAVAILABLE"
  | "DB_QUERY_FAILED"
  | "DB_NOT_FOUND";

export class DbError extends Error {
  readonly code: DbErrorCode;
  readonly retryable: boolean;
  readonly cause?: unknown;

  constructor(input: {
    code: DbErrorCode;
    message: string;
    retryable?: boolean;
    cause?: unknown;
  }) {
    super(input.message, { cause: input.cause });
    this.name = "DbError";
    this.code = input.code;
    this.retryable = input.retryable ?? false;
    this.cause = input.cause;
  }
}

export function isDbError(error: unknown): error is DbError {
  return error instanceof DbError;
}
