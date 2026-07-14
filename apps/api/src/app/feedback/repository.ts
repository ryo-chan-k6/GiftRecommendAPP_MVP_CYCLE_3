import { randomUUID } from "node:crypto";

import {
  DbError,
  isDbError,
  type DbSession,
} from "../../infrastructure/db/index.js";
import { ApiError } from "../../middlewares/error/api-error.js";
import { FEEDBACK_ERROR_CODES, FEEDBACK_ERROR_MESSAGES } from "./constants.js";
import type {
  FeedbackPersistenceInput,
  FeedbackRecord,
  IdempotencyLookup,
  RecommendationReasonContext,
  RecommendationResultContext,
  RecommendationResultItemContext,
} from "./types.js";

export type FeedbackRepositoryOptions = {
  session: DbSession;
  feedbackTableName?: string;
  resultTableName?: string;
  resultItemTableName?: string;
  reasonTableName?: string;
};

function isUniqueViolation(error: unknown): boolean {
  if (!isDbError(error)) {
    return false;
  }

  const cause = error.cause;
  if (cause !== null && typeof cause === "object" && "code" in cause) {
    return (cause as { code: string }).code === "23505";
  }

  return false;
}

function mapDbError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error;
  }

  if (isDbError(error)) {
    return new ApiError({
      code: FEEDBACK_ERROR_CODES.DB_QUERY_FAILED,
      httpStatus: 500,
      message: FEEDBACK_ERROR_MESSAGES.DB_QUERY_FAILED,
      retryable: true,
      cause: error,
    });
  }

  return new ApiError({
    code: FEEDBACK_ERROR_CODES.UNEXPECTED,
    httpStatus: 500,
    message: FEEDBACK_ERROR_MESSAGES.UNEXPECTED,
    retryable: false,
    cause: error,
  });
}

type ResultRow = {
  recommendation_result_id: string;
  recommendation_run_id: string | null;
  recommendation_request_id: string | null;
};

type ResultItemRow = {
  recommendation_result_item_id: string;
  recommendation_result_id: string;
  item_id: string | null;
  rank: number | null;
};

type ReasonRow = {
  recommendation_reason_id: string;
  recommendation_result_id: string;
  recommendation_result_item_id: string | null;
};

type FeedbackRow = {
  recommendation_feedback_id: string;
  recommendation_result_id: string;
  recommendation_run_id: string | null;
  recommendation_request_id: string | null;
  recommendation_result_item_id: string | null;
  recommendation_reason_id: string | null;
  feedback_target_type: string;
  feedback_type: string;
  feedback_value_type: string;
  feedback_value: unknown;
  feedback_choice_code: string | null;
  feedback_reason_category: string | null;
  feedback_rating: number;
  feedback_text: string | null;
  source_page: string | null;
  session_id: string | null;
  user_agent: string | null;
  item_id: string | null;
  rank_at_feedback: number | null;
  is_positive: boolean | null;
  is_negative: boolean | null;
  submitted_at: string | Date;
  updated_at: string | Date | null;
};

function mapFeedbackRow(row: FeedbackRow): FeedbackRecord {
  return {
    recommendationFeedbackId: row.recommendation_feedback_id,
    recommendationResultId: row.recommendation_result_id,
    recommendationRunId: row.recommendation_run_id,
    recommendationRequestId: row.recommendation_request_id,
    recommendationResultItemId: row.recommendation_result_item_id,
    recommendationReasonId: row.recommendation_reason_id,
    feedbackTargetType: row.feedback_target_type as FeedbackRecord["feedbackTargetType"],
    feedbackType: row.feedback_type as FeedbackRecord["feedbackType"],
    feedbackValueType: row.feedback_value_type as FeedbackRecord["feedbackValueType"],
    feedbackValue: row.feedback_value,
    feedbackChoiceCode: row.feedback_choice_code,
    feedbackReasonCategory: row.feedback_reason_category,
    feedbackRating: row.feedback_rating,
    feedbackText: row.feedback_text,
    sourcePage: row.source_page,
    sessionId: row.session_id,
    userAgent: row.user_agent,
    itemId: row.item_id,
    rankAtFeedback: row.rank_at_feedback,
    isPositive: row.is_positive,
    isNegative: row.is_negative,
    submittedAt:
      row.submitted_at instanceof Date
        ? row.submitted_at.toISOString()
        : row.submitted_at,
    updatedAt:
      row.updated_at === null
        ? null
        : row.updated_at instanceof Date
          ? row.updated_at.toISOString()
          : row.updated_at,
  };
}

