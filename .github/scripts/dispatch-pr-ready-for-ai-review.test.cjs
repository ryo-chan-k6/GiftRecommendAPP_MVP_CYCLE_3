"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const dispatch = require("./dispatch-pr-ready-for-ai-review.cjs");

test("buildClientPayload: ready_for_ai_reviewを正規化する", () => {
  const payload = dispatch.buildClientPayload({
    prNumber: 10,
    fixOutcome: "ready_for_ai_review",
  });
  assert.equal(payload.pr_number, "10");
  assert.equal(payload.fix_outcome, "ready_for_ai_review");
});

test("buildClientPayload: 不正なfix_outcomeは拒否する", () => {
  assert.throws(
    () => dispatch.buildClientPayload({ prNumber: 10, fixOutcome: "invalid" }),
    /Invalid fix_outcome/,
  );
});

test("dispatchPrReadyForAiReview: dry_runではAPIを呼ばない", async () => {
  let called = 0;
  const result = await dispatch.dispatchPrReadyForAiReview({
    repository: "o/r",
    prNumber: 10,
    fixOutcome: "ready_for_ai_review",
    token: "t",
    dryRun: true,
    fetchImpl: async () => {
      called += 1;
    },
  });
  assert.equal(result.ok, true);
  assert.equal(result.eventType, "fix_ready_for_ai_review");
  assert.equal(called, 0);
});
