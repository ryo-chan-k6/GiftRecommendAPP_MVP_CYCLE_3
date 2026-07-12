import {
  DbError,
  isDbError,
  type DbSession,
} from "../../infrastructure/db/index.js";
import { ApiError } from "../../middlewares/error/api-error.js";
import {
  OCCASION_MASTERS_ERROR_CODES,
  OCCASION_MASTERS_ERROR_MESSAGES,
} from "./constants.js";
import type { OccasionMasterItem, OccasionMasterRow } from "./types.js";

export type OccasionMasterRepositoryOptions = {
  session: DbSession;
  tableName?: string;
};

/**
 * MOD-API-012: occasion_master 読取。
 * is_active=true のみ。ORDER BY display_order, occasion_code。
 * pair_master は参照しない。
 */
export class OccasionMasterRepository {
  readonly session: DbSession;
  readonly tableName: string;

  constructor(options: OccasionMasterRepositoryOptions) {
    this.session = options.session;
    this.tableName = options.tableName ?? "occasion_master";
  }

  async listActive(): Promise<OccasionMasterItem[]> {
    const health = this.session.healthCheck();
    if (!health.isAvailable) {
      throw new ApiError({
        code: OCCASION_MASTERS_ERROR_CODES.DB_READ_FAILED,
        httpStatus: 500,
        message: OCCASION_MASTERS_ERROR_MESSAGES.DB_READ_FAILED,
        retryable: true,
      });
    }

    const sql = `
SELECT occasion_code, occasion_label, display_order
FROM ${this.tableName}
WHERE is_active = true
ORDER BY display_order ASC, occasion_code ASC
`.trim();

    try {
      const result = await this.session.query<OccasionMasterRow>(sql);
      return result.rows.map(mapRowToItem);
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }

      if (isDbError(error) || error instanceof DbError) {
        throw new ApiError({
          code: OCCASION_MASTERS_ERROR_CODES.DB_READ_FAILED,
          httpStatus: 500,
          message: OCCASION_MASTERS_ERROR_MESSAGES.DB_READ_FAILED,
          retryable: true,
          cause: error,
        });
      }

      throw new ApiError({
        code: OCCASION_MASTERS_ERROR_CODES.UNEXPECTED,
        httpStatus: 500,
        message: OCCASION_MASTERS_ERROR_MESSAGES.UNEXPECTED,
        retryable: false,
        cause: error,
      });
    }
  }
}

function mapRowToItem(row: OccasionMasterRow): OccasionMasterItem {
  const item: OccasionMasterItem = {
    occasionCode: row.occasion_code,
    occasionLabel: row.occasion_label,
  };

  if (row.display_order !== undefined && row.display_order !== null) {
    item.displayOrder = Number(row.display_order);
  }

  return item;
}
