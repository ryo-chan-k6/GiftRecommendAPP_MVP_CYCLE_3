import { test } from "node:test";
import assert from "node:assert/strict";

import { ApiError } from "../../../../src/middlewares/error/api-error.js";
import {
  GeneratedRecoClient,
  RecoError,
  ScaffoldRecoClient,
  type RecoFetch,
} from "../../../../src/infrastructure/reco-client/index.js";
import { ScaffoldDbSession } from "../../../../src/infrastructure/db/session.js";
import { createRecoClient } from "../../../../src/lib/reco-client/factory.js";
import {
  PUBLIC_ERROR_CODES,
  RecommendationApplicationService,
  RecommendationRequestRepository,
  validateRecommendationRunRequest,
} from "../../../../src/app/recommendations/index.js";

const validRequestBody = {
  relationship: { relationshipCode: "boss" },
  occasion: { occasionCode: "thanks" },
  execution: { mode: "ui" },
};

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

function createService(recoClient: ScaffoldRecoClient | GeneratedRecoClient) {
  return new RecommendationApplicationService({
    recoClient,
    requestRepository: new RecommendationRequestRepository({
      session: new ScaffoldDbSession(),
    }),
  });
}

test("RecommendationApplicationService enriches ngKeywords before reco call", async () => {
  const recoClient = new ScaffoldRecoClient({
    runResult: {
      recommendationRunId: "run-ng",
      recommendationResultId: "result-ng",
      recommendationRequestId: "ignored",
      resultStatus: "completed",
      resultItemCount: 0,
      items: [],
    },
  });
  const service = createService(recoClient);

  await service.runRecommendation({
    request: validateRecommendationRunRequest({
      ...validRequestBody,
      ngCondition: { ngText: "アルコールはNG" },
    }),
    traceId: "trace-ng",
    requestId: "request-ng",
  });

  assert.equal(recoClient.runRecommendationCalls.length, 1);
  const passed = recoClient.runRecommendationCalls[0]
    .recommendationRequest as {
    ngCondition?: { ngText?: string; ngKeywords?: string[] };
  };
  assert.deepEqual(passed.ngCondition, {
    ngText: "アルコールはNG",
    ngKeywords: ["アルコール"],
  });
});

test("RecommendationApplicationService maps empty reco result to Public empty + GRS-REC-001", async () => {
  const recoClient = new ScaffoldRecoClient({
    runResult: {
      recommendationRunId: "run-empty",
      recommendationResultId: "result-empty",
      recommendationRequestId: "ignored",
      resultStatus: "completed",
      resultItemCount: 0,
      items: [],
    },
  });
  const service = createService(recoClient);

  const response = await service.runRecommendation({
    request: validateRecommendationRunRequest(validRequestBody),
    traceId: "trace-empty",
    requestId: "request-empty",
  });

  assert.equal(response.data.resultStatus, "empty");
  assert.equal(response.data.resultItemCount, 0);
  assert.deepEqual(response.data.items, []);
  assert.equal(response.meta.resultCode, PUBLIC_ERROR_CODES.NO_CANDIDATES);
  assert.equal(response.meta.traceId, "trace-empty");
  assert.equal(response.meta.requestId, "request-empty");
  assert.equal(recoClient.runRecommendationCalls.length, 1);
});

test("RecommendationApplicationService propagates mapped reco auth failure", async () => {
  const recoClient = new ScaffoldRecoClient();
  recoClient.runRecommendation = async () => {
    throw new RecoError({
      code: "RECO_REQUEST_FAILED",
      message: "unauthorized",
      retryable: false,
      statusCode: 401,
      upstreamCode: "GRS-AUTH-001",
    });
  };

  const service = createService(recoClient);

  await assert.rejects(
    () =>
      service.runRecommendation({
        request: validateRecommendationRunRequest(validRequestBody),
        traceId: "trace-auth",
        requestId: "request-auth",
      }),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.code, PUBLIC_ERROR_CODES.RECOMMENDATION_FAILED);
      assert.equal(error.httpStatus, 500);
      return true;
    },
  );
});

test("createRecoClient mode generated is used by RecommendationApplicationService and calls reco run endpoint", async () => {
  let calledUrl = "";
  const fetchImpl = createMockFetch((url, init) => {
    calledUrl = url;
    assert.equal(init?.method, "POST");

    return new Response(
      JSON.stringify({
        data: {
          recommendationRunId: "run-generated",
          recommendationResultId: "result-generated",
          recommendationRequestId: "request-generated",
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
              finalScore: 0.9,
              contextScore: 0.8,
              scoreBreakdown: { matching: 0.7 },
            },
          ],
        },
        meta: {
          traceId: "trace-generated",
          requestId: "request-generated",
        },
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  });

  const recoClient = createRecoClient({
    mode: "generated",
    config: baseConfig,
    generated: { fetchImpl },
  });
  assert.equal(recoClient instanceof GeneratedRecoClient, true);

  const service = createService(recoClient as GeneratedRecoClient);
  const response = await service.runRecommendation({
    request: validateRecommendationRunRequest(validRequestBody),
    traceId: "trace-generated",
    requestId: "request-generated",
  });

  assert.match(calledUrl, /\/internal\/reco\/v1\/recommendations\/run$/);
  assert.equal(response.data.items.length, 1);
  assert.equal(response.data.resultStatus, "completed");
  assert.equal("finalScore" in response.data.items[0], false);
  assert.equal(response.meta.traceId, "trace-generated");
});

test("createRecoClient mode scaffold returns ScaffoldRecoClient for DI tests", () => {
  const client = createRecoClient({ mode: "scaffold" });
  assert.equal(client instanceof ScaffoldRecoClient, true);
});
