import { test } from "node:test";
import assert from "node:assert/strict";
import type { Request, Response } from "express";

import { ApiError } from "../../../src/middlewares/error/api-error.js";
import {
  createValidationApiError,
  errorHandler,
} from "../../../src/middlewares/error/error.middleware.js";
import { requestMetaMiddleware } from "../../../src/middlewares/request-meta.js";

function createMockResponse(): Response & {
  statusCode: number;
  body: unknown;
  locals: Record<string, unknown>;
} {
  const state = {
    statusCode: 200,
    body: undefined as unknown,
    locals: {} as Record<string, unknown>,
  };

  return {
    locals: state.locals,
    status(code: number) {
      state.statusCode = code;
      return this;
    },
    json(payload: unknown) {
      state.body = payload;
      return this;
    },
    get headersSent() {
      return false;
    },
    get statusCode() {
      return state.statusCode;
    },
    get body() {
      return state.body;
    },
  } as Response & {
    statusCode: number;
    body: unknown;
    locals: Record<string, unknown>;
  };
}

test("errorHandler maps ApiError to GRS error response", () => {
  const req = {
    header() {
      return undefined;
    },
  } as unknown as Request;
  const res = createMockResponse();
  requestMetaMiddleware(req, res, () => undefined);

  const apiError = new ApiError({
    code: "GRS-COM-004",
    httpStatus: 404,
    message: "Resource not found.",
    retryable: false,
  });

  errorHandler(apiError, req, res, () => undefined);

  assert.equal(res.statusCode, 404);
  assert.deepEqual(res.body, {
    error: {
      code: "GRS-COM-004",
      message: "Resource not found.",
      retryable: false,
    },
    meta: res.locals.apiMeta,
  });
});

test("errorHandler masks unknown errors as GRS-COM-999", () => {
  const req = {
    header() {
      return undefined;
    },
  } as unknown as Request;
  const res = createMockResponse();
  requestMetaMiddleware(req, res, () => undefined);

  errorHandler(new Error("db connection failed"), req, res, () => undefined);

  const body = res.body as {
    error: { code: string; message: string; retryable: boolean };
  };

  assert.equal(res.statusCode, 500);
  assert.equal(body.error.code, "GRS-COM-999");
  assert.equal(body.error.retryable, true);
  assert.match(body.error.message, /一時的な問題/);
});

test("createValidationApiError includes field details", () => {
  const error = createValidationApiError([
    { field: "budgetMax", message: "Expected number" },
  ]);

  assert.equal(error.code, "GRS-VAL-001");
  assert.equal(error.httpStatus, 400);
  assert.deepEqual(error.details, [
    { field: "budgetMax", message: "Expected number" },
  ]);
});
