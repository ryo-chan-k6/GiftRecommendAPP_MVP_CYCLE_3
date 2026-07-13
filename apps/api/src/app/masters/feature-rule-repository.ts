import {
  DbError,
  isDbError,
  type DbSession,
} from "../../infrastructure/db/index.js";
import { ApiError } from "../../middlewares/error/api-error.js";
import {
  FEATURE_RULE_MASTERS_ERROR_CODES,
  FEATURE_RULE_MASTERS_ERROR_MESSAGES,
} from "./constants.js";
import {
  SemanticConfigVersionResolver,
  type CurrentSemanticConfigVersion,
} from "./semantic-config-version-resolver.js";
import type {
  BaseValueRuleMasterItem,
  ConceptFeatureRuleMasterItem,
  FeatureRuleMastersData,
  FeatureRuleReader,
  OccasionBaseValueRuleItem,
  RelationshipBaseValueRuleItem,
} from "./types.js";

export type FeatureRuleRepositoryOptions = {
  session: DbSession;
  versionResolver?: SemanticConfigVersionResolver;
};

type RelationshipRuleDbRow = {
  relationship_code: string;
  feature_code: string;
  feature_base_value: string | number;
};

type OccasionRuleDbRow = {
  occasion_code: string;
  feature_code: string;
  feature_base_value: string | number;
};

type ConceptFeatureRuleDbRow = {
  concept_code: string;
  feature_code: string;
  feature_delta: string | number;
  polarity: string | null;
};

/**
 * MOD-API-012: Feature Rule 読取。
 * Version 解決は共通 Resolver に委譲。Pair / is_active は Public に載せない。
 */
export class FeatureRuleRepository implements FeatureRuleReader {
  readonly session: DbSession;
  readonly versionResolver: SemanticConfigVersionResolver;

  constructor(options: FeatureRuleRepositoryOptions) {
    this.session = options.session;
    this.versionResolver =
      options.versionResolver ??
      new SemanticConfigVersionResolver({ session: options.session });
  }

  async getCurrentRules(): Promise<FeatureRuleMastersData> {
    const version = await this.versionResolver.resolveCurrent();
    const [relationshipRules, occasionRules, conceptFeatureRules] =
      await Promise.all([
        this.listActiveRelationshipRules(version),
        this.listActiveOccasionRules(version),
        this.listActiveConceptFeatureRules(version),
      ]);

    return {
      configName: version.configName,
      versionLabel: version.versionLabel,
      baseValueRules: [...relationshipRules, ...occasionRules],
      conceptFeatureRules,
    };
  }

  private async listActiveRelationshipRules(
    version: CurrentSemanticConfigVersion,
  ): Promise<RelationshipBaseValueRuleItem[]> {
    const sql = `
SELECT relationship_code, feature_code, feature_base_value
FROM relationship_rule
WHERE semantic_config_version_id = $1
  AND is_active = true
ORDER BY relationship_code ASC, feature_code ASC
`.trim();

    try {
      const result = await this.session.query<RelationshipRuleDbRow>(sql, [
        version.semanticConfigVersionId,
      ]);
      return result.rows.map(mapRelationshipRuleRow);
    } catch (error) {
      throw mapReadError(error);
    }
  }

  private async listActiveOccasionRules(
    version: CurrentSemanticConfigVersion,
  ): Promise<OccasionBaseValueRuleItem[]> {
    const sql = `
SELECT occasion_code, feature_code, feature_base_value
FROM occasion_rule
WHERE semantic_config_version_id = $1
  AND is_active = true
ORDER BY occasion_code ASC, feature_code ASC
`.trim();

    try {
      const result = await this.session.query<OccasionRuleDbRow>(sql, [
        version.semanticConfigVersionId,
      ]);
      return result.rows.map(mapOccasionRuleRow);
    } catch (error) {
      throw mapReadError(error);
    }
  }

