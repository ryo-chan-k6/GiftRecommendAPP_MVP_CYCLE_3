"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { createProjectV2Client, sleep, DEFAULT_FIND_RETRY_ATTEMPTS } = require("./project-v2-utils.cjs");

test("createProjectV2Client: loadProject prefers user then organization", async () => {
  const calls = [];
  const github = {
    graphql: async (_query, vars) => {
      calls.push(vars);
      return {
        user: null,
        organization: {
          projectV2: {
            id: "PVT_org",
            fields: { nodes: [{ name: "Status", id: "f1", options: [{ id: "o1", name: "Todo" }] }] },
          },
        },
      };
    },
  };
  const client = createProjectV2Client({
    github,
    projectOwner: "example-org",
    projectNumber: 4,
  });
  const project = await client.loadProject();
  assert.equal(project.id, "PVT_org");
  assert.equal(calls[0].owner, "example-org");
});

test("findProjectItem: retries until item appears", async () => {
  let attempts = 0;
  const github = {
    graphql: async (query) => {
      if (query.includes("addProjectV2ItemById")) {
        return { addProjectV2ItemById: { item: { id: "item_new" } } };
      }
      if (query.includes("items(first:")) {
        attempts += 1;
        if (attempts < 2) {
          return { node: { items: { nodes: [], pageInfo: { hasNextPage: false } } } };
        }
        return {
          node: {
            items: {
              nodes: [{ id: "item_new", content: { id: "ISSUE_1" } }],
              pageInfo: { hasNextPage: false },
            },
          },
        };
      }
      return {};
    },
  };
  const client = createProjectV2Client({
    github,
    projectOwner: "owner",
    projectNumber: 4,
    findRetryAttempts: 3,
    findRetryDelayMs: 1,
  });
  const project = { id: "PVT_test" };
  const itemId = await client.findProjectItem(project, "ISSUE_1");
  assert.equal(itemId, "item_new");
  assert.equal(attempts, 2);
});

test("getFieldDateValue: uses ProjectV2Item node query", async () => {
  let capturedQuery = "";
  const github = {
    graphql: async (query, vars) => {
      capturedQuery = query;
      assert.equal(vars.itemId, "ITEM_1");
      assert.equal(vars.fieldName, "Actual Start");
      return {
        node: {
          fieldValueByName: { date: "2026-06-01" },
        },
      };
    },
  };
  const client = createProjectV2Client({ github, projectOwner: "u", projectNumber: 1 });
  const value = await client.getFieldDateValue("ITEM_1", "Actual Start");
  assert.equal(value, "2026-06-01");
  assert.match(capturedQuery, /ProjectV2Item/);
  assert.doesNotMatch(capturedQuery, /ProjectV2\s*\{[^}]*item\(id:/);
});

test("constants: default retry attempts", () => {
  assert.equal(DEFAULT_FIND_RETRY_ATTEMPTS, 5);
});

test("sleep resolves", async () => {
  const start = Date.now();
  await sleep(10);
  assert.ok(Date.now() - start >= 5);
});
