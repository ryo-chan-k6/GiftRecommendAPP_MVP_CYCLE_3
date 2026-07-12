import { DbError } from "./errors.js";
import type {
  DbHealth,
  DbQueryParams,
  DbQueryResult,
  DbRow,
} from "./types.js";

export interface DbSession {
  readonly backend: string;

  healthCheck(): DbHealth;

  query<TRow extends DbRow = DbRow>(
    sql: string,
    params?: DbQueryParams,
  ): Promise<DbQueryResult<TRow>>;

  execute(sql: string, params?: DbQueryParams): Promise<number>;
}

export type ScaffoldDbSessionOptions = {
  backend?: string;
  isAvailable?: boolean;
  queryRows?: DbRow[];
  affectedRows?: number;
};

/** Phase4a placeholder session without a real PostgreSQL connection. */
export class ScaffoldDbSession implements DbSession {
  readonly backend: string;
  private readonly isAvailable: boolean;
  private readonly queryRows: DbRow[];
  private readonly affectedRows: number;
  readonly operations: Array<{
    kind: "query" | "execute";
    sql: string;
    params: DbQueryParams;
  }>;

  constructor(options: ScaffoldDbSessionOptions = {}) {
    this.backend = options.backend ?? "scaffold";
    this.isAvailable = options.isAvailable ?? true;
    this.queryRows = options.queryRows ?? [];
    this.affectedRows = options.affectedRows ?? 0;
    this.operations = [];
  }

  healthCheck(): DbHealth {
    return {
      isAvailable: this.isAvailable,
      backend: this.backend,
    };
  }

  async query<TRow extends DbRow = DbRow>(
    sql: string,
    params: DbQueryParams = [],
  ): Promise<DbQueryResult<TRow>> {
    this.assertAvailable();

    this.operations.push({ kind: "query", sql, params });

    const rows = this.queryRows as TRow[];

    return {
      rows,
      rowCount: rows.length,
    };
  }

  async execute(
    sql: string,
    params: DbQueryParams = [],
  ): Promise<number> {
    this.assertAvailable();

    this.operations.push({ kind: "execute", sql, params });

    return this.affectedRows;
  }

  private assertAvailable(): void {
    if (!this.isAvailable) {
      throw new DbError({
        code: "DB_UNAVAILABLE",
        message: "database session is unavailable",
        retryable: true,
      });
    }
  }
}
