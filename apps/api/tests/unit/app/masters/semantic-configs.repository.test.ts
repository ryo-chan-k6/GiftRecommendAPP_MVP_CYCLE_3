import assert from "node:assert/strict";
import { test } from "node:test";

import {
  SEMANTIC_CONFIG_MASTERS_ERROR_CODES,
  SemanticConfigRepository,
  SemanticConfigVersionResolver,
} from "../../../../src/app/masters/index.js";
import {
  DbError,
  ScaffoldDbSession,
  type DbHealth,
  type DbQueryParams,
  type DbQueryResult,
  type DbRow,
  type DbSession,
} from "../../../../src/infrastructure/db/index.js";
import { ApiError } from "../../../../src/middlewares/error/api-error.js";

/** SQL 内容に応じて行を返す session（Version / Concept / Feature）。 */
class MultiQuerySession implements DbSession {
  readonly backend = "multi-query";
  readonly operations: { sql: string; params?: DbQueryParams }[] = [];

  constructor(
    private readonly handlers: {
      versionRows: DbRow[];
      conceptRows: DbRow[];
      featureRows: DbRow[];
    },
  ) {}

  healthCheck(): DbHealth {
    return { isAvailable: true, backend: this.backend };
  }

  async query<TRow extends DbRow = DbRow>(
    sql: string,
    params?: DbQueryParams,
  ): Promise<DbQueryResult<TRow>> {
    this.operations.push({ sql, params });
    let rows: DbRow[] = [];
    if (sql.includes("FROM semantic_config_version")) {
      rows = this.handlers.versionRows;
    } else if (sql.includes("FROM semantic_concept")) {
      rows = this.handlers.conceptRows;
    } else if (sql.includes("FROM feature_definition")) {
      rows = this.handlers.featureRows;
    }
    return { rows: rows as TRow[], rowCount: rows.length };
  }

  async execute(): Promise<number> {
    return 0;
  }
}

test("SemanticConfigVersionResolver returns single current version", async () => {
  const session = new ScaffoldDbSession({
    queryRows: [
      {
        semantic_config_version_id: "ver-1",
        config_name: "mvp-default",
        version_label: "v1",
      },
    ],
  });
  const resolver = new SemanticConfigVersionResolver({ session });
  const current = await resolver.resolveCurrent();
  assert.equal(current.configName, "mvp-default");
  assert.equal(current.versionLabel, "v1");
  assert.equal(current.semanticConfigVersionId, "ver-1");
});

test("SemanticConfigVersionResolver throws GRS-CFG-001 when empty", async () => {
  const resolver = new SemanticConfigVersionResolver({
    session: new ScaffoldDbSession({ queryRows: [] }),
  });
  await assert.rejects(
    () => resolver.resolveCurrent(),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(
        error.code,
        SEMANTIC_CONFIG_MASTERS_ERROR_CODES.CURRENT_NOT_FOUND,
      );
      return true;
    },
  );
});

test("SemanticConfigVersionResolver throws GRS-CFG-002 when multiple current", async () => {
  const resolver = new SemanticConfigVersionResolver({
    session: new ScaffoldDbSession({
      queryRows: [
        {
          semantic_config_version_id: "ver-1",
          config_name: "a",
          version_label: "v1",
        },
        {
          semantic_config_version_id: "ver-2",
          config_name: "b",
          version_label: "v2",
        },
      ],
    }),
  });
  await assert.rejects(
    () => resolver.resolveCurrent(),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(
        error.code,
        SEMANTIC_CONFIG_MASTERS_ERROR_CODES.RESOLVE_FAILED,
      );
      return true;
    },
  );
});

test("SemanticConfigRepository assembles snapshot and rejects feature empty", async () => {
  const okSession = new MultiQuerySession({
    versionRows: [
      {
        semantic_config_version_id: "ver-1",
        config_name: "mvp-default",
        version_label: "v1",
      },
    ],
    conceptRows: [
      {
        concept_code: "thanks",
        concept_label: "感謝",
        concept_description: null,
        is_active: true,
      },
    ],
    featureRows: [
      {
        feature_code: "formality",
        feature_label: "フォーマル度",
        feature_group: "social",
        display_order: 1,
        is_active: true,
      },
    ],
  });

  const repository = new SemanticConfigRepository({ session: okSession });
  const snapshot = await repository.getCurrentSnapshot();
  assert.equal(snapshot.configName, "mvp-default");
  assert.equal(snapshot.semanticConcepts.length, 1);
  assert.equal(snapshot.featureDefinitions[0]?.featureCode, "formality");
  assert.equal("semanticConfigVersionId" in snapshot, false);
  assert.ok(
    okSession.operations[0]?.sql.includes("is_current = true"),
  );

  const emptyFeatureSession = new MultiQuerySession({
    versionRows: [
      {
        semantic_config_version_id: "ver-1",
        config_name: "mvp-default",
        version_label: "v1",
      },
    ],
    conceptRows: [],
    featureRows: [],
  });
  const emptyRepo = new SemanticConfigRepository({
    session: emptyFeatureSession,
  });
  await assert.rejects(
    () => emptyRepo.getCurrentSnapshot(),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(
        error.code,
        SEMANTIC_CONFIG_MASTERS_ERROR_CODES.FEATURE_MISSING,
      );
      return true;
    },
  );
});

test("SemanticConfigVersionResolver maps DbError to GRS-DB-002", async () => {
  class FailSession implements DbSession {
    readonly backend = "fail";
    healthCheck(): DbHealth {
      return { isAvailable: true, backend: this.backend };
    }
    async query<TRow extends DbRow = DbRow>(
      _sql: string,
      _params?: DbQueryParams,
    ): Promise<DbQueryResult<TRow>> {
      throw new DbError({
        code: "DB_QUERY_FAILED",
        message: "simulated",
        retryable: true,
      });
    }
    async execute(): Promise<number> {
      return 0;
    }
  }

  const resolver = new SemanticConfigVersionResolver({
    session: new FailSession(),
  });
  await assert.rejects(
    () => resolver.resolveCurrent(),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(
        error.code,
        SEMANTIC_CONFIG_MASTERS_ERROR_CODES.DB_READ_FAILED,
      );
      return true;
    },
  );
});
