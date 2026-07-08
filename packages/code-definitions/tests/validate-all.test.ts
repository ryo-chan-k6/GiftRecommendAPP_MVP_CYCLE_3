import { test } from "node:test";
import assert from "node:assert/strict";
import {
  ERROR_CODE_PATTERN,
  getPackageRoot,
  loadAllDefinitions,
  validatePackageDefinitions,
} from "../src/index.js";

test("ERROR_CODE_PATTERN accepts GRS domain codes", () => {
  assert.match("GRS-COM-001", ERROR_CODE_PATTERN);
  assert.match("GRS-REC-101", ERROR_CODE_PATTERN);
  assert.doesNotMatch("GRS-com-001", ERROR_CODE_PATTERN);
});

test("loadAllDefinitions loads enum and error catalogs", async () => {
  const packageRoot = getPackageRoot(
    new URL("../src/index.js", import.meta.url).href,
  );
  const loaded = await loadAllDefinitions(packageRoot);

  assert.ok(loaded.codeDefinitions.length >= 20);
  assert.ok(loaded.errorCatalogs.length >= 17);
  assert.equal(loaded.errorCodeFormat.document.definition_type, "error_code_format");
});

test("feature_code has MVP 8 axes", async () => {
  const packageRoot = getPackageRoot(
    new URL("../src/index.js", import.meta.url).href,
  );
  const loaded = await loadAllDefinitions(packageRoot);
  const featureCode = loaded.codeDefinitions.find(
    (entry) => entry.document.code_definition.id === "feature_code",
  );

  assert.ok(featureCode);
  assert.equal(featureCode.document.values.length, 8);
});

test("validatePackageDefinitions passes for repository definitions", async () => {
  const packageRoot = getPackageRoot(
    new URL("../src/index.js", import.meta.url).href,
  );
  const result = await validatePackageDefinitions(packageRoot);

  if (!result.ok) {
    assert.fail(
      `validation issues:\n${result.issues.map((issue) => `- ${issue.path}: ${issue.message}`).join("\n")}`,
    );
  }

  assert.equal(result.ok, true);
});
