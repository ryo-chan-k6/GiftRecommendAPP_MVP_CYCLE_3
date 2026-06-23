import { test } from "node:test";
import assert from "node:assert/strict";
import type { Request, Response } from "express";

import { requestMetaMiddleware } from "../../../src/middlewares/request-meta.js";

test("requestMetaMiddleware preserves incoming x-trace-id", () => {
  const req = {
    header(name: string) {
      return name.toLowerCase() === "x-trace-id" ? "trace-existing" : undefined;
    },
  } as Request;
  const res = { locals: {} } as Response;

  requestMetaMiddleware(req, res, () => undefined);

  assert.equal(res.locals.apiMeta?.traceId, "trace-existing");
  assert.match(res.locals.apiMeta?.requestId ?? "", /^req_/);
});

test("requestMetaMiddleware generates traceId when header is absent", () => {
  const req = {
    header() {
      return undefined;
    },
  } as unknown as Request;
  const res = { locals: {} } as Response;

  requestMetaMiddleware(req, res, () => undefined);

  assert.match(res.locals.apiMeta?.traceId ?? "", /^[0-9a-f-]{36}$/);
});
