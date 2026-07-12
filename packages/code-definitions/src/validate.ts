import { ERROR_CODE_PATTERN } from "./constants.js";
import { CODE_DEFINITION_CATEGORIES } from "./types.js";
import type {
  CodeDefinitionDocument,
  ErrorCatalogDocument,
  ErrorCodeFormatDocument,
  ValidationIssue,
} from "./types.js";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function pushIssue(
  issues: ValidationIssue[],
  path: string,
  message: string,
): void {
  issues.push({ path, message });
}

export function validateCodeDefinitionDocument(
  filePath: string,
  document: unknown,
): ValidationIssue[] {
  const issues: ValidationIssue[] = [];

  if (!isRecord(document)) {
    pushIssue(issues, filePath, "document must be an object");
    return issues;
  }

  if (document.definition_type !== "code_definition") {
    pushIssue(
      issues,
      `${filePath}.definition_type`,
      'must be "code_definition"',
    );
  }

  const codeDefinition = document.code_definition;
  if (!isRecord(codeDefinition)) {
    pushIssue(issues, `${filePath}.code_definition`, "is required");
    return issues;
  }

  for (const key of ["id", "physical_name", "logical_name", "category"]) {
    if (typeof codeDefinition[key] !== "string" || codeDefinition[key] === "") {
      pushIssue(
        issues,
        `${filePath}.code_definition.${key}`,
        "must be a non-empty string",
      );
    }
  }

  if (
    typeof codeDefinition.category === "string" &&
    !CODE_DEFINITION_CATEGORIES.includes(
      codeDefinition.category as (typeof CODE_DEFINITION_CATEGORIES)[number],
    )
  ) {
    pushIssue(
      issues,
      `${filePath}.code_definition.category`,
      `must be one of ${CODE_DEFINITION_CATEGORIES.join(", ")}`,
    );
  }

  if (typeof codeDefinition.mvp_scope !== "boolean") {
    pushIssue(
      issues,
      `${filePath}.code_definition.mvp_scope`,
      "must be boolean",
    );
  }

  if (!Array.isArray(document.values) || document.values.length === 0) {
    pushIssue(issues, `${filePath}.values`, "must be a non-empty array");
    return issues;
  }

  const seenValues = new Set<string>();
  document.values.forEach((entry, index) => {
    const basePath = `${filePath}.values[${index}]`;
    if (!isRecord(entry)) {
      pushIssue(issues, basePath, "must be an object");
      return;
    }

    for (const key of ["value", "label", "meaning"]) {
      if (typeof entry[key] !== "string" || entry[key] === "") {
        pushIssue(issues, `${basePath}.${key}`, "must be a non-empty string");
      }
    }

    for (const key of ["terminal", "enabled"]) {
      if (typeof entry[key] !== "boolean") {
        pushIssue(issues, `${basePath}.${key}`, "must be boolean");
      }
    }

    if (typeof entry.value === "string") {
      if (seenValues.has(entry.value)) {
        pushIssue(
          issues,
          `${basePath}.value`,
          `duplicate value "${entry.value}"`,
        );
      }
      seenValues.add(entry.value);
    }
  });

  return issues;
}

