import type {
  OccasionMasterItem,
  RecommendationRunResponseData,
  RelationshipMasterItem,
} from "@/generated/api/giftRecommendationServicePublicAPI.schemas";

export type MasterOption = {
  code: string;
  label: string;
  displayOrder: number;
};

export type RecommendationInputFormValues = {
  relationshipCode: string;
  occasionCode: string;
  budgetMin: string;
  budgetMax: string;
  preferredText: string;
  nonPreferredText: string;
  ngText: string;
  topK: number;
};

export type RecommendationInputFieldErrors = Partial<
  Record<
    | "relationshipCode"
    | "occasionCode"
    | "budgetMin"
    | "budgetMax"
    | "preferredText"
    | "nonPreferredText"
    | "ngText",
    string
  >
>;

export type MastersLoadState =
  | { status: "idle" | "loading" }
  | {
      status: "success";
      relationships: MasterOption[];
      occasions: MasterOption[];
      /** PUB-007 / 008 は取得のみ（UI 非表示） */
      semanticConfigLoaded: boolean;
      featureRulesLoaded: boolean;
    }
  | {
      status: "error";
      message: string;
      traceId?: string;
    };

export type ScreenPhase =
  | "form"
  | "running"
  | "empty"
  | "error";

export type RunErrorState = {
  message: string;
  code?: string;
  traceId?: string;
};

export type StoredRecommendationResult = RecommendationRunResponseData;

export function toRelationshipOptions(
  items: RelationshipMasterItem[],
): MasterOption[] {
  return [...items]
    .map((item) => ({
      code: item.relationshipCode,
      label: item.relationshipLabel,
      displayOrder: item.displayOrder ?? Number.MAX_SAFE_INTEGER,
    }))
    .sort((a, b) =>
      a.displayOrder === b.displayOrder
        ? a.code.localeCompare(b.code)
        : a.displayOrder - b.displayOrder,
    );
}

export function toOccasionOptions(items: OccasionMasterItem[]): MasterOption[] {
  return [...items]
    .map((item) => ({
      code: item.occasionCode,
      label: item.occasionLabel,
      displayOrder: item.displayOrder ?? Number.MAX_SAFE_INTEGER,
    }))
    .sort((a, b) =>
      a.displayOrder === b.displayOrder
        ? a.code.localeCompare(b.code)
        : a.displayOrder - b.displayOrder,
    );
}

export function createEmptyFormValues(
  overrides?: Partial<RecommendationInputFormValues>,
): RecommendationInputFormValues {
  return {
    relationshipCode: "",
    occasionCode: "",
    budgetMin: "",
    budgetMax: "",
    preferredText: "",
    nonPreferredText: "",
    ngText: "",
    topK: 10,
    ...overrides,
  };
}
