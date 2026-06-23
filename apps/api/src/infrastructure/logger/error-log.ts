import type { LogContext } from "./context.js";
import type { ErrorLogEntry, ErrorLogRecordInput } from "./types.js";

const SENSITIVE_KEYS = new Set([
  "authorization",
  "apikey",
  "api_key",
  "password",
  "secret",
  "token",
  "cookie",
  "session",
]);

function maskValue(key: string, value: unknown): unknown {
  if (SENSITIVE_KEYS.has(key.toLowerCase())) {
    return "***REDACTED***";
  }

  if (value !== null && typeof value === "object" && !Array.isArray(value)) {
    return maskErrorDetail(value as Record<string, unknown>);
  }

  return value;
}

/** error_detail_json 向けの簡易マスキング（ログ・Observability設計書 §3.1 Secret保護）。 */
export function maskErrorDetail(
  detail: Record<string, unknown>,
): Record<string, unknown> {
  const masked: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(detail)) {
    masked[key] = maskValue(key, value);
  }

  return masked;
}

export function buildErrorLogEntry(
  input: ErrorLogRecordInput,
  context: LogContext,
): ErrorLogEntry {
  return {
    traceId: input.traceId ?? context.traceId ?? "",
    requestId: input.requestId ?? context.requestId,
    ownerType: input.ownerType,
    ownerId: input.ownerId,
    service: input.service ?? "api",
    errorCode: input.errorCode,
    errorMessage: input.errorMessage,
    severity: input.severity,
    retryable: input.retryable,
    errorDetail:
      input.errorDetail === undefined
        ? undefined
        : maskErrorDetail(input.errorDetail),
    occurredAt: input.occurredAt ?? new Date().toISOString(),
  };
}