/** MOD-API-010: recommendation_feedback 永続化と Result / Item / Reason 読取。 */
export class FeedbackRepository {
  readonly session: DbSession;
  readonly feedbackTableName: string;
  readonly resultTableName: string;
  readonly resultItemTableName: string;
  readonly reasonTableName: string;

  constructor(options: FeedbackRepositoryOptions) {
    this.session = options.session;
    this.feedbackTableName = options.feedbackTableName ?? "recommendation_feedback";
    this.resultTableName = options.resultTableName ?? "recommendation_result";
    this.resultItemTableName =
      options.resultItemTableName ?? "recommendation_result_item";
    this.reasonTableName = options.reasonTableName ?? "recommendation_reason";
  }

  async findResult(
    resultId: string,
  ): Promise<RecommendationResultContext | null> {
    const sql = `
SELECT recommendation_result_id, recommendation_run_id, recommendation_request_id
FROM ${this.resultTableName}
WHERE recommendation_result_id = $1
LIMIT 1
`.trim();

    try {
      const result = await this.session.query<ResultRow>(sql, [resultId]);
      const row = result.rows[0];
      if (row === undefined) {
        return null;
      }

      return {
        recommendationResultId: row.recommendation_result_id,
        recommendationRunId: row.recommendation_run_id,
        recommendationRequestId: row.recommendation_request_id,
      };
    } catch (error) {
      throw mapDbError(error);
    }
  }

  async findResultItem(
    resultItemId: string,
    resultId: string,
  ): Promise<RecommendationResultItemContext | null> {
    const sql = `
SELECT recommendation_result_item_id, recommendation_result_id, item_id, rank
FROM ${this.resultItemTableName}
WHERE recommendation_result_item_id = $1
  AND recommendation_result_id = $2
LIMIT 1
`.trim();

    try {
      const result = await this.session.query<ResultItemRow>(sql, [
        resultItemId,
        resultId,
      ]);
      const row = result.rows[0];
      if (row === undefined) {
        return null;
      }

      return {
        recommendationResultItemId: row.recommendation_result_item_id,
        recommendationResultId: row.recommendation_result_id,
        itemId: row.item_id,
        rank: row.rank,
      };
    } catch (error) {
      throw mapDbError(error);
    }
  }

  async findReason(
    reasonId: string,
    resultId: string,
  ): Promise<RecommendationReasonContext | null> {
    const sql = `
SELECT recommendation_reason_id, recommendation_result_id, recommendation_result_item_id
FROM ${this.reasonTableName}
WHERE recommendation_reason_id = $1
  AND recommendation_result_id = $2
LIMIT 1
`.trim();

    try {
      const result = await this.session.query<ReasonRow>(sql, [
        reasonId,
        resultId,
      ]);
      const row = result.rows[0];
      if (row === undefined) {
        return null;
      }

      return {
        recommendationReasonId: row.recommendation_reason_id,
        recommendationResultId: row.recommendation_result_id,
        recommendationResultItemId: row.recommendation_result_item_id,
      };
    } catch (error) {
      throw mapDbError(error);
    }
  }

  async findByIdempotencyKey(
    lookup: IdempotencyLookup,
  ): Promise<FeedbackRecord | null> {
    let sql: string;
    let params: unknown[];

    if (lookup.feedbackTargetType === "result") {
      sql = `
SELECT *
FROM ${this.feedbackTableName}
WHERE session_id = $1
  AND recommendation_result_id = $2
  AND feedback_type = $3
  AND feedback_target_type = 'result'
LIMIT 1
`.trim();
      params = [
        lookup.sessionId,
        lookup.recommendationResultId,
        lookup.feedbackType,
      ];
    } else if (lookup.feedbackTargetType === "item") {
      sql = `
SELECT *
FROM ${this.feedbackTableName}
WHERE session_id = $1
  AND recommendation_result_item_id = $2
  AND feedback_type = $3
  AND feedback_target_type = 'item'
LIMIT 1
`.trim();
      params = [
        lookup.sessionId,
        lookup.recommendationResultItemId,
        lookup.feedbackType,
      ];
    } else {
      sql = `
SELECT *
FROM ${this.feedbackTableName}
WHERE session_id = $1
  AND recommendation_reason_id = $2
  AND feedback_type = $3
  AND feedback_target_type = 'reason'
LIMIT 1
`.trim();
      params = [
        lookup.sessionId,
        lookup.recommendationReasonId,
        lookup.feedbackType,
      ];
    }

    try {
      const result = await this.session.query<FeedbackRow>(sql, params);
      const row = result.rows[0];
      return row === undefined ? null : mapFeedbackRow(row);
    } catch (error) {
      throw mapDbError(error);
    }
  }

