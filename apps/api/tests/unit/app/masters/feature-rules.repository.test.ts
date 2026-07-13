import assert from "node:assert/strict";
import { test } from "node:test";

import {
  FEATURE_RULE_MASTERS_ERROR_CODES,
  FeatureRuleRepository,
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

/** SQL 内容に応じて Rule 行を返す session（Version / 3 Rule テーブル）。 */
class FeatureRuleQuerySession implements DbSession {
  readonly backend = "feature-rule-query";
  readonly operations: { sql: string; params?: DbQueryParams }[] = [];

  constructor(
    private readonly handlers: {
      versionRows: DbRow[];
      relationshipRows: DbRow[];
      occasionRows: DbRow[];
      conceptFeatureRows: DbRow[];
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
    } else if (sql.includes("FROM relationship_rule")) {
      rows = this.handlers.relationshipRows;
    } else if (sql.includes("FROM occasion_rule")) {
      rows = this.handlers.occasionRows;
    } else if (sql.includes("FROM concept_feature_rule")) {
      rows = this.handlers.conceptFeatureRows;
    }
    return { rows: rows as TRow[], rowCount: rows.length };
  }

  async execute(): Promise<number> {
    return 0;
  }
}

test("FeatureRuleRepository assembles 2 groups and omits internal version id", async () => {
  const session = new FeatureRuleQuerySession({
    versionRows: [
      {
        semantic_config_version_id: "ver-1",
        config_name: "mvp-semantic-config",
        version_label: "v1.0.0",
      },
    ],
    relationshipRows: [
      {
        relationship_code: "friend",
        feature_code: "formality",
        feature_base_value: "0.400",
      },
    ],
    occasionRows: [
      {
        occasion_code: "thanks",
        feature_code: "emotion",
        feature_base_value: "0.700",
      },
    ],
    conceptFeatureRows: [
      {
        concept_code: "formal_refined",
        feature_code: "formality",
        feature_delta: "0.150",
        polarity: "positive",
      },
    ],
  });

  const repository = new FeatureRuleRepository({ session });
  const snapshot = await repository.getCurrentRules();

  assert.equal(snapshot.configName, "mvp-semantic-config");
  assert.equal(snapshot.versionLabel, "v1.0.0");
  assert.equal(snapshot.baseValueRules.length, 2);
  assert.equal(snapshot.baseValueRules[0]?.ruleType, "relationship");
  assert.equal(snapshot.baseValueRules[1]?.ruleType, "occasion");
  assert.equal(snapshot.conceptFeatureRules.length, 1);
  assert.equal("semanticConfigVersionId" in snapshot, false);
  assert.ok(session.operations[0]?.sql.includes("is_current = true"));
});

test("FeatureRuleRepository throws GRS-CFG-001 when current version missing", async () => {
  const repository = new FeatureRuleRepository({
    session: new FeatureRuleQuerySession({
      versionRows: [],
      relationshipRows: [],
      occasionRows: [],
      conceptFeatureRows: [],
    }),
  });

  await assert.rejects(
    () => repository.getCurrentRules(),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(
        error.code,
        FEATURE_RULE_MASTERS_ERROR_CODES.CURRENT_NOT_FOUND,
      );
      return true;
    },
  );
});

test("FeatureRuleRepository throws GRS-CFG-002 when multiple current versions", async () => {
  const repository = new FeatureRuleRepository({
    session: new FeatureRuleQuerySession({
      versionRows: [
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
      relationshipRows: [],
      occasionRows: [],
      conceptFeatureRows: [],
    }),
  });

  await assert.rejects(
    () => repository.getCurrentRules(),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(
        error.code,
        FEATURE_RULE_MASTERS_ERROR_CODES.RESOLVE_FAILED,
      );
      return true;
    },
  );
});

test("FeatureRuleRepository filters active rows for relationship and occasion rules", async () => {
  const session = new FeatureRuleQuerySession({
    versionRows: [
      {
        semantic_config_version_id: "ver-1",
        config_name: "mvp-semantic-config",
        version_label: "v1.0.0",
      },
    ],
    relationshipRows: [],
    occasionRows: [],
    conceptFeatureRows: [],
  });

  const repository = new FeatureRuleRepository({ session });
  await repository.getCurrentRules();

  const relationshipSql = session.operations.find((op) =>
    op.sql.includes("FROM relationship_rule"),
  )?.sql;
  const occasionSql = session.operations.find((op) =>
    op.sql.includes("FROM occasion_rule"),
  )?.sql;
  assert.ok(relationshipSql);
  assert.ok(occasionSql);
  assert.match(relationshipSql, /is_active\s*=\s*true/);
  assert.match(occasionSql, /is_active\s*=\s*true/);
});

test("FeatureRuleRepository excludes inactive semantic_concept rows from conceptFeatureRules", async () => {
  const session = new FeatureRuleQuerySession({
    versionRows: [
      {
        semantic_config_version_id: "ver-1",
        config_name: "mvp-semantic-config",
        version_label: "v1.0.0",
      },
    ],
    relationshipRows: [],
    occasionRows: [],
    conceptFeatureRows: [
      {
        concept_code: "active_concept",
        feature_code: "formality",
        feature_delta: "0.100",
        polarity: "positive",
      },
    ],
  });

  const repository = new FeatureRuleRepository({ session });
  const snapshot = await repository.getCurrentRules();

  assert.equal(snapshot.conceptFeatureRules.length, 1);
  assert.equal(snapshot.conceptFeatureRules[0]?.conceptCode, "active_concept");

  const conceptSql = session.operations.find((op) =>
    op.sql.includes("FROM concept_feature_rule"),
  )?.sql;
  assert.ok(conceptSql);
  assert.match(conceptSql, /sc\.is_active\s*=\s*true/);
  assert.match(
    conceptSql,
    /sc\.semantic_config_version_id\s*=\s*cfr\.semantic_config_version_id/,
  );
});

test("FeatureRuleRepository maps DbError on rule read to GRS-DB-002", async () => {
  class FailOnRuleReadSession implements DbSession {
    readonly backend = "fail-on-rule-read";

    healthCheck(): DbHealth {
      return { isAvailable: true, backend: this.backend };
    }

    async query<TRow extends DbRow = DbRow>(
      sql: string,
      _params?: DbQueryParams,
    ): Promise<DbQueryResult<TRow>> {
      if (sql.includes("FROM semantic_config_version")) {
        return {
          rows: [
            {
              semantic_config_version_id: "ver-1",
              config_name: "mvp-semantic-config",
              version_label: "v1.0.0",
            },
          ] as unknown as TRow[],
          rowCount: 1,
        };
      }
      throw new DbError({
        code: "DB_QUERY_FAILED",
        message: "simulated rule read failure",
        retryable: true,
      });
    }

    async execute(): Promise<number> {
      return 0;
    }
  }

  const repository = new FeatureRuleRepository({
    session: new FailOnRuleReadSession(),
  });

  await assert.rejects(
    () => repository.getCurrentRules(),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(
        error.code,
        FEATURE_RULE_MASTERS_ERROR_CODES.DB_READ_FAILED,
      );
      return true;
    },
  );
});

test("FeatureRuleRepository maps unavailable DB health to GRS-DB-002", async () => {
  const repository = new FeatureRuleRepository({
    session: new ScaffoldDbSession({ isAvailable: false }),
  });

  await assert.rejects(
    () => repository.getCurrentRules(),
    (error: unknown) => {
      assert.ok(error instanceof ApiError);
      assert.equal(
        error.code,
        FEATURE_RULE_MASTERS_ERROR_CODES.DB_READ_FAILED,
      );
      return true;
    },
  );
});
