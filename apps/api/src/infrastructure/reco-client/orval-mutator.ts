import { AsyncLocalStorage } from "node:async_hooks";
import {
  buildRecoFetchInit,
  buildRecoRequestUrl,
  resolveRecoRequestTimeoutMs,
} from "./config.js";
import type { RecoClientConfig, RecoTraceContext } from "./types.js";

export type RecoFetch = typeof fetch;

export type RecoFetchRuntime = {
  config: RecoClientConfig;
  trace?: RecoTraceContext;
  fetchImpl?: RecoFetch;
};

type RecoFetchResponse = {
  data: unknown;
  status: number;
  headers: Headers;
};

const recoFetchRuntime = new AsyncLocalStorage<RecoFetchRuntime>();

/** Run generated reco-client calls with per-request transport context. */
export function runWithRecoFetchRuntime<T>(
  runtime: RecoFetchRuntime,
  fn: () => Promise<T>,
): Promise<T> {
  return recoFetchRuntime.run(runtime, fn);
}

async function fetchWithTimeout(
  url: string,
  init: RequestInit,
  timeoutMs: number,
  fetchImpl: RecoFetch,
): Promise<Response> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetchImpl(url, {
      ...init,
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }
}

/** Orval custom mutator: base URL, Internal API Key, trace headers, timeout. */
export async function recoFetch<T extends RecoFetchResponse>(
  url: string,
  init: RequestInit = {},
): Promise<T> {
  const runtime = recoFetchRuntime.getStore();
  if (runtime === undefined) {
    throw new Error("recoFetch called outside runWithRecoFetchRuntime");
  }

  const fetchImpl = runtime.fetchImpl ?? fetch;
  const timeoutMs = resolveRecoRequestTimeoutMs(runtime.config);
  const requestInit = buildRecoFetchInit(runtime.config, init, runtime.trace);
  const absoluteUrl = buildRecoRequestUrl(runtime.config.baseUrl, url);
  const response = await fetchWithTimeout(
    absoluteUrl,
    requestInit,
    timeoutMs,
    fetchImpl,
  );
  const body = [204, 205, 304].includes(response.status)
    ? null
    : await response.text();
  const data = body ? JSON.parse(body) : {};

  return {
    data,
    status: response.status,
    headers: response.headers,
  } as T;
}
