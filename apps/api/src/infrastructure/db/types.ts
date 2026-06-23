/** Database access types for Phase4a API db Repository scaffold. */

export type DbHealth = {
  isAvailable: boolean;
  backend: string;
};

/** Parameterized query input. Values are bound by the session implementation. */
export type DbQueryParams = readonly unknown[];

export type DbQueryResult<TRow extends DbRow = DbRow> = {
  rows: TRow[];
  rowCount: number;
};

export type DbRow = Record<string, unknown>;

export type DbRepositoryOperation = {
  operation: "query" | "execute";
  sql: string;
  params: DbQueryParams;
};
