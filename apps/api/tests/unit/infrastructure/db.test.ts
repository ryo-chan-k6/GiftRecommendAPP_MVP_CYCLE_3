import { test } from "node:test";
import assert from "node:assert/strict";
import {
  createDbSession,
  DbError,
  isDbError,
  maskDatabaseUrl,
  PostgresDbSession,
  ScaffoldDbRepository,
  ScaffoldDbSession,
} from "../../../src/infrastructure/db/index.js";

test("ScaffoldDbSession reports health", () => {
  const session = new ScaffoldDbSession();

  assert.deepEqual(session.healthCheck(), {
    isAvailable: true,
    backend: "scaffold",
  });
});

test("ScaffoldDbSession records query and execute operations", async () => {
  const session = new ScaffoldDbSession({
    queryRows: [{ id: "req-1", status: "pending" }],
    affectedRows: 2,
  });

  const queryResult = await session.query(
    "SELECT * FROM recommendation_request WHERE id = $1",
    ["req-1"],
  );
  const affected = await session.execute(
    "UPDATE recommendation_request SET status = $1 WHERE id = $2",
    ["completed", "req-1"],
  );

  assert.equal(queryResult.rowCount, 1);
  assert.deepEqual(queryResult.rows[0], { id: "req-1", status: "pending" });
  assert.equal(affected, 2);
  assert.deepEqual(session.operations, [
    {
      kind: "query",
      sql: "SELECT * FROM recommendation_request WHERE id = $1",
      params: ["req-1"],
    },
    {
      kind: "execute",
      sql: "UPDATE recommendation_request SET status = $1 WHERE id = $2",
      params: ["completed", "req-1"],
    },
  ]);
});

test("ScaffoldDbSession throws DB_UNAVAILABLE when session is down", async () => {
  const session = new ScaffoldDbSession({ isAvailable: false });

  await assert.rejects(
    () => session.query("SELECT 1"),
    (error: unknown) => {
      assert.equal(isDbError(error), true);
      assert.equal((error as DbError).code, "DB_UNAVAILABLE");
      assert.equal((error as DbError).retryable, true);
      return true;
    },
  );
});

test("ScaffoldDbRepository finds rows via session or fallback rows", async () => {
  const session = new ScaffoldDbSession();
  const repository = new ScaffoldDbRepository({
    session,
    tableName: "relationship_master",
    rows: [{ id: "rel-1", label: "friend" }],
  });

  const found = await repository.findById("rel-1");
  const missing = await repository.findById("rel-999");

  assert.deepEqual(found, { id: "rel-1", label: "friend" });
  assert.equal(missing, null);
  assert.deepEqual(repository.findByIdCalls, [
    { id: "rel-1" },
    { id: "rel-999" },
  ]);
  assert.equal(session.operations.length, 2);
});

test("ScaffoldDbRepository.requireById throws DB_NOT_FOUND", async () => {
  const repository = new ScaffoldDbRepository({
    session: new ScaffoldDbSession(),
    tableName: "occasion_master",
    rows: [],
  });

  await assert.rejects(
    () => repository.requireById("occ-1"),
    (error: unknown) => {
      assert.equal(isDbError(error), true);
      assert.equal((error as DbError).code, "DB_NOT_FOUND");
      assert.equal((error as DbError).retryable, false);
      return true;
    },
  );
});

test("maskDatabaseUrl redacts credentials", () => {
  const masked = maskDatabaseUrl(
    "postgresql://app_user:secret-pass@db.example.com:5432/gift_reco",
  );

  assert.equal(
    masked,
    "postgresql://***REDACTED***:***REDACTED***@db.example.com:5432/gift_reco",
  );
  assert.equal(maskDatabaseUrl(""), "");
});

test("createDbSession uses scaffold when URL is missing or scaffold://", () => {
  const missing = createDbSession({ databaseUrl: null });
  const empty = createDbSession({ databaseUrl: "  " });
  const scaffoldScheme = createDbSession({
    databaseUrl: "scaffold://local",
  });
  const forced = createDbSession({
    databaseUrl: "postgresql://u:p@localhost:5432/db",
    forceScaffold: true,
  });

  assert.equal(missing.backend, "scaffold");
  assert.equal(empty.backend, "scaffold");
  assert.equal(scaffoldScheme.backend, "scaffold");
  assert.equal(forced.backend, "scaffold");
});

test("createDbSession uses postgres when URL is set", async () => {
  const session = createDbSession({
    databaseUrl: "postgresql://app_user:secret-pass@127.0.0.1:54322/postgres",
  });

  assert.equal(session.backend, "postgres");
  assert.ok(session instanceof PostgresDbSession);
  assert.equal(
    session.connectionInfo,
    "postgresql://***REDACTED***:***REDACTED***@127.0.0.1:54322/postgres",
  );
  await session.end();
});

test("PostgresDbSession query/execute use parameterized pool.query", async () => {
  const calls: Array<{ sql: string; params: unknown[] }> = [];
  const pool = {
    query: async (sql: string, params: unknown[]) => {
      calls.push({ sql, params });
      return { rows: [{ ok: 1 }], rowCount: 1 };
    },
    end: async () => undefined,
  };

  const session = new PostgresDbSession({
    connectionString:
      "postgresql://app_user:secret-pass@127.0.0.1:54322/postgres",
    pool: pool as never,
  });

  const result = await session.query("SELECT 1 AS ok WHERE id = $1", ["x"]);
  const affected = await session.execute(
    "INSERT INTO recommendation_request (recommendation_request_id) VALUES ($1)",
    ["id-1"],
  );

  assert.deepEqual(result.rows, [{ ok: 1 }]);
  assert.equal(affected, 1);
  assert.equal(calls.length, 2);
  assert.deepEqual(calls[0]?.params, ["x"]);
  assert.deepEqual(calls[1]?.params, ["id-1"]);
});

test("PostgresDbSession wraps pool errors as DbError", async () => {
  const pool = {
    query: async () => {
      throw new Error("connection refused");
    },
    end: async () => undefined,
  };

  const session = new PostgresDbSession({
    connectionString:
      "postgresql://app_user:secret-pass@127.0.0.1:54322/postgres",
    pool: pool as never,
  });

  await assert.rejects(
    () => session.query("SELECT 1"),
    (error: unknown) => {
      assert.equal(isDbError(error), true);
      assert.equal((error as DbError).code, "DB_QUERY_FAILED");
      assert.equal((error as DbError).retryable, true);
      return true;
    },
  );
});
