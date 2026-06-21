export const SCHEMA_VERSION = "1.0";

export const ERROR_CODE_PATTERN = /^GRS-[A-Z]{2,4}-\d{3}$/;

export const CODE_DEFINITION_DIRS = [
  "semantic",
  "application",
  "state",
  "batch",
] as const;

export const ERROR_CATALOG_FILES = [
  "com.yaml",
  "val.yaml",
  "auth.yaml",
  "rate.yaml",
  "req.yaml",
  "rec.yaml",
  "res.yaml",
  "fdb.yaml",
  "itm.yaml",
  "ext.yaml",
  "raw.yaml",
  "bat.yaml",
  "db.yaml",
  "cfg.yaml",
  "llm.yaml",
  "eval.yaml",
  "obs.yaml",
] as const;
