import { test } from "node:test";
import assert from "node:assert/strict";
import { createRecoClient } from "../../../src/lib/reco-client/index.js";
import {
  buildRecoFetchInit,
  buildRecoRequestUrl,
  DEFAULT_RECO_REQUEST_TIMEOUT_MS,
  GeneratedRecoClient,
  isRecoError,
  maskRecoApiKey,
  RECO_INTERNAL_API_KEY_HEADER,
  RECO_REQUEST_ID_HEADER,
  RECO_TRACE_ID_HEADER,
  RecoError,
  resolveRecoClientConfig,
  ScaffoldRecoClient,
  type RecoFetch,
} from "../../../src/infrastructure/reco-client/index.js";

const baseConfig = {
  baseUrl: "http://reco.local:8000",
  apiKey: "test-key",
  timeoutMs: 100,
};

function createMockFetch(
  handler: (url: string, init?: RequestInit) => Response | Promise<Response>,
): RecoFetch {
  return ((url: RequestInfo | URL, init?: RequestInit) => {
    const resolvedUrl =
      typeof url === "string"
        ? url
        : url instanceof URL
          ? url.toString()
          : url.url;
    return Promise.resolve(handler(resolvedUrl, init));
  }) as RecoFetch;
}

test("ScaffoldRecoClient reports health when available", async () => {
  const client = new ScaffoldRecoClient();

  const health = await client.healthCheck();

  assert.equal(client.healthCheckCalls, 1);
  assert.deepEqual(health, {
    isAvailable: true,
    status: "ok",
    backend: "scaffold",
  });
});

test("ScaffoldRecoClient throws RecoError when unavailable", async () => {
  const client = new ScaffoldRecoClient({ isAvailable: false });

  await assert.rejects(
    () => client.healthCheck(),
    (error: unknown) => {
      assert.equal(isRecoError(error), true);
      assert.equal((error as RecoError).code, "RECO_UNAVAILABLE");
      assert.equal((error as RecoError).retryable, true);
      return true;
    },
  );
});

test("ScaffoldRecoClient runs recommendation with request id", async () => {
  const client = new ScaffoldRecoClient({
    runResult: {
      recommendationRunId: "run-1",
      recommendationResultId: "result-1",
      recommendationRequestId: "ignored",
      items: [{ itemId: "item-1" }],
    },
  });

  const result = await client.runRecommendation({
    recommendationRequestId: "req-42",
    recommendationRequest: { occasionCode: "birthday" },
    traceId: "trace-42",
    requestId: "req-42",
  });

  assert.equal(client.runRecommendationCalls.length, 1);
  assert.equal(result.recommendationRequestId, "req-42");
  assert.equal(result.recommendationRunId, "run-1");
  assert.deepEqual(result.items, [{ itemId: "item-1" }]);
});

test("ScaffoldRecoClient rejects empty recommendationRequestId", async () => {
  const client = new ScaffoldRecoClient();

  await assert.rejects(
    () =>
      client.runRecommendation({
        recommendationRequestId: "  ",
        recommendationRequest: {},
        traceId: "trace-1",
        requestId: "req-1",
      }),
    (error: unknown) => {
      assert.equal(isRecoError(error), true);
      assert.equal((error as RecoError).code, "RECO_REQUEST_FAILED");
      return true;
    },
  );
});

test("resolveRecoClientConfig reads environment variable names", () => {
  const config = resolveRecoClientConfig({
    RECO_BASE_URL: "http://reco.local:8000",
    RECO_INTERNAL_API_KEY: "test-key",
    RECO_REQUEST_TIMEOUT_MS: "6000",
  });

  assert.deepEqual(config, {
    baseUrl: "http://reco.local:8000",
    apiKey: "test-key",
    timeoutMs: 6000,
  });
});

test("resolveRecoClientConfig defaults timeout to 9000ms (above hard 8000ms)", () => {
  const config = resolveRecoClientConfig({
    RECO_BASE_URL: "http://reco.local:8000",
    RECO_INTERNAL_API_KEY: "test-key",
  });

  assert.equal(config.timeoutMs, DEFAULT_RECO_REQUEST_TIMEOUT_MS);
  assert.equal(config.timeoutMs, 9000);
});

test("buildRecoRequestUrl joins base URL and internal path", () => {
  assert.equal(
    buildRecoRequestUrl("http://reco.local:8000/", "/internal/reco/v1/health"),
    "http://reco.local:8000/internal/reco/v1/health",
  );
});

test("buildRecoFetchInit sets Internal API Key and trace headers", () => {
  const init = buildRecoFetchInit(
    { baseUrl: "http://reco.local:8000", apiKey: "secret-key" },
    { method: "GET" },
    { traceId: "trace-1", requestId: "req-1" },
  );

  const headers = new Headers(init.headers);
  assert.equal(headers.get(RECO_INTERNAL_API_KEY_HEADER), "secret-key");
  assert.equal(headers.get(RECO_TRACE_ID_HEADER), "trace-1");
  assert.equal(headers.get(RECO_REQUEST_ID_HEADER), "req-1");
});

test("maskRecoApiKey redacts secret values", () => {
  assert.equal(maskRecoApiKey(undefined), "");
  assert.equal(maskRecoApiKey(""), "");
  assert.equal(maskRecoApiKey("secret-key"), "***REDACTED***");
});

