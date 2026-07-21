"use client";

import { Suspense } from "react";

import { Text } from "@/components/display/Text";
import { PageLayout } from "@/components/layout/PageLayout";
import { ItemDetailPage } from "@/features/item-detail";
import { LOADING_MESSAGE, PAGE_TITLE } from "@/features/item-detail/constants";

/**
 * SCR-006 商品詳細画面（API-PUB-003 本実装）。
 */
export default function ItemDetailRoutePage() {
  return (
    <Suspense
      fallback={
        <PageLayout title={PAGE_TITLE}>
          <Text className="text-text-secondary">{LOADING_MESSAGE}</Text>
        </PageLayout>
      }
    >
      <ItemDetailPage />
    </Suspense>
  );
}
