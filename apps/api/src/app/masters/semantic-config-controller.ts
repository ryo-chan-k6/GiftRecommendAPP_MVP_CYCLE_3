import type { NextFunction, Request, Response } from "express";

import type { ApiLogger } from "../../infrastructure/logger/logger.js";
import { ApiError, isApiError } from "../../middlewares/error/api-error.js";
import { resolveRequestMeta } from "../../middlewares/request-meta.js";
import {
  SEMANTIC_CONFIG_MASTERS_ERROR_CODES,
  SEMANTIC_CONFIG_MASTERS_ERROR_MESSAGES,
  SEMANTIC_CONFIG_MASTERS_METRICS,
  SEMANTIC_CONFIG_MASTERS_PATH,
} from "./constants.js";
import type {
  SemanticConfigMastersSuccessResponse,
  SemanticConfigReader,
} from "./types.js";

export type SemanticConfigControllerOptions = {
  reader: SemanticConfigReader;
  logger?: ApiLogger;
  generatedAtFactory?: () => string;
};

/** MVP: 未定義 Query を受け付けない。 */
function assertNoUnknownQuery(req: Request): void {
  const keys = Object.keys(req.query ?? {});
  if (keys.length > 0) {
    throw new ApiError({
      code: SEMANTIC_CONFIG_MASTERS_ERROR_CODES.INVALID_REQUEST,
      httpStatus: 400,
      message: SEMANTIC_CONFIG_MASTERS_ERROR_MESSAGES.INVALID_REQUEST,
      retryable: false,
    });
  }
}

/** MOD-API-011: GET /semantic-configs Controller。 */
export function createSemanticConfigController(
  options: SemanticConfigControllerOptions,
) {
  const {
    reader,
    logger,
    generatedAtFactory = () => new Date().toISOString(),
  } = options;

  return async function getSemanticConfigsHandler(
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

      const snapshot = await reader.getCurrentSnapshot();
      const generatedAt = generatedAtFactory();
      const body: SemanticConfigMastersSuccessResponse = {
        data: snapshot,
        meta: {
          traceId: meta.traceId,
          requestId: meta.requestId,
          generatedAt,
        },
      };

      boundLogger?.info(SEMANTIC_CONFIG_MASTERS_METRICS.REQUEST_COUNT, {
        path: SEMANTIC_CONFIG_MASTERS_PATH,
        method: "GET",
        httpStatus: 200,
        conceptCount: snapshot.semanticConcepts.length,
        featureCount: snapshot.featureDefinitions.length,
        hasTraceHeader: Boolean(req.header("x-trace-id")),
        hasRequestIdHeader: Boolean(req.header("x-request-id")),
      });

      res.status(200).json(body);
    } catch (error) {
      const apiError = isApiError(error)
        ? error
        : new ApiError({
            code: SEMANTIC_CONFIG_MASTERS_ERROR_CODES.UNEXPECTED,
            httpStatus: 500,
            message: SEMANTIC_CONFIG_MASTERS_ERROR_MESSAGES.UNEXPECTED,
            retryable: false,
            cause: error,
          });

      boundLogger?.info(SEMANTIC_CONFIG_MASTERS_METRICS.REQUEST_COUNT, {
        path: SEMANTIC_CONFIG_MASTERS_PATH,
        method: "GET",
        httpStatus: apiError.httpStatus,
        errorCode: apiError.code,
      });
      boundLogger?.error(SEMANTIC_CONFIG_MASTERS_METRICS.ERROR_COUNT, {
        path: SEMANTIC_CONFIG_MASTERS_PATH,
        httpStatus: apiError.httpStatus,
        errorCode: apiError.code,
      });

      next(apiError);
    }
  };
}
