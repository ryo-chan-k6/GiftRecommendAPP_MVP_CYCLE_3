import {
  getFeatureRuleMasters,
  getGetFeatureRuleMastersUrl,
  getGetMastersOccasionsUrl,
  getGetMastersRelationshipsUrl,
  getGetSemanticConfigMastersUrl,
  getMastersOccasions,
  getMastersRelationships,
  getSemanticConfigMasters,
  type getFeatureRuleMastersResponse,
  type getMastersOccasionsResponse,
  type getMastersRelationshipsResponse,
  type getSemanticConfigMastersResponse,
} from "@/generated/api/masters/masters";
import {
  getRunRecommendationUrl,
  runRecommendation,
  type runRecommendationResponse,
} from "@/generated/api/recommendations/recommendations";
import type { RecommendationRunRequest } from "@/generated/api/giftRecommendationServicePublicAPI.schemas";

import { getPublicApiBaseUrl, resolvePublicApiUrl } from "./base-url";

/**
 * generated client は相対パス固定のため、ベース URL 未設定時はそのまま委譲する。
 * 設定時は同一契約の URL ヘルパー + fetch で絶対 URL を解決する。
 */
async function fetchJsonAtUrl<T>(
  path: string,
  init?: RequestInit,
): Promise<{ data: T; status: number; headers: Headers }> {
  const res = await fetch(resolvePublicApiUrl(path), init);
  const body = [204, 205, 304].includes(res.status) ? null : await res.text();
  const data = (body ? JSON.parse(body) : {}) as T;
  return { data, status: res.status, headers: res.headers };
}

export async function fetchRelationshipMasters(
  options?: RequestInit,
): Promise<getMastersRelationshipsResponse> {
  if (!getPublicApiBaseUrl()) {
    return getMastersRelationships(options);
  }
  return fetchJsonAtUrl(getGetMastersRelationshipsUrl(), {
    ...options,
    method: "GET",
  }) as Promise<getMastersRelationshipsResponse>;
}

export async function fetchOccasionMasters(
  options?: RequestInit,
): Promise<getMastersOccasionsResponse> {
  if (!getPublicApiBaseUrl()) {
    return getMastersOccasions(options);
  }
  return fetchJsonAtUrl(getGetMastersOccasionsUrl(), {
    ...options,
    method: "GET",
  }) as Promise<getMastersOccasionsResponse>;
}

export async function fetchSemanticConfigMasters(
  options?: RequestInit,
): Promise<getSemanticConfigMastersResponse> {
  if (!getPublicApiBaseUrl()) {
    return getSemanticConfigMasters(options);
  }
  return fetchJsonAtUrl(getGetSemanticConfigMastersUrl(), {
    ...options,
    method: "GET",
  }) as Promise<getSemanticConfigMastersResponse>;
}

export async function fetchFeatureRuleMasters(
  options?: RequestInit,
): Promise<getFeatureRuleMastersResponse> {
  if (!getPublicApiBaseUrl()) {
    return getFeatureRuleMasters(options);
  }
  return fetchJsonAtUrl(getGetFeatureRuleMastersUrl(), {
    ...options,
    method: "GET",
  }) as Promise<getFeatureRuleMastersResponse>;
}

export async function postRecommendationRun(
  request: RecommendationRunRequest,
  options?: RequestInit,
): Promise<runRecommendationResponse> {
  if (!getPublicApiBaseUrl()) {
    return runRecommendation(request, options);
  }
  return fetchJsonAtUrl(getRunRecommendationUrl(), {
    ...options,
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    body: JSON.stringify(request),
  }) as Promise<runRecommendationResponse>;
}
