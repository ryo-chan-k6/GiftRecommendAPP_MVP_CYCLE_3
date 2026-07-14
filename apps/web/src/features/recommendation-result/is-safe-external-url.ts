/**
 * 外部EC遷移用。javascript: 等を拒否し、http(s) のみ許可する。
 */
export function isSafeExternalUrl(url: string | undefined): boolean {
  if (!url) {
    return false;
  }
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:";
  } catch {
    return false;
  }
}
