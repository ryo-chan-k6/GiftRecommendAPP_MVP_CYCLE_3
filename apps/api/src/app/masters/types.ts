/** API-PUB-005 内部 DTO / Public Response 形（実装面）。 */

export type RelationshipMasterRow = {
  relationshipCode: string;
  relationshipLabel: string;
  displayOrder: number;
};

export type RelationshipPublicItem = {
  relationshipCode: string;
  relationshipLabel: string;
  displayOrder?: number;
};

export type RelationshipsSuccessData = {
  relationships: RelationshipPublicItem[];
};

export type RelationshipsSuccessMeta = {
  traceId: string;
  requestId: string;
  generatedAt: string;
  count: number;
};

export type RelationshipsSuccessResponse = {
  data: RelationshipsSuccessData;
  meta: RelationshipsSuccessMeta;
};

/** MOD-API-012 の読取 I/F（Router 注入・UT 用）。 */
export type RelationshipMasterReader = {
  listActive(): Promise<RelationshipMasterRow[]>;
};

/** occasion_master 行（DB / scaffold）。is_active はフィルタ専用。 */
export type OccasionMasterRow = {
  occasion_code: string;
  occasion_label: string;
  display_order: number;
  is_active?: boolean;
};

/** Public Response の Occasion 選択肢（契約・OpenAPI）。 */
export type OccasionMasterItem = {
  occasionCode: string;
  occasionLabel: string;
  displayOrder?: number;
};

export type OccasionMastersSuccessResponse = {
  data: {
    occasions: OccasionMasterItem[];
  };
  meta: {
    traceId: string;
    requestId: string;
    generatedAt: string;
    count: number;
  };
};

/** API-PUB-007 Public Concept 項目。 */
export type SemanticConceptItem = {
  conceptCode: string;
  conceptLabel: string;
  conceptDescription?: string;
  isActive: boolean;
};

/** API-PUB-007 Public Feature Definition 項目。 */
export type FeatureDefinitionItem = {
  featureCode: string;
  featureLabel: string;
  featureGroup: "social" | "symbolic" | string;
  displayOrder?: number;
  isActive: boolean;
};

export type SemanticConfigMastersData = {
  configName: string;
  versionLabel: string;
  semanticConcepts: SemanticConceptItem[];
  featureDefinitions: FeatureDefinitionItem[];
};

export type SemanticConfigMastersSuccessResponse = {
  data: SemanticConfigMastersData;
  meta: {
    traceId: string;
    requestId: string;
    generatedAt: string;
  };
};

/** MOD-API-012 の読取 I/F（Router 注入・UT 用）。 */
export type SemanticConfigReader = {
  getCurrentSnapshot(): Promise<SemanticConfigMastersData>;
};

/** API-PUB-008 Relationship 基準値 Rule。 */
export type RelationshipBaseValueRuleItem = {
  ruleType: "relationship";
  relationshipCode: string;
  featureCode: string;
  featureBaseValue: number;
};

/** API-PUB-008 Occasion 基準値 Rule。 */
export type OccasionBaseValueRuleItem = {
  ruleType: "occasion";
  occasionCode: string;
  featureCode: string;
  featureBaseValue: number;
};

export type BaseValueRuleMasterItem =
  | RelationshipBaseValueRuleItem
  | OccasionBaseValueRuleItem;

/** API-PUB-008 Concept Feature Rule。 */
export type ConceptFeatureRuleMasterItem = {
  conceptCode: string;
  featureCode: string;
  featureDelta: number;
  polarity?: "positive" | "negative" | "mixed";
};

export type FeatureRuleMastersData = {
  configName: string;
  versionLabel: string;
  baseValueRules: BaseValueRuleMasterItem[];
  conceptFeatureRules: ConceptFeatureRuleMasterItem[];
};

export type FeatureRuleMastersSuccessResponse = {
  data: FeatureRuleMastersData;
  meta: {
    traceId: string;
    requestId: string;
    generatedAt: string;
  };
};

/** MOD-API-012 Feature Rule 読取 I/F（Router 注入・UT 用）。 */
export type FeatureRuleReader = {
  getCurrentRules(): Promise<FeatureRuleMastersData>;
};
