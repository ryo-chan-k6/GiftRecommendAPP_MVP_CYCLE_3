import { QUERY_KEYS, SESSION_KEYS } from "./constants";
import {
  createEmptyFormValues,
  type RecommendationInputFormValues,
  type StoredRecommendationResult,
} from "./types";

function readSession(key: string): string {
  if (typeof window === "undefined") {
    return "";
  }
  try {
    return window.sessionStorage.getItem(key) ?? "";
  } catch {
    return "";
  }
}

function writeSession(key: string, value: string): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    if (value) {
      window.sessionStorage.setItem(key, value);
    } else {
      window.sessionStorage.removeItem(key);
    }
  } catch {
    // sessionStorage 不可時は復元を諦める（画面操作は継続可）
  }
}

export function readFormValuesFromLocation(
  searchParams: URLSearchParams,
): RecommendationInputFormValues {
  const topKRaw = searchParams.get(QUERY_KEYS.topK);
  const topKParsed = topKRaw ? Number(topKRaw) : Number.NaN;
  const topK =
    Number.isInteger(topKParsed) && topKParsed >= 1 && topKParsed <= 50
      ? topKParsed
      : 10;

  return createEmptyFormValues({
    relationshipCode: searchParams.get(QUERY_KEYS.relationshipCode) ?? "",
    occasionCode: searchParams.get(QUERY_KEYS.occasionCode) ?? "",
    budgetMin: searchParams.get(QUERY_KEYS.budgetMin) ?? "",
    budgetMax: searchParams.get(QUERY_KEYS.budgetMax) ?? "",
    preferredText: readSession(SESSION_KEYS.preferredText),
    nonPreferredText: readSession(SESSION_KEYS.nonPreferredText),
    ngText: readSession(SESSION_KEYS.ngText),
    topK,
  });
}

export function persistFormValues(values: RecommendationInputFormValues): void {
  writeSession(SESSION_KEYS.preferredText, values.preferredText);
  writeSession(SESSION_KEYS.nonPreferredText, values.nonPreferredText);
  writeSession(SESSION_KEYS.ngText, values.ngText);

  if (typeof window === "undefined") {
    return;
  }

  const params = new URLSearchParams();
  if (values.relationshipCode) {
    params.set(QUERY_KEYS.relationshipCode, values.relationshipCode);
  }
  if (values.occasionCode) {
    params.set(QUERY_KEYS.occasionCode, values.occasionCode);
  }
  if (values.budgetMin.trim()) {
    params.set(QUERY_KEYS.budgetMin, values.budgetMin.trim());
  }
  if (values.budgetMax.trim()) {
    params.set(QUERY_KEYS.budgetMax, values.budgetMax.trim());
  }
  if (values.topK !== 10) {
    params.set(QUERY_KEYS.topK, String(values.topK));
  }

  const query = params.toString();
  const nextUrl = query
    ? `${window.location.pathname}?${query}`
    : window.location.pathname;
  window.history.replaceState(null, "", nextUrl);
}

export function storeRecommendationResult(
  result: StoredRecommendationResult,
): void {
  writeSession(
    `${SESSION_KEYS.lastResultPrefix}${result.recommendationResultId}`,
    JSON.stringify(result),
  );
}

export function readRecommendationResult(
  resultId: string,
): StoredRecommendationResult | null {
  const raw = readSession(`${SESSION_KEYS.lastResultPrefix}${resultId}`);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as StoredRecommendationResult;
  } catch {
    return null;
  }
}
