/**
 * Planned Start（日付）と Status（Backlog）に基づき Todo へ昇格するかの判定。
 * JST の暦日のみ比較（時刻は考慮しない）。
 */

function todayJstYmd(d = new Date()) {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Tokyo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(d);
}

function isBacklogStatus(name) {
  return String(name || "").trim().toLowerCase() === "backlog";
}

/** API の date 文字列を YYYY-MM-DD に正規化。解釈不能なら null */
function normalizePlannedStartYmd(raw) {
  if (raw == null || raw === "") return null;
  const s = String(raw).trim();
  const ymd = s.length >= 10 ? s.slice(0, 10) : s;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(ymd)) return null;
  return ymd;
}

/**
 * @param {{ statusOptionName: string | null | undefined, plannedStartYmd: string | null | undefined, todayYmd?: string }}} p
 * @returns {boolean}
 */
function shouldPromoteFromBacklogToTodo(p) {
  const today = p.todayYmd ?? todayJstYmd();
  const planned = normalizePlannedStartYmd(p.plannedStartYmd);
  if (!planned) return false;
  if (!isBacklogStatus(p.statusOptionName)) return false;
  return planned.localeCompare(today) <= 0;
}

module.exports = {
  todayJstYmd,
  isBacklogStatus,
  normalizePlannedStartYmd,
  shouldPromoteFromBacklogToTodo,
};
