import { test } from "node:test";
import assert from "node:assert/strict";

import { ApiError } from "../../../../src/middlewares/error/api-error.js";
import { RecoError } from "../../../../src/infrastructure/reco-client/errors.js";
import {
  mapRecoErrorToApiError,
  mapRecoResultToPublicResponse,
  PUBLIC_ERROR_CODES,
} from "../../../../src/app/recommendations/index.js";

test("mapRecoResultToPublicResponse puts traceId and requestId into meta", () => {
  const response = mapRecoResultToPublicResponse({
    recoResult: {
      recommendationRunId: "run-1",
      recommendationResultId: "result-1",
      recommendationRequestId: "req-1",
      resultItemCount: 1,
      items: [
        {
          recommendationResultItemId: "item-result-1",
          itemId: "item-1",
          rank: 1,
          itemName: "Gift",
          itemPrice: 1000,
          itemUrl: "https://example.com/item/1",
        },
      ],
    },
    recommendationRequestId: "req-1",
    traceId: "trace-from-header",
    requestId: "request-from-middleware",
    topK: 10,
    generatedAt: "2026-07-10T00:00:00.000Z",
  });

  assert.equal(response.meta.traceId, "trace-from-header");
  assert.equal(response.meta.requestId, "request-from-middleware");
  assert.equal(response.meta.generatedAt, "2026-07-10T00:00:00.000Z");
  assert.equal(response.meta.resultCode, undefined);
  assert.equal(response.data.resultStatus, "completed");
  assert.equal(response.data.resultItemCount, 1);
  assert.equal(response.data.topK, 10);
  assert.equal(response.data.fallbackUsed, false);
});

test("mapRecoResultToPublicResponse excludes warnings and internal score fields", () => {
  // Internal 側に混入しうるフィールドを意図的に渡し、Public へ漏れないことを検証する
  const recoResult = {
    recommendationRunId: "run-1",
    recommendationResultId: "result-1",
    recommendationRequestId: "req-1",
    resultItemCount: 1,
    warnings: [{ code: "W-1", message: "internal" }],
    metricSummary: { matching: 0.9 },
    items: [
      {
        recommendationResultItemId: "item-result-1",
        itemId: "item-1",
        rank: 1,
        itemName: "Gift",
        itemPrice: 1000,
        itemUrl: "https://example.com/item/1",
        finalScore: 0.91,
        contextScore: 0.88,
        scoreBreakdown: { matching: 0.7, ranking: 0.2 },
        reasonData: { source: "llm" },
        reasonSummary: "上司へのお礼に適しています",
        isFallback: false,
      },
    ],
  };

  const response = mapRecoResultToPublicResponse({
    recoResult,
    recommendationRequestId: "req-1",
    traceId: "trace-1",
    requestId: "request-1",
    topK: 10,
  });

  assert.equal("warnings" in response.data, false);
  assert.equal("metricSummary" in response.data, false);
  assert.equal("scoreBreakdown" in response.data.items[0], false);
  assert.equal("finalScore" in response.data.items[0], false);
  assert.equal("contextScore" in response.data.items[0], false);
  assert.equal("reasonData" in response.data.items[0], false);
  assert.equal(response.data.items[0].reasonSummary, "上司へのお礼に適しています");
});

test("mapRecoResultToPublicResponse maps partial status and fallbackUsed from items", () => {
  const response = mapRecoResultToPublicResponse({
    recoResult: {
      recommendationRunId: "run-1",
      recommendationResultId: "result-1",
      recommendationRequestId: "req-1",
      resultStatus: "partial",
      resultItemCount: 1,
      items: [
        {
          recommendationResultItemId: "item-result-1",
          itemId: "item-1",
          rank: 1,
          itemName: "Gift",
          itemPrice: 1000,
          itemUrl: "https://example.com/item/1",
          reasonSummary: "代替理由",
          isFallback: true,
        },
      ],
    },
    recommendationRequestId: "req-1",
    traceId: "trace-1",
    requestId: "request-1",
    topK: 5,
  });

  assert.equal(response.data.resultStatus, "partial");
  assert.equal(response.data.fallbackUsed, true);
  assert.equal(response.data.items[0].isFallback, true);
});

test("mapRecoErrorToApiError maps upstream GRS-REQ-001 to Public 400", () => {
  const apiError = mapRecoErrorToApiError(
    new RecoError({
      code: "RECO_REQUEST_FAILED",
      message: "invalid",
      retryable: false,
      statusCode: 400,
      upstreamCode: "GRS-REQ-001",
    }),
  );

  assert.ok(apiError instanceof ApiError);
  assert.equal(apiError.code, "GRS-REQ-001");
  assert.equal(apiError.httpStatus, 400);
  assert.equal(apiError.retryable, false);
});

test("mapRecoErrorToApiError maps upstream GRS-DB-001 to Public 503", () => {
  const apiError = mapRecoErrorToApiError(
    new RecoError({
      code: "RECO_REQUEST_FAILED",
      message: "db unavailable",
      retryable: true,
      statusCode: 503,
      upstreamCode: "GRS-DB-001",
    }),
  );

  assert.equal(apiError.code, "GRS-DB-001");
  assert.equal(apiError.httpStatus, 503);
});

test("mapRecoErrorToApiError maps unknown non-RecoError to 500 GRS-REC-002", () => {
  const apiError = mapRecoErrorToApiError(new Error("unexpected"));

  assert.equal(apiError.code, PUBLIC_ERROR_CODES.RECOMMENDATION_FAILED);
  assert.equal(apiError.httpStatus, 500);
  assert.equal(apiError.retryable, true);
});

test("mapRecoErrorToApiError passes through existing ApiError", () => {
  const original = new ApiError({
    code: PUBLIC_ERROR_CODES.RELATIONSHIP_REQUIRED,
    httpStatus: 400,
    message: "贈る相手を選択してください。",
    retryable: false,
  });

  const mapped = mapRecoErrorToApiError(original);
  assert.equal(mapped, original);
});
