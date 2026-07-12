/** API-PUB-005 内部 DTO / Public Response 形（実装面）。 */

export type RelationshipMasterRow = {
  relationshipCode: string;
  relationshipLabel: string;
  displayOrder: number;
};

export type RelationshipPublicItem = {
  relationshipCode: string;
  relationshipLabel: string;
  displayOrder?: number;
};

export type RelationshipsSuccessData = {
  relationships: RelationshipPublicItem[];
};

export type RelationshipsSuccessMeta = {
  traceId: string;
  requestId: string;
  generatedAt: string;
  count: number;
};

export type RelationshipsSuccessResponse = {
  data: RelationshipsSuccessData;
  meta: RelationshipsSuccessMeta;
};

/** MOD-API-012 の読取 I/F（Router 注入・UT 用）。 */
export type RelationshipMasterReader = {
  listActive(): Promise<RelationshipMasterRow[]>;
};
