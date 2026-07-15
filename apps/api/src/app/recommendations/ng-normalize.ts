import type { NgConditionInput, RecommendationRunRequest } from "./types.js";

/** 「はNG」「禁止」等の接尾辞を剥がす。 */
const NG_SUFFIX_PATTERN =
  /(?:は|が|を|の)?(?:NG|ＮＧ|ng|禁止|不可|ダメ|だめ|避けたい|避けて(?:ほしい|下さい|ください)|不要)(?:[。．.!！]?)*$/;

/** 既知ヒント（部分含有で拾う）。 */
const KNOWN_NG_HINT_TOKENS = [
  "アルコール",
  "ワイン",
  "ビール",
  "日本酒",
  "お酒",
] as const;

/**
 * Public `ngText` から INT-002 向け `ngKeywords` を派生する（MOD-RECO-012: api 正本）。
 *
 * 例: 「アルコールはNG」→「アルコール」
 */
export function deriveNgKeywordsFromText(ngText: string | undefined): string[] {
  const raw = ngText?.trim() ?? "";
  if (!raw) {
    return [];
  }

  const keywords: string[] = [];
  const cleaned = raw
    .replace(NG_SUFFIX_PATTERN, "")
    .replace(/^[ 　、。．，,・]+|[ 　、。．，,・]+$/g, "")
    .trim();
  if (cleaned) {
    keywords.push(cleaned);
  }

  for (const token of KNOWN_NG_HINT_TOKENS) {
    if (raw.includes(token) && !keywords.includes(token)) {
      keywords.push(token);
    }
  }

  if (keywords.length === 0) {
    keywords.push(raw);
  }

  return dedupePreserveOrder(keywords);
}

function dedupePreserveOrder(values: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const value of values) {
    if (seen.has(value)) {
      continue;
    }
    seen.add(value);
    result.push(value);
  }
  return result;
}

export type EnrichedNgCondition = NgConditionInput & {
  ngKeywords?: string[];
  ngCategories?: string[];
};

/** reco INT-002 向けに ngKeywords を付与した Request を返す（永続化列は変更しない）。 */
export function enrichRecommendationRequestForReco(
  request: RecommendationRunRequest,
): RecommendationRunRequest & { ngCondition?: EnrichedNgCondition } {
  const ng = request.ngCondition;
  if (ng === undefined) {
    return request;
  }

  const derived = deriveNgKeywordsFromText(ng.ngText);
  if (derived.length === 0) {
    return request;
  }

  const enrichedNg: EnrichedNgCondition = {
    ...ng,
    ngKeywords: derived,
  };

  return {
    ...request,
    ngCondition: enrichedNg,
  };
}
