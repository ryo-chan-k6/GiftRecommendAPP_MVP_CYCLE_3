"""Message masking for Error Log and RecoError (MOD-RECO-024 §12)."""

from __future__ import annotations

import re

_MASK_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)(authorization\s*:\s*bearer\s+)(\S+)"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(authorization\s*[:=]\s*)(\S+)"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(api[_-]?key\s*[:=]\s*)(\S+)"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(bearer\s+)(\S+)"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(cookie\s*[:=]\s*)(\S+)"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(session[_-]?token\s*[:=]\s*)(\S+)"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(password\s*[:=]\s*)(\S+)"), r"\1***REDACTED***"),
    (re.compile(r"(?i)(secret\s*[:=]\s*)(\S+)"), r"\1***REDACTED***"),
)


def mask_sensitive_text(value: str) -> str:
    """Remove secret-like substrings from free-form error text."""
    masked = value
    for pattern, replacement in _MASK_PATTERNS:
        masked = pattern.sub(replacement, masked)
    return masked
