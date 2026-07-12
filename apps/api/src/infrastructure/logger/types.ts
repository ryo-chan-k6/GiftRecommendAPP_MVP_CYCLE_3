/** Structured log and error_log types for Phase4a API logger scaffold. */

export type LogLevel = "debug" | "info" | "warn" | "error" | "critical";

/** error_log.service — web は DB 非保存のため含めない（コード定義書 §6.4）。 */
export type ErrorLogService = "api" | "reco" | "batch";

/** error_log.severity（コード定義書 §6.5）。 */
export type ErrorLogSeverity = "warn" | "error" | "critical";

export type StructuredLogRecord = {
  timestamp: string;
  level: LogLevel;
  service: "api";
  traceId?: string;
  requestId?: string;
  eventName: string;
  message?: string;
  attributes: Record<string, unknown>;
};

export type ErrorLogEntry = {
  traceId: string;
  requestId?: string;
  ownerType?: string;
  ownerId?: string;
  service: ErrorLogService;
  errorCode: string;
  errorMessage: string;
  severity: ErrorLogSeverity;
  retryable?: boolean;
  errorDetail?: Record<string, unknown>;
  occurredAt: string;
};

export type ErrorLogRecordInput = {
  traceId?: string;
  requestId?: string;
  ownerType?: string;
  ownerId?: string;
  service?: ErrorLogService;
  errorCode: string;
  errorMessage: string;
  severity: ErrorLogSeverity;
  retryable?: boolean;
  errorDetail?: Record<string, unknown>;
  occurredAt?: string;
};
