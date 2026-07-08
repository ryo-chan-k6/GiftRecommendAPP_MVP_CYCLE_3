export const CODE_DEFINITION_CATEGORIES = [
  "state",
  "application",
  "semantic",
  "batch",
] as const;

export type CodeDefinitionCategory =
  (typeof CODE_DEFINITION_CATEGORIES)[number];

export type CodeDefinitionValue = {
  value: string;
  label: string;
  meaning: string;
  terminal: boolean;
  enabled: boolean;
};

export type CodeDefinitionDocument = {
  schema_version: string;
  definition_type: "code_definition";
  code_definition: {
    id: string;
    physical_name: string;
    logical_name: string;
    category: CodeDefinitionCategory;
    mvp_scope: boolean;
  };
  values: CodeDefinitionValue[];
  db_usages?: Array<Record<string, unknown>>;
};

export type ErrorCodeEntry = {
  code: string;
  internal_name: string;
  http_status: number;
  retryable: boolean;
  severity: "warn" | "error" | "critical";
  user_message_key: string;
  owner_types: string[];
  mvp_scope: boolean;
};

export type ErrorCatalogDocument = {
  schema_version: string;
  definition_type: "error_catalog";
  error_catalog: {
    domain: string;
    domain_label: string;
    mvp_scope: boolean;
    codes: ErrorCodeEntry[];
  };
};

export type ErrorCodeFormatDocument = {
  schema_version: string;
  definition_type: "error_code_format";
  error_code_format: {
    pattern: string;
    example: string;
    description: string;
  };
};

export type ValidationIssue = {
  path: string;
  message: string;
};
