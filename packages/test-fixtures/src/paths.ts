import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const FIXTURE_MANIFEST_FILE = "fixtures/manifest.json";

export function getPackageRoot(importMetaUrl: string = import.meta.url): string {
  return join(dirname(fileURLToPath(importMetaUrl)), "..", "..");
}

export function resolveFixturePath(
  packageRoot: string,
  relativePath: string,
): string {
  return join(packageRoot, relativePath);
}
