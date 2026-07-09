import { randomUUID } from "node:crypto";

import { DbError } from "../../infrastructure/db/errors.js";
import type { DbSession } from "../../infrastructure/db/session.js";
import { ApiError } from "../../middlewares/error/api-error.js";
import { PUBLIC_ERROR_CODES, PUBLIC_ERROR_MESSAGES } from "./constants.js";
import type {
  RecommendationRequestRecord,
  RecommendationRunRequest,
} from "./types.js";

export type RecommendationRequestRepositoryOptions = {
  session: DbSession;
  tableName?: string;
};

/** MOD-API-004: recommendation_request 永続化（scaffold / DB session 利用）。 */
export class RecommendationRequestRepository {
  readonly session: DbSession;
  readonly tableName: string;
  readonly insertCalls: Array<{
    request: RecommendationRunRequest;
    traceId: string;
  }>;

  private readonly inMemoryRows: RecommendationRequestRecord[];

  constructor(options: RecommendationRequestRepositoryOptions) {
    this.session = options.session;
    this.tableName = options.tableName ?? "recommendation_request";
    this.insertCalls = [];
    this.inMemoryRows = [];
  }

  async insert(input: {
    request: RecommendationRunRequest;
    traceId: string;
  }): Promise<RecommendationRequestRecord> {
    this.insertCalls.push(input);

    const now = new Date().toISOString();
    const id = randomUUID();
    const record: RecommendationRequestRecord = {
      id,
      requestMode: input.request.execution.mode,
      relationshipCode: input.request.relationship.relationshipCode,
      occasionCode: input.request.occasion.occasionCode,
      budgetMin: input.request.budget?.budgetMin,
      budgetMax: input.request.budget?.budgetMax,
      currency: input.request.budget?.currency ?? "JPY",
      taxIncluded: input.request.budget?.taxIncluded,
      preferredText: input.request.preferredCondition?.preferredText,
      nonPreferredText:
        input.request.nonPreferredCondition?.nonPreferredText,
      ngText: input.request.ngCondition?.ngText,
      freeText: input.request.freeText,
      topK: input.request.execution.topK,
      candidateLimit: input.request.execution.candidateLimit,
      includeReason: input.request.execution.includeReason,
      includeDebugInfo: input.request.execution.includeDebugInfo,
      requestPayload: input.request,
      validatedPayload: input.request,
      traceId: input.traceId,
      createdAt: now,
      validatedAt: now,
    };

    try {
      await this.session.execute(
        `INSERT INTO ${this.tableName} (recommendation_request_id, request_mode, relationship_code, occasion_code, request_payload, validated_payload, trace_id, created_at, validated_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
        [
          id,
          record.requestMode,
          record.relationshipCode,
          record.occasionCode,
          JSON.stringify(record.requestPayload),
          JSON.stringify(record.validatedPayload),
          record.traceId,
          record.createdAt,
          record.validatedAt,
        ],
      );
    } catch (error) {
      if (error instanceof DbError) {
        throw new ApiError({
          code: PUBLIC_ERROR_CODES.REQUEST_SAVE_FAILED,
          httpStatus: 500,
          message: PUBLIC_ERROR_MESSAGES.REQUEST_SAVE_FAILED,
          retryable: true,
          cause: error,
        });
      }

      throw error;
    }

    this.inMemoryRows.push(record);
    return record;
  }

  listInMemory(): RecommendationRequestRecord[] {
    return [...this.inMemoryRows];
  }
}
