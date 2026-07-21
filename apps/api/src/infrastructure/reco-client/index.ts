export {
  buildRecoFetchInit,
  buildRecoRequestUrl,
  DEFAULT_RECO_REQUEST_TIMEOUT_MS,
  maskRecoApiKey,
  RECO_INTERNAL_API_KEY_HEADER,
  RECO_REQUEST_ID_HEADER,
  RECO_TRACE_ID_HEADER,
  resolveRecoClientConfig,
  resolveRecoRequestTimeoutMs,
} from "./config.js";
export {
  GeneratedRecoClient,
  RecoClient,
  ScaffoldRecoClient,
} from "./client.js";
export type {
  GeneratedRecoClientOptions,
  ScaffoldRecoClientOptions,
} from "./client.js";
export {
  assertRecoClientReady,
  mapRecoErrorResponse,
  mapRecoTransportError,
} from "./error-mapper.js";
export { isRecoError, RecoError, type RecoErrorCode } from "./errors.js";
export {
  parseRecoErrorResponse,
  toRecoHealth,
  toRecoRecommendationRunRequest,
  toRecoRecommendationRunResult,
} from "./mapper.js";
export { callGetRecoHealth, callRunRecoRecommendation } from "./transport.js";
export type { RecoFetch } from "./transport.js";
export type {
  RecoClientConfig,
  RecoHealth,
  RecoRecommendationRunInput,
  RecoRecommendationRunResult,
  RecoServiceStatus,
  RecoTraceContext,
} from "./types.js";
