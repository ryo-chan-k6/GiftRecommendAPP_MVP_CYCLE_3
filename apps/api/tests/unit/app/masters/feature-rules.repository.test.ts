import assert from "node:assert/strict";
import { test } from "node:test";

import { FeatureRuleRepository } from "../../../../src/app/masters/index.js";
import {
  type DbHealth,
  type DbQueryParams,
  type DbQueryResult,
  type DbRow,
  type DbSession,
} from "../../../../src/infrastructure/db/index.js";

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
