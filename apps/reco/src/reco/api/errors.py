"""API layer exceptions and HTTP status resolution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorDetail:
    field: str
    message: str


@dataclass
class RecoApiError(Exception):
    """HTTP error propagated to clients with GRS-* code."""

    status_code: int
    error_code: str
    message: str
    details: list[ErrorDetail] | None = None


ERROR_MESSAGES: dict[str, str] = {
    "GRS-AUTH-001": "認証に失敗しました。",
    "GRS-AUTH-004": "認証情報が不足しています。",
    "GRS-REQ-001": "リクエスト内容を確認してください。",
    "GRS-REQ-002": "指定された条件では推薦を実行できません。",
    "GRS-REQ-006": "条件が厳しすぎるため推薦を実行できません。",
    "GRS-REC-002": "レコメンド処理に失敗しました。時間を置いて再度お試しください。",
    "GRS-REC-101": "レコメンド処理に時間がかかっています。時間を置いて再度お試しください。",
    "GRS-REC-201": "レコメンド処理の状態が不正です。再度お試しください。",
    "GRS-REC-999": "レコメンド処理で予期しないエラーが発生しました。",
    "GRS-COM-003": "現在サービスを利用できません。時間を置いて再度お試しください。",
}


def default_message(error_code: str) -> str:
    return ERROR_MESSAGES.get(
        error_code,
        "レコメンド処理に失敗しました。時間を置いて再度お試しください。",
    )


def resolve_http_status(error_code: str) -> int:
    """Map GRS-* codes to HTTP status (エラーコード定義書・契約仕様書 §8.1)."""
    if error_code.startswith("GRS-AUTH-"):
        if error_code in {"GRS-AUTH-002", "GRS-AUTH-003", "GRS-AUTH-005"}:
            return 403
        return 401
    if error_code.startswith("GRS-REQ-"):
        if error_code in {"GRS-REQ-002", "GRS-REQ-006"}:
            return 422
        return 400
    if error_code == "GRS-REC-101":
        return 504
    if error_code == "GRS-REC-201":
        return 409
    if error_code.startswith("GRS-LLM-"):
        return 504 if error_code == "GRS-LLM-101" else 502
    if error_code.startswith("GRS-DB-"):
        if error_code == "GRS-DB-005":
            return 409
        if error_code in {"GRS-DB-001", "GRS-DB-002"}:
            return 503
        return 500
    if error_code == "GRS-COM-003":
        return 503
    if error_code.startswith("GRS-REC-"):
        return 500
    return 500


def reco_error_from_code(
    error_code: str,
    *,
    message: str | None = None,
    details: list[ErrorDetail] | None = None,
) -> RecoApiError:
    return RecoApiError(
        status_code=resolve_http_status(error_code),
        error_code=error_code,
        message=message or default_message(error_code),
        details=details,
    )
