import {
  DbError,
  isDbError,
  type DbSession,
} from "../../infrastructure/db/index.js";
import { ApiError } from "../../middlewares/error/api-error.js";
import {
  SEMANTIC_CONFIG_MASTERS_ERROR_CODES,
  SEMANTIC_CONFIG_MASTERS_ERROR_MESSAGES,
} from "./constants.js";
import {
  SemanticConfigVersionResolver,
  type CurrentSemanticConfigVersion,
} from "./semantic-config-version-resolver.js";
import type {
  FeatureDefinitionItem,
  SemanticConceptItem,
  SemanticConfigMastersData,
  SemanticConfigReader,
} from "./types.js";

export type SemanticConfigRepositoryOptions = {
  session: DbSession;
  versionResolver?: SemanticConfigVersionResolver;
};

type ConceptDbRow = {
  concept_code: string;
  concept_label: string;
  concept_description: string | null;
  is_active: boolean;
};

type FeatureDbRow = {
  feature_code: string;
  feature_label: string;
  feature_group: string;
  display_order: number;
  is_active: boolean;
};

/**
 * MOD-API-012: Semantic Config スナップショット読取。
 * Version 解決は共通 Resolver に委譲。UUID / Rule は Public に載せない。
 */
export class SemanticConfigRepository implements SemanticConfigReader {
  readonly session: DbSession;
  readonly versionResolver: SemanticConfigVersionResolver;

  constructor(options: SemanticConfigRepositoryOptions) {
    this.session = options.session;
    this.versionResolver =
      options.versionResolver ??
      new SemanticConfigVersionResolver({ session: options.session });
  }

  async getCurrentSnapshot(): Promise<SemanticConfigMastersData> {
    const version = await this.versionResolver.resolveCurrent();
    const semanticConcepts = await this.listActiveConcepts(version);
    const featureDefinitions = await this.listActiveFeatures(version);

    if (featureDefinitions.length === 0) {
      throw new ApiError({
        code: SEMANTIC_CONFIG_MASTERS_ERROR_CODES.FEATURE_MISSING,
        httpStatus: 500,
        message: SEMANTIC_CONFIG_MASTERS_ERROR_MESSAGES.FEATURE_MISSING,
        retryable: true,
      });
    }

    return {
      configName: version.configName,
      versionLabel: version.versionLabel,
      semanticConcepts,
      featureDefinitions,
    };
  }

  private async listActiveConcepts(
    version: CurrentSemanticConfigVersion,
  ): Promise<SemanticConceptItem[]> {
    const sql = `
SELECT concept_code, concept_label, concept_description, is_active
FROM semantic_concept
WHERE semantic_config_version_id = $1
  AND is_active = true
ORDER BY concept_code ASC
`.trim();

    try {
      const result = await this.session.query<ConceptDbRow>(sql, [
        version.semanticConfigVersionId,
      ]);
      return result.rows.map(mapConceptRow);
    } catch (error) {
      throw mapReadError(error);
    }
  }

  private async listActiveFeatures(
    version: CurrentSemanticConfigVersion,
  ): Promise<FeatureDefinitionItem[]> {
    const sql = `
SELECT feature_code, feature_label, feature_group, display_order, is_active
FROM feature_definition
WHERE semantic_config_version_id = $1
  AND is_active = true
ORDER BY display_order ASC, feature_code ASC
`.trim();

    try {
      const result = await this.session.query<FeatureDbRow>(sql, [
        version.semanticConfigVersionId,
      ]);
      return result.rows.map(mapFeatureRow);
    } catch (error) {
      throw mapReadError(error);
    }
  }
}

/** DATABASE_URL 未設定等 → GRS-CFG-001（実装仕様書 §11）。 */
export class UnresolvedSemanticConfigReader implements SemanticConfigReader {
  async getCurrentSnapshot(): Promise<SemanticConfigMastersData> {
    throw new ApiError({
      code: SEMANTIC_CONFIG_MASTERS_ERROR_CODES.CURRENT_NOT_FOUND,
      httpStatus: 500,
      message: SEMANTIC_CONFIG_MASTERS_ERROR_MESSAGES.CURRENT_NOT_FOUND,
      retryable: true,
    });
  }
}

/** UT 用固定スナップショット Reader。 */
export class InMemorySemanticConfigReader implements SemanticConfigReader {
  constructor(private readonly snapshot: SemanticConfigMastersData) {}

  async getCurrentSnapshot(): Promise<SemanticConfigMastersData> {
    return {
      configName: this.snapshot.configName,
      versionLabel: this.snapshot.versionLabel,
      semanticConcepts: [...this.snapshot.semanticConcepts],
      featureDefinitions: [...this.snapshot.featureDefinitions],
    };
  }
}

function mapConceptRow(row: ConceptDbRow): SemanticConceptItem {
  const item: SemanticConceptItem = {
    conceptCode: row.concept_code,
    conceptLabel: row.concept_label,
    isActive: true,
  };
  if (row.concept_description !== undefined && row.concept_description !== null) {
    item.conceptDescription = row.concept_description;
  }
  return item;
}

function mapFeatureRow(row: FeatureDbRow): FeatureDefinitionItem {
  const item: FeatureDefinitionItem = {
    featureCode: row.feature_code,
    featureLabel: row.feature_label,
    featureGroup: row.feature_group as FeatureDefinitionItem["featureGroup"],
    isActive: true,
  };
  if (row.display_order !== undefined && row.display_order !== null) {
    item.displayOrder = Number(row.display_order);
  }
  return item;
}

function mapReadError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error;
  }

  if (isDbError(error) || error instanceof DbError) {
    return new ApiError({
      code: SEMANTIC_CONFIG_MASTERS_ERROR_CODES.DB_READ_FAILED,
      httpStatus: 500,
      message: SEMANTIC_CONFIG_MASTERS_ERROR_MESSAGES.DB_READ_FAILED,
      retryable: true,
      cause: error,
    });
  }

  return new ApiError({
    code: SEMANTIC_CONFIG_MASTERS_ERROR_CODES.UNEXPECTED,
    httpStatus: 500,
    message: SEMANTIC_CONFIG_MASTERS_ERROR_MESSAGES.UNEXPECTED,
    retryable: false,
    cause: error,
  });
}
