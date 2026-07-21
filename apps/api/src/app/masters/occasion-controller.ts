import type { NextFunction, Request, Response } from "express";

import type { ApiLogger } from "../../infrastructure/logger/logger.js";
import { ApiError, isApiError } from "../../middlewares/error/api-error.js";
import { resolveRequestMeta } from "../../middlewares/request-meta.js";
import {
  OCCASION_MASTERS_ERROR_CODES,
  OCCASION_MASTERS_ERROR_MESSAGES,
  OCCASION_MASTERS_METRICS,
  OCCASION_MASTERS_PATH,
} from "./constants.js";
import type { OccasionMasterRepository } from "./occasion-repository.js";
import type { OccasionMastersSuccessResponse } from "./types.js";

export type OccasionControllerOptions = {
  repository: OccasionMasterRepository;
  logger?: ApiLogger;
  /**
   * false のとき DB を叩かず GRS-CFG-005（設定解決不能）。
   * 空配列（読取成功・0 件）とは区別する。既定 true。
   */
  mastersConfigResolved?: boolean;
};

/** MOD-API-011: GET /occasions Controller。 */
export function createOccasionController(options: OccasionControllerOptions) {
  const {
    repository,
    logger,
    mastersConfigResolved = true,
  } = options;

  return async function getOccasionsHandler(
    req: Request,
    res: Response,
    next: NextFunction,
  ): Promise<void> {
    const meta = resolveRequestMeta(res);
    const boundLogger = logger?.bind({
      traceId: meta.traceId,
      requestId: meta.requestId,
    });

    try {
      if (!mastersConfigResolved) {
        throw new ApiError({
          code: OCCASION_MASTERS_ERROR_CODES.CONFIG_UNRESOLVED,
          httpStatus: 500,
          message: OCCASION_MASTERS_ERROR_MESSAGES.CONFIG_UNRESOLVED,
          retryable: true,
        });
      }

      const occasions = await repository.listActive();
      const generatedAt = new Date().toISOString();
      const body: OccasionMastersSuccessResponse = {
        data: { occasions },
        meta: {
          traceId: meta.traceId,
          requestId: meta.requestId,
          generatedAt,
          count: occasions.length,
        },
      };

      boundLogger?.info(OCCASION_MASTERS_METRICS.REQUEST_COUNT, {
        path: OCCASION_MASTERS_PATH,
        method: "GET",
        httpStatus: 200,
        count: occasions.length,
        hasTraceHeader: Boolean(req.header("x-trace-id")),
        hasRequestIdHeader: Boolean(req.header("x-request-id")),
      });

      res.status(200).json(body);
    } catch (error) {
      const apiError = isApiError(error)
        ? error
        : new ApiError({
            code: OCCASION_MASTERS_ERROR_CODES.UNEXPECTED,
            httpStatus: 500,
            message: OCCASION_MASTERS_ERROR_MESSAGES.UNEXPECTED,
            retryable: false,
            cause: error,
          });

      boundLogger?.info(OCCASION_MASTERS_METRICS.REQUEST_COUNT, {
        path: OCCASION_MASTERS_PATH,
        method: "GET",
        httpStatus: apiError.httpStatus,
        errorCode: apiError.code,
      });
      boundLogger?.error(OCCASION_MASTERS_METRICS.ERROR_COUNT, {
        path: OCCASION_MASTERS_PATH,
        httpStatus: apiError.httpStatus,
        errorCode: apiError.code,
      });

      next(apiError);
    }
  };
}
