import { DbError } from "../../infrastructure/db/errors.js";
import type { DbSession } from "../../infrastructure/db/session.js";
import type { DbRow } from "../../infrastructure/db/types.js";
import { ApiError } from "../../middlewares/error/api-error.js";
import {
  MASTERS_RELATIONSHIPS_ERROR_CODES,
  MASTERS_RELATIONSHIPS_ERROR_MESSAGES,
} from "./constants.js";
import type {
  RelationshipMasterReader,
  RelationshipMasterRow,
} from "./types.js";

export type RelationshipMasterRepositoryOptions = {
  session: DbSession;
  tableName?: string;
};

type RelationshipMasterDbRow = DbRow & {
  relationship_code: string;
  relationship_label: string;
  display_order: number;
};

/**
 * MOD-API-012: relationship_master 参照。
 * is_active=true のみ、ORDER BY display_order, relationship_code。
 */
export class RelationshipMasterRepository implements RelationshipMasterReader {
  readonly session: DbSession;
  readonly tableName: string;

  constructor(options: RelationshipMasterRepositoryOptions) {
    this.session = options.session;
    this.tableName = options.tableName ?? "relationship_master";
  }

  async listActive(): Promise<RelationshipMasterRow[]> {
    try {
      const result = await this.session.query<RelationshipMasterDbRow>(
        `SELECT relationship_code, relationship_label, display_order
         FROM ${this.tableName}
         WHERE is_active = true
         ORDER BY display_order ASC, relationship_code ASC`,
      );

      return result.rows.map((row) => ({
        relationshipCode: row.relationship_code,
        relationshipLabel: row.relationship_label,
        displayOrder: row.display_order,
      }));
    } catch (error) {
      if (error instanceof DbError) {
        throw new ApiError({
          code: MASTERS_RELATIONSHIPS_ERROR_CODES.DB_READ_FAILED,
          httpStatus: 500,
          message: MASTERS_RELATIONSHIPS_ERROR_MESSAGES.DB_READ_FAILED,
          retryable: true,
          cause: error,
        });
      }
      throw error;
    }
  }
}

/** DATABASE_URL 未設定等でマスタ参照不能なときの Reader（GRS-CFG-005）。 */
export class UnresolvedRelationshipMasterReader
  implements RelationshipMasterReader
{
  async listActive(): Promise<RelationshipMasterRow[]> {
    throw new ApiError({
      code: MASTERS_RELATIONSHIPS_ERROR_CODES.MASTER_CONFIG_UNRESOLVED,
      httpStatus: 500,
      message: MASTERS_RELATIONSHIPS_ERROR_MESSAGES.MASTER_CONFIG_UNRESOLVED,
      retryable: true,
    });
  }
}

/** UT 用の固定行 Reader。 */
export class InMemoryRelationshipMasterReader
  implements RelationshipMasterReader
{
  constructor(private readonly rows: RelationshipMasterRow[]) {}

  async listActive(): Promise<RelationshipMasterRow[]> {
    return [...this.rows].sort((a, b) => {
      if (a.displayOrder !== b.displayOrder) {
        return a.displayOrder - b.displayOrder;
      }
      return a.relationshipCode.localeCompare(b.relationshipCode);
    });
  }
}

export function isDatabaseUrlConfigured(
  databaseUrl: string | undefined | null = process.env.DATABASE_URL,
): boolean {
  if (typeof databaseUrl !== "string") {
    return false;
  }
  const trimmed = databaseUrl.trim();
  return trimmed !== "" && !trimmed.startsWith("scaffold://");
}
