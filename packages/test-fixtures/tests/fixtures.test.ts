import { test } from "node:test";
import assert from "node:assert/strict";
import {
  FIXTURE_SCHEMA_VERSION,
  getPackageRoot,
  loadFixtureManifest,
  loadMvpUserFeaturesBaseline,
  loadRecommendationRequestBossThanksMinimal,
} from "../src/index.js";

test("loadFixtureManifest loads package manifest", async () => {
  const packageRoot = getPackageRoot(
    new URL("../src/index.js", import.meta.url).href,
  );
  const manifest = await loadFixtureManifest(packageRoot);

  assert.equal(manifest.schemaVersion, FIXTURE_SCHEMA_VERSION);
  assert.equal(manifest.packageId, "packages-test-fixtures");
  assert.ok(manifest.items.mvp_user_features_baseline);
  assert.ok(manifest.items.recommendation_request_boss_thanks_minimal);
});

test("loadMvpUserFeaturesBaseline returns MVP 8-axis vector", async () => {
  const packageRoot = getPackageRoot(
    new URL("../src/index.js", import.meta.url).href,
  );
  const fixture = await loadMvpUserFeaturesBaseline(packageRoot);

  assert.equal(fixture.featureCodes.length, 8);
  assert.equal(fixture.featureCodes.includes("formality"), true);
  assert.equal(fixture.values.formality, 0.75);
  assert.equal(fixture.values.story_richness, 0.45);
});

test("loadRecommendationRequestBossThanksMinimal returns minimal request", async () => {
  const packageRoot = getPackageRoot(
    new URL("../src/index.js", import.meta.url).href,
  );
  const fixture = await loadRecommendationRequestBossThanksMinimal(packageRoot);

  assert.equal(fixture.relationship.relationshipCode, "boss");
  assert.equal(fixture.occasion.occasionCode, "thanks");
  assert.equal(fixture.budget?.budgetMax, 5000);
  assert.equal(fixture.execution?.topK, 10);
});
