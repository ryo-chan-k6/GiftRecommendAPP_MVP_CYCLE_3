/** API-PUB-002 Public Request / Response 型（OpenAPI public-api.yaml 整合）。 */

export type RelationshipInput = {
  relationshipCode: string;
  relationshipLabel?: string;
};

export type OccasionInput = {
  occasionCode: string;
  occasionLabel?: string;
};

export type BudgetInput = {
  budgetMin?: number;
  budgetMax?: number;
  currency?: string;
  taxIncluded?: boolean;
};

export type PreferredConditionInput = {
  preferredText?: string;
};

export type NonPreferredConditionInput = {
  nonPreferredText?: string;
};

export type NgConditionInput = {
  ngText?: string;
};

export type ExecutionInput = {
  mode: "ui";
  topK: number;
  candidateLimit: number;
  includeReason: boolean;
  includeDebugInfo: boolean;
};

export type RecommendationRunRequest = {
  relationship: RelationshipInput;
  occasion: OccasionInput;
  budget?: BudgetInput;
  preferredCondition?: PreferredConditionInput;
  nonPreferredCondition?: NonPreferredConditionInput;
  ngCondition?: NgConditionInput;
  freeText?: string;
  execution: ExecutionInput;
};

export type PublicRecommendationResultItem = {
  recommendationResultItemId: string;
  itemId: string;
  rank: number;
  itemName: string;
  itemPrice: number;
  itemUrl: string;
  itemImageUrl?: string;
  itemCatchcopy?: string;
  shopName?: string;
  reasonSummary?: string;
  reasonPoints?: string[];
  reasonDetail?: string;
  reasonBadges?: Array<{ label?: string; code?: string }>;
  cautionNote?: string;
  isFallback?: boolean;
};

export type PublicResultStatus = "completed" | "empty" | "partial";

export type RecommendationRunResponseData = {
  recommendationResultId: string;
  recommendationRequestId: string;
  recommendationRunId: string;
  resultStatus: PublicResultStatus;
  topK: number;
  resultItemCount: number;
  fallbackUsed: boolean;
  displayMessage?: string;
  items: PublicRecommendationResultItem[];
};

export type RecommendationRunSuccessMeta = {
  traceId: string;
  requestId: string;
  generatedAt?: string;
  resultCode?: string;
};

export type RecommendationRunSuccessResponse = {
  data: RecommendationRunResponseData;
  meta: RecommendationRunSuccessMeta;
};

export type RecommendationRequestRecord = {
  id: string;
  requestMode: string;
  relationshipCode: string;
  occasionCode: string;
  budgetMin?: number;
  budgetMax?: number;
  currency: string;
  taxIncluded?: boolean;
  preferredText?: string;
  nonPreferredText?: string;
  ngText?: string;
  freeText?: string;
  topK: number;
  candidateLimit: number;
  includeReason: boolean;
  includeDebugInfo: boolean;
  requestPayload: RecommendationRunRequest;
  validatedPayload: RecommendationRunRequest;
  traceId: string;
  createdAt: string;
  validatedAt: string;
};
