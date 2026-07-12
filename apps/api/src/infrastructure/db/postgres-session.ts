import pg from "pg";

import { maskDatabaseUrl } from "./connection.js";
import { DbError } from "./errors.js";
import type { DbSession } from "./session.js";
import type {
  DbHealth,
  DbQueryParams,
  DbQueryResult,
  DbRow,
} from "./types.js";

const { Pool } = pg;

export type PostgresDbSessionOptions = {
  connectionString: string;
  /** Injected pool for unit tests. */
  pool?: pg.Pool;
};

/** PostgreSQL session backed by `pg` Pool（DATABASE_URL）。 */
export class PostgresDbSession implements DbSession {
  readonly backend = "postgres";
  private readonly pool: pg.Pool;
  private readonly maskedUrl: string;

  constructor(options: PostgresDbSessionOptions) {
    const connectionString = options.connectionString.trim();
    if (connectionString === "") {
      throw new DbError({
        code: "DB_UNAVAILABLE",
        message: "DATABASE_URL is empty",
        retryable: false,
      });
    }

    this.maskedUrl = maskDatabaseUrl(connectionString);
    this.pool =
      options.pool ??
      new Pool({
        connectionString,
      });
  }

  /** Masked connection string for safe logging (never log raw URL). */
  get connectionInfo(): string {
    return this.maskedUrl;
  }

  healthCheck(): DbHealth {
    return {
      isAvailable: true,
      backend: this.backend,
    };
  }

  async query<TRow extends DbRow = DbRow>(
    sql: string,
    params: DbQueryParams = [],
  ): Promise<DbQueryResult<TRow>> {
    try {
      const result = await this.pool.query(sql, [...params]);
      return {
        rows: result.rows as TRow[],
        rowCount: result.rowCount ?? result.rows.length,
      };
    } catch (error) {
      throw new DbError({
        code: "DB_QUERY_FAILED",
        message: "database query failed",
        retryable: true,
        cause: error,
      });
    }
  }

  async execute(sql: string, params: DbQueryParams = []): Promise<number> {
    const result = await this.query(sql, params);
    return result.rowCount;
  }

  async end(): Promise<void> {
    await this.pool.end();
  }
}
