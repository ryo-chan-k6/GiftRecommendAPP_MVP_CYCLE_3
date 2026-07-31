import type { RecoClientConfig, RecoTraceContext } from "./types.js";

const RECO_BASE_URL_ENV = "RECO_BASE_URL";
const RECO_INTERNAL_API_KEY_ENV = "RECO_INTERNAL_API_KEY";
const RECO_REQUEST_TIMEOUT_MS_ENV = "RECO_REQUEST_TIMEOUT_MS";

/** reco hard timeout (8,000ms) 以上を確保する api→reco HTTP timeout のデフォルト。 */
export const DEFAULT_RECO_REQUEST_TIMEOUT_MS = 9_000;

export const RECO_INTERNAL_API_KEY_HEADER = "X-Internal-Api-Key";
export const RECO_TRACE_ID_HEADER = "X-Trace-Id";
export const RECO_REQUEST_ID_HEADER = "X-Request-Id";

/** Resolve reco client settings from environment variable names only (no secret values). */
export function resolveRecoClientConfig(
  env: NodeJS.ProcessEnv = process.env,
): RecoClientConfig {
  const baseUrl = env[RECO_BASE_URL_ENV]?.trim() ?? "";
  const apiKey = env[RECO_INTERNAL_API_KEY_ENV]?.trim();
  const timeoutRaw = env[RECO_REQUEST_TIMEOUT_MS_ENV]?.trim();
  const timeoutMs =
    timeoutRaw === undefined || timeoutRaw === ""
      ? DEFAULT_RECO_REQUEST_TIMEOUT_MS
      : Number.parseInt(timeoutRaw, 10);

  return {
    baseUrl,
    apiKey: apiKey === "" ? undefined : apiKey,
    timeoutMs:
      Number.isFinite(timeoutMs) && timeoutMs > 0
        ? timeoutMs
        : DEFAULT_RECO_REQUEST_TIMEOUT_MS,
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

/** Merge Internal API Key and trace headers for Internal Reco API calls. */
export function buildRecoFetchInit(
  config: RecoClientConfig,
  init: RequestInit = {},
  trace?: RecoTraceContext,
): RequestInit {
  const headers = new Headers(init.headers);

  if (config.apiKey !== undefined) {
    headers.set(RECO_INTERNAL_API_KEY_HEADER, config.apiKey);
  }

  if (trace?.traceId !== undefined && trace.traceId.trim() !== "") {
    headers.set(RECO_TRACE_ID_HEADER, trace.traceId);
  }

  if (trace?.requestId !== undefined && trace.requestId.trim() !== "") {
    headers.set(RECO_REQUEST_ID_HEADER, trace.requestId);
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

export function resolveRecoRequestTimeoutMs(
  config: RecoClientConfig,
): number {
  return config.timeoutMs ?? DEFAULT_RECO_REQUEST_TIMEOUT_MS;
}
