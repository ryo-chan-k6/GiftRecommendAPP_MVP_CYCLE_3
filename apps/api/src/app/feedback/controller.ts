import type { NextFunction, Request, Response } from "express";

import type { ApiLogger } from "../../infrastructure/logger/logger.js";
import { ApiError, isApiError } from "../../middlewares/error/api-error.js";
import { resolveRequestMeta } from "../../middlewares/request-meta.js";
import {
  FEEDBACK_ERROR_CODES,
  FEEDBACK_ERROR_MESSAGES,
  FEEDBACK_METRICS,
  FEEDBACK_SUBMIT_PATH,
} from "./constants.js";
import type { FeedbackService } from "./service.js";
import {
  validateFeedbackSubmitPath,
  validateFeedbackSubmitRequest,
} from "./validator.js";

const JSON_MEDIA_TYPE = "application/json";

function assertJsonContentType(req: Request): void {
  const contentType = req.header("content-type");
  if (
    contentType === undefined ||
    !contentType.toLowerCase().includes(JSON_MEDIA_TYPE)
  ) {
    throw new ApiError({
      code: FEEDBACK_ERROR_CODES.INVALID_REQUEST,
      httpStatus: 400,
      message: FEEDBACK_ERROR_MESSAGES.INVALID_REQUEST,
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
      code: FEEDBACK_ERROR_CODES.INVALID_REQUEST,
      httpStatus: 400,
      message: FEEDBACK_ERROR_MESSAGES.INVALID_REQUEST,
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

function recordMetrics(
  logger: ApiLogger | undefined,
  input: {
    traceId: string;
    requestId: string;
    httpStatus: number;
    errorCode?: string;
    isPositive?: boolean | null;
    isNegative?: boolean | null;
  },
): void {
  const boundLogger = logger?.bind({
    traceId: input.traceId,
    requestId: input.requestId,
  });

  boundLogger?.info(FEEDBACK_METRICS.COUNT, {
    path: FEEDBACK_SUBMIT_PATH,
    method: "POST",
    httpStatus: input.httpStatus,
    ...(input.errorCode !== undefined ? { code: input.errorCode } : {}),
  });

  if (input.errorCode !== undefined) {
    boundLogger?.error(FEEDBACK_METRICS.ERROR_COUNT, {
      path: FEEDBACK_SUBMIT_PATH,
      httpStatus: input.httpStatus,
      code: input.errorCode,
    });
    return;
  }

  if (input.isPositive === true) {
    boundLogger?.info(FEEDBACK_METRICS.POSITIVE_COUNT, {
      path: FEEDBACK_SUBMIT_PATH,
      httpStatus: input.httpStatus,
    });
  }

  if (input.isNegative === true) {
    boundLogger?.info(FEEDBACK_METRICS.NEGATIVE_COUNT, {
      path: FEEDBACK_SUBMIT_PATH,
      httpStatus: input.httpStatus,
    });
  }
}

export type FeedbackControllerOptions = {
  service: FeedbackService;
  logger?: ApiLogger;
};

/** MOD-API-007: POST /:resultId/feedback Controller。 */
export function createFeedbackController(options: FeedbackControllerOptions) {
  const { service, logger } = options;

  return async function submitFeedbackHandler(
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
      assertJsonContentType(req);
      assertJsonAccept(req);

      const resultId = validateFeedbackSubmitPath(req.params.resultId);
      const validatedRequest = validateFeedbackSubmitRequest(req.body);

      boundLogger?.info("feedback_submit_requested", {
        path: req.path,
        method: req.method,
        feedbackTargetType: validatedRequest.feedbackTargetType,
        feedbackType: validatedRequest.feedbackType,
      });

      const result = await service.submitFeedback({
        resultId,
        request: validatedRequest,
        traceId: meta.traceId,
        requestId: meta.requestId,
        userAgent: req.header("user-agent"),
      });

      setTraceHeaders(res, meta.traceId, meta.requestId);
      recordMetrics(logger, {
        traceId: meta.traceId,
        requestId: meta.requestId,
        httpStatus: result.httpStatus,
        isPositive: result.isPositive,
        isNegative: result.isNegative,
      });

      res.status(result.httpStatus).json(result.body);
    } catch (error) {
      const apiError = isApiError(error)
        ? error
        : new ApiError({
            code: FEEDBACK_ERROR_CODES.UNEXPECTED,
            httpStatus: 500,
            message: FEEDBACK_ERROR_MESSAGES.UNEXPECTED,
            retryable: false,
            cause: error,
          });

      recordMetrics(logger, {
        traceId: meta.traceId,
        requestId: meta.requestId,
        httpStatus: apiError.httpStatus,
        errorCode: apiError.code,
      });

      next(apiError);
    }
  };
}
