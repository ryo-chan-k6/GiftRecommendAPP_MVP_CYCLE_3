import { Router, type NextFunction, type Request, type Response } from "express";

import { createDbSession } from "../../infrastructure/db/factory.js";
import type { ApiLogger } from "../../infrastructure/logger/logger.js";
import { ApiError } from "../../middlewares/error/api-error.js";
import { resolveRequestMeta } from "../../middlewares/request-meta.js";
import {
  MASTERS_RELATIONSHIPS_ERROR_CODES,
  MASTERS_RELATIONSHIPS_ERROR_MESSAGES,
  MASTERS_RELATIONSHIPS_METRICS,
  MASTERS_RELATIONSHIPS_PATH,
} from "./constants.js";
import {
  isDatabaseUrlConfigured,
  RelationshipMasterRepository,
  UnresolvedRelationshipMasterReader,
} from "./relationship-repository.js";
import type {
  RelationshipMasterReader,
  RelationshipPublicItem,
  RelationshipsSuccessResponse,
} from "./types.js";

export type MastersRouterDeps = {
  logger?: ApiLogger;
  relationshipReader?: RelationshipMasterReader;
  generatedAtFactory?: () => string;
};

function createDefaultRelationshipReader(): RelationshipMasterReader {
  if (!isDatabaseUrlConfigured()) {
    return new UnresolvedRelationshipMasterReader();
  }
  return new RelationshipMasterRepository({
    session: createDbSession(),
  });
}

function toPublicItems(
  rows: Awaited<ReturnType<RelationshipMasterReader["listActive"]>>,
): RelationshipPublicItem[] {
  return rows.map((row) => ({
    relationshipCode: row.relationshipCode,
    relationshipLabel: row.relationshipLabel,
    displayOrder: row.displayOrder,
  }));
}

/**
 * API-PUB-005: GET /api/v1/masters/relationships
 * 契約正本: packages/contracts/openapi/public-api.yaml（getMastersRelationships）
 * 実装正本: docs/06_実装設計/api/API-PUB-005_Relationshipマスタ取得API実装仕様書.md
 */
export function createMastersRouter(deps: MastersRouterDeps = {}): Router {
  const router = Router();
  const { logger } = deps;
  const relationshipReader =
    deps.relationshipReader ?? createDefaultRelationshipReader();
  const generatedAtFactory =
    deps.generatedAtFactory ?? (() => new Date().toISOString());

  router.get(
    "/relationships",
    (req: Request, res: Response, next: NextFunction): void => {
      void (async () => {
        try {
          const meta = resolveRequestMeta(res);
          const boundLogger = logger?.bind({
            traceId: meta.traceId,
            requestId: meta.requestId,
          });

          const rows = await relationshipReader.listActive();
          const relationships = toPublicItems(rows);
          const generatedAt = generatedAtFactory();

          boundLogger?.info(MASTERS_RELATIONSHIPS_METRICS.REQUEST_COUNT, {
            path: MASTERS_RELATIONSHIPS_PATH,
            method: "GET",
            httpStatus: 200,
            count: relationships.length,
            hasTraceHeader: Boolean(req.header("x-trace-id")),
            hasRequestIdHeader: Boolean(req.header("x-request-id")),
          });

          const body: RelationshipsSuccessResponse = {
            data: { relationships },
            meta: {
              traceId: meta.traceId,
              requestId: meta.requestId,
              generatedAt,
              count: relationships.length,
            },
          };
          res.status(200).json(body);
        } catch (error) {
          const meta = resolveRequestMeta(res);
          const boundLogger = logger?.bind({
            traceId: meta.traceId,
            requestId: meta.requestId,
          });

          if (error instanceof ApiError) {
            boundLogger?.error(MASTERS_RELATIONSHIPS_METRICS.ERROR_COUNT, {
              path: MASTERS_RELATIONSHIPS_PATH,
              httpStatus: error.httpStatus,
              code: error.code,
            });
            boundLogger?.info(MASTERS_RELATIONSHIPS_METRICS.REQUEST_COUNT, {
              path: MASTERS_RELATIONSHIPS_PATH,
              method: "GET",
              httpStatus: error.httpStatus,
              code: error.code,
            });
            next(error);
            return;
          }

          boundLogger?.error(MASTERS_RELATIONSHIPS_METRICS.ERROR_COUNT, {
            path: MASTERS_RELATIONSHIPS_PATH,
            httpStatus: 500,
            code: MASTERS_RELATIONSHIPS_ERROR_CODES.UNEXPECTED,
          });
          boundLogger?.info(MASTERS_RELATIONSHIPS_METRICS.REQUEST_COUNT, {
            path: MASTERS_RELATIONSHIPS_PATH,
            method: "GET",
            httpStatus: 500,
          });
          next(
            new ApiError({
              code: MASTERS_RELATIONSHIPS_ERROR_CODES.UNEXPECTED,
              httpStatus: 500,
              message: MASTERS_RELATIONSHIPS_ERROR_MESSAGES.UNEXPECTED,
              retryable: false,
              cause: error,
            }),
          );
        }
      })();
    },
  );

  return router;
}
