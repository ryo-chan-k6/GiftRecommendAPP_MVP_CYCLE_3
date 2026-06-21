import { ERROR_CODE_PATTERN } from "./deps/code-definitions.js";
import type { CodeDefinitionId, CodeDefinitionValue, CodeValueCatalog } from "./types.js";

export function isCodeDefinitionValue(
  catalog: CodeValueCatalog,
  id: CodeDefinitionId,
  value: string,
): value is CodeDefinitionValue {
  const values = catalog[id];
  return values !== undefined && values.includes(value);
}

export function assertCodeDefinitionValue(
  catalog: CodeValueCatalog,
  id: CodeDefinitionId,
  value: string,
): asserts value is CodeDefinitionValue {
  if (!isCodeDefinitionValue(catalog, id, value)) {
    throw new Error(`Invalid code value for ${id}: ${value}`);
  }
}

export function isErrorCode(value: string): boolean {
  return ERROR_CODE_PATTERN.test(value);
}

export function isKnownErrorCode(
  errorCodes: ReadonlySet<string>,
  value: string,
): value is string {
  return errorCodes.has(value);
}
