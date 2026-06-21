import {
  getPackageRoot,
  loadAllDefinitions,
  type LoadedDefinitions,
} from "./deps/code-definitions.js";
import type { CodeValueCatalog } from "./types.js";

type CodeDefinitionEntry = LoadedDefinitions["codeDefinitions"][number];

export function buildCodeValueCatalog(
  codeDefinitions: CodeDefinitionEntry[],
): CodeValueCatalog {
  const catalog: Record<string, string[]> = {};

  for (const entry of codeDefinitions) {
    const id = entry.document.code_definition.id;
    catalog[id] = entry.document.values
      .filter((value) => value.enabled)
      .map((value) => value.value);
  }

  return Object.freeze(
    Object.fromEntries(
      Object.entries(catalog).map(([id, values]) => [id, Object.freeze([...values])]),
    ),
  );
}

export function buildErrorCodeSet(
  errorCatalogs: LoadedDefinitions["errorCatalogs"],
): ReadonlySet<string> {
  const codes = new Set<string>();

  for (const entry of errorCatalogs) {
    for (const code of entry.document.error_catalog.codes) {
      if (code.mvp_scope) {
        codes.add(code.code);
      }
    }
  }

  return codes;
}

export async function loadMvpSharedTypeCatalog(
  codeDefinitionsPackageRoot: string = getPackageRoot(),
): Promise<{
  codeValues: CodeValueCatalog;
  errorCodes: ReadonlySet<string>;
}> {
  const loaded = await loadAllDefinitions(codeDefinitionsPackageRoot);

  return {
    codeValues: buildCodeValueCatalog(loaded.codeDefinitions),
    errorCodes: buildErrorCodeSet(loaded.errorCatalogs),
  };
}
