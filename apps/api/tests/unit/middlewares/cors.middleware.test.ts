import { test } from "node:test";
import assert from "node:assert/strict";
import type { Request, Response } from "express";

import {
  createCorsMiddleware,
  parseAllowedOrigins,
} from "../../../src/middlewares/cors/cors.middleware.js";

function createMockResponse() {
  const state = {
    statusCode: 200,
    headers: {} as Record<string, unknown>,
    body: undefined as unknown,
  };

  return {
    get statusCode() {
      return state.statusCode;
    },
    setHeader(name: string, value: string | number | readonly string[]) {
      if (Array.isArray(value)) {
        state.headers[name.toLowerCase()] = value.join(", ");
      } else {
        state.headers[name.toLowerCase()] = value;
      }
      return this;
    },
    status(code: number) {
      state.statusCode = code;
      return this;
    },
    end() {
      return this;
    },
    json(payload: unknown) {
      state.body = payload;
      return this;
    },
    get headers() {
      return state.headers;
    },
    get body() {
      return state.body;
    },
  };
}

function createMockRequest(input: {
  method?: string;
  origin?: string;
}): Request {
  return {
    method: input.method ?? "GET",
    header(name: string) {
      if (name.toLowerCase() === "origin") {
        return input.origin;
      }
      return undefined;
    },
  } as Request;
}

test("parseAllowedOrigins splits comma-separated env values", () => {
  assert.deepEqual(
    parseAllowedOrigins("http://localhost:3000,https://example.test"),
    ["http://localhost:3000", "https://example.test"],
  );
});

test("createCorsMiddleware allows configured origin", () => {
  const middleware = createCorsMiddleware({
    allowedOrigins: ["http://localhost:3000"],
  });
  const req = createMockRequest({ origin: "http://localhost:3000" });
  const res = createMockResponse();
  let nextCalled = false;

  middleware(req, res as unknown as Response, () => {
    nextCalled = true;
  });

  assert.equal(nextCalled, true);
  assert.equal(res.headers["access-control-allow-origin"], "http://localhost:3000");
});

test("createCorsMiddleware responds 204 for OPTIONS preflight", () => {
  const middleware = createCorsMiddleware({
    allowedOrigins: ["http://localhost:3000"],
  });
  const req = createMockRequest({
    method: "OPTIONS",
    origin: "http://localhost:3000",
  });
  const res = createMockResponse();
  let nextCalled = false;

  middleware(req, res as unknown as Response, () => {
    nextCalled = true;
  });

  assert.equal(nextCalled, false);
  assert.equal(res.statusCode, 204);
});

test("createCorsMiddleware omits allow-origin for disallowed origin", () => {
  const middleware = createCorsMiddleware({
    allowedOrigins: ["http://localhost:3000"],
  });
  const req = createMockRequest({ origin: "https://evil.example" });
  const res = createMockResponse();

  middleware(req, res as unknown as Response, () => undefined);

  assert.equal(res.headers["access-control-allow-origin"], undefined);
});