  async insert(input: FeedbackPersistenceInput): Promise<FeedbackRecord> {
    const id = randomUUID();
    const now = new Date().toISOString();

    const sql = `
INSERT INTO ${this.feedbackTableName} (
  recommendation_feedback_id,
  recommendation_result_id,
  recommendation_run_id,
  recommendation_request_id,
  recommendation_result_item_id,
  recommendation_reason_id,
  feedback_target_type,
  feedback_type,
  feedback_value_type,
  feedback_value,
  feedback_choice_code,
  feedback_reason_category,
  feedback_rating,
  feedback_text,
  source_page,
  session_id,
  user_agent,
  item_id,
  rank_at_feedback,
  is_positive,
  is_negative,
  feedback_status,
  submitted_at
) VALUES (
  $1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb,
  $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, 'submitted', $22
)
RETURNING *
`.trim();

    const params = [
      id,
      input.recommendationResultId,
      input.recommendationRunId,
      input.recommendationRequestId,
      input.recommendationResultItemId,
      input.recommendationReasonId,
      input.feedbackTargetType,
      input.feedbackType,
      input.feedbackValueType,
      input.feedbackValue === null || input.feedbackValue === undefined
        ? null
        : JSON.stringify(input.feedbackValue),
      input.feedbackChoiceCode,
      input.feedbackReasonCategory,
      input.feedbackRating,
      input.feedbackText,
      input.sourcePage,
      input.sessionId,
      input.userAgent,
      input.itemId,
      input.rankAtFeedback,
      input.isPositive,
      input.isNegative,
      now,
    ];

    try {
      const result = await this.session.query<FeedbackRow>(sql, params);
      const row = result.rows[0];
      if (row === undefined) {
        throw new ApiError({
          code: FEEDBACK_ERROR_CODES.SAVE_FAILED,
          httpStatus: 500,
          message: FEEDBACK_ERROR_MESSAGES.SAVE_FAILED,
          retryable: true,
        });
      }

      return mapFeedbackRow(row);
    } catch (error) {
      if (isUniqueViolation(error)) {
        throw error;
      }

      if (error instanceof ApiError) {
        throw error;
      }

      throw new ApiError({
        code: FEEDBACK_ERROR_CODES.SAVE_FAILED,
        httpStatus: 500,
        message: FEEDBACK_ERROR_MESSAGES.SAVE_FAILED,
        retryable: true,
        cause: error,
      });
    }
  }

  async update(
    feedbackId: string,
    input: FeedbackPersistenceInput,
  ): Promise<FeedbackRecord> {
    const now = new Date().toISOString();

    const sql = `
UPDATE ${this.feedbackTableName}
SET
  feedback_value_type = $2,
  feedback_value = $3::jsonb,
  feedback_choice_code = $4,
  feedback_reason_category = $5,
  feedback_rating = $6,
  feedback_text = $7,
  source_page = $8,
  user_agent = $9,
  item_id = $10,
  rank_at_feedback = $11,
  is_positive = $12,
  is_negative = $13,
  updated_at = $14
WHERE recommendation_feedback_id = $1
RETURNING *
`.trim();

    const params = [
      feedbackId,
      input.feedbackValueType,
      input.feedbackValue === null || input.feedbackValue === undefined
        ? null
        : JSON.stringify(input.feedbackValue),
      input.feedbackChoiceCode,
      input.feedbackReasonCategory,
      input.feedbackRating,
      input.feedbackText,
      input.sourcePage,
      input.userAgent,
      input.itemId,
      input.rankAtFeedback,
      input.isPositive,
      input.isNegative,
      now,
    ];

    try {
      const result = await this.session.query<FeedbackRow>(sql, params);
      const row = result.rows[0];
      if (row === undefined) {
        throw new ApiError({
          code: FEEDBACK_ERROR_CODES.SAVE_FAILED,
          httpStatus: 500,
          message: FEEDBACK_ERROR_MESSAGES.SAVE_FAILED,
          retryable: true,
        });
      }

      return mapFeedbackRow(row);
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }

      throw new ApiError({
        code: FEEDBACK_ERROR_CODES.SAVE_FAILED,
        httpStatus: 500,
        message: FEEDBACK_ERROR_MESSAGES.SAVE_FAILED,
        retryable: true,
        cause: error,
      });
    }
  }
}

export type InMemoryFeedbackStoreSeed = {
  results?: RecommendationResultContext[];
  items?: RecommendationResultItemContext[];
  reasons?: RecommendationReasonContext[];
};

