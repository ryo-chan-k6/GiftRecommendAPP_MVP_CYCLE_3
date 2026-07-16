import {
  ERROR_MESSAGE_FETCH,
  ERROR_MESSAGE_NOT_FOUND,
  ERROR_MESSAGE_VALIDATION,
  ERROR_TITLE_FETCH,
  ERROR_TITLE_NOT_FOUND,
  ERROR_TITLE_VALIDATION,
} from "./constants";

export type FeedbackUiError = {
  kind: "validation" | "not_found" | "fetch_failed";
  title: string;
  message: string;
  retryable: boolean;
  alertVariant: "warning" | "error";
};

function readErrorCode(data: unknown): string | undefined {
  if (!data || typeof data !== "object") {
    return undefined;
  }
  const error = (data as { error?: { code?: unknown } }).error;
  return typeof error?.code === "string" ? error.code : undefined;
}

/**
 * API-PUB-004 / 画面仕様 §11.5・§13 に沿った UI エラー写像。
 */
export function mapFeedbackSubmitError(
  status: number | null,
  data?: unknown,
): FeedbackUiError {
  const code = readErrorCode(data);

  if (
    status === 400 ||
    code === "GRS-FDB-001" ||
    code === "GRS-FDB-004" ||
    code === "GRS-REQ-001"
  ) {
    return {
      kind: "validation",
      title: ERROR_TITLE_VALIDATION,
      message: ERROR_MESSAGE_VALIDATION,
      retryable: false,
      alertVariant: "warning",
    };
  }

  if (status === 404 || code === "GRS-FDB-002") {
    return {
      kind: "not_found",
      title: ERROR_TITLE_NOT_FOUND,
      message: ERROR_MESSAGE_NOT_FOUND,
      retryable: false,
      alertVariant: "warning",
    };
  }

  return {
    kind: "fetch_failed",
    title: ERROR_TITLE_FETCH,
    message: ERROR_MESSAGE_FETCH,
    retryable: true,
    alertVariant: "error",
  };
}
