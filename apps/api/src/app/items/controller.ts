import type { NextFunction, Request, Response } from "express";

import type { ApiLogger } from "../../infrastructure/logger/logger.js";
import { ApiError, isApiError } from "../../middlewares/error/api-error.js";
import { resolveRequestMeta } from "../../middlewares/request-meta.js";
import {
  ITEM_DETAIL_ERROR_CODES,
  ITEM_DETAIL_ERROR_MESSAGES,
  ITEM_DETAIL_METRICS,
  ITEM_DETAIL_PATH,
  ITEM_ID_MAX_LENGTH,
  ITEM_ID_PATTERN,
  POPULARITY_BADGE_LABEL,
} from "./constants.js";
import type { ItemDetailReader } from "./types.js";
import type {
  ItemDetailRecord,
  ItemDetailSuccessResponse,
  PublicItemDetail,
  PublicItemImageEntry,
} from "./types.js";

export type ItemDetailControllerOptions = {
  reader: ItemDetailReader;
  logger?: ApiLogger;
  generatedAtFactory?: () => string;
};

/** MVP: 未定義 Query を受け付けない。 */
function assertNoUnknownQuery(req: Request): void {
  const keys = Object.keys(req.query ?? {});
  if (keys.length > 0) {
    throw new ApiError({
      code: ITEM_DETAIL_ERROR_CODES.INVALID_REQUEST,
      httpStatus: 400,
      message: ITEM_DETAIL_ERROR_MESSAGES.INVALID_REQUEST,
      retryable: false,
      details: [{ field: "query", message: "unknown query parameters are not allowed" }],
    });
  }
}

/** OpenAPI ItemIdPath 準拠の Path 検証。 */
export function validateItemId(rawItemId: string | undefined): string {
  const itemId = rawItemId?.trim() ?? "";
  if (itemId === "") {
    throw new ApiError({
      code: ITEM_DETAIL_ERROR_CODES.INVALID_REQUEST,
      httpStatus: 400,
      message: ITEM_DETAIL_ERROR_MESSAGES.INVALID_REQUEST,
      retryable: false,
      details: [{ field: "itemId", message: "itemId is required" }],
    });
  }

  if (itemId.length > ITEM_ID_MAX_LENGTH) {
    throw new ApiError({
      code: ITEM_DETAIL_ERROR_CODES.INVALID_REQUEST,
      httpStatus: 400,
      message: ITEM_DETAIL_ERROR_MESSAGES.INVALID_REQUEST,
      retryable: false,
      details: [{ field: "itemId", message: "itemId exceeds max length" }],
    });
  }

  if (!ITEM_ID_PATTERN.test(itemId)) {
    throw new ApiError({
      code: ITEM_DETAIL_ERROR_CODES.INVALID_REQUEST,
      httpStatus: 400,
      message: ITEM_DETAIL_ERROR_MESSAGES.INVALID_REQUEST,
      retryable: false,
      details: [{ field: "itemId", message: "itemId contains invalid characters" }],
    });
  }

  return itemId;
}

function toImageKind(
  imageSizeType: string | null,
): PublicItemImageEntry["kind"] | undefined {
  if (imageSizeType === "small" || imageSizeType === "medium") {
    return imageSizeType;
  }
  return undefined;
}

function buildPublicItemDetail(record: ItemDetailRecord): PublicItemDetail {
  const sortedImages = [...record.images].sort(
    (a, b) => a.displayOrder - b.displayOrder,
  );
  const primaryImage = sortedImages.find((image) => image.isPrimary);

  const detail: PublicItemDetail = {
    itemId: record.itemId,
    itemName: record.itemName,
    itemPrice: record.price,
    itemUrl: record.itemUrl,
    isActive: true,
  };

  if (record.catchcopy !== null && record.catchcopy !== "") {
    detail.itemCatchcopy = record.catchcopy;
  }

  if (record.itemCaption !== null && record.itemCaption !== "") {
    detail.itemDescription = record.itemCaption;
  }

  if (record.externalGenreId !== null) {
    detail.genreId = record.externalGenreId;
    if (record.genreName !== null && record.genreName !== "") {
      detail.genreName = record.genreName;
    }
  }

  if (primaryImage !== undefined) {
    detail.itemImageUrl = primaryImage.imageUrl;
  }

  if (sortedImages.length > 0) {
    detail.images = sortedImages.map((image) => {
      const entry: PublicItemImageEntry = { url: image.imageUrl };
      const kind = toImageKind(image.imageSizeType);
      if (kind !== undefined) {
        entry.kind = kind;
      }
      if (image.isPrimary) {
        entry.isPrimary = true;
      }
      return entry;
    });
  }

  if (record.reviewAverage !== null && record.reviewCount !== null) {
    detail.reviewSummary = {
      average: record.reviewAverage,
      count: record.reviewCount,
    };
  }

  if (record.popularityRank !== null) {
    detail.popularityBadge = {
      label: POPULARITY_BADGE_LABEL,
      rank: record.popularityRank,
    };
  }

  return detail;
}

