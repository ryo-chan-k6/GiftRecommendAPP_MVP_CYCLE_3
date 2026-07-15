import { z } from "zod";

import { ApiError } from "../../middlewares/error/api-error.js";
import {
  FEEDBACK_ERROR_CODES,
  FEEDBACK_ERROR_MESSAGES,
  FEEDBACK_TARGET_TYPES,
  FEEDBACK_TYPE_ALLOWED_TARGETS,
  FEEDBACK_TYPES,
  FEEDBACK_VALUE_TYPES,
  MAX_COMMENT_LENGTH,
} from "./constants.js";
import type { FeedbackSubmitRequest, FeedbackType } from "./types.js";

const feedbackTargetTypeSchema = z.enum(FEEDBACK_TARGET_TYPES);
const feedbackTypeSchema = z.enum(FEEDBACK_TYPES);
const feedbackValueTypeSchema = z.enum(FEEDBACK_VALUE_TYPES);

const feedbackSubmitBodySchema = z.object({
  feedbackTargetType: feedbackTargetTypeSchema,
  feedbackType: feedbackTypeSchema,
  rating: z.number().int().min(1).max(5),
  resultItemId: z.string().optional(),
  reasonId: z.string().optional(),
  feedbackValueType: feedbackValueTypeSchema.optional(),
  feedbackValue: z.union([z.boolean(), z.number(), z.string()]).optional(),
  feedbackChoiceCode: z.string().optional(),
  feedbackReasonCategory: z.string().optional(),
  comment: z.string().optional(),
  sourcePage: z.string().optional(),
  sessionId: z.string().optional(),
});

function throwValidationError(
  code: string,
  message: string,
  details?: { field: string; message: string }[],
): never {
  throw new ApiError({
    code,
    httpStatus: 400,
    message,
    retryable: false,
    details,
  });
}

function assertTypeTargetConsistency(
  feedbackType: FeedbackType,
  feedbackTargetType: FeedbackSubmitRequest["feedbackTargetType"],
): void {
  const allowed = FEEDBACK_TYPE_ALLOWED_TARGETS[feedbackType];
  if (allowed === "any") {
    return;
  }

  if (!allowed.includes(feedbackTargetType)) {
    throwValidationError(
      FEEDBACK_ERROR_CODES.INVALID_CONTENT,
      FEEDBACK_ERROR_MESSAGES.INVALID_CONTENT,
      [
        {
          field: "feedbackType",
          message: "feedbackType is not allowed for feedbackTargetType",
        },
      ],
    );
  }
}

function assertConditionalRequiredFields(
  input: z.infer<typeof feedbackSubmitBodySchema>,
): void {
  if (input.feedbackTargetType === "item") {
    if (input.resultItemId === undefined || input.resultItemId.trim() === "") {
      throwValidationError(
        FEEDBACK_ERROR_CODES.INVALID_CONTENT,
        FEEDBACK_ERROR_MESSAGES.INVALID_CONTENT,
        [{ field: "resultItemId", message: "resultItemId is required" }],
      );
    }
  }

  if (input.feedbackTargetType === "reason") {
    if (input.reasonId === undefined || input.reasonId.trim() === "") {
      throwValidationError(
        FEEDBACK_ERROR_CODES.INVALID_CONTENT,
        FEEDBACK_ERROR_MESSAGES.INVALID_CONTENT,
        [{ field: "reasonId", message: "reasonId is required" }],
      );
    }
  }
}

/** 契約仕様書 §9 に基づく Path / Body Validation。 */
export function validateFeedbackSubmitPath(resultId: unknown): string {
  if (typeof resultId !== "string" || resultId.trim() === "") {
    throwValidationError(
      FEEDBACK_ERROR_CODES.INVALID_CONTENT,
      FEEDBACK_ERROR_MESSAGES.INVALID_CONTENT,
      [{ field: "resultId", message: "resultId is required" }],
    );
  }

  return resultId.trim();
}

/** 契約仕様書 §9 に基づく Body Validation。 */
export function validateFeedbackSubmitRequest(body: unknown): FeedbackSubmitRequest {
  if (body === null || typeof body !== "object") {
    throwValidationError(
      FEEDBACK_ERROR_CODES.INVALID_REQUEST,
      FEEDBACK_ERROR_MESSAGES.INVALID_REQUEST,
    );
  }

  const parsed = feedbackSubmitBodySchema.safeParse(body);
  if (!parsed.success) {
    const hasCommentLengthIssue = parsed.error.issues.some(
      (issue) =>
        issue.path.length === 1 &&
        issue.path[0] === "comment" &&
        issue.code === "too_big",
    );

    if (hasCommentLengthIssue) {
      throwValidationError(
        FEEDBACK_ERROR_CODES.COMMENT_TOO_LONG,
        FEEDBACK_ERROR_MESSAGES.COMMENT_TOO_LONG,
        [{ field: "comment", message: `comment must be at most ${MAX_COMMENT_LENGTH} characters` }],
      );
    }

    throwValidationError(
      FEEDBACK_ERROR_CODES.INVALID_CONTENT,
      FEEDBACK_ERROR_MESSAGES.INVALID_CONTENT,
      parsed.error.issues.map((issue) => ({
        field: issue.path.length > 0 ? issue.path.join(".") : "_root",
        message: issue.message,
      })),
    );
  }

  const input = parsed.data;

  if (input.comment !== undefined && input.comment.length > MAX_COMMENT_LENGTH) {
    throwValidationError(
      FEEDBACK_ERROR_CODES.COMMENT_TOO_LONG,
      FEEDBACK_ERROR_MESSAGES.COMMENT_TOO_LONG,
      [{ field: "comment", message: `comment must be at most ${MAX_COMMENT_LENGTH} characters` }],
    );
  }

  assertTypeTargetConsistency(input.feedbackType, input.feedbackTargetType);
  assertConditionalRequiredFields(input);

  return {
    feedbackTargetType: input.feedbackTargetType,
    feedbackType: input.feedbackType,
    rating: input.rating,
    ...(input.resultItemId !== undefined
      ? { resultItemId: input.resultItemId.trim() }
      : {}),
    ...(input.reasonId !== undefined ? { reasonId: input.reasonId.trim() } : {}),
    ...(input.feedbackValueType !== undefined
      ? { feedbackValueType: input.feedbackValueType }
      : {}),
    ...(input.feedbackValue !== undefined
      ? { feedbackValue: input.feedbackValue }
      : {}),
    ...(input.feedbackChoiceCode !== undefined
      ? { feedbackChoiceCode: input.feedbackChoiceCode }
      : {}),
    ...(input.feedbackReasonCategory !== undefined
      ? { feedbackReasonCategory: input.feedbackReasonCategory }
      : {}),
    ...(input.comment !== undefined ? { comment: input.comment } : {}),
    ...(input.sourcePage !== undefined ? { sourcePage: input.sourcePage } : {}),
    ...(input.sessionId !== undefined && input.sessionId.trim() !== ""
      ? { sessionId: input.sessionId.trim() }
      : {}),
  };
}
