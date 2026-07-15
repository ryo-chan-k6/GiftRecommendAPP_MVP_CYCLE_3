import assert from "node:assert/strict";
import { test } from "node:test";

import { ApiError } from "../../../../src/middlewares/error/api-error.js";
import {
  ITEM_DETAIL_ERROR_CODES,
  ITEM_ID_MAX_LENGTH,
  validateItemId,
} from "../../../../src/app/items/index.js";

test("validateItemId accepts valid itemId", () => {
  const itemId = "550e8400-e29b-41d4-a716-446655440001";
  assert.equal(validateItemId(itemId), itemId);
});

test("validateItemId rejects empty and whitespace", () => {
  for (const value of ["", "   ", undefined]) {
    assert.throws(
      () => validateItemId(value),
      (error: unknown) => {
        assert.ok(error instanceof ApiError);
        assert.equal(error.httpStatus, 400);
        assert.equal(error.code, ITEM_DETAIL_ERROR_CODES.INVALID_REQUEST);
        return true;
      },
    );
  }
});

test("validateItemId rejects invalid characters", () => {
  assert.throws(
    () => validateItemId("item@001"),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.code, ITEM_DETAIL_ERROR_CODES.INVALID_REQUEST);
      return true;
    },
  );
});

test("validateItemId rejects maxLength overflow", () => {
  const tooLong = "a".repeat(ITEM_ID_MAX_LENGTH + 1);
  assert.throws(
    () => validateItemId(tooLong),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.code, ITEM_DETAIL_ERROR_CODES.INVALID_REQUEST);
      return true;
    },
  );
});
