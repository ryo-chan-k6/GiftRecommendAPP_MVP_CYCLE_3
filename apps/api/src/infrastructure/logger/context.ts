/** Correlation identifiers for API observability (ログ・Observability設計書 §5.1). */

export type LogContext = {
  traceId?: string;
  requestId?: string;
};

export function mergeLogContext(
  base: LogContext,
  overrides: Partial<LogContext>,
): LogContext {
  return {
    traceId: overrides.traceId ?? base.traceId,
    requestId: overrides.requestId ?? base.requestId,
  };
}
