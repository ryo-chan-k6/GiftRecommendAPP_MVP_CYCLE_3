"""Surface GRS-REC-* resolution (MOD-RECO-024 §8.3)."""

from __future__ import annotations

from reco.domain.errors import RecoDomainError

from .constants import (
    LLM_MODULE_SURFACE_CODES,
    MODULE_SURFACE_ERROR_CODES,
    SURFACE_ERROR_CODE_CONFIG,
    SURFACE_ERROR_CODE_RETRIEVAL,
    SURFACE_ERROR_CODE_RUN_CONFLICT,
    SURFACE_ERROR_CODE_TIMEOUT,
    SURFACE_ERROR_CODE_UNKNOWN,
    USER_MEANING_MODULE_IDS,
)


def _code_prefix(code: str, prefix: str) -> bool:
    return code.startswith(prefix)


def _is_surface_code(code: str) -> bool:
    return code.startswith("GRS-REC-")


def _extract_code_from_cause(cause: BaseException | None) -> str | None:
    if cause is None:
        return None
    code = getattr(cause, "error_code", None)
    if isinstance(code, str) and code:
        return code
    return None


def _resolve_from_detail_code(detail_code: str, *, module_id: str) -> str | None:
    if _code_prefix(detail_code, "GRS-CFG-"):
        return SURFACE_ERROR_CODE_CONFIG
    if _code_prefix(detail_code, "GRS-LLM-"):
        if module_id in USER_MEANING_MODULE_IDS:
            return LLM_MODULE_SURFACE_CODES.get(module_id)
        return MODULE_SURFACE_ERROR_CODES.get(module_id)
    if _code_prefix(detail_code, "GRS-DB-"):
        if detail_code == "GRS-DB-005":
            return SURFACE_ERROR_CODE_RUN_CONFLICT
        return MODULE_SURFACE_ERROR_CODES.get(module_id)
    if _code_prefix(detail_code, "GRS-EXT-") or _code_prefix(detail_code, "GRS-RAW-"):
        return SURFACE_ERROR_CODE_RETRIEVAL
    if detail_code == SURFACE_ERROR_CODE_TIMEOUT:
        return SURFACE_ERROR_CODE_TIMEOUT
    if detail_code == SURFACE_ERROR_CODE_RUN_CONFLICT:
        return SURFACE_ERROR_CODE_RUN_CONFLICT
    if _is_surface_code(detail_code):
        return detail_code
    return None


def resolve_surface_code(
    *,
    module_id: str,
    error_code: str | None,
    cause: BaseException | None,
) -> tuple[str, str | None]:
    """Return surface code and optional detail code for Error Log JSON."""
    cause_code = _extract_code_from_cause(cause)
    detail_code: str | None = None

    if cause_code and _is_surface_code(cause_code):
        detail = getattr(cause, "detail_error_code", None) if cause is not None else None
        if detail is None and error_code and not _is_surface_code(error_code):
            detail = error_code
        return cause_code, detail if isinstance(detail, str) else None

    if isinstance(cause, RecoDomainError) and not _is_surface_code(cause.error_code):
        detail_code = cause.error_code
    elif cause_code:
        detail_code = cause_code
    elif error_code:
        detail_code = error_code

    if detail_code:
        resolved = _resolve_from_detail_code(detail_code, module_id=module_id)
        if resolved is not None:
            stored_detail = detail_code if not _is_surface_code(detail_code) else None
            if stored_detail is None and error_code and not _is_surface_code(error_code):
                stored_detail = error_code
            return resolved, stored_detail

    if error_code and _is_surface_code(error_code):
        return error_code, None

    if cause is not None and not detail_code:
        fallback = MODULE_SURFACE_ERROR_CODES.get(module_id)
        if fallback is not None:
            return fallback, None

    if module_id in MODULE_SURFACE_ERROR_CODES:
        return MODULE_SURFACE_ERROR_CODES[module_id], detail_code if detail_code and not _is_surface_code(detail_code) else None

    return SURFACE_ERROR_CODE_UNKNOWN, detail_code if detail_code and not _is_surface_code(detail_code) else None
