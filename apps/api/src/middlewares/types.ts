/** OpenAPI ErrorDetail に整合する Validation 詳細。 */
export interface ErrorDetail {
  field: string;
  message: string;
}

/** OpenAPI ErrorResponse に整合する Phase4a 骨格型。 */
export interface ErrorResponseBody {
  error: {
    code: string;
    message: string;
    details?: ErrorDetail[];
    retryable: boolean;
  };
  meta: RequestMeta;
}

/** 横断追跡・リクエスト識別（API設計方針 §8.2 / common.yaml Meta）。 */
export interface RequestMeta {
  traceId: string;
  requestId: string;
}
