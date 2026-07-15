import { test } from "node:test";
import assert from "node:assert/strict";

import {
  deriveNgKeywordsFromText,
  enrichRecommendationRequestForReco,
} from "../../../../src/app/recommendations/ng-normalize.js";
import type { RecommendationRunRequest } from "../../../../src/app/recommendations/types.js";

test("deriveNgKeywordsFromText maps アルコールはNG to アルコール", () => {
  assert.deepEqual(deriveNgKeywordsFromText("アルコールはNG"), ["アルコール"]);
});

test("deriveNgKeywordsFromText returns empty for blank", () => {
  assert.deepEqual(deriveNgKeywordsFromText(undefined), []);
  assert.deepEqual(deriveNgKeywordsFromText("  "), []);
});

test("enrichRecommendationRequestForReco attaches ngKeywords for reco", () => {
  const request: RecommendationRunRequest = {
    relationship: { relationshipCode: "boss" },
    occasion: { occasionCode: "thanks" },
    ngCondition: { ngText: "アルコールはNG" },
    execution: {
      mode: "ui",
      topK: 10,
      candidateLimit: 50,
      includeReason: true,
      includeDebugInfo: false,
    },
  };

  const enriched = enrichRecommendationRequestForReco(request);
  assert.deepEqual(enriched.ngCondition, {
    ngText: "アルコールはNG",
    ngKeywords: ["アルコール"],
  });
  // 元の request は変更しない
  assert.deepEqual(request.ngCondition, { ngText: "アルコールはNG" });
});
