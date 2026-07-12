import { test } from "node:test";
import assert from "node:assert/strict";
import {
  buildCodeValueCatalog,
  buildErrorCodeSet,
  isCodeDefinitionValue,
  isErrorCode,
  isKnownErrorCode,
  loadMvpSharedTypeCatalog,
} from "../index.js";

test("loadMvpSharedTypeCatalog builds catalogs from code-definitions", async () => {
  const { codeValues, errorCodes } = await loadMvpSharedTypeCatalog();

  assert.ok(Object.keys(codeValues).length >= 20);
  assert.ok(errorCodes.size >= 50);
  assert.deepEqual(codeValues.feature_code, [
    "formality",
    "safety",
    "brand_appropriateness",
    "emotion",
    "novelty",
    "intimacy",
    "symbolic_identity",
    "story_richness",
  ]);
});

test("isCodeDefinitionValue validates against catalog", async () => {
  const { codeValues } = await loadMvpSharedTypeCatalog();

  assert.equal(
    isCodeDefinitionValue(codeValues, "recommendation_run_status", "running"),
    true,
  );
  assert.equal(
    isCodeDefinitionValue(codeValues, "recommendation_run_status", "invalid"),
    false,
  );
});

test("isErrorCode and isKnownErrorCode validate error codes", async () => {
  const { errorCodes } = await loadMvpSharedTypeCatalog();

  assert.equal(isErrorCode("GRS-COM-001"), true);
  assert.equal(isErrorCode("invalid"), false);
  assert.equal(isKnownErrorCode(errorCodes, "GRS-COM-001"), true);
  assert.equal(isKnownErrorCode(errorCodes, "GRS-XXX-999"), false);
});

test("buildCodeValueCatalog excludes disabled values", () => {
  const catalog = buildCodeValueCatalog([
    {
      filePath: "example.yaml",
      document: {
        schema_version: "1.0",
        definition_type: "code_definition",
        code_definition: {
          id: "example_status",
          physical_name: "status",
          logical_name: "Example",
          category: "state",
          mvp_scope: true,
        },
        values: [
          {
            value: "active",
            label: "Active",
            meaning: "enabled",
            terminal: false,
            enabled: true,
          },
          {
            value: "retired",
            label: "Retired",
            meaning: "disabled",
            terminal: true,
            enabled: false,
          },
        ],
      },
    },
  ]);

  assert.deepEqual(catalog.example_status, ["active"]);
  assert.equal(buildErrorCodeSet([]).size, 0);
});
