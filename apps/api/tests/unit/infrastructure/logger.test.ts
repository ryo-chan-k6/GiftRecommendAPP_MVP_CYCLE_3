import { test } from "node:test";
import assert from "node:assert/strict";
import {
  ScaffoldApiLogger,
  generateRequestId,
  generateTraceId,
  isValidTraceId,
  maskErrorDetail,
  mergeLogContext,
  resolveTraceId,
} from "../../../src/infrastructure/logger/index.js";

test("mergeLogContext preserves unspecified fields", () => {
  const merged = mergeLogContext(
    { traceId: "trace-1", requestId: "req-1" },
    { requestId: "req-2" },
  );

  assert.deepEqual(merged, {
    traceId: "trace-1",
    requestId: "req-2",
  });
});

test("resolveTraceId generates when incoming is missing or invalid", () => {
  const generated = resolveTraceId();
  assert.match(generated, /^trace_/);
  assert.equal(isValidTraceId(generated), true);

  const inherited = resolveTraceId("trace_valid123");
  assert.equal(inherited, "trace_valid123");

  const replaced = resolveTraceId("invalid id!");
  assert.match(replaced, /^trace_/);
});

test("generateTraceId and generateRequestId use stable prefixes", () => {
  assert.match(generateTraceId(), /^trace_/);
  assert.match(generateRequestId(), /^req_/);
});

test("maskErrorDetail redacts sensitive keys", () => {
  const masked = maskErrorDetail({
    phase: "validation",
    authorization: "Bearer secret",
    nested: {
      api_key: "abc",
      count: 1,
    },
  });

  assert.equal(masked.phase, "validation");
  assert.equal(masked.authorization, "***REDACTED***");
  assert.deepEqual(masked.nested, {
    api_key: "***REDACTED***",
    count: 1,
  });
});

test("ScaffoldApiLogger records structured logs with bound context", () => {
  const logger = new ScaffoldApiLogger({
    traceId: "trace-1",
    requestId: "req-1",
  });

  const bound = logger.bind({ requestId: "req-2" });
  bound.info("request_received", { method: "POST" });
  logger.warn("validation_failed", { field: "budget" });

  assert.equal(logger.records.length, 2);
  assert.equal(logger.records[0]?.eventName, "request_received");
  assert.equal(logger.records[0]?.traceId, "trace-1");
  assert.equal(logger.records[0]?.requestId, "req-2");
  assert.equal(logger.records[0]?.service, "api");
  assert.deepEqual(logger.records[0]?.attributes, { method: "POST" });
  assert.equal(logger.records[1]?.level, "warn");
});

test("ScaffoldApiLogger records error_log entries with masked detail", () => {
  const logger = new ScaffoldApiLogger({
    traceId: "trace-err",
    requestId: "req-err",
  });

  const entry = logger.recordError({
    errorCode: "GRS-COM-001",
    errorMessage: "Validation failed",
    severity: "error",
    retryable: false,
    ownerType: "recommendation_request",
    ownerId: "rr-1",
    errorDetail: {
      field: "budget",
      token: "must-not-leak",
    },
  });

  assert.equal(logger.errorLogs.length, 1);
  assert.equal(entry.traceId, "trace-err");
  assert.equal(entry.requestId, "req-err");
  assert.equal(entry.service, "api");
  assert.equal(entry.errorCode, "GRS-COM-001");
  assert.deepEqual(entry.errorDetail, {
    field: "budget",
    token: "***REDACTED***",
  });
});

test("recordError requires traceId in context or input", () => {
  const logger = new ScaffoldApiLogger();

  assert.throws(
    () =>
      logger.recordError({
        errorCode: "GRS-COM-001",
        errorMessage: "missing trace",
        severity: "error",
      }),
    /traceId is required/,
  );
});