test("GeneratedRecoClient healthCheck maps ok response", async () => {
  const fetchImpl = createMockFetch((url, init) => {
    assert.equal(url, "http://reco.local:8000/internal/reco/v1/health");
    assert.equal(init?.method, "GET");
    const headers = new Headers(init?.headers);
    assert.equal(headers.get(RECO_INTERNAL_API_KEY_HEADER), "test-key");

    return new Response(
      JSON.stringify({
        data: {
          status: "ok",
          service: "reco",
        },
        meta: {
          traceId: "trace-health",
          requestId: "req-health",
        },
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  });

  const client = new GeneratedRecoClient({
    config: baseConfig,
    fetchImpl,
  });

  const health = await client.healthCheck({
    traceId: "trace-health",
    requestId: "req-health",
  });

  assert.deepEqual(health, {
    isAvailable: true,
    status: "ok",
    backend: "reco",
  });
});

test("GeneratedRecoClient runRecommendation sends trace headers and maps resultItems", async () => {
  const fetchImpl = createMockFetch((url, init) => {
    assert.equal(
      url,
      "http://reco.local:8000/internal/reco/v1/recommendations/run",
    );
    assert.equal(init?.method, "POST");

    const headers = new Headers(init?.headers);
    assert.equal(headers.get(RECO_INTERNAL_API_KEY_HEADER), "test-key");
    assert.equal(headers.get(RECO_TRACE_ID_HEADER), "trace-run");
    assert.equal(headers.get(RECO_REQUEST_ID_HEADER), "req-run");

    return new Response(
      JSON.stringify({
        data: {
          recommendationRunId: "run-1",
          recommendationResultId: "result-1",
          recommendationRequestId: "request-1",
          resultStatus: "completed",
          topK: 10,
          resultItemCount: 1,
          fallbackUsed: false,
          resultItems: [
            {
              recommendationResultItemId: "item-result-1",
              itemId: "item-1",
              rank: 1,
              itemName: "Gift",
              itemPrice: 3000,
              itemUrl: "https://example.com/item-1",
              contextScore: 0.8,
              finalScore: 0.75,
            },
          ],
        },
        meta: {
          traceId: "trace-run",
          requestId: "req-run",
          resultCode: "GRS-REC-000",
        },
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  });

  const client = new GeneratedRecoClient({
    config: baseConfig,
    fetchImpl,
  });

  const result = await client.runRecommendation({
    recommendationRequestId: "request-1",
    recommendationRequest: {
      relationship: { relationshipCode: "boss" },
      occasion: { occasionCode: "thanks" },
      execution: { mode: "ui" },
    },
    traceId: "trace-run",
    requestId: "req-run",
  });

  assert.equal(result.recommendationRunId, "run-1");
  assert.equal(result.resultItemCount, 1);
  assert.equal(result.items.length, 1);
  assert.equal(result.items[0]?.itemId, "item-1");
  assert.deepEqual(result.meta, {
    traceId: "trace-run",
    requestId: "req-run",
    resultCode: "GRS-REC-000",
  });
});

test("GeneratedRecoClient maps reco auth error to RecoError with upstream code", async () => {
  const fetchImpl = createMockFetch(() => {
    return new Response(
      JSON.stringify({
        error: {
          code: "GRS-AUTH-001",
          message: "認証に失敗しました。",
        },
        meta: {
          traceId: "trace-auth",
          requestId: "req-auth",
        },
      }),
      { status: 401, headers: { "Content-Type": "application/json" } },
    );
  });

  const client = new GeneratedRecoClient({
    config: baseConfig,
    fetchImpl,
  });

  await assert.rejects(
    () =>
      client.runRecommendation({
        recommendationRequestId: "request-1",
        recommendationRequest: {
          relationship: { relationshipCode: "boss" },
          occasion: { occasionCode: "thanks" },
          execution: { mode: "ui" },
        },
        traceId: "trace-auth",
        requestId: "req-auth",
      }),
    (error: unknown) => {
      assert.equal(isRecoError(error), true);
      const recoError = error as RecoError;
      assert.equal(recoError.code, "RECO_REQUEST_FAILED");
      assert.equal(recoError.upstreamCode, "GRS-AUTH-001");
      assert.equal(recoError.statusCode, 401);
      return true;
    },
  );
});

test("GeneratedRecoClient maps timeout to retryable RecoError", async () => {
  const fetchImpl = createMockFetch(() => {
    const error = new Error("aborted");
    error.name = "AbortError";
    return Promise.reject(error);
  });

  const client = new GeneratedRecoClient({
    config: { ...baseConfig, timeoutMs: 1 },
    fetchImpl,
  });

  await assert.rejects(
    () => client.healthCheck(),
    (error: unknown) => {
      assert.equal(isRecoError(error), true);
      const recoError = error as RecoError;
      assert.equal(recoError.code, "RECO_UNAVAILABLE");
      assert.equal(recoError.upstreamCode, "GRS-REC-101");
      assert.equal(recoError.retryable, true);
      return true;
    },
  );
});

test("createRecoClient returns scaffold client in scaffold mode", () => {
  const client = createRecoClient({ mode: "scaffold" });
  assert.equal(client instanceof ScaffoldRecoClient, true);
});

test("createRecoClient returns generated client in generated mode", () => {
  const client = createRecoClient({
    mode: "generated",
    config: baseConfig,
  });
  assert.equal(client instanceof GeneratedRecoClient, true);
});
