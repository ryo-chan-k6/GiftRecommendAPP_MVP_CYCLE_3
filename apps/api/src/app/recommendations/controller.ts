import type { NextFunction, Request, Response } from "express";

import type { ApiLogger } from "../../infrastructure/logger/logger.js";
import { resolveRequestMeta } from "../../middlewares/request-meta.js";
import { ApiError } from "../../middlewares/error/api-error.js";
import type { RecommendationApplicationService } from "./application-service.js";
import { validateRecommendationRunRequest } from "./validator.js";

const JSON_MEDIA_TYPE = "application/json";

function assertJsonContentType(req: Request): void {
  const contentType = req.header("content-type");
  if (
    contentType === undefined ||
    !contentType.toLowerCase().includes(JSON_MEDIA_TYPE)
  ) {
    throw new ApiError({
      code: "GRS-REQ-001",
      httpStatus: 400,
      message: "条件を確認してください。",
      retryable: false,
      details: [{ field: "Content-Type", message: "application/json is required" }],
    });
  }
}

function assertJsonAccept(req: Request): void {
  const accept = req.header("accept");
  if (accept === undefined || accept === "*/*") {
    return;
  }

  if (!accept.toLowerCase().includes(JSON_MEDIA_TYPE)) {
    throw new ApiError({
      code: "GRS-REQ-001",
      httpStatus: 400,
      message: "条件を確認してください。",
      retryable: false,
      details: [{ field: "Accept", message: "application/json is required" }],
    });
  }
}

function setTraceHeaders(
  res: Response,
  traceId: string,
  requestId: string,
): void {
  res.setHeader("X-Trace-Id", traceId);
  res.setHeader("X-Request-Id", requestId);
}

export type RecommendationControllerOptions = {
  applicationService: RecommendationApplicationService;
  logger?: ApiLogger;
};

/** MOD-API-001: POST /api/v1/recommendations Controller。 */
export function createRecommendationController(
  options: RecommendationControllerOptions,
) {
  const { applicationService, logger } = options;

  return async function runRecommendationHandler(
    req: Request,
    res: Response,
    next: NextFunction,
  ): Promise<void> {
    try {
      assertJsonContentType(req);
      assertJsonAccept(req);

      const meta = resolveRequestMeta(res);
      const boundLogger = logger?.bind({
        traceId: meta.traceId,
        requestId: meta.requestId,
      });

      boundLogger?.info("recommendation_run_requested", {
        path: req.path,
        method: req.method,
      });

      const validatedRequest = validateRecommendationRunRequest(req.body);
      const response = await applicationService.runRecommendation({
        request: validatedRequest,
        traceId: meta.traceId,
        requestId: meta.requestId,
      });

      setTraceHeaders(res, meta.traceId, meta.requestId);
      res.status(200).json(response);
    } catch (error) {
      next(error);
    }
  };
}
