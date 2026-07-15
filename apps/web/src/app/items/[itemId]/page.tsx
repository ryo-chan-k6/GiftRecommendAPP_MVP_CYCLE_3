"use client";

import { useParams, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { Text } from "@/components/display/Text";
import { Alert } from "@/components/feedback/Alert";
import { PageLayout } from "@/components/layout/PageLayout";
import { TextLink } from "@/components/nav/TextLink";

/**
 * SCR-006 商品詳細の MVP スタブ。
 * SCR-004 からの導線到達先。本体（API-PUB-003）は別 Epic。
 */
function ItemDetailStubContent() {
  const params = useParams<{ itemId: string }>();
  const searchParams = useSearchParams();
  const itemId = params.itemId;
  const fromResultId = searchParams.get("fromResultId");
  const backHref = fromResultId
    ? `/recommendations/${encodeURIComponent(fromResultId)}`
    : "/recommendations";

  return (
    <PageLayout title="商品詳細">
      <Alert variant="info" title="商品詳細は準備中です">
        <p>
          この画面は SCR-006 のプレースホルダです。商品詳細の本実装（API-PUB-003）は別 Task
          で行います。
        </p>
        {itemId ? (
          <p className="mt-2 text-small text-text-muted">itemId: {itemId}</p>
        ) : null}
      </Alert>
      <div className="mt-4">
        <TextLink href={backHref}>結果一覧へ戻る</TextLink>
      </div>
    </PageLayout>
  );
}

export default function ItemDetailStubPage() {
  return (
    <Suspense
      fallback={
        <PageLayout title="商品詳細">
          <Text className="text-text-secondary">読み込み中…</Text>
        </PageLayout>
      }
    >
      <ItemDetailStubContent />
    </Suspense>
  );
}
