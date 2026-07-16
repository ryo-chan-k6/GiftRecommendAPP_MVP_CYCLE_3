"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Alert } from "@/components/feedback/Alert";
import { Button } from "@/components/action/Button";
import { EmptyState } from "@/components/feedback/EmptyState";
import { LoadingPanel } from "@/components/feedback/LoadingPanel";
import { PageLayout } from "@/components/layout/PageLayout";
import { Text } from "@/components/display/Text";
import { ResultStatus } from "@/generated/api/giftRecommendationServicePublicAPI.schemas";
import { postRecommendationRun } from "@/lib/api";

import { buildRecommendationRunRequest } from "./build-request";
import {
  EMPTY_RESULT_MESSAGE,
  MASTERS_EMPTY_MESSAGE,
  MASTERS_ERROR_MESSAGE,
  RUN_ERROR_FALLBACK_MESSAGE,
  RUNNING_MESSAGE,
} from "./constants";
import {
  persistFormValues,
  readFormValuesFromLocation,
  storeRecommendationResult,
} from "./form-persistence";
import { isErrorResponse, loadRecommendationMasters } from "./load-masters";
import { RecommendationInputForm } from "./RecommendationInputForm";
import { RecommendationRunErrorView } from "./RecommendationRunErrorView";
import type {
  MastersLoadState,
  RecommendationInputFieldErrors,
  RecommendationInputFormValues,
  RunErrorState,
  ScreenPhase,
} from "./types";
import { createEmptyFormValues } from "./types";
import { hasFieldErrors, validateRecommendationInput } from "./validation";

