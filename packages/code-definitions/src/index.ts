import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  loadCodeDefinitions,
  loadErrorCatalogs,
  loadErrorCodeFormat,
} from "./load.js";
import type { LoadedDefinitions } from "./validate.js";
import { validateLoadedDefinitions } from "./validate.js";

export function getPackageRoot(importMetaUrl: string = import.meta.url): string {
  return join(dirname(fileURLToPath(importMetaUrl)), "..", "..");
}

export async function loadAllDefinitions(
  packageRoot: string = getPackageRoot(),
): Promise<LoadedDefinitions> {
  const [codeDefinitions, errorCatalogs, errorCodeFormat] = await Promise.all([
    loadCodeDefinitions(packageRoot),
    loadErrorCatalogs(packageRoot),
    loadErrorCodeFormat(packageRoot),
  ]);

  return {
    codeDefinitions,
    errorCatalogs,
    errorCodeFormat,
  };
}

export async function validatePackageDefinitions(
  packageRoot: string = getPackageRoot(),
): Promise<{ ok: boolean; issues: ReturnType<typeof validateLoadedDefinitions> }> {
  const loaded = await loadAllDefinitions(packageRoot);
  const issues = validateLoadedDefinitions(loaded);
  return { ok: issues.length === 0, issues };
}

export * from "./constants.js";
export * from "./load.js";
export * from "./types.js";
export * from "./validate.js";
