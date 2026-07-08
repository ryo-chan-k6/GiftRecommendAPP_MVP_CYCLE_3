import { test } from "node:test";
import assert from "node:assert/strict";
import type { NextFunction, Request, Response } from "express";
import { z } from "zod";

import { ApiError } from "../../../src/middlewares/error/api-error.js";
import { createValidationMiddleware } from "../../../src/middlewares/validation/validation.middleware.js";

test("createValidationMiddleware passes parsed body to next", () => {
  const schema = z.object({
    budgetMax: z.number().int().positive(),
  });
  const middleware = createValidationMiddleware(schema, "body");

  const req = { body: { budgetMax: 5000 } } as Request;
  let nextError: unknown;

  middleware(req, {} as Response, ((error?: unknown) => {
    nextError = error;
  }) as NextFunction);

  assert.equal(nextError, undefined);
  assert.deepEqual(req.body, { budgetMax: 5000 });
});

test("createValidationMiddleware forwards validation ApiError", () => {
  const schema = z.object({
    budgetMax: z.number().int().positive(),
  });
  const middleware = createValidationMiddleware(schema, "body");

  const req = { body: { budgetMax: "invalid" } } as Request;
  let nextError: unknown;

  middleware(req, {} as Response, ((error?: unknown) => {
    nextError = error;
  }) as NextFunction);

  assert.ok(nextError instanceof ApiError);
  assert.equal((nextError as ApiError).code, "GRS-VAL-001");
  assert.ok((nextError as ApiError).details?.some((detail) => detail.field === "budgetMax"));
});
