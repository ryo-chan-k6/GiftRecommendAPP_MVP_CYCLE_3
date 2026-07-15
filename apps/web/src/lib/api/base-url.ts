/**
 * Public API（apps/api）のベース URL。
 * 未設定時は同一オリジン相対パス（`/api/v1/...`）を使う。
 * secret は置かない（公開ベース URL のみ）。
 */
export function getPublicApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
  return raw.replace(/\/$/, "");
}

export function resolvePublicApiUrl(path: string): string {
  const base = getPublicApiBaseUrl();
  if (!base) {
    return path;
  }
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}
