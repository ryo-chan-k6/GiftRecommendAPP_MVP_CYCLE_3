import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { parse } from "yaml";
import {
  CODE_DEFINITION_DIRS,
  ERROR_CATALOG_FILES,
  SCHEMA_VERSION,
} from "./constants.js";
import type {
  CodeDefinitionDocument,
  ErrorCatalogDocument,
  ErrorCodeFormatDocument,
} from "./types.js";

export async function readYamlFile<T>(filePath: string): Promise<T> {
  const content = await readFile(filePath, "utf8");
  return parse(content) as T;
}

export async function loadCodeDefinitions(
  packageRoot: string,
): Promise<Array<{ filePath: string; document: CodeDefinitionDocument }>> {
  const results: Array<{ filePath: string; document: CodeDefinitionDocument }> =
    [];

  for (const dir of CODE_DEFINITION_DIRS) {
    const dirPath = join(packageRoot, dir);
    const entries = await readdir(dirPath);
    const yamlFiles = entries.filter((name) => name.endsWith(".yaml")).sort();

    for (const fileName of yamlFiles) {
      const filePath = join(dirPath, fileName);
      const document = await readYamlFile<CodeDefinitionDocument>(filePath);
      results.push({ filePath, document });
    }
  }

  return results;
}

export async function loadErrorCatalogs(
  packageRoot: string,
): Promise<Array<{ filePath: string; document: ErrorCatalogDocument }>> {
  const errorDir = join(packageRoot, "error");
  const results: Array<{ filePath: string; document: ErrorCatalogDocument }> =
    [];

  for (const fileName of ERROR_CATALOG_FILES) {
    const filePath = join(errorDir, fileName);
    const document = await readYamlFile<ErrorCatalogDocument>(filePath);
    results.push({ filePath, document });
  }

  return results;
}

export async function loadErrorCodeFormat(
  packageRoot: string,
): Promise<{ filePath: string; document: ErrorCodeFormatDocument }> {
  const filePath = join(packageRoot, "error", "error_code_format.yaml");
  const document = await readYamlFile<ErrorCodeFormatDocument>(filePath);
  return { filePath, document };
}

export function assertSchemaVersion(
  document: { schema_version?: string },
  filePath: string,
): void {
  if (document.schema_version !== SCHEMA_VERSION) {
    throw new Error(
      `${filePath}: schema_version must be "${SCHEMA_VERSION}" (got "${document.schema_version ?? ""}")`,
    );
  }
}
