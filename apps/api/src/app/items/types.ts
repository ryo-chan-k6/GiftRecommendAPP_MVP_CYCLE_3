/** API-PUB-003 商品詳細の内部 DTO / Response 型。 */

export type ItemImageRecord = {
  imageUrl: string;
  imageSizeType: string | null;
  displayOrder: number;
  isPrimary: boolean;
};

export type ItemDetailRecord = {
  itemId: string;
  itemName: string;
  price: number;
  itemUrl: string;
  catchcopy: string | null;
  itemCaption: string | null;
  externalGenreId: string | null;
  genreName: string | null;
  isActive: boolean;
  images: ItemImageRecord[];
  reviewAverage: number | null;
  reviewCount: number | null;
  popularityRank: number | null;
};

export type ItemDetailReader = {
  findDetail(itemId: string): Promise<ItemDetailRecord | null>;
};

export type PublicItemImageEntry = {
  url: string;
  kind?: "small" | "medium";
  isPrimary?: boolean;
};

export type PublicItemDetail = {
  itemId: string;
  itemName: string;
  itemPrice: number;
  itemUrl: string;
  itemImageUrl?: string;
  itemCatchcopy?: string;
  itemDescription?: string;
  shopName?: string;
  genreId?: string;
  genreName?: string;
  reviewSummary?: {
    average: number;
    count: number;
  };
  images?: PublicItemImageEntry[];
  popularityBadge?: {
    label: string;
    rank: number;
  };
  isActive: boolean;
};

export type ItemDetailSuccessResponse = {
  data: PublicItemDetail;
  meta: {
    traceId: string;
    requestId: string;
    generatedAt?: string;
  };
};
