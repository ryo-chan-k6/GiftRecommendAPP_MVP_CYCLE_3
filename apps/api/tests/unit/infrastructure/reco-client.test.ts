import { test } from "node:test";
import assert from "node:assert/strict";
import {
  buildRecoFetchInit,
  buildRecoRequestUrl,
  isRecoError,
  maskRecoApiKey,
  RecoError,
  resolveRecoClientConfig,
  ScaffoldRecoClient,
} from "../../../src/infrastructure/reco-client/index.js";

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
  });

  assert.deepEqual(config, {
    baseUrl: "http://reco.local:8000",
    apiKey: "test-key",
  });
});

test("buildRecoRequestUrl joins base URL and internal path", () => {
  assert.equal(
    buildRecoRequestUrl("http://reco.local:8000/", "/internal/reco/v1/health"),
    "http://reco.local:8000/internal/reco/v1/health",
  );
});

test("buildRecoFetchInit sets Authorization header when api key exists", () => {
  const init = buildRecoFetchInit(
    { baseUrl: "http://reco.local:8000", apiKey: "secret-key" },
    { method: "GET" },
  );

  const headers = new Headers(init.headers);
  assert.equal(headers.get("Authorization"), "Bearer secret-key");
});

test("maskRecoApiKey redacts secret values", () => {
  assert.equal(maskRecoApiKey(undefined), "");
  assert.equal(maskRecoApiKey(""), "");
  assert.equal(maskRecoApiKey("secret-key"), "***REDACTED***");
});