export function RecommendationInputPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [phase, setPhase] = useState<ScreenPhase>("form");
  const [masters, setMasters] = useState<MastersLoadState>({
    status: "loading",
  });
  const [values, setValues] = useState<RecommendationInputFormValues>(() =>
    createEmptyFormValues(),
  );
  const [errors, setErrors] = useState<RecommendationInputFieldErrors>({});
  const [runError, setRunError] = useState<RunErrorState | null>(null);
  const [hydrated, setHydrated] = useState(false);

  const refreshMasters = useCallback(async () => {
    setMasters({ status: "loading" });
    const next = await loadRecommendationMasters();
    setMasters(next);
  }, []);

  useEffect(() => {
    void refreshMasters();
  }, [refreshMasters]);

  useEffect(() => {
    if (hydrated) {
      return;
    }
    setValues(readFormValuesFromLocation(searchParams));
    setHydrated(true);
  }, [hydrated, searchParams]);

  const relationships = useMemo(
    () => (masters.status === "success" ? masters.relationships : []),
    [masters],
  );
  const occasions = useMemo(
    () => (masters.status === "success" ? masters.occasions : []),
    [masters],
  );
  const mastersEmpty =
    masters.status === "success" &&
    (relationships.length === 0 || occasions.length === 0);
  const mastersLoading =
    masters.status === "loading" || masters.status === "idle";

  const submitDisabled = useMemo(
    () =>
      mastersLoading ||
      masters.status === "error" ||
      mastersEmpty ||
      phase === "running",
    [masters.status, mastersEmpty, mastersLoading, phase],
  );

  const onChange = useCallback(
    (patch: Partial<RecommendationInputFormValues>) => {
      setValues((prev) => ({ ...prev, ...patch }));
    },
    [],
  );

  const onBlurField = useCallback(
    (field: keyof RecommendationInputFieldErrors) => {
      if (masters.status !== "success") {
        return;
      }
      const nextErrors = validateRecommendationInput(
        values,
        relationships,
        occasions,
      );
      setErrors((prev) => {
        if (nextErrors[field]) {
          return { ...prev, [field]: nextErrors[field] };
        }
        const rest = { ...prev };
        delete rest[field];
        return rest;
      });
    },
    [masters.status, occasions, relationships, values],
  );

  const onSubmit = useCallback(async () => {
    if (masters.status !== "success" || mastersEmpty) {
      return;
    }

    const nextErrors = validateRecommendationInput(
      values,
      relationships,
      occasions,
    );
    setErrors(nextErrors);
    if (hasFieldErrors(nextErrors)) {
      return;
    }

    persistFormValues(values);
    setPhase("running");
    setRunError(null);

    const request = buildRecommendationRunRequest(
      values,
      relationships,
      occasions,
    );

    try {
      const response = await postRecommendationRun(request);
      if (response.status !== 200) {
        const payload = response.data;
        setRunError({
          message: isErrorResponse(payload)
            ? payload.error.message || RUN_ERROR_FALLBACK_MESSAGE
            : RUN_ERROR_FALLBACK_MESSAGE,
          code: isErrorResponse(payload) ? payload.error.code : undefined,
          traceId: isErrorResponse(payload)
            ? payload.meta?.traceId
            : undefined,
        });
        setPhase("error");
        return;
      }

      const result = response.data.data;
      storeRecommendationResult(result);

      if (
        result.resultStatus === ResultStatus.empty ||
        result.resultItemCount === 0 ||
        result.items.length === 0
      ) {
        setPhase("empty");
        return;
      }

      router.push(`/recommendations/${result.recommendationResultId}`);
    } catch {
      setRunError({ message: RUN_ERROR_FALLBACK_MESSAGE });
      setPhase("error");
    }
  }, [
    masters.status,
    mastersEmpty,
    occasions,
    relationships,
    router,
    values,
  ]);

  if (phase === "running") {
    return (
      <PageLayout title="レコメンド実行中">
        <LoadingPanel message={RUNNING_MESSAGE}>
          <Text className="text-small text-text-muted">
            しばらくお待ちください。
          </Text>
        </LoadingPanel>
      </PageLayout>
    );
  }

  if (phase === "empty") {
    return (
      <PageLayout title="おすすめが見つかりませんでした">
        <EmptyState
          title="条件に合うギフトがありません"
          description={EMPTY_RESULT_MESSAGE}
          action={
            <Button
              variant="secondary"
              onClick={() => {
                setPhase("form");
              }}
            >
              条件を変更する
            </Button>
          }
        />
      </PageLayout>
    );
  }

  if (phase === "error" && runError) {
    return (
      <RecommendationRunErrorView
        error={runError}
        onBackToForm={() => {
          setPhase("form");
          setRunError(null);
        }}
        onRetry={() => {
          void onSubmit();
        }}
      />
    );
  }

  return (
    <PageLayout title="レコメンド条件入力">
      <Text className="mb-6 text-text-secondary">
        贈る相手・用途・予算などを入力して、ギフト候補を探します。
      </Text>

      {masters.status === "error" ? (
        <Alert variant="error" title={MASTERS_ERROR_MESSAGE} className="mb-6">
          <p>選択項目を再取得してください。</p>
          {masters.traceId ? (
            <p className="mt-2 text-small text-text-muted">
              traceId: {masters.traceId}
            </p>
          ) : null}
          <div className="mt-4">
            <Button variant="secondary" onClick={() => void refreshMasters()}>
              再試行
            </Button>
          </div>
        </Alert>
      ) : null}

      {mastersEmpty ? (
        <Alert variant="warning" title={MASTERS_EMPTY_MESSAGE} className="mb-6">
          <p>マスタに有効な選択肢がありません。</p>
        </Alert>
      ) : null}

      <RecommendationInputForm
        values={values}
        errors={errors}
        relationships={relationships}
        occasions={occasions}
        mastersLoading={mastersLoading}
        mastersEmpty={mastersEmpty}
        submitDisabled={submitDisabled}
        onChange={onChange}
        onBlurField={onBlurField}
        onSubmit={() => {
          void onSubmit();
        }}
      />
    </PageLayout>
  );
}
