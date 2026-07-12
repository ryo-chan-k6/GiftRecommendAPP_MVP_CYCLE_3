import { Router, type NextFunction, type Request, type Response } from "express";

import type { ApiLogger } from "../../infrastructure/logger/logger.js";
import { ApiError } from "../../middlewares/error/api-error.js";
import { resolveRequestMeta } from "../../middlewares/request-meta.js";

/** 契約確定値（API-PUB-001）。 */
export const API_HEALTH_SERVICE = "okuri" as const;
export const API_HEALTH_API_VERSION = "v1" as const;
export const API_HEALTH_STATUS_OK = "ok" as const;
export const API_HEALTH_STATUS_UNAVAILABLE = "unavailable" as const;

export const API_HEALTH_ERROR_CODES = {
  UNAVAILABLE: "GRS-COM-003",
} as const;

const UNAVAILABLE_MESSAGE =
  "現在サービスを利用できません。時間を置いて再度お試しください。";

export type HealthAggregatedStatus = "ok" | "unavailable";

export type HealthRouterDeps = {
  logger?: ApiLogger;
  /**
   * 稼働判定（MVP 方針 A の本番は常に ok）。
   * UT で unavailable / 例外経路を検証するための注入口。
   */
  resolveStatus?: () => HealthAggregatedStatus;
  /** checkedAt 生成。例外時は 500 経路の検証に利用する。 */
  checkedAtFactory?: () => string;
};

/**
 * API-PUB-001: GET /api/v1/health
 * 契約正本: packages/contracts/openapi/public-api.yaml
 * 実装正本: docs/06_実装設計/api/API-PUB-001_APIヘルスチェックAPI実装仕様書.md
 * MVP 方針 A: プロセス稼働確認のみ。DB / reco の個別結果は表面化しない。
 */
export function createHealthRouter(deps: HealthRouterDeps = {}): Router {
  const router = Router();
  const { logger } = deps;
  const resolveStatus = deps.resolveStatus ?? (() => API_HEALTH_STATUS_OK);
  const checkedAtFactory =
    deps.checkedAtFactory ?? (() => new Date().toISOString());

  router.get(
    "/health",
    (req: Request, res: Response, next: NextFunction): void => {
      try {
        const meta = resolveRequestMeta(res);
        const boundLogger = logger?.bind({
          traceId: meta.traceId,
          requestId: meta.requestId,
        });

        const status = resolveStatus();
        if (status === API_HEALTH_STATUS_UNAVAILABLE) {
          boundLogger?.error("api_error_count", {
            path: "/api/v1/health",
            httpStatus: 503,
            status: API_HEALTH_STATUS_UNAVAILABLE,
          });
          throw new ApiError({
            code: API_HEALTH_ERROR_CODES.UNAVAILABLE,
            httpStatus: 503,
            message: UNAVAILABLE_MESSAGE,
            retryable: true,
          });
        }

        const checkedAt = checkedAtFactory();

        // access / metric 境界（API一覧: api_request_count）。Secret は載せない。
        boundLogger?.info("api_request_count", {
          path: "/api/v1/health",
          method: "GET",
          status: API_HEALTH_STATUS_OK,
          httpStatus: 200,
          // Header 有無のみ。値はログに出さない（trace は meta 経由で bind 済み）。
          hasTraceHeader: Boolean(req.header("x-trace-id")),
          hasRequestIdHeader: Boolean(req.header("x-request-id")),
        });

        res.status(200).json({
          data: {
            status: API_HEALTH_STATUS_OK,
            service: API_HEALTH_SERVICE,
            apiVersion: API_HEALTH_API_VERSION,
            checkedAt,
          },
          meta: {
            traceId: meta.traceId,
            requestId: meta.requestId,
            generatedAt: checkedAt,
          },
        });
      } catch (error) {
        // 想定外は error middleware へ。Response に stack / 内部詳細を載せない。
        if (!(error instanceof ApiError)) {
          const meta = resolveRequestMeta(res);
          logger
            ?.bind({ traceId: meta.traceId, requestId: meta.requestId })
            .error("api_error_count", {
              path: "/api/v1/health",
              httpStatus: 500,
            });
        }
        next(error);
      }
    },
  );

  return router;
}
