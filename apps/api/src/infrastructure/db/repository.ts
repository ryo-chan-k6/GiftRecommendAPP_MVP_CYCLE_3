import { DbError } from "./errors.js";
import type { DbSession } from "./session.js";
import type { DbQueryParams, DbRow } from "./types.js";

export interface DbRepository {
  readonly session: DbSession;
}

export type ScaffoldDbRepositoryOptions<TRow extends DbRow> = {
  session: DbSession;
  tableName: string;
  rows?: TRow[];
};

/**
 * Phase4a base Repository scaffold.
 * Domain-specific repositories in Phase4b extend this boundary.
 */
export class ScaffoldDbRepository<TRow extends DbRow> implements DbRepository {
  readonly session: DbSession;
  readonly tableName: string;
  readonly findByIdCalls: Array<{ id: string }>;

  private readonly rows: TRow[];

  constructor(options: ScaffoldDbRepositoryOptions<TRow>) {
    this.session = options.session;
    this.tableName = options.tableName;
    this.rows = options.rows ?? [];
    this.findByIdCalls = [];
  }

  async findById(id: string): Promise<TRow | null> {
    this.findByIdCalls.push({ id });

    const sql = `SELECT * FROM ${this.tableName} WHERE id = $1`;
    const result = await this.session.query<TRow>(sql, [id]);

    if (result.rows.length > 0) {
      return result.rows[0] ?? null;
    }

    const matched = this.rows.find((row) => String(row.id) === id);
    return matched ?? null;
  }

  async list(limit = 100): Promise<TRow[]> {
    const sql = `SELECT * FROM ${this.tableName} LIMIT $1`;
    const result = await this.session.query<TRow>(sql, [limit]);

    if (result.rows.length > 0) {
      return result.rows;
    }

    return this.rows.slice(0, limit);
  }

  async requireById(id: string): Promise<TRow> {
    const row = await this.findById(id);

    if (row === null) {
      throw new DbError({
        code: "DB_NOT_FOUND",
        message: `record not found in ${this.tableName}`,
        retryable: false,
      });
    }

    return row;
  }

  protected async runQuery<TRowResult extends DbRow = TRow>(
    sql: string,
    params: DbQueryParams = [],
  ): Promise<TRowResult[]> {
    const result = await this.session.query<TRowResult>(sql, params);
    return result.rows;
  }
}
