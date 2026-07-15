import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiError } from "../../../../src/middlewares/error/api-error.js";
import {
  FEEDBACK_ERROR_CODES,
  validateFeedbackSubmitPath,
  validateFeedbackSubmitRequest,
} from "../../../../src/app/feedback/index.js";

const validItemBody = {
  feedbackTargetType: "item",
  resultItemId: "item-001",
  feedbackType: "item_good",
  rating: 4,
};

test("validateFeedbackSubmitRequest accepts valid item feedback", () => {
  const result = validateFeedbackSubmitRequest(validItemBody);
  assert.equal(result.feedbackTargetType, "item");
  assert.equal(result.feedbackType, "item_good");
  assert.equal(result.rating, 4);
  assert.equal(result.resultItemId, "item-001");
});

test("validateFeedbackSubmitRequest throws GRS-FDB-001 when type and target mismatch", () => {
  assert.throws(
    () =>
      validateFeedbackSubmitRequest({
        feedbackTargetType: "result",
        feedbackType: "item_good",
        rating: 4,
      }),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.code, FEEDBACK_ERROR_CODES.INVALID_CONTENT);
      assert.equal(error.httpStatus, 400);
      return true;
    },
  );
});

test("validateFeedbackSubmitRequest throws GRS-FDB-001 when rating missing", () => {
  assert.throws(
    () =>
      validateFeedbackSubmitRequest({
        feedbackTargetType: "item",
        resultItemId: "item-001",
        feedbackType: "item_good",
      }),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.code, FEEDBACK_ERROR_CODES.INVALID_CONTENT);
      return true;
    },
  );
});

test("validateFeedbackSubmitRequest throws GRS-FDB-004 when comment exceeds 500 chars", () => {
  assert.throws(
    () =>
      validateFeedbackSubmitRequest({
        ...validItemBody,
        comment: "a".repeat(501),
      }),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.code, FEEDBACK_ERROR_CODES.COMMENT_TOO_LONG);
      return true;
    },
  );
});

test("validateFeedbackSubmitRequest throws GRS-REQ-001 for non-object body", () => {
  assert.throws(
    () => validateFeedbackSubmitRequest(null),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.code, FEEDBACK_ERROR_CODES.INVALID_REQUEST);
      return true;
    },
  );
});

test("validateFeedbackSubmitRequest throws GRS-FDB-001 when item target lacks resultItemId", () => {
  assert.throws(
    () =>
      validateFeedbackSubmitRequest({
        feedbackTargetType: "item",
        feedbackType: "item_good",
        rating: 4,
      }),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.code, FEEDBACK_ERROR_CODES.INVALID_CONTENT);
      return true;
    },
  );
});

test("validateFeedbackSubmitPath trims resultId", () => {
  assert.equal(validateFeedbackSubmitPath("  result-001  "), "result-001");
});

test("validateFeedbackSubmitPath throws GRS-FDB-001 for empty resultId", () => {
  assert.throws(
    () => validateFeedbackSubmitPath(""),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.code, FEEDBACK_ERROR_CODES.INVALID_CONTENT);
      return true;
    },
  );
});
