#!/usr/bin/env python3
"""Minimal Supabase Storage (S3-compatible) live connectivity probe (Issue #1617).

Usage (from repo root or apps/batch):

  set -a && source /path/to/.env && set +a
  cd apps/batch
  uv run python ../../scripts/batch/object_storage_live_verify.py --live-object-storage \\
    --output-dir ../../scripts/batch/output-object-storage-live

Safety:
  - Refuses to call the network without --live-object-storage
    (or BATCH_OBJECT_STORAGE_LIVE=1/true/yes/on)
  - Never prints secret values
  - Limits to put + get (+ optional missing-key get) of a tiny probe object
  - Does not delete / list / multipart
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _mask(value: str | None) -> str:
    if value is None or value.strip() == "":
        return "(empty)"
    if len(value) <= 8:
        return "***REDACTED***"
    return f"{value[:2]}***REDACTED***{value[-2:]}"


def _mask_endpoint(endpoint: str | None) -> str:
    if endpoint is None or endpoint.strip() == "":
        return "(empty)"
    parsed = urlparse(endpoint.strip())
    if not parsed.scheme or not parsed.netloc:
        return "***REDACTED***"
    # host only; no query / credentials
    return f"{parsed.scheme}://{parsed.netloc}/…"


@dataclass
class CallResult:
    name: str
    ok: bool
    elapsed_ms: float
    error_code: str | None = None
    error_message: str | None = None
    http_status_hint: str | None = None
    observations: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


def _run_call(name: str, fn: Any) -> CallResult:
    started = time.perf_counter()
    try:
        details = fn()
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if not isinstance(details, dict):
            details = {"result": details}
        return CallResult(name=name, ok=True, elapsed_ms=elapsed_ms, details=details)
    except Exception as exc:  # noqa: BLE001 — probe must capture any failure shape
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        code = getattr(exc, "code", None)
        message = str(exc)
        # Never echo secrets if somehow present in message
        for secret_name in (
            "OBJECT_STORAGE_ACCESS_KEY",
            "OBJECT_STORAGE_SECRET_KEY",
        ):
            secret_val = os.environ.get(secret_name)
            if secret_val and secret_val in message:
                message = message.replace(secret_val, "***REDACTED***")
        return CallResult(
            name=name,
            ok=False,
            elapsed_ms=elapsed_ms,
            error_code=str(code) if code else type(exc).__name__,
            error_message=message[:500],
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Object Storage (S3-compatible) live verify (explicit flag only)"
    )
    parser.add_argument(
        "--live-object-storage",
        action="store_true",
        help="Required to perform real HTTP calls (or set BATCH_OBJECT_STORAGE_LIVE).",
    )
    parser.add_argument(
        "--bucket",
        default=None,
        help="Override OBJECT_STORAGE_BUCKET (default: env or raw-products).",
    )
    parser.add_argument(
        "--key-prefix",
        default="live-verify/1617",
        help="Object key prefix (default: live-verify/1617).",
    )
    parser.add_argument(
        "--region",
        default=None,
        help="SigV4 region (default: OBJECT_STORAGE_REGION or us-east-1).",
    )
    parser.add_argument(
        "--probe-missing",
        action="store_true",
        help="Also GET a non-existent key (expect None / not found).",
    )
    parser.add_argument(
        "--output-dir",
        default="scripts/batch/output-object-storage-live",
        help="Directory for report.json / summary.md (gitignored pattern).",
    )
    args = parser.parse_args(argv)

    # Import path setup before flag helpers
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "batch" / "src"))
    from batch.infrastructure.object_storage import (  # noqa: E402
        ObjectRef,
        ObjectStorageError,
        S3CompatibleObjectStorageClient,
        create_object_storage_client,
        missing_live_object_storage_credentials,
        resolve_live_object_storage_flag,
    )

    live = resolve_live_object_storage_flag(
        cli_live=args.live_object_storage,
        env_value=os.environ.get("BATCH_OBJECT_STORAGE_LIVE"),
    )
    if not live:
        print(
            "Refusing network calls: pass --live-object-storage explicitly "
            "(or set BATCH_OBJECT_STORAGE_LIVE=1). No HTTP request was made.",
            file=sys.stderr,
        )
        return 3

    access_key = (os.environ.get("OBJECT_STORAGE_ACCESS_KEY") or "").strip() or None
    secret_key = (os.environ.get("OBJECT_STORAGE_SECRET_KEY") or "").strip() or None
    endpoint = (os.environ.get("OBJECT_STORAGE_ENDPOINT") or "").strip() or None
    bucket = (
        (args.bucket or os.environ.get("OBJECT_STORAGE_BUCKET") or "raw-products").strip()
    )
    region = (
        args.region
        or (os.environ.get("OBJECT_STORAGE_REGION") or "").strip()
        or "us-east-1"
    )

    missing = missing_live_object_storage_credentials(
        access_key=access_key,
        secret_key=secret_key,
        endpoint=endpoint,
    )
    if missing:
        print(f"{missing} No HTTP request was made.", file=sys.stderr)
        return 2

    client = create_object_storage_client(
        access_key,
        secret_key,
        endpoint=endpoint,
        region=region,
        live=True,
    )
    if not isinstance(client, S3CompatibleObjectStorageClient):
        print(
            "create_object_storage_client(live=True) did not return "
            "S3CompatibleObjectStorageClient. No HTTP request was made.",
            file=sys.stderr,
        )
        return 2

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    probe_id = uuid.uuid4().hex[:12]
    key = f"{args.key_prefix.rstrip('/')}/{stamp}-{probe_id}.json"
    body = json.dumps(
        {
            "probe": "object_storage_live_verify",
            "issue": 1617,
            "stamp": stamp,
            "probe_id": probe_id,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    content_type = "application/json"
    ref = ObjectRef(bucket=bucket, key=key)

    calls: list[CallResult] = []

    def _put() -> dict[str, Any]:
        stored = client.put_object(ref, body=body, content_type=content_type)
        return {
            "bucket": stored.ref.bucket,
            "key": stored.ref.key,
            "content_type": stored.content_type,
            "body_len": len(stored.body),
        }

    def _get() -> dict[str, Any]:
        stored = client.get_object(ref)
        if stored is None:
            raise ObjectStorageError(
                code="GRS-RAW-004",
                message="get returned None for just-written key",
            )
        body_match = stored.body == body
        return {
            "bucket": stored.ref.bucket,
            "key": stored.ref.key,
            "content_type": stored.content_type,
            "body_len": len(stored.body),
            "body_match": body_match,
        }

    calls.append(_run_call("put_object", _put))
    calls.append(_run_call("get_object", _get))

    if args.probe_missing:
        missing_ref = ObjectRef(
            bucket=bucket,
            key=f"{args.key_prefix.rstrip('/')}/missing-{probe_id}.json",
        )

        def _get_missing() -> dict[str, Any]:
            stored = client.get_object(missing_ref)
            return {"returned_none": stored is None, "key": missing_ref.key}

        calls.append(_run_call("get_object.missing_key", _get_missing))
        if calls[-1].ok and calls[-1].details.get("returned_none") is not True:
            calls[-1].observations.append(
                "missing key did not return None — confirm bucket/path-style behavior"
            )

    put_ok = any(c.name == "put_object" and c.ok for c in calls)
    get_ok = any(c.name == "get_object" and c.ok for c in calls)
    body_match = False
    for c in calls:
        if c.name == "get_object" and c.ok:
            body_match = bool(c.details.get("body_match"))

    verdict = "Go" if put_ok and get_ok and body_match else ("Adjust" if put_ok or get_ok else "Block")

    report = {
        "task": "supabase-storage-live-verify",
        "issue": 1617,
        "client": "S3CompatibleObjectStorageClient",
        "connection_plan": "A",
        "product": "Supabase Storage",
        "credentials": {
            "OBJECT_STORAGE_ACCESS_KEY_present": bool(access_key),
            "OBJECT_STORAGE_SECRET_KEY_present": bool(secret_key),
            "OBJECT_STORAGE_ENDPOINT_present": bool(endpoint),
            "OBJECT_STORAGE_BUCKET": bucket,
            "OBJECT_STORAGE_ENDPOINT_masked": _mask_endpoint(endpoint),
            "OBJECT_STORAGE_ACCESS_KEY_masked": _mask(access_key),
            "OBJECT_STORAGE_SECRET_KEY_masked": _mask(secret_key),
            "region": region,
        },
        "request_params": {
            "key": key,
            "content_type": content_type,
            "body_len": len(body),
            "probe_missing": args.probe_missing,
        },
        "calls": [asdict(c) for c in calls],
        "summary": {
            "success_count": sum(1 for c in calls if c.ok),
            "failure_count": sum(1 for c in calls if not c.ok),
            "max_elapsed_ms": max((c.elapsed_ms for c in calls), default=0.0),
            "put_ok": put_ok,
            "get_ok": get_ok,
            "body_match": body_match,
            "verdict": verdict,
        },
        "notes": [
            "Probe object is left in the bucket (delete out of scope).",
            "Secrets must never be copied from report.json into docs/PR.",
        ],
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "report.json"
    summary_path = out_dir / "summary.md"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Object Storage live verify summary",
        "",
        f"- issue: #1617",
        f"- client: S3CompatibleObjectStorageClient",
        f"- bucket: {bucket}",
        f"- endpoint: {_mask_endpoint(endpoint)}",
        f"- region: {region}",
        f"- key: {key}",
        f"- verdict: {verdict}",
        f"- success: {report['summary']['success_count']} / {len(calls)}",
        "",
        "| name | ok | ms | error_code | notes |",
        "| ---- | -- | -- | ---------- | ----- |",
    ]
    for c in calls:
        note = c.error_message or ",".join(c.observations) or ""
        note = note.replace("|", "/")[:120]
        lines.append(
            f"| {c.name} | {c.ok} | {c.elapsed_ms:.1f} | {c.error_code or ''} | {note} |"
        )
    lines.append("")
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {report_path}")
    print(f"Wrote {summary_path}")
    print(
        f"verdict={verdict} "
        f"success={report['summary']['success_count']} "
        f"failure={report['summary']['failure_count']} "
        f"endpoint={_mask_endpoint(endpoint)} "
        f"bucket={bucket}"
    )
    return 0 if put_ok and get_ok and body_match else 1


if __name__ == "__main__":
    raise SystemExit(main())
