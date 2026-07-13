import { Suspense } from "react";

import { LoadingPanel } from "@/components/feedback/LoadingPanel";
import { PageLayout } from "@/components/layout/PageLayout";
import { RecommendationInputPage } from "@/features/recommendation-input";

function RecommendationsFallback() {
  return (
    <PageLayout title="レコメンド条件入力">
      <LoadingPanel message="画面を準備しています" />
    </PageLayout>
  );
}

/** SCR-002 レコメンド条件入力画面（`/recommendations`） */
export default function RecommendationsPage() {
  return (
    <Suspense fallback={<RecommendationsFallback />}>
      <RecommendationInputPage />
    </Suspense>
  );
}
