import { isDbError } from "../../infrastructure/db/index.js";
import { ApiError } from "../../middlewares/error/api-error.js";
import {
  FEEDBACK_ERROR_CODES,
  FEEDBACK_ERROR_MESSAGES,
  FEEDBACK_SUCCESS_MESSAGES,
  MAX_USER_AGENT_LENGTH,
} from "./constants.js";
import type { FeedbackRepository } from "./repository.js";
import type {
  FeedbackPersistenceInput,
  FeedbackSubmitRequest,
  FeedbackSubmitResult,
  FeedbackType,
  FeedbackValueType,
  IdempotencyLookup,
} from "./types.js";

export type FeedbackServiceOptions = {
  repository: FeedbackRepository;
};

const CHOICE_FEEDBACK_TYPES = new Set<FeedbackType>([
  "item_not_match",
  "item_ng_violation",
  "item_avoid_match",
]);

function inferFeedbackValueType(feedbackType: FeedbackType): FeedbackValueType {
  if (feedbackType === "comment") {
    return "text";
  }

  if (CHOICE_FEEDBACK_TYPES.has(feedbackType)) {
    return "choice";
  }

  if (feedbackType.endsWith("_good") || feedbackType.endsWith("_bad")) {
    return "boolean";
  }

  return "rating";
}

function deriveSentiment(feedbackType: FeedbackType): {
  isPositive: boolean | null;
  isNegative: boolean | null;
} {
  if (feedbackType.endsWith("_good")) {
    return { isPositive: true, isNegative: false };
  }

  if (
    feedbackType.endsWith("_bad") ||
    CHOICE_FEEDBACK_TYPES.has(feedbackType)
  ) {
    return { isPositive: false, isNegative: true };
  }

  return { isPositive: null, isNegative: null };
}

function truncateUserAgent(userAgent: string | undefined): string | null {
  if (userAgent === undefined || userAgent.trim() === "") {
    return null;
  }

  return userAgent.slice(0, MAX_USER_AGENT_LENGTH);
}

function buildPersistenceInput(input: {
  resultId: string;
  request: FeedbackSubmitRequest;
  recommendationRunId: string | null;
  recommendationRequestId: string | null;
  recommendationResultItemId: string | null;
  recommendationReasonId: string | null;
  itemId: string | null;
  rankAtFeedback: number | null;
  userAgent: string | undefined;
}): FeedbackPersistenceInput {
  const feedbackValueType =
    input.request.feedbackValueType ??
    inferFeedbackValueType(input.request.feedbackType);
  const sentiment = deriveSentiment(input.request.feedbackType);

  return {
    recommendationResultId: input.resultId,
    recommendationRunId: input.recommendationRunId,
    recommendationRequestId: input.recommendationRequestId,
    recommendationResultItemId: input.recommendationResultItemId,
    recommendationReasonId: input.recommendationReasonId,
    feedbackTargetType: input.request.feedbackTargetType,
    feedbackType: input.request.feedbackType,
    feedbackValueType,
    feedbackValue: input.request.feedbackValue ?? null,
    feedbackChoiceCode: input.request.feedbackChoiceCode ?? null,
    feedbackReasonCategory: input.request.feedbackReasonCategory ?? null,
    feedbackRating: input.request.rating,
    feedbackText: input.request.comment ?? null,
    sourcePage: input.request.sourcePage ?? null,
    sessionId: input.request.sessionId ?? null,
    userAgent: truncateUserAgent(input.userAgent),
    itemId: input.itemId,
    rankAtFeedback: input.rankAtFeedback,
    isPositive: sentiment.isPositive,
    isNegative: sentiment.isNegative,
  };
}

function buildSuccessResponse(input: {
  feedbackId: string;
  status: "accepted" | "updated";
  traceId: string;
  requestId: string;
  acceptedAt: string;
}): FeedbackSubmitResult {
  const message =
    input.status === "accepted"
      ? FEEDBACK_SUCCESS_MESSAGES.ACCEPTED
      : FEEDBACK_SUCCESS_MESSAGES.UPDATED;

  return {
    httpStatus: input.status === "accepted" ? 201 : 200,
    isPositive: null,
    isNegative: null,
    body: {
      data: {
        recommendationFeedbackId: input.feedbackId,
        status: input.status,
        message,
      },
      meta: {
        traceId: input.traceId,
        requestId: input.requestId,
        acceptedAt: input.acceptedAt,
      },
    },
  };
}

/** MOD-API-009: 存在確認・冪等判定・保存制御。 */
export class FeedbackService {
  readonly repository: FeedbackRepository;

  constructor(options: FeedbackServiceOptions) {
    this.repository = options.repository;
  }

