import { readFile } from "node:fs/promises";
import { FIXTURE_MANIFEST_FILE, getPackageRoot, resolveFixturePath } from "./paths.js";
import type { FixtureManifest } from "./types.js";

export const FIXTURE_SCHEMA_VERSION = "1.0";

export async function loadFixtureManifest(
  packageRoot: string = getPackageRoot(),
): Promise<FixtureManifest> {
  const manifestPath = resolveFixturePath(packageRoot, FIXTURE_MANIFEST_FILE);
  const content = await readFile(manifestPath, "utf8");
  const manifest = JSON.parse(content) as FixtureManifest;

  if (manifest.schemaVersion !== FIXTURE_SCHEMA_VERSION) {
    throw new Error(
      `${manifestPath}: schemaVersion must be "${FIXTURE_SCHEMA_VERSION}" (got "${manifest.schemaVersion ?? ""}")`,
    );
  }

  return manifest;
}
