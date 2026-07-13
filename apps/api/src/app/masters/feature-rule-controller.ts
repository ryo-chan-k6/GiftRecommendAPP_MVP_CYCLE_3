import type { NextFunction, Request, Response } from "express";

import type { ApiLogger } from "../../infrastructure/logger/logger.js";
import { ApiError, isApiError } from "../../middlewares/error/api-error.js";
import { resolveRequestMeta } from "../../middlewares/request-meta.js";
import {
  FEATURE_RULE_MASTERS_ERROR_CODES,
  FEATURE_RULE_MASTERS_ERROR_MESSAGES,
  FEATURE_RULE_MASTERS_METRICS,
  FEATURE_RULE_MASTERS_PATH,
} from "./constants.js";
import type {
  FeatureRuleMastersSuccessResponse,
  FeatureRuleReader,
} from "./types.js";

export type FeatureRuleControllerOptions = {
  reader: FeatureRuleReader;
  logger?: ApiLogger;
  generatedAtFactory?: () => string;
  /**
   * false のとき DB を叩かず GRS-CFG-005（設定解決不能）。
   * 空配列（読取成功・0 件）とは区別する。既定 true。
   */
  mastersConfigResolved?: boolean;
};

/** MVP: 未定義 Query を受け付けない。 */
function assertNoUnknownQuery(req: Request): void {
  const keys = Object.keys(req.query ?? {});
  if (keys.length > 0) {
    throw new ApiError({
      code: FEATURE_RULE_MASTERS_ERROR_CODES.INVALID_REQUEST,
      httpStatus: 400,
      message: FEATURE_RULE_MASTERS_ERROR_MESSAGES.INVALID_REQUEST,
      retryable: false,
    });
  }
}

/** MOD-API-011: GET /feature-rules Controller。 */
export function createFeatureRuleController(
  options: FeatureRuleControllerOptions,
) {
  const {
    reader,
    logger,
    generatedAtFactory = () => new Date().toISOString(),
    mastersConfigResolved = true,
  } = options;

  return async function getFeatureRulesHandler(
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
      assertNoUnknownQuery(req);

      if (!mastersConfigResolved) {
        throw new ApiError({
          code: FEATURE_RULE_MASTERS_ERROR_CODES.CONFIG_UNRESOLVED,
          httpStatus: 500,
          message: FEATURE_RULE_MASTERS_ERROR_MESSAGES.CONFIG_UNRESOLVED,
          retryable: true,
        });
      }

      const snapshot = await reader.getCurrentRules();
      const generatedAt = generatedAtFactory();
      const body: FeatureRuleMastersSuccessResponse = {
        data: snapshot,
        meta: {
          traceId: meta.traceId,
          requestId: meta.requestId,
          generatedAt,
        },
      };

      boundLogger?.info(FEATURE_RULE_MASTERS_METRICS.REQUEST_COUNT, {
        path: FEATURE_RULE_MASTERS_PATH,
        method: "GET",
        httpStatus: 200,
        baseValueRuleCount: snapshot.baseValueRules.length,
        conceptFeatureRuleCount: snapshot.conceptFeatureRules.length,
        hasTraceHeader: Boolean(req.header("x-trace-id")),
        hasRequestIdHeader: Boolean(req.header("x-request-id")),
      });

      res.status(200).json(body);
    } catch (error) {
      const apiError = isApiError(error)
        ? error
        : new ApiError({
            code: FEATURE_RULE_MASTERS_ERROR_CODES.UNEXPECTED,
            httpStatus: 500,
            message: FEATURE_RULE_MASTERS_ERROR_MESSAGES.UNEXPECTED,
            retryable: false,
            cause: error,
          });

      boundLogger?.info(FEATURE_RULE_MASTERS_METRICS.REQUEST_COUNT, {
        path: FEATURE_RULE_MASTERS_PATH,
        method: "GET",
        httpStatus: apiError.httpStatus,
        errorCode: apiError.code,
      });
      boundLogger?.error(FEATURE_RULE_MASTERS_METRICS.ERROR_COUNT, {
        path: FEATURE_RULE_MASTERS_PATH,
        httpStatus: apiError.httpStatus,
        errorCode: apiError.code,
      });

      next(apiError);
    }
  };
}