  private async listActiveConceptFeatureRules(
    version: CurrentSemanticConfigVersion,
  ): Promise<ConceptFeatureRuleMasterItem[]> {
    const sql = `
SELECT sc.concept_code, cfr.feature_code, cfr.feature_delta, cfr.polarity
FROM concept_feature_rule cfr
INNER JOIN semantic_concept sc
  ON sc.semantic_concept_id = cfr.semantic_concept_id
WHERE cfr.semantic_config_version_id = $1
  AND cfr.is_active = true
ORDER BY sc.concept_code ASC, cfr.feature_code ASC
`.trim();

    try {
      const result = await this.session.query<ConceptFeatureRuleDbRow>(sql, [
        version.semanticConfigVersionId,
      ]);
      return result.rows.map(mapConceptFeatureRuleRow);
    } catch (error) {
      throw mapReadError(error);
    }
  }
}

/** DATABASE_URL 未設定等 → GRS-CFG-005。 */
export class UnresolvedFeatureRuleReader implements FeatureRuleReader {
  async getCurrentRules(): Promise<FeatureRuleMastersData> {
    throw new ApiError({
      code: FEATURE_RULE_MASTERS_ERROR_CODES.CONFIG_UNRESOLVED,
      httpStatus: 500,
      message: FEATURE_RULE_MASTERS_ERROR_MESSAGES.CONFIG_UNRESOLVED,
      retryable: true,
    });
  }
}

/** UT 用固定スナップショット Reader。 */
export class InMemoryFeatureRuleReader implements FeatureRuleReader {
  constructor(private readonly snapshot: FeatureRuleMastersData) {}

  async getCurrentRules(): Promise<FeatureRuleMastersData> {
    return {
      configName: this.snapshot.configName,
      versionLabel: this.snapshot.versionLabel,
      baseValueRules: [...this.snapshot.baseValueRules] as BaseValueRuleMasterItem[],
      conceptFeatureRules: [...this.snapshot.conceptFeatureRules],
    };
  }
}

function toNumber(value: string | number): number {
  return typeof value === "number" ? value : Number(value);
}

function mapRelationshipRuleRow(
  row: RelationshipRuleDbRow,
): RelationshipBaseValueRuleItem {
  return {
    ruleType: "relationship",
    relationshipCode: row.relationship_code,
    featureCode: row.feature_code,
    featureBaseValue: toNumber(row.feature_base_value),
  };
}

function mapOccasionRuleRow(row: OccasionRuleDbRow): OccasionBaseValueRuleItem {
  return {
    ruleType: "occasion",
    occasionCode: row.occasion_code,
    featureCode: row.feature_code,
    featureBaseValue: toNumber(row.feature_base_value),
  };
}

function mapConceptFeatureRuleRow(
  row: ConceptFeatureRuleDbRow,
): ConceptFeatureRuleMasterItem {
  const item: ConceptFeatureRuleMasterItem = {
    conceptCode: row.concept_code,
    featureCode: row.feature_code,
    featureDelta: toNumber(row.feature_delta),
  };
  if (
    row.polarity === "positive" ||
    row.polarity === "negative" ||
    row.polarity === "mixed"
  ) {
    item.polarity = row.polarity;
  }
  return item;
}

function mapReadError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error;
  }

  if (isDbError(error) || error instanceof DbError) {
    return new ApiError({
      code: FEATURE_RULE_MASTERS_ERROR_CODES.DB_READ_FAILED,
      httpStatus: 500,
      message: FEATURE_RULE_MASTERS_ERROR_MESSAGES.DB_READ_FAILED,
      retryable: true,
      cause: error,
    });
  }

  return new ApiError({
    code: FEATURE_RULE_MASTERS_ERROR_CODES.UNEXPECTED,
    httpStatus: 500,
    message: FEATURE_RULE_MASTERS_ERROR_MESSAGES.UNEXPECTED,
    retryable: false,
    cause: error,
  });
}
