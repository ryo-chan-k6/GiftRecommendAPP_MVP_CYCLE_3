import { PostgresDbSession } from "./postgres-session.js";
import { ScaffoldDbSession, type DbSession } from "./session.js";

export type CreateDbSessionOptions = {
  /** Explicit URL. Defaults to `process.env.DATABASE_URL`. */
  databaseUrl?: string | null;
  /** Force scaffold（unit test / CI）。 */
  forceScaffold?: boolean;
};

/**
 * Build a DbSession from DATABASE_URL when a real URL is provided.
 * Empty / missing / `scaffold://` → ScaffoldDbSession（CI・単体テスト向け）。
 */
export function createDbSession(
  options: CreateDbSessionOptions = {},
): DbSession {
  if (options.forceScaffold) {
    return new ScaffoldDbSession();
  }

  const url =
    options.databaseUrl === undefined
      ? process.env.DATABASE_URL
      : options.databaseUrl;

  if (
    typeof url === "string" &&
    url.trim() !== "" &&
    !url.startsWith("scaffold://")
  ) {
    return new PostgresDbSession({ connectionString: url.trim() });
  }

  return new ScaffoldDbSession();
}
