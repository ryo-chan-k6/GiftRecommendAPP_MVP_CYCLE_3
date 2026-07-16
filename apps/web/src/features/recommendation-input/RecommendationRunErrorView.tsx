"use client";

import { Alert } from "@/components/feedback/Alert";
import { Button } from "@/components/action/Button";
import { PageLayout } from "@/components/layout/PageLayout";

import {
  RUN_ERROR_ALERT_TITLE,
  RUN_ERROR_BACK_LABEL,
  RUN_ERROR_PAGE_TITLE,
  RUN_ERROR_RETRY_LABEL,
} from "./constants";
import type { RunErrorState } from "./types";

type RecommendationRunErrorViewProps = {
  error: RunErrorState;
  onBackToForm: () => void;
  onRetry: () => void;
};

/**
 * SCR-008: 推薦実行失敗時の画面状態。
 * 独立 route は持たず、SCR-002 と同一 URL 上で表示する。
 */
export function RecommendationRunErrorView({
  error,
  onBackToForm,
  onRetry,
}: RecommendationRunErrorViewProps) {
  return (
    <PageLayout title={RUN_ERROR_PAGE_TITLE}>
      <Alert variant="error" title={RUN_ERROR_ALERT_TITLE}>
        <p>{error.message}</p>
        {error.code ? (
          <p className="mt-2 text-small text-text-muted">code: {error.code}</p>
        ) : null}
        {error.traceId ? (
          <p className="mt-1 text-small text-text-muted">
            traceId: {error.traceId}
          </p>
        ) : null}
        <div className="mt-4 flex flex-wrap gap-3">
          <Button variant="primary" onClick={onBackToForm}>
            {RUN_ERROR_BACK_LABEL}
          </Button>
          <Button variant="secondary" onClick={onRetry}>
            {RUN_ERROR_RETRY_LABEL}
          </Button>
        </div>
      </Alert>
    </PageLayout>
  );
}
