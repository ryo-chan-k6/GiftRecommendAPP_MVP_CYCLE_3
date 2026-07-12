import { mergeLogContext, type LogContext } from "./context.js";
import { buildErrorLogEntry } from "./error-log.js";
import type {
  ErrorLogEntry,
  ErrorLogRecordInput,
  LogLevel,
  StructuredLogRecord,
} from "./types.js";

export type { LogContext } from "./context.js";
export type {
  ErrorLogEntry,
  ErrorLogRecordInput,
  ErrorLogSeverity,
  ErrorLogService,
  LogLevel,
  StructuredLogRecord,
} from "./types.js";

export interface ApiLogger {
  readonly context: LogContext;

  bind(context: Partial<LogContext>): ApiLogger;

  info(eventName: string, attributes?: Record<string, unknown>): void;

  warn(eventName: string, attributes?: Record<string, unknown>): void;

  error(eventName: string, attributes?: Record<string, unknown>): void;

  recordError(input: ErrorLogRecordInput): ErrorLogEntry;
}

export class ScaffoldApiLogger implements ApiLogger {
  readonly context: LogContext;
  readonly records: StructuredLogRecord[];
  readonly errorLogs: ErrorLogEntry[];

  constructor(
    context: LogContext = {},
    records: StructuredLogRecord[] = [],
    errorLogs: ErrorLogEntry[] = [],
  ) {
    this.context = context;
    this.records = records;
    this.errorLogs = errorLogs;
  }

  bind(context: Partial<LogContext>): ScaffoldApiLogger {
    return new ScaffoldApiLogger(
      mergeLogContext(this.context, context),
      this.records,
      this.errorLogs,
    );
  }

  info(eventName: string, attributes: Record<string, unknown> = {}): void {
    this.append("info", eventName, attributes);
  }

  warn(eventName: string, attributes: Record<string, unknown> = {}): void {
    this.append("warn", eventName, attributes);
  }

  error(eventName: string, attributes: Record<string, unknown> = {}): void {
    this.append("error", eventName, attributes);
  }

  recordError(input: ErrorLogRecordInput): ErrorLogEntry {
    const entry = buildErrorLogEntry(input, this.context);

    if (entry.traceId === "") {
      throw new Error("traceId is required to record error_log");
    }

    this.errorLogs.push(entry);
    return entry;
  }

  private append(
    level: LogLevel,
    eventName: string,
    attributes: Record<string, unknown>,
  ): void {
    this.records.push({
      timestamp: new Date().toISOString(),
      level,
      service: "api",
      traceId: this.context.traceId,
      requestId: this.context.requestId,
      eventName,
      attributes: { ...attributes },
    });
  }
}
