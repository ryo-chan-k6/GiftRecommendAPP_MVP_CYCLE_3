import { test } from "node:test";
import assert from "node:assert/strict";

import {
  buildErrorResponseBody,
  SCAFFOLD_ERROR_CODES,
} from "../../../src/lib/error-response/index.js";

const meta = {
  traceId: "trace-001",
  requestId: "req_abc123",
};

test("buildErrorResponseBody returns error and meta without details", () => {
  const body = buildErrorResponseBody({
    code: SCAFFOLD_ERROR_CODES.UNEXPECTED,
    message: "一時的な問題が発生しました。",
    retryable: true,
    meta,
  });

  assert.deepEqual(body, {
    error: {
      code: "GRS-COM-999",
      message: "一時的な問題が発生しました。",
      retryable: true,
    },
    meta,
  });
  assert.equal("details" in body.error, false);
});

test("buildErrorResponseBody omits details when empty", () => {
  const body = buildErrorResponseBody({
    code: SCAFFOLD_ERROR_CODES.VALIDATION,
    message: "入力内容を確認してください。",
    retryable: false,
    meta,
    details: [],
  });

  assert.equal("details" in body.error, false);
});

test("buildErrorResponseBody includes validation details when present", () => {
  const body = buildErrorResponseBody({
    code: SCAFFOLD_ERROR_CODES.VALIDATION,
    message: "入力内容を確認してください。",
    retryable: false,
    meta,
    details: [{ field: "budgetMax", message: "Expected number" }],
  });

  assert.deepEqual(body.error.details, [
    { field: "budgetMax", message: "Expected number" },
  ]);
});
