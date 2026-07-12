/** code_definitions.yaml の論理 ID（snake_case） */
export type CodeDefinitionId = string;

/** code_definition.values[].value の物理値 */
export type CodeDefinitionValue = string;

/**
 * code_definition.id をキー、enabled な value 集合を値とするカタログ。
 * enum定義書 §4 の「shared-types / seed 生成のキー」に対応する。
 */
export type CodeValueCatalog = Readonly<
  Record<CodeDefinitionId, readonly CodeDefinitionValue[]>
>;

export type CodeValueOf<
  Catalog extends CodeValueCatalog,
  Id extends keyof Catalog & string,
> = Catalog[Id][number];

/** GRS-{DOMAIN}-{NUMBER} 形式の error_code */
export type ErrorCode = string;
