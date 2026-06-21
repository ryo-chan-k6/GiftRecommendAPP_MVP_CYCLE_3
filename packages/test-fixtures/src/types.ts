export type FixtureManifest = {
  schemaVersion: string;
  packageId: string;
  paths: Record<string, string>;
  items: Record<
    string,
    {
      path: string;
      role: string;
    }
  >;
};

export type FeatureFixtureDocument = {
  description: string;
  featureCodes: string[];
  values: Record<string, number>;
};

export type RecommendationRequestFixtureDocument = {
  description: string;
  relationship: {
    relationshipCode: string;
    relationshipLabel: string;
  };
  occasion: {
    occasionCode: string;
    occasionLabel: string;
  };
  budget?: {
    budgetMin?: number;
    budgetMax?: number;
    currency?: string;
    taxIncluded?: boolean;
  };
  execution?: {
    mode?: string;
    topK?: number;
  };
};
