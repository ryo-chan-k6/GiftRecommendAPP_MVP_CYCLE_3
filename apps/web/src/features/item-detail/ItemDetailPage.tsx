"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";

import { Button } from "@/components/action/Button";
import { Text } from "@/components/display/Text";
import { Alert } from "@/components/feedback/Alert";
import { PageLayout } from "@/components/layout/PageLayout";
import { TextLink } from "@/components/nav/TextLink";
import type {
  PublicItemDetail,
  PublicRecommendationResultItem,
} from "@/generated/api/giftRecommendationServicePublicAPI.schemas";
import { fetchItemDetail } from "@/lib/api";

import {
  BACK_TO_INPUT_LABEL,
  BACK_TO_RESULT_LABEL,
  INPUT_HREF,
  LOADING_MESSAGE,
  PAGE_TITLE,
  RETRY_LABEL,
  buildResultListHref,
} from "./constants";
import { ItemDetailView } from "./ItemDetailView";
import {
  mapItemDetailError,
  type ItemDetailUiError,
} from "./map-item-detail-error";
import { resolveRecommendationContext } from "./resolve-recommendation-context";

type LoadState =
  | { status: "loading" }
  | { status: "error"; error: ItemDetailUiError }
  | {
      status: "ready";
      item: PublicItemDetail;
      context: PublicRecommendationResultItem | null;
    };

/**
 * SCR-006 商品詳細。API-PUB-003 が正本。推薦文脈は sessionStorage のみ。
 */
export function ItemDetailPage() {
  const params = useParams<{ itemId: string }>();
  const searchParams = useSearchParams();
  const itemId = params.itemId ? decodeURIComponent(params.itemId) : "";
  const fromResultId = searchParams.get("fromResultId");

  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [reloadToken, setReloadToken] = useState(0);

  const backHref =
    fromResultId && fromResultId.length > 0
      ? buildResultListHref(fromResultId)
      : INPUT_HREF;
  const backLabel =
    fromResultId && fromResultId.length > 0
      ? BACK_TO_RESULT_LABEL
      : BACK_TO_INPUT_LABEL;

  const load = useCallback(async () => {
    if (!itemId) {
      setState({
        status: "error",
        error: mapItemDetailError(400),
      });
      return;
    }

    setState({ status: "loading" });
    const context = resolveRecommendationContext(itemId, fromResultId);

    try {
      const response = await fetchItemDetail(itemId);
      if (response.status === 200) {
        setState({
          status: "ready",
          item: response.data.data,
          context,
        });
        return;
      }
      setState({
        status: "error",
        error: mapItemDetailError(response.status, response.data),
      });
    } catch {
      setState({
        status: "error",
        error: mapItemDetailError(null),
      });
    }
  }, [fromResultId, itemId]);

  useEffect(() => {
    void load();
  }, [load, reloadToken]);

  return (
    <PageLayout title={PAGE_TITLE}>
      <div className="mb-4">
        <TextLink href={backHref}>{backLabel}</TextLink>
      </div>

      {state.status === "loading" ? (
        <Text className="text-text-secondary">{LOADING_MESSAGE}</Text>
      ) : null}

      {state.status === "error" ? (
        <Alert variant={state.error.alertVariant} title={state.error.title}>
          <p>{state.error.message}</p>
          <div className="mt-4 flex flex-wrap gap-3">
            {state.error.retryable ? (
              <Button
                type="button"
                variant="secondary"
                onClick={() => setReloadToken((value) => value + 1)}
              >
                {RETRY_LABEL}
              </Button>
            ) : null}
            <TextLink href={backHref}>{backLabel}</TextLink>
          </div>
        </Alert>
      ) : null}

      {state.status === "ready" ? (
        <ItemDetailView item={state.item} context={state.context} />
      ) : null}
    </PageLayout>
  );
}
