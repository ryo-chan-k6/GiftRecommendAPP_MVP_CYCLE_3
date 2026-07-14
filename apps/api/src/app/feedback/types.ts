import type {
  FEEDBACK_TARGET_TYPES,
  FEEDBACK_TYPES,
  FEEDBACK_VALUE_TYPES,
} from "./constants.js";

export type FeedbackTargetType = (typeof FEEDBACK_TARGET_TYPES)[number];
export type FeedbackType = (typeof FEEDBACK_TYPES)[number];
export type FeedbackValueType = (typeof FEEDBACK_VALUE_TYPES)[number];

export type FeedbackSubmitRequest = {
  feedbackTargetType: FeedbackTargetType;
  feedbackType: FeedbackType;
  rating: number;
  resultItemId?: string;
  reasonId?: string;
  feedbackValueType?: FeedbackValueType;
  feedbackValue?: boolean | number | string;
  feedbackChoiceCode?: string;
  feedbackReasonCategory?: string;
  comment?: string;
  sourcePage?: string;
  sessionId?: string;
};

export type RecommendationResultContext = {
  recommendationResultId: string;
  recommendationRunId: string | null;
  recommendationRequestId: string | null;
};

export type RecommendationResultItemContext = {
  recommendationResultItemId: string;
  recommendationResultId: string;
  itemId: string | null;
  rank: number | null;
};

export type RecommendationReasonContext = {
  recommendationReasonId: string;
  recommendationResultId: string;
  recommendationResultItemId: string | null;
};

export type FeedbackPersistenceInput = {
  recommendationResultId: string;
  recommendationRunId: string | null;
  recommendationRequestId: string | null;
  recommendationResultItemId: string | null;
  recommendationReasonId: string | null;
  feedbackTargetType: FeedbackTargetType;
  feedbackType: FeedbackType;
  feedbackValueType: FeedbackValueType;
  feedbackValue: unknown | null;
  feedbackChoiceCode: string | null;
  feedbackReasonCategory: string | null;
  feedbackRating: number;
  feedbackText: string | null;
  sourcePage: string | null;
  sessionId: string | null;
  userAgent: string | null;
  itemId: string | null;
  rankAtFeedback: number | null;
  isPositive: boolean | null;
  isNegative: boolean | null;
};

export type FeedbackRecord = FeedbackPersistenceInput & {
  recommendationFeedbackId: string;
  submittedAt: string;
  updatedAt: string | null;
};

export type IdempotencyLookup = {
  sessionId: string;
  feedbackTargetType: FeedbackTargetType;
  feedbackType: FeedbackType;
  recommendationResultId: string;
  recommendationResultItemId: string | null;
  recommendationReasonId: string | null;
};

export type FeedbackSubmitSuccessResponse = {
  data: {
    recommendationFeedbackId: string;
    status: "accepted" | "updated";
    message?: string;
  };
  meta: {
    traceId: string;
    requestId: string;
    acceptedAt?: string;
  };
};

export type FeedbackSubmitResult = {
  httpStatus: 201 | 200;
  body: FeedbackSubmitSuccessResponse;
  isPositive: boolean | null;
  isNegative: boolean | null;
};