function recordMetrics(
  logger: ApiLogger | undefined,
  input: {
    traceId: string;
    requestId: string;
    itemId?: string;
    httpStatus: number;
    errorCode?: string;
    hasPrimaryImage?: boolean;
  },
): void {
  const boundLogger = logger?.bind({
    traceId: input.traceId,
    requestId: input.requestId,
  });

  boundLogger?.info(ITEM_DETAIL_METRICS.REQUEST_COUNT, {
    path: ITEM_DETAIL_PATH,
    method: "GET",
    httpStatus: input.httpStatus,
    ...(input.itemId !== undefined ? { itemId: input.itemId } : {}),
    ...(input.errorCode !== undefined ? { code: input.errorCode } : {}),
    ...(input.hasPrimaryImage !== undefined
      ? { hasPrimaryImage: input.hasPrimaryImage }
      : {}),
  });

  if (input.errorCode === ITEM_DETAIL_ERROR_CODES.NOT_FOUND) {
    boundLogger?.info(ITEM_DETAIL_METRICS.NOT_FOUND_COUNT, {
      path: ITEM_DETAIL_PATH,
      httpStatus: input.httpStatus,
      code: input.errorCode,
      ...(input.itemId !== undefined ? { itemId: input.itemId } : {}),
    });
  }
}

/** MOD-API-014: GET /:itemId Controller。 */
export function createItemDetailController(options: ItemDetailControllerOptions) {
  const {
    reader,
    logger,
    generatedAtFactory = () => new Date().toISOString(),
  } = options;

  return async function getItemDetailHandler(
    req: Request,
    res: Response,
    next: NextFunction,
  ): Promise<void> {
    const meta = resolveRequestMeta(res);
    let itemId: string | undefined;

    try {
      assertNoUnknownQuery(req);
      const rawItemId = req.params.itemId;
      itemId = validateItemId(
        Array.isArray(rawItemId) ? rawItemId[0] : rawItemId,
      );

      const record = await reader.findDetail(itemId);
      if (record === null) {
        throw new ApiError({
          code: ITEM_DETAIL_ERROR_CODES.NOT_FOUND,
          httpStatus: 404,
          message: ITEM_DETAIL_ERROR_MESSAGES.NOT_FOUND,
          retryable: false,
        });
      }

      if (!record.isActive) {
        throw new ApiError({
          code: ITEM_DETAIL_ERROR_CODES.INACTIVE,
          httpStatus: 422,
          message: ITEM_DETAIL_ERROR_MESSAGES.INACTIVE,
          retryable: false,
        });
      }

      const data = buildPublicItemDetail(record);
      const body: ItemDetailSuccessResponse = {
        data,
        meta: {
          traceId: meta.traceId,
          requestId: meta.requestId,
          generatedAt: generatedAtFactory(),
        },
      };

      const hasPrimaryImage = record.images.some((image) => image.isPrimary);
      recordMetrics(logger, {
        traceId: meta.traceId,
        requestId: meta.requestId,
        itemId,
        httpStatus: 200,
        hasPrimaryImage,
      });

      res.status(200).json(body);
    } catch (error) {
      const apiError = isApiError(error)
        ? error
        : new ApiError({
            code: ITEM_DETAIL_ERROR_CODES.UNEXPECTED,
            httpStatus: 500,
            message: ITEM_DETAIL_ERROR_MESSAGES.UNEXPECTED,
            retryable: false,
            cause: error,
          });

      recordMetrics(logger, {
        traceId: meta.traceId,
        requestId: meta.requestId,
        itemId,
        httpStatus: apiError.httpStatus,
        errorCode: apiError.code,
      });

      next(apiError);
    }
  };
}
