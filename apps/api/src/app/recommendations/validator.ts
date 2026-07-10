import { z } from "zod";

import { ApiError } from "../../middlewares/error/api-error.js";
import {
  DEFAULT_EXECUTION,
  PUBLIC_ERROR_CODES,
  PUBLIC_ERROR_MESSAGES,
} from "./constants.js";
import type { RecommendationRunRequest } from "./types.js";

const relationshipSchema = z.object({
  relationshipCode: z.string(),
  relationshipLabel: z.string().max(50).optional(),
});

const occasionSchema = z.object({
  occasionCode: z.string(),
  occasionLabel: z.string().max(50).optional(),
});

const budgetSchema = z
  .object({
    budgetMin: z.number().int().min(0).optional(),
    budgetMax: z.number().int().min(0).optional(),
    currency: z.string().optional(),
    taxIncluded: z.boolean().optional(),
  })
  .optional();

const preferredConditionSchema = z
  .object({
    preferredText: z.string().max(500).optional(),
  })
  .optional();

const nonPreferredConditionSchema = z
  .object({
    nonPreferredText: z.string().max(500).optional(),
  })
  .optional();

const ngConditionSchema = z
  .object({
    ngText: z.string().max(300).optional(),
  })
  .optional();

const executionSchema = z.object({
  mode: z.enum(["ui", "evaluation", "batch"]),
  topK: z.number().int().min(1).max(50).optional(),
  candidateLimit: z.number().int().min(1).optional(),
  includeReason: z.boolean().optional(),
  includeDebugInfo: z.boolean().optional(),
});

const recommendationRunRequestSchema = z.object({
  relationship: relationshipSchema,
  occasion: occasionSchema,
  budget: budgetSchema,
  preferredCondition: preferredConditionSchema,
  nonPreferredCondition: nonPreferredConditionSchema,
  ngCondition: ngConditionSchema,
  freeText: z.string().max(800).optional(),
  execution: executionSchema,
});

function throwValidationError(
  code: string,
  message: string,
  httpStatus: number,
  details?: { field: string; message: string }[],
): never {
  throw new ApiError({
    code,
    httpStatus,
    message,
    retryable: false,
    details,
  });
}

function assertNonEmptyCode(
  value: string | undefined,
  code: string,
  message: string,
): void {
  if (value === undefined || value.trim() === "") {
    throwValidationError(code, message, 400);
  }
}

function applyExecutionDefaults(
  execution: z.infer<typeof executionSchema>,
): RecommendationRunRequest["execution"] {
  const topK = execution.topK ?? DEFAULT_EXECUTION.topK;
  const candidateLimit =
    execution.candidateLimit ?? DEFAULT_EXECUTION.candidateLimit;

  return {
    mode: "ui",
    topK,
    candidateLimit,
    includeReason:
      execution.includeReason ?? DEFAULT_EXECUTION.includeReason,
    includeDebugInfo:
      execution.includeDebugInfo ?? DEFAULT_EXECUTION.includeDebugInfo,
  };
}

/** 契約仕様書 §9 に基づく Public Request Validation と default 適用。 */
export function validateRecommendationRunRequest(
  body: unknown,
): RecommendationRunRequest {
  if (body === null || typeof body !== "object") {
    throwValidationError(
      PUBLIC_ERROR_CODES.INVALID_CONDITION,
      PUBLIC_ERROR_MESSAGES.INVALID_CONDITION,
      400,
    );
  }

  const parsed = recommendationRunRequestSchema.safeParse(body);

  if (!parsed.success) {
    throwValidationError(
      PUBLIC_ERROR_CODES.INVALID_CONDITION,
      PUBLIC_ERROR_MESSAGES.INVALID_CONDITION,
      400,
      parsed.error.issues.map((issue) => ({
        field: issue.path.length > 0 ? issue.path.join(".") : "_root",
        message: issue.message,
      })),
    );
  }

  const input = parsed.data;

  assertNonEmptyCode(
    input.relationship.relationshipCode,
    PUBLIC_ERROR_CODES.RELATIONSHIP_REQUIRED,
    PUBLIC_ERROR_MESSAGES.RELATIONSHIP_REQUIRED,
  );
  assertNonEmptyCode(
    input.occasion.occasionCode,
    PUBLIC_ERROR_CODES.OCCASION_REQUIRED,
    PUBLIC_ERROR_MESSAGES.OCCASION_REQUIRED,
  );

  if (input.execution.mode !== "ui") {
    throwValidationError(
      PUBLIC_ERROR_CODES.INVALID_CONDITION,
      PUBLIC_ERROR_MESSAGES.INVALID_CONDITION,
      400,
      [{ field: "execution.mode", message: "Public MVP allows ui only" }],
    );
  }

  const execution = applyExecutionDefaults(input.execution);

  if (
    input.budget?.budgetMin !== undefined &&
    input.budget.budgetMax !== undefined &&
    input.budget.budgetMin > input.budget.budgetMax
  ) {
    throwValidationError(
      PUBLIC_ERROR_CODES.INVALID_CONDITION,
      PUBLIC_ERROR_MESSAGES.INVALID_CONDITION,
      400,
      [{ field: "budget", message: "budgetMin must be less than or equal to budgetMax" }],
    );
  }

  if (execution.candidateLimit < execution.topK) {
    throwValidationError(
      PUBLIC_ERROR_CODES.INVALID_CONDITION,
      PUBLIC_ERROR_MESSAGES.INVALID_CONDITION,
      400,
      [
        {
          field: "execution.candidateLimit",
          message: "candidateLimit must be greater than or equal to topK",
        },
      ],
    );
  }

  const budget =
    input.budget === undefined
      ? undefined
      : {
          ...input.budget,
          currency: input.budget.currency ?? DEFAULT_EXECUTION.currency,
        };

  return {
    relationship: {
      relationshipCode: input.relationship.relationshipCode.trim(),
      ...(input.relationship.relationshipLabel !== undefined
        ? { relationshipLabel: input.relationship.relationshipLabel }
        : {}),
    },
    occasion: {
      occasionCode: input.occasion.occasionCode.trim(),
      ...(input.occasion.occasionLabel !== undefined
        ? { occasionLabel: input.occasion.occasionLabel }
        : {}),
    },
    ...(budget !== undefined ? { budget } : {}),
    ...(input.preferredCondition !== undefined
      ? { preferredCondition: input.preferredCondition }
      : {}),
    ...(input.nonPreferredCondition !== undefined
      ? { nonPreferredCondition: input.nonPreferredCondition }
      : {}),
    ...(input.ngCondition !== undefined ? { ngCondition: input.ngCondition } : {}),
    ...(input.freeText !== undefined ? { freeText: input.freeText } : {}),
    execution,
  };
}
