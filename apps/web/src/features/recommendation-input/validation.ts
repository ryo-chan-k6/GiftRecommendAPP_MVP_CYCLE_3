import {
  NG_TEXT_MAX,
  NON_PREFERRED_TEXT_MAX,
  PREFERRED_TEXT_MAX,
  VALIDATION_MESSAGES,
} from "./constants";
import type {
  MasterOption,
  RecommendationInputFieldErrors,
  RecommendationInputFormValues,
} from "./types";

function parseBudget(raw: string): number | null {
  const trimmed = raw.trim();
  if (trimmed === "") {
    return null;
  }
  if (!/^\d+$/.test(trimmed)) {
    return Number.NaN;
  }
  return Number(trimmed);
}

export function validateRecommendationInput(
  values: RecommendationInputFormValues,
  relationships: MasterOption[],
  occasions: MasterOption[],
): RecommendationInputFieldErrors {
  const errors: RecommendationInputFieldErrors = {};

  if (!values.relationshipCode) {
    errors.relationshipCode = VALIDATION_MESSAGES.relationshipRequired;
  } else if (!relationships.some((item) => item.code === values.relationshipCode)) {
    errors.relationshipCode = VALIDATION_MESSAGES.masterCodeInvalid;
  }

  if (!values.occasionCode) {
    errors.occasionCode = VALIDATION_MESSAGES.occasionRequired;
  } else if (!occasions.some((item) => item.code === values.occasionCode)) {
    errors.occasionCode = VALIDATION_MESSAGES.masterCodeInvalid;
  }

  const budgetMin = parseBudget(values.budgetMin);
  const budgetMax = parseBudget(values.budgetMax);

  if (values.budgetMax.trim() === "") {
    errors.budgetMax = VALIDATION_MESSAGES.budgetMaxRequired;
  } else if (budgetMax === null || Number.isNaN(budgetMax) || budgetMax < 0) {
    errors.budgetMax = VALIDATION_MESSAGES.budgetInvalid;
  }

  if (values.budgetMin.trim() !== "") {
    if (budgetMin === null || Number.isNaN(budgetMin) || budgetMin < 0) {
      errors.budgetMin = VALIDATION_MESSAGES.budgetInvalid;
    }
  }

  if (
    errors.budgetMin === undefined &&
    errors.budgetMax === undefined &&
    budgetMin !== null &&
    !Number.isNaN(budgetMin) &&
    budgetMax !== null &&
    !Number.isNaN(budgetMax) &&
    budgetMin > budgetMax
  ) {
    errors.budgetMin = VALIDATION_MESSAGES.budgetRange;
    errors.budgetMax = VALIDATION_MESSAGES.budgetRange;
  }

  if (values.preferredText.length > PREFERRED_TEXT_MAX) {
    errors.preferredText = VALIDATION_MESSAGES.textTooLong;
  }
  if (values.nonPreferredText.length > NON_PREFERRED_TEXT_MAX) {
    errors.nonPreferredText = VALIDATION_MESSAGES.textTooLong;
  }
  if (values.ngText.length > NG_TEXT_MAX) {
    errors.ngText = VALIDATION_MESSAGES.textTooLong;
  }

  return errors;
}

export function hasFieldErrors(
  errors: RecommendationInputFieldErrors,
): boolean {
  return Object.keys(errors).length > 0;
}
