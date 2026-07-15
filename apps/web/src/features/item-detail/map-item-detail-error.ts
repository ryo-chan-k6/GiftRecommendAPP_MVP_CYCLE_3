import {
  ERROR_MESSAGE_BAD_REQUEST,
  ERROR_MESSAGE_FETCH,
  ERROR_MESSAGE_INACTIVE,
  ERROR_MESSAGE_NOT_FOUND,
  ERROR_TITLE_BAD_REQUEST,
  ERROR_TITLE_FETCH,
  ERROR_TITLE_INACTIVE,
  ERROR_TITLE_NOT_FOUND,
} from "./constants";

export type ItemDetailErrorKind =
  | "not_found"
  | "inactive"
  | "bad_request"
  | "fetch_failed";

export type ItemDetailUiError = {
  kind: ItemDetailErrorKind;
  title: string;
  message: string;
  retryable: boolean;
  alertVariant: "warning" | "error" | "info";
};

function readErrorCode(data: unknown): string | undefined {
  if (!data || typeof data !== "object") {
    return undefined;
  }
  const error = (data as { error?: { code?: unknown } }).error;
  return typeof error?.code === "string" ? error.code : undefined;
}

/**
 * API-PUB-003 / 画面仕様 §11.4・§13 に沿って UI エラーへ写像する。
 * HTTP status や error.code の生値はユーザー向けに出さない。
 */
export function mapItemDetailError(
  status: number | null,
  data?: unknown,
): ItemDetailUiError {
  const code = readErrorCode(data);

  if (status === 404 || code === "GRS-ITM-001") {
    return {
      kind: "not_found",
      title: ERROR_TITLE_NOT_FOUND,
      message: ERROR_MESSAGE_NOT_FOUND,
      retryable: false,
      alertVariant: "warning",
    };
  }

  if (status === 422 || code === "GRS-ITM-002") {
    return {
      kind: "inactive",
      title: ERROR_TITLE_INACTIVE,
      message: ERROR_MESSAGE_INACTIVE,
      retryable: false,
      alertVariant: "warning",
    };
  }

  if (status === 400 || code === "GRS-REQ-001") {
    return {
      kind: "bad_request",
      title: ERROR_TITLE_BAD_REQUEST,
      message: ERROR_MESSAGE_BAD_REQUEST,
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
