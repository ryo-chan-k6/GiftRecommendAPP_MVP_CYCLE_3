import { DbError, isDbError } from "../../infrastructure/db/index.js";
import type { DbSession } from "../../infrastructure/db/session.js";
import type { DbRow } from "../../infrastructure/db/types.js";
import { ApiError } from "../../middlewares/error/api-error.js";
import {
  ITEM_DETAIL_ERROR_CODES,
  ITEM_DETAIL_ERROR_MESSAGES,
  POPULARITY_SNAPSHOT_PERIOD,
  POPULARITY_SNAPSHOT_SOURCE,
} from "./constants.js";
import type { ItemDetailReader, ItemDetailRecord, ItemImageRecord } from "./types.js";

export type ItemDetailRepositoryOptions = {
  session: DbSession;
  itemTableName?: string;
  itemImageTableName?: string;
  itemReviewSummaryTableName?: string;
  itemPopularitySignalTableName?: string;
  rankingSnapshotTableName?: string;
  externalGenreTableName?: string;
};

type ItemBaseRow = DbRow & {
  item_id: string;
  item_name: string;
  price: number;
  item_url: string;
  catchcopy: string | null;
  item_caption: string | null;
  external_genre_id: string | number | null;
  is_active: boolean;
  genre_name: string | null;
};

type ItemImageRow = DbRow & {
  image_url: string;
  image_size_type: string | null;
  display_order: number;
  is_primary: boolean;
};

type ReviewSummaryRow = DbRow & {
  review_average: number | string | null;
  review_count: number;
};

type PopularityRankRow = DbRow & {
  rank: number;
};

function mapDbError(error: unknown): ApiError {
  if (error instanceof ApiError) {
    return error;
  }

  if (isDbError(error)) {
    if (error.code === "DB_UNAVAILABLE") {
      return new ApiError({
        code: ITEM_DETAIL_ERROR_CODES.DB_UNAVAILABLE,
        httpStatus: 503,
        message: ITEM_DETAIL_ERROR_MESSAGES.DB_UNAVAILABLE,
        retryable: true,
        cause: error,
      });
    }

    return new ApiError({
      code: ITEM_DETAIL_ERROR_CODES.DB_QUERY_FAILED,
      httpStatus: 500,
      message: ITEM_DETAIL_ERROR_MESSAGES.DB_QUERY_FAILED,
      retryable: true,
      cause: error,
    });
  }

  return new ApiError({
    code: ITEM_DETAIL_ERROR_CODES.UNEXPECTED,
    httpStatus: 500,
    message: ITEM_DETAIL_ERROR_MESSAGES.UNEXPECTED,
    retryable: false,
    cause: error,
  });
}

function toGenreIdString(value: string | number | null): string | null {
  if (value === null) {
    return null;
  }
  return String(value);
}

function mapImageRow(row: ItemImageRow): ItemImageRecord {
  return {
    imageUrl: row.image_url,
    imageSizeType: row.image_size_type,
    displayOrder: row.display_order,
    isPrimary: row.is_primary,
  };
}

/** MOD-API-015: item 系テーブル読取。 */
export class ItemDetailRepository implements ItemDetailReader {
  readonly session: DbSession;
  readonly itemTableName: string;
  readonly itemImageTableName: string;
  readonly itemReviewSummaryTableName: string;
  readonly itemPopularitySignalTableName: string;
  readonly rankingSnapshotTableName: string;
  readonly externalGenreTableName: string;

  constructor(options: ItemDetailRepositoryOptions) {
    this.session = options.session;
    this.itemTableName = options.itemTableName ?? "item";
    this.itemImageTableName = options.itemImageTableName ?? "item_image";
    this.itemReviewSummaryTableName =
      options.itemReviewSummaryTableName ?? "item_review_summary";
    this.itemPopularitySignalTableName =
      options.itemPopularitySignalTableName ?? "item_popularity_signal";
    this.rankingSnapshotTableName =
      options.rankingSnapshotTableName ?? "ranking_snapshot";
    this.externalGenreTableName =
      options.externalGenreTableName ?? "external_genre";
  }