  async submitFeedback(input: {
    resultId: string;
    request: FeedbackSubmitRequest;
    traceId: string;
    requestId: string;
    userAgent?: string;
  }): Promise<FeedbackSubmitResult> {
    const result = await this.repository.findResult(input.resultId);
    if (result === null) {
      throw new ApiError({
        code: FEEDBACK_ERROR_CODES.TARGET_NOT_FOUND,
        httpStatus: 404,
        message: FEEDBACK_ERROR_MESSAGES.TARGET_NOT_FOUND,
        retryable: false,
      });
    }

    let recommendationResultItemId: string | null = null;
    let recommendationReasonId: string | null = null;
    let itemId: string | null = null;
    let rankAtFeedback: number | null = null;

    if (input.request.feedbackTargetType === "item") {
      const item = await this.repository.findResultItem(
        input.request.resultItemId as string,
        input.resultId,
      );
      if (item === null) {
        throw new ApiError({
          code: FEEDBACK_ERROR_CODES.TARGET_NOT_FOUND,
          httpStatus: 404,
          message: FEEDBACK_ERROR_MESSAGES.TARGET_NOT_FOUND,
          retryable: false,
        });
      }

      recommendationResultItemId = item.recommendationResultItemId;
      itemId = item.itemId;
      rankAtFeedback = item.rank;
    }

    if (input.request.feedbackTargetType === "reason") {
      const reason = await this.repository.findReason(
        input.request.reasonId as string,
        input.resultId,
      );
      if (reason === null) {
        throw new ApiError({
          code: FEEDBACK_ERROR_CODES.TARGET_NOT_FOUND,
          httpStatus: 404,
          message: FEEDBACK_ERROR_MESSAGES.TARGET_NOT_FOUND,
          retryable: false,
        });
      }

      recommendationReasonId = reason.recommendationReasonId;

      if (input.request.resultItemId !== undefined) {
        const item = await this.repository.findResultItem(
          input.request.resultItemId,
          input.resultId,
        );
        if (
          item === null ||
          (reason.recommendationResultItemId !== null &&
            reason.recommendationResultItemId !== item.recommendationResultItemId)
        ) {
          throw new ApiError({
            code: FEEDBACK_ERROR_CODES.TARGET_NOT_FOUND,
            httpStatus: 404,
            message: FEEDBACK_ERROR_MESSAGES.TARGET_NOT_FOUND,
            retryable: false,
          });
        }

        recommendationResultItemId = item.recommendationResultItemId;
        itemId = item.itemId;
        rankAtFeedback = item.rank;
      } else if (reason.recommendationResultItemId !== null) {
        const item = await this.repository.findResultItem(
          reason.recommendationResultItemId,
          input.resultId,
        );
        if (item !== null) {
          recommendationResultItemId = item.recommendationResultItemId;
          itemId = item.itemId;
          rankAtFeedback = item.rank;
        }
      }
    }

    const persistenceInput = buildPersistenceInput({
      resultId: input.resultId,
      request: input.request,
      recommendationRunId: result.recommendationRunId,
      recommendationRequestId: result.recommendationRequestId,
      recommendationResultItemId,
      recommendationReasonId,
      itemId,
      rankAtFeedback,
      userAgent: input.userAgent,
    });

    const idempotencyLookup: IdempotencyLookup | null =
      input.request.sessionId !== undefined
        ? {
            sessionId: input.request.sessionId,
            feedbackTargetType: input.request.feedbackTargetType,
            feedbackType: input.request.feedbackType,
            recommendationResultId: input.resultId,
            recommendationResultItemId,
            recommendationReasonId,
          }
        : null;

    if (idempotencyLookup !== null) {
      const existing = await this.repository.findByIdempotencyKey(
        idempotencyLookup,
      );
      if (existing !== null) {
        const updated = await this.repository.update(
          existing.recommendationFeedbackId,
          persistenceInput,
        );
        const response = buildSuccessResponse({
          feedbackId: updated.recommendationFeedbackId,
          status: "updated",
          traceId: input.traceId,
          requestId: input.requestId,
          acceptedAt: updated.updatedAt ?? updated.submittedAt,
        });
        response.isPositive = updated.isPositive;
        response.isNegative = updated.isNegative;
        return response;
      }
    }

    try {
      const created = await this.repository.insert(persistenceInput);
      const response = buildSuccessResponse({
        feedbackId: created.recommendationFeedbackId,
        status: "accepted",
        traceId: input.traceId,
        requestId: input.requestId,
        acceptedAt: created.submittedAt,
      });
      response.isPositive = created.isPositive;
      response.isNegative = created.isNegative;
      return response;
    } catch (error) {
      if (
        isDbError(error) &&
        idempotencyLookup !== null &&
        error.cause !== null &&
        typeof error.cause === "object" &&
        "code" in error.cause &&
        (error.cause as { code: string }).code === "23505"
      ) {
        const existing = await this.repository.findByIdempotencyKey(
          idempotencyLookup,
        );
        if (existing === null) {
          throw new ApiError({
            code: FEEDBACK_ERROR_CODES.SAVE_FAILED,
            httpStatus: 500,
            message: FEEDBACK_ERROR_MESSAGES.SAVE_FAILED,
            retryable: true,
            cause: error,
          });
        }

        const updated = await this.repository.update(
          existing.recommendationFeedbackId,
          persistenceInput,
        );
        const response = buildSuccessResponse({
          feedbackId: updated.recommendationFeedbackId,
          status: "updated",
          traceId: input.traceId,
          requestId: input.requestId,
          acceptedAt: updated.updatedAt ?? updated.submittedAt,
        });
        response.isPositive = updated.isPositive;
        response.isNegative = updated.isNegative;
        return response;
      }

      throw error;
    }
  }
}

export function createFeedbackService(
  options: FeedbackServiceOptions,
): FeedbackService {
  return new FeedbackService(options);
}
