import { test } from "node:test";
import assert from "node:assert/strict";

import { ApiError } from "../../../../src/middlewares/error/api-error.js";
import {
  PUBLIC_ERROR_CODES,
  validateRecommendationRunRequest,
} from "../../../../src/app/recommendations/index.js";

const validRequestBody = {
  relationship: { relationshipCode: "boss" },
  occasion: { occasionCode: "thanks" },
  execution: { mode: "ui" },
};

test("validateRecommendationRunRequest throws GRS-REQ-001 when budgetMin > budgetMax", () => {
  assert.throws(
    () =>
      validateRecommendationRunRequest({
        ...validRequestBody,
        budget: { budgetMin: 5000, budgetMax: 3000 },
      }),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.code, PUBLIC_ERROR_CODES.INVALID_CONDITION);
      assert.equal(error.httpStatus, 400);
      assert.equal(error.details?.[0]?.field, "budget");
      return true;
    },
  );
});

test("validateRecommendationRunRequest accepts budgetMin equal to budgetMax", () => {
  const result = validateRecommendationRunRequest({
    ...validRequestBody,
    budget: { budgetMin: 3000, budgetMax: 3000 },
  });

  assert.equal(result.budget?.budgetMin, 3000);
  assert.equal(result.budget?.budgetMax, 3000);
  assert.equal(result.budget?.currency, "JPY");
});

test("validateRecommendationRunRequest accepts budget omitted", () => {
  const result = validateRecommendationRunRequest(validRequestBody);
  assert.equal(result.budget, undefined);
});

test("validateRecommendationRunRequest throws GRS-REQ-001 when execution.mode is not ui", () => {
  assert.throws(
    () =>
      validateRecommendationRunRequest({
        ...validRequestBody,
        execution: { mode: "batch" },
      }),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.code, PUBLIC_ERROR_CODES.INVALID_CONDITION);
      assert.equal(error.httpStatus, 400);
      assert.equal(error.details?.[0]?.field, "execution.mode");
      return true;
    },
  );
});

test("validateRecommendationRunRequest throws GRS-REQ-001 when candidateLimit < topK", () => {
  assert.throws(
    () =>
      validateRecommendationRunRequest({
        ...validRequestBody,
        execution: { mode: "ui", topK: 20, candidateLimit: 10 },
      }),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.code, PUBLIC_ERROR_CODES.INVALID_CONDITION);
      assert.equal(error.details?.[0]?.field, "execution.candidateLimit");
      return true;
    },
  );
});

test("validateRecommendationRunRequest throws GRS-REQ-001 when body is not an object", () => {
  assert.throws(
    () => validateRecommendationRunRequest(null),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.code, PUBLIC_ERROR_CODES.INVALID_CONDITION);
      assert.equal(error.httpStatus, 400);
      return true;
    },
  );
});

test("validateRecommendationRunRequest throws GRS-REQ-001 when freeText exceeds maxLength", () => {
  assert.throws(
    () =>
      validateRecommendationRunRequest({
        ...validRequestBody,
        freeText: "a".repeat(801),
      }),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.code, PUBLIC_ERROR_CODES.INVALID_CONDITION);
      assert.equal(error.httpStatus, 400);
      return true;
    },
  );
});

test("validateRecommendationRunRequest trims relationship and occasion codes", () => {
  const result = validateRecommendationRunRequest({
    relationship: { relationshipCode: "  boss  " },
    occasion: { occasionCode: " thanks " },
    execution: { mode: "ui" },
  });

  assert.equal(result.relationship.relationshipCode, "boss");
  assert.equal(result.occasion.occasionCode, "thanks");
});
