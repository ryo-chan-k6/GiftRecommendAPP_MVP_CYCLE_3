import { test } from "node:test";
import assert from "node:assert/strict";
import {
  DbError,
  isDbError,
  maskDatabaseUrl,
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
