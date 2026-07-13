"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { Button } from "@/components/action/Button";
import { Alert } from "@/components/feedback/Alert";
import { PageLayout } from "@/components/layout/PageLayout";
import { Text } from "@/components/display/Text";
import { TextLink } from "@/components/nav/TextLink";
import { readRecommendationResult } from "@/features/recommendation-input/form-persistence";
import type { StoredRecommendationResult } from "@/features/recommendation-input/types";

/**
 * SCR-004 結果一覧の受け皿（本 Epic では最小プレースホルダ）。
 * 実行結果は sessionStorage 経由で受け取る。
 */
export default function RecommendationResultPlaceholderPage() {
  const params = useParams<{ resultId: string }>();
  const resultId = params.resultId;
  const [result, setResult] = useState<StoredRecommendationResult | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setResult(readRecommendationResult(resultId));
    setReady(true);
  }, [resultId]);

  return (
    <PageLayout title="レコメンド結果">
      {!ready ? (
        <Text className="text-text-secondary">読み込み中…</Text>
      ) : result ? (
        <div className="flex flex-col gap-4">
          <Alert variant="info" title="結果を受け取りました">
            <p>
              結果一覧画面（SCR-004）は後続 Task で実装します。ここでは実行結果の受け渡し確認のみ行います。
            </p>
            <p className="mt-2 text-small text-text-muted">
              recommendationResultId: {result.recommendationResultId}
            </p>
            <p className="text-small text-text-muted">
              resultStatus: {result.resultStatus} / items:{" "}
              {result.resultItemCount}
            </p>
          </Alert>
          <ul className="flex flex-col gap-2">
            {result.items.slice(0, 5).map((item) => (
              <li key={item.recommendationResultItemId} className="text-body">
                {item.rank}. {item.itemName}
              </li>
            ))}
          </ul>
          <TextLink href="/recommendations">条件入力へ戻る</TextLink>
        </div>
      ) : (
        <Alert variant="warning" title="結果データがありません">
          <p>
            sessionStorage に結果が見つかりませんでした。条件入力から再度実行してください。
          </p>
          <div className="mt-4">
            <Button
              variant="secondary"
              onClick={() => {
                window.location.href = "/recommendations";
              }}
            >
              条件入力へ戻る
            </Button>
          </div>
        </Alert>
      )}
    </PageLayout>
  );
}
