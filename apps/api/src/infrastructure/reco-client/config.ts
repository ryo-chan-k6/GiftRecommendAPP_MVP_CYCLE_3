import type { RecoClientConfig } from "./types.js";

const RECO_BASE_URL_ENV = "RECO_BASE_URL";
const RECO_INTERNAL_API_KEY_ENV = "RECO_INTERNAL_API_KEY";

/** Resolve reco client settings from environment variable names only (no secret values). */
export function resolveRecoClientConfig(
  env: NodeJS.ProcessEnv = process.env,
): RecoClientConfig {
  const baseUrl = env[RECO_BASE_URL_ENV]?.trim() ?? "";
  const apiKey = env[RECO_INTERNAL_API_KEY_ENV]?.trim();

  return {
    baseUrl,
    apiKey: apiKey === "" ? undefined : apiKey,
  };
}

/** Build absolute Internal Reco API URL from base URL and generated path. */
export function buildRecoRequestUrl(baseUrl: string, path: string): string {
  const normalizedBase = baseUrl.replace(/\/$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  if (normalizedBase === "") {
    return normalizedPath;
  }

  return `${normalizedBase}${normalizedPath}`;
}

/** Merge Authorization header for Internal Reco API calls. */
export function buildRecoFetchInit(
  config: RecoClientConfig,
  init: RequestInit = {},
): RequestInit {
  const headers = new Headers(init.headers);

  if (config.apiKey !== undefined) {
    headers.set("Authorization", `Bearer ${config.apiKey}`);
  }

  return {
    ...init,
    headers,
  };
}

/** Redact reco internal API key before logging. */
export function maskRecoApiKey(apiKey: string | undefined): string {
  if (apiKey === undefined || apiKey.trim() === "") {
    return "";
  }

  return "***REDACTED***";
}
