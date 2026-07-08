import { readFile } from "node:fs/promises";
import { getPackageRoot, resolveFixturePath } from "./paths.js";
import { loadFixtureManifest } from "./manifest.js";
import type {
  FeatureFixtureDocument,
  FixtureManifest,
  RecommendationRequestFixtureDocument,
} from "./types.js";

export async function readJsonFixture<T>(
  packageRoot: string,
  relativePath: string,
): Promise<T> {
  const filePath = resolveFixturePath(packageRoot, relativePath);
  const content = await readFile(filePath, "utf8");
  return JSON.parse(content) as T;
}

export async function loadFixtureItem<T>(
  itemKey: keyof FixtureManifest["items"],
  packageRoot: string = getPackageRoot(),
): Promise<T> {
  const manifest = await loadFixtureManifest(packageRoot);
  const item = manifest.items[itemKey];

  if (!item) {
    throw new Error(`Unknown fixture item: ${String(itemKey)}`);
  }

  return readJsonFixture<T>(packageRoot, item.path);
}

export async function loadMvpUserFeaturesBaseline(
  packageRoot: string = getPackageRoot(),
): Promise<FeatureFixtureDocument> {
  return loadFixtureItem<FeatureFixtureDocument>(
    "mvp_user_features_baseline",
    packageRoot,
  );
}

export async function loadRecommendationRequestBossThanksMinimal(
  packageRoot: string = getPackageRoot(),
): Promise<RecommendationRequestFixtureDocument> {
  return loadFixtureItem<RecommendationRequestFixtureDocument>(
    "recommendation_request_boss_thanks_minimal",
    packageRoot,
  );
}
