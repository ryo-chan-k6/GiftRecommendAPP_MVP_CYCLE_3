"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

import { Button } from "@/components/action/Button";
import { Text } from "@/components/display/Text";
import { Alert } from "@/components/feedback/Alert";
import { PageLayout } from "@/components/layout/PageLayout";
import { TextLink } from "@/components/nav/TextLink";
import { readRecommendationResult } from "@/features/recommendation-input/form-persistence";
import type { StoredRecommendationResult } from "@/features/recommendation-input/types";

import {
  BACK_TO_INPUT_LABEL,
  LOADING_MESSAGE,
  MISSING_RESULT_MESSAGE,
  MISSING_RESULT_TITLE,
  PAGE_TITLE,
  RESEARCH_HREF,
  RESEARCH_LABEL,
} from "./constants";
import { RecommendationResultItem } from "./RecommendationResultItem";

type LoadState =
  | { status: "loading" }
  | { status: "missing" }
  | { status: "ready"; result: StoredRecommendationResult };

/**
 * SCR-004 レコメンド結果一覧。
 * 一覧データは API-PUB-002 Response を sessionStorage から読む（再取得しない）。
 */
export function RecommendationResultPage() {
  const params = useParams<{ resultId: string }>();
  const resultId = params.resultId;
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    if (!resultId) {
      setState({ status: "missing" });
      return;
    }
    const stored = readRecommendationResult(resultId);
    if (!stored || stored.recommendationResultId !== resultId) {
      setState({ status: "missing" });
      return;
    }
    setState({ status: "ready", result: stored });
  }, [resultId]);

  const sortedItems = useMemo(() => {
    if (state.status !== "ready") {
      return [];
    }
    return [...state.result.items].sort((a, b) => a.rank - b.rank);
  }, [state]);

  return (
    <PageLayout title={PAGE_TITLE}>
      <div className="mb-4">
        <TextLink href={RESEARCH_HREF}>{RESEARCH_LABEL}</TextLink>
      </div>

      {state.status === "loading" ? (
        <Text className="text-text-secondary">{LOADING_MESSAGE}</Text>
      ) : null}

      {state.status === "missing" ? (
        <Alert variant="warning" title={MISSING_RESULT_TITLE}>
          <p>{MISSING_RESULT_MESSAGE}</p>
          <div className="mt-4">
            <Button
              variant="secondary"
              onClick={() => {
                window.location.href = RESEARCH_HREF;
              }}
            >
              {BACK_TO_INPUT_LABEL}
            </Button>
          </div>
        </Alert>
      ) : null}

      {state.status === "ready" ? (
        <div className="flex flex-col gap-2">
          {state.result.displayMessage ? (
            <Alert variant="info" title="補足">
              {state.result.displayMessage}
            </Alert>
          ) : null}

          {sortedItems.length === 0 ? (
            <Alert variant="warning" title="表示できる商品がありません">
              <p>
                この画面は結果ありの遷移を想定しています。条件を変更して再検索してください。
              </p>
              <div className="mt-4">
                <TextLink href={RESEARCH_HREF}>{RESEARCH_LABEL}</TextLink>
              </div>
            </Alert>
          ) : (
            <ul className="flex flex-col">
              {sortedItems.map((item) => (
                <li key={item.recommendationResultItemId}>
                  <RecommendationResultItem
                    item={item}
                    resultId={state.result.recommendationResultId}
                  />
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </PageLayout>
  );
}
