import { SESSION_STORAGE_KEY } from "./constants";

function createSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `sess_${crypto.randomUUID()}`;
  }
  return `sess_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
}

/**
 * MVP 匿名 Feedback 用。PII を含めない sessionId を sessionStorage に保持する。
 */
export function getOrCreateFeedbackSessionId(): string {
  if (typeof window === "undefined") {
    return createSessionId();
  }
  try {
    const existing = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (existing && existing.startsWith("sess_")) {
      return existing;
    }
    const created = createSessionId();
    window.sessionStorage.setItem(SESSION_STORAGE_KEY, created);
    return created;
  } catch {
    return createSessionId();
  }
}