  async findDetail(itemId: string): Promise<ItemDetailRecord | null> {
    try {
      const base = await this.findItemBase(itemId);
      if (base === null) {
        return null;
      }

      const [images, review, popularityRank] = await Promise.all([
        this.findImages(itemId),
        this.findReviewSummary(itemId),
        base.externalGenreId === null
          ? Promise.resolve(null)
          : this.findPopularityRank(itemId, base.externalGenreId),
      ]);

      return {
        ...base,
        images,
        reviewAverage: review?.reviewAverage ?? null,
        reviewCount: review?.reviewCount ?? null,
        popularityRank,
      };
    } catch (error) {
      throw mapDbError(error);
    }
  }

  private async findItemBase(
    itemId: string,
  ): Promise<Omit<
    ItemDetailRecord,
    "images" | "reviewAverage" | "reviewCount" | "popularityRank"
  > | null> {
    const sql = `
SELECT
  i.item_id,
  i.item_name,
  i.price,
  i.item_url,
  i.catchcopy,
  i.item_caption,
  i.external_genre_id,
  i.is_active,
  eg.genre_name
FROM ${this.itemTableName} i
LEFT JOIN ${this.externalGenreTableName} eg
  ON i.external_genre_id = eg.external_genre_id
WHERE i.item_id = $1::uuid
LIMIT 1
`.trim();

    const result = await this.session.query<ItemBaseRow>(sql, [itemId]);
    const row = result.rows[0];
    if (row === undefined) {
      return null;
    }

    return {
      itemId: row.item_id,
      itemName: row.item_name,
      price: row.price,
      itemUrl: row.item_url,
      catchcopy: row.catchcopy,
      itemCaption: row.item_caption,
      externalGenreId: toGenreIdString(row.external_genre_id),
      genreName: row.genre_name,
      isActive: row.is_active,
    };
  }

  private async findImages(itemId: string): Promise<ItemImageRecord[]> {
    const sql = `
SELECT image_url, image_size_type, display_order, is_primary
FROM ${this.itemImageTableName}
WHERE item_id = $1::uuid
ORDER BY display_order ASC
`.trim();

    const result = await this.session.query<ItemImageRow>(sql, [itemId]);
    return result.rows.map(mapImageRow);
  }

  private async findReviewSummary(
    itemId: string,
  ): Promise<{ reviewAverage: number; reviewCount: number } | null> {
    const sql = `
SELECT review_average, review_count
FROM ${this.itemReviewSummaryTableName}
WHERE item_id = $1::uuid
LIMIT 1
`.trim();

    const result = await this.session.query<ReviewSummaryRow>(sql, [itemId]);
    const row = result.rows[0];
    if (row === undefined) {
      return null;
    }

    const average =
      row.review_average === null
        ? null
        : typeof row.review_average === "number"
          ? row.review_average
          : Number(row.review_average);

    if (average === null || Number.isNaN(average)) {
      return null;
    }

    return {
      reviewAverage: average,
      reviewCount: row.review_count,
    };
  }

  private async findPopularityRank(
    itemId: string,
    externalGenreId: string,
  ): Promise<number | null> {
    const sql = `
SELECT ips.rank
FROM ${this.itemPopularitySignalTableName} ips
INNER JOIN ${this.rankingSnapshotTableName} rs
  ON ips.ranking_snapshot_id = rs.ranking_snapshot_id
WHERE ips.item_id = $1::uuid
  AND rs.source = $2
  AND rs.period = $3
  AND rs.external_genre_id = $4::bigint
ORDER BY rs.last_build_date DESC, rs.fetched_at DESC
LIMIT 1
`.trim();

    const result = await this.session.query<PopularityRankRow>(sql, [
      itemId,
      POPULARITY_SNAPSHOT_SOURCE,
      POPULARITY_SNAPSHOT_PERIOD,
      externalGenreId,
    ]);
    const row = result.rows[0];
    return row === undefined ? null : row.rank;
  }
}

export type InMemoryItemDetailSeed = {
  items?: ItemDetailRecord[];
};

/** 単体テスト向け in-memory Reader（DI 注入用）。 */
export class InMemoryItemDetailRepository implements ItemDetailReader {
  private readonly items = new Map<string, ItemDetailRecord>();

  constructor(seed: InMemoryItemDetailSeed = {}) {
    for (const item of seed.items ?? []) {
      this.items.set(item.itemId, item);
    }
  }

  async findDetail(itemId: string): Promise<ItemDetailRecord | null> {
    return this.items.get(itemId) ?? null;
  }
}