export function validateErrorCatalogDocument(
  filePath: string,
  document: unknown,
): ValidationIssue[] {
  const issues: ValidationIssue[] = [];

  if (!isRecord(document)) {
    pushIssue(issues, filePath, "document must be an object");
    return issues;
  }

  if (document.definition_type !== "error_catalog") {
    pushIssue(
      issues,
      `${filePath}.definition_type`,
      'must be "error_catalog"',
    );
  }

  const catalog = document.error_catalog;
  if (!isRecord(catalog)) {
    pushIssue(issues, `${filePath}.error_catalog`, "is required");
    return issues;
  }

  for (const key of ["domain", "domain_label"]) {
    if (typeof catalog[key] !== "string" || catalog[key] === "") {
      pushIssue(
        issues,
        `${filePath}.error_catalog.${key}`,
        "must be a non-empty string",
      );
    }
  }

  if (typeof catalog.mvp_scope !== "boolean") {
    pushIssue(
      issues,
      `${filePath}.error_catalog.mvp_scope`,
      "must be boolean",
    );
  }

  if (!Array.isArray(catalog.codes) || catalog.codes.length === 0) {
    pushIssue(issues, `${filePath}.error_catalog.codes`, "must be a non-empty array");
    return issues;
  }

  const domain = typeof catalog.domain === "string" ? catalog.domain : "";
  catalog.codes.forEach((entry, index) => {
    const basePath = `${filePath}.error_catalog.codes[${index}]`;
    if (!isRecord(entry)) {
      pushIssue(issues, basePath, "must be an object");
      return;
    }

    for (const key of ["code", "internal_name", "user_message_key"]) {
      if (typeof entry[key] !== "string" || entry[key] === "") {
        pushIssue(issues, `${basePath}.${key}`, "must be a non-empty string");
      }
    }

    if (typeof entry.http_status !== "number") {
      pushIssue(issues, `${basePath}.http_status`, "must be a number");
    }

    if (typeof entry.retryable !== "boolean") {
      pushIssue(issues, `${basePath}.retryable`, "must be boolean");
    }

    if (
      entry.severity !== "warn" &&
      entry.severity !== "error" &&
      entry.severity !== "critical"
    ) {
      pushIssue(
        issues,
        `${basePath}.severity`,
        'must be "warn", "error", or "critical"',
      );
    }

    if (!Array.isArray(entry.owner_types) || entry.owner_types.length === 0) {
      pushIssue(
        issues,
        `${basePath}.owner_types`,
        "must be a non-empty array",
      );
    }

    if (typeof entry.mvp_scope !== "boolean") {
      pushIssue(issues, `${basePath}.mvp_scope`, "must be boolean");
    }

    if (typeof entry.code === "string") {
      if (!ERROR_CODE_PATTERN.test(entry.code)) {
        pushIssue(
          issues,
          `${basePath}.code`,
          `must match ${ERROR_CODE_PATTERN}`,
        );
      }

      const codeDomain = entry.code.split("-")[1];
      if (domain && codeDomain !== domain) {
        pushIssue(
          issues,
          `${basePath}.code`,
          `domain segment must match catalog domain "${domain}"`,
        );
      }
    }
  });

  return issues;
}

export function validateErrorCodeFormatDocument(
  filePath: string,
  document: unknown,
): ValidationIssue[] {
  const issues: ValidationIssue[] = [];

  if (!isRecord(document)) {
    pushIssue(issues, filePath, "document must be an object");
    return issues;
  }

  if (document.definition_type !== "error_code_format") {
    pushIssue(
      issues,
      `${filePath}.definition_type`,
      'must be "error_code_format"',
    );
  }

  const format = document.error_code_format;
  if (!isRecord(format)) {
    pushIssue(issues, `${filePath}.error_code_format`, "is required");
    return issues;
  }

  for (const key of ["pattern", "example", "description"]) {
    if (typeof format[key] !== "string" || format[key] === "") {
      pushIssue(
        issues,
        `${filePath}.error_code_format.${key}`,
        "must be a non-empty string",
      );
    }
  }

  if (
    typeof format.example === "string" &&
    !ERROR_CODE_PATTERN.test(format.example)
  ) {
    pushIssue(
      issues,
      `${filePath}.error_code_format.example`,
      `must match ${ERROR_CODE_PATTERN}`,
    );
  }

  return issues;
}

export function collectDuplicateErrorCodes(
  catalogs: Array<{ filePath: string; document: ErrorCatalogDocument }>,
): ValidationIssue[] {
  const seen = new Map<string, string>();
  const issues: ValidationIssue[] = [];

  for (const { filePath, document } of catalogs) {
    for (const entry of document.error_catalog.codes) {
      const previous = seen.get(entry.code);
      if (previous) {
        issues.push({
          path: `${filePath}.error_catalog.codes`,
          message: `duplicate error code "${entry.code}" (also in ${previous})`,
        });
      } else {
        seen.set(entry.code, filePath);
      }
    }
  }

  return issues;
}

export type LoadedDefinitions = {
  codeDefinitions: Array<{ filePath: string; document: CodeDefinitionDocument }>;
  errorCatalogs: Array<{ filePath: string; document: ErrorCatalogDocument }>;
  errorCodeFormat: { filePath: string; document: ErrorCodeFormatDocument };
};

export function validateLoadedDefinitions(
  loaded: LoadedDefinitions,
): ValidationIssue[] {
  const issues: ValidationIssue[] = [];

  for (const { filePath, document } of loaded.codeDefinitions) {
    issues.push(...validateCodeDefinitionDocument(filePath, document));
  }

  issues.push(
    ...validateErrorCodeFormatDocument(
      loaded.errorCodeFormat.filePath,
      loaded.errorCodeFormat.document,
    ),
  );

  for (const { filePath, document } of loaded.errorCatalogs) {
    issues.push(...validateErrorCatalogDocument(filePath, document));
  }

  issues.push(...collectDuplicateErrorCodes(loaded.errorCatalogs));

  return issues;
}
