"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const {
  shouldPromoteFromBacklogToTodo,
  normalizePlannedStartYmd,
  isBacklogStatus,
  todayJstYmd,
} = require("./planned-start-status-policy.cjs");

test("normalizePlannedStartYmd: ISO を先頭10文字で切る", () => {
  assert.equal(normalizePlannedStartYmd("2026-05-13T00:00:00Z"), "2026-05-13");
  assert.equal(normalizePlannedStartYmd("2026-05-13"), "2026-05-13");
});

test("normalizePlannedStartYmd: 空は null", () => {
  assert.equal(normalizePlannedStartYmd(null), null);
  assert.equal(normalizePlannedStartYmd(""), null);
  assert.equal(normalizePlannedStartYmd("   "), null);
});

test("isBacklogStatus: 大文字小文字無視", () => {
  assert.equal(isBacklogStatus("Backlog"), true);
  assert.equal(isBacklogStatus("BACKLOG"), true);
  assert.equal(isBacklogStatus("Todo"), false);
});

test("shouldPromote: Backlog かつ予定日が当日以前 → true", () => {
  assert.equal(
    shouldPromoteFromBacklogToTodo({
      statusOptionName: "Backlog",
      plannedStartYmd: "2026-05-10",
      todayYmd: "2026-05-13",
    }),
    true,
  );
  assert.equal(
    shouldPromoteFromBacklogToTodo({
      statusOptionName: "Backlog",
      plannedStartYmd: "2026-05-13",
      todayYmd: "2026-05-13",
    }),
    true,
  );
});

test("shouldPromote: 予定日が未来 → false", () => {
  assert.equal(
    shouldPromoteFromBacklogToTodo({
      statusOptionName: "Backlog",
      plannedStartYmd: "2026-05-14",
      todayYmd: "2026-05-13",
    }),
    false,
  );
});

test("shouldPromote: Status が Todo なら false", () => {
  assert.equal(
    shouldPromoteFromBacklogToTodo({
      statusOptionName: "Todo",
      plannedStartYmd: "2026-01-01",
      todayYmd: "2026-05-13",
    }),
    false,
  );
});

test("shouldPromote: Planned Start 欠落 → false", () => {
  assert.equal(
    shouldPromoteFromBacklogToTodo({
      statusOptionName: "Backlog",
      plannedStartYmd: null,
      todayYmd: "2026-05-13",
    }),
    false,
  );
});

test("todayJstYmd: 形式が YYYY-MM-DD", () => {
  const s = todayJstYmd(new Date("2026-05-12T16:00:00.000Z"));
  assert.ok(/^\d{4}-\d{2}-\d{2}$/.test(s));
});
