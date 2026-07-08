import { randomUUID } from "node:crypto";

/** Header 等から受け取る trace_id の最小検証（API設計方針書 §12.2）。 */
const TRACE_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._-]{7,127}$/;

export function isValidTraceId(value: string): boolean {
  return TRACE_ID_PATTERN.test(value);
}

export function generateTraceId(): string {
  return `trace_${randomUUID().replace(/-/g, "")}`;
}

export function generateRequestId(): string {
  return `req_${randomUUID().replace(/-/g, "")}`;
}

/**
 * web から trace_id が来ない場合は新規生成し、来る場合は検証して引き継ぐ。
 */
export function resolveTraceId(incoming?: string | null): string {
  if (incoming === undefined || incoming === null || incoming.trim() === "") {
    return generateTraceId();
  }

  const normalized = incoming.trim();
  if (!isValidTraceId(normalized)) {
    return generateTraceId();
  }

  return normalized;
}
