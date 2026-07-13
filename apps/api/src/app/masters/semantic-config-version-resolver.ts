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

/** PUB-007 / PUB-008 共通: current Semantic Config Version 解決結果。 */
export type CurrentSemanticConfigVersion = {
  semanticConfigVersionId: string;
  configName: string;
  versionLabel: string;
};

export type SemanticConfigVersionResolverOptions = {
  session: DbSession;
};

type CurrentVersionDbRow = {
  semantic_config_version_id: string;
  config_name: string;
  version_label: string;
};

/**
 * current Version Resolver（実装仕様書 §3.2 / §11）。
 * 親 is_active → 子 is_current → JOIN config_name。
 * 0 件 → GRS-CFG-001、複数件 → GRS-CFG-002。キャッシュなし（都度 SELECT）。
 */
export class SemanticConfigVersionResolver {
  readonly session: DbSession;

  constructor(options: SemanticConfigVersionResolverOptions) {
    this.session = options.session;
  }

  async resolveCurrent(): Promise<CurrentSemanticConfigVersion> {
    const health = this.session.healthCheck();
    if (!health.isAvailable) {
      throw new ApiError({
        code: SEMANTIC_CONFIG_MASTERS_ERROR_CODES.DB_READ_FAILED,
        httpStatus: 500,
        message: SEMANTIC_CONFIG_MASTERS_ERROR_MESSAGES.DB_READ_FAILED,
        retryable: true,
      });
    }

    const sql = `
SELECT scv.semantic_config_version_id, sc.config_name, scv.version_label
FROM semantic_config_version scv
INNER JOIN semantic_config sc
  ON sc.semantic_config_id = scv.semantic_config_id
WHERE sc.is_active = true
  AND scv.is_current = true
`.trim();

    try {
      const result = await this.session.query<CurrentVersionDbRow>(sql);

      if (result.rows.length === 0) {
        throw new ApiError({
          code: SEMANTIC_CONFIG_MASTERS_ERROR_CODES.CURRENT_NOT_FOUND,
          httpStatus: 500,
          message: SEMANTIC_CONFIG_MASTERS_ERROR_MESSAGES.CURRENT_NOT_FOUND,
          retryable: true,
        });
      }

      if (result.rows.length > 1) {
        throw new ApiError({
          code: SEMANTIC_CONFIG_MASTERS_ERROR_CODES.RESOLVE_FAILED,
          httpStatus: 500,
          message: SEMANTIC_CONFIG_MASTERS_ERROR_MESSAGES.RESOLVE_FAILED,
          retryable: true,
        });
      }

      const row = result.rows[0]!;
      return {
        semanticConfigVersionId: String(row.semantic_config_version_id),
        configName: row.config_name,
        versionLabel: row.version_label,
      };
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }

      if (isDbError(error) || error instanceof DbError) {
        throw new ApiError({
          code: SEMANTIC_CONFIG_MASTERS_ERROR_CODES.DB_READ_FAILED,
          httpStatus: 500,
          message: SEMANTIC_CONFIG_MASTERS_ERROR_MESSAGES.DB_READ_FAILED,
          retryable: true,
          cause: error,
        });
      }

      throw new ApiError({
        code: SEMANTIC_CONFIG_MASTERS_ERROR_CODES.RESOLVE_FAILED,
        httpStatus: 500,
        message: SEMANTIC_CONFIG_MASTERS_ERROR_MESSAGES.RESOLVE_FAILED,
        retryable: true,
        cause: error,
      });
    }
  }
}
