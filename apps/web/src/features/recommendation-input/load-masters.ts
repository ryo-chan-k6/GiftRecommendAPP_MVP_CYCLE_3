import type { ErrorResponse } from "@/generated/api/giftRecommendationServicePublicAPI.schemas";
import {
  fetchFeatureRuleMasters,
  fetchOccasionMasters,
  fetchRelationshipMasters,
  fetchSemanticConfigMasters,
} from "@/lib/api";

import { MASTERS_ERROR_MESSAGE } from "./constants";
import {
  toOccasionOptions,
  toRelationshipOptions,
  type MastersLoadState,
} from "./types";

function extractTraceId(payload: unknown): string | undefined {
  if (
    payload &&
    typeof payload === "object" &&
    "meta" in payload &&
    payload.meta &&
    typeof payload.meta === "object" &&
    "traceId" in payload.meta &&
    typeof (payload.meta as { traceId?: unknown }).traceId === "string"
  ) {
    return (payload.meta as { traceId: string }).traceId;
  }
  return undefined;
}

/**
 * API-PUB-005〜008 を並列取得する。
 * 007 / 008 は UI 非表示だが失敗時はマスタ取得エラーとして扱う（画面仕様 §14 / §22-3）。
 */
export async function loadRecommendationMasters(): Promise<MastersLoadState> {
  try {
    const [
      relationshipsRes,
      occasionsRes,
      semanticRes,
      featureRulesRes,
    ] = await Promise.all([
      fetchRelationshipMasters(),
      fetchOccasionMasters(),
      fetchSemanticConfigMasters(),
      fetchFeatureRuleMasters(),
    ]);

    const failed = [
      relationshipsRes,
      occasionsRes,
      semanticRes,
      featureRulesRes,
    ].find((res) => res.status !== 200);

    if (failed) {
      return {
        status: "error",
        message: MASTERS_ERROR_MESSAGE,
        traceId: extractTraceId(failed.data),
      };
    }

    if (
      relationshipsRes.status !== 200 ||
      occasionsRes.status !== 200 ||
      semanticRes.status !== 200 ||
      featureRulesRes.status !== 200
    ) {
      return { status: "error", message: MASTERS_ERROR_MESSAGE };
    }

    return {
      status: "success",
      relationships: toRelationshipOptions(
        relationshipsRes.data.data.relationships,
      ),
      occasions: toOccasionOptions(occasionsRes.data.data.occasions),
      semanticConfigLoaded: true,
      featureRulesLoaded: true,
    };
  } catch {
    return { status: "error", message: MASTERS_ERROR_MESSAGE };
  }
}

export function isErrorResponse(payload: unknown): payload is ErrorResponse {
  return (
    !!payload &&
    typeof payload === "object" &&
    "error" in payload &&
    typeof (payload as ErrorResponse).error?.message === "string"
  );
}
