export {
  mergeLogContext,
  type LogContext,
} from "./context.js";
export { buildErrorLogEntry, maskErrorDetail } from "./error-log.js";
export { ApiLogger, ScaffoldApiLogger } from "./logger.js";
export type {
  ErrorLogEntry,
  ErrorLogRecordInput,
  ErrorLogSeverity,
  ErrorLogService,
  LogLevel,
  StructuredLogRecord,
} from "./types.js";
export {
  generateRequestId,
  generateTraceId,
  isValidTraceId,
  resolveTraceId,
} from "./trace-id.js";