/** 単体テスト向け in-memory Repository（DI 注入用）。 */
export class InMemoryFeedbackRepository extends FeedbackRepository {
  readonly results = new Map<string, RecommendationResultContext>();
  readonly items = new Map<string, RecommendationResultItemContext>();
  readonly reasons = new Map<string, RecommendationReasonContext>();
  readonly feedbacks: FeedbackRecord[] = [];

  constructor(seed: InMemoryFeedbackStoreSeed = {}) {
    super({ session: new InMemoryDbSession() });

    for (const result of seed.results ?? []) {
      this.results.set(result.recommendationResultId, result);
    }
    for (const item of seed.items ?? []) {
      this.items.set(item.recommendationResultItemId, item);
    }
    for (const reason of seed.reasons ?? []) {
      this.reasons.set(reason.recommendationReasonId, reason);
    }
  }

  override async findResult(
    resultId: string,
  ): Promise<RecommendationResultContext | null> {
    return this.results.get(resultId) ?? null;
  }

  override async findResultItem(
    resultItemId: string,
    resultId: string,
  ): Promise<RecommendationResultItemContext | null> {
    const item = this.items.get(resultItemId);
    if (item === undefined || item.recommendationResultId !== resultId) {
      return null;
    }
    return item;
  }

  override async findReason(
    reasonId: string,
    resultId: string,
  ): Promise<RecommendationReasonContext | null> {
    const reason = this.reasons.get(reasonId);
    if (reason === undefined || reason.recommendationResultId !== resultId) {
      return null;
    }
    return reason;
  }

  override async findByIdempotencyKey(
    lookup: IdempotencyLookup,
  ): Promise<FeedbackRecord | null> {
    return (
      this.feedbacks.find((record) => matchesIdempotencyKey(record, lookup)) ??
      null
    );
  }

  override async insert(input: FeedbackPersistenceInput): Promise<FeedbackRecord> {
    if (input.sessionId !== null) {
      const duplicate = this.feedbacks.find((record) =>
        matchesIdempotencyKey(record, {
          sessionId: input.sessionId as string,
          feedbackTargetType: input.feedbackTargetType,
          feedbackType: input.feedbackType,
          recommendationResultId: input.recommendationResultId,
          recommendationResultItemId: input.recommendationResultItemId,
          recommendationReasonId: input.recommendationReasonId,
        }),
      );

      if (duplicate !== undefined) {
        throw new DbError({
          code: "DB_QUERY_FAILED",
          message: "unique violation",
          retryable: false,
          cause: { code: "23505" },
        });
      }
    }

    const now = new Date().toISOString();
    const record: FeedbackRecord = {
      recommendationFeedbackId: randomUUID(),
      ...input,
      submittedAt: now,
      updatedAt: null,
    };
    this.feedbacks.push(record);
    return record;
  }

  override async update(
    feedbackId: string,
    input: FeedbackPersistenceInput,
  ): Promise<FeedbackRecord> {
    const index = this.feedbacks.findIndex(
      (record) => record.recommendationFeedbackId === feedbackId,
    );
    if (index === -1) {
      throw new ApiError({
        code: FEEDBACK_ERROR_CODES.SAVE_FAILED,
        httpStatus: 500,
        message: FEEDBACK_ERROR_MESSAGES.SAVE_FAILED,
        retryable: true,
      });
    }

    const now = new Date().toISOString();
    const updated: FeedbackRecord = {
      ...this.feedbacks[index],
      ...input,
      recommendationFeedbackId: feedbackId,
      updatedAt: now,
    };
    this.feedbacks[index] = updated;
    return updated;
  }
}

function matchesIdempotencyKey(
  record: FeedbackRecord,
  lookup: IdempotencyLookup,
): boolean {
  if (record.sessionId !== lookup.sessionId) {
    return false;
  }

  if (record.feedbackType !== lookup.feedbackType) {
    return false;
  }

  if (lookup.feedbackTargetType === "result") {
    return (
      record.feedbackTargetType === "result" &&
      record.recommendationResultId === lookup.recommendationResultId
    );
  }

  if (lookup.feedbackTargetType === "item") {
    return (
      record.feedbackTargetType === "item" &&
      record.recommendationResultItemId === lookup.recommendationResultItemId
    );
  }

  return (
    record.feedbackTargetType === "reason" &&
    record.recommendationReasonId === lookup.recommendationReasonId
  );
}

class InMemoryDbSession implements DbSession {
  readonly backend = "in-memory";

  healthCheck() {
    return { isAvailable: true, backend: this.backend };
  }

  async query() {
    return { rows: [], rowCount: 0 };
  }

  async execute() {
    return 0;
  }
}
