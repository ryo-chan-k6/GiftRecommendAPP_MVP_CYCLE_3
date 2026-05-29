"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const dispatch = require("./dispatch-pr-review-status-sync.cjs");

test("buildClientPayload: review_resultを正規化する", () => {
  const payload = dispatch.buildClientPayload({
    prNumber: 275,
    reviewResult: "Human Reviewへ進行可",
  });
  assert.equal(payload.pr_number, "275");
  assert.equal(payload.review_result, "approve_for_human_review");
});

test("buildClientPayload: 無効なreview_resultは拒否する", () => {
  assert.throws(
    () => dispatch.buildClientPayload({ prNumber: 1, reviewResult: "invalid" }),
    /Invalid review_result/,
  );
});

test("dispatchPrReviewStatusSync: dry_runではAPIを呼ばない", async () => {
  let called = false;
  const result = await dispatch.dispatchPrReviewStatusSync({
    owner: "o",
    repo: "r",
    prNumber: 10,
    reviewResult: "approve_for_human_review",
    token: "test-token",
    dryRun: true,
    fetchImpl: async () => {
      called = true;
    },
  });
  assert.equal(result.ok, true);
  assert.equal(result.dryRun, true);
  assert.equal(called, false);
});

test("dispatchPrReviewStatusSync: repository_dispatchをPOSTする", async () => {
  const calls = [];
  const result = await dispatch.dispatchPrReviewStatusSync({
    repository: "o/r",
    prNumber: 12,
    reviewResult: "request_changes",
    token: "test-token",
    fetchImpl: async (url, options) => {
      calls.push({ url, options });
      return { ok: true, status: 204, async text() { return ""; } };
    },
  });
  assert.equal(result.ok, true);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, "https://api.github.com/repos/o/r/dispatches");
  const body = JSON.parse(calls[0].options.body);
  assert.equal(body.event_type, "ai_review_status_sync");
  assert.equal(body.client_payload.pr_number, "12");
  assert.equal(body.client_payload.review_result, "request_changes");
});
