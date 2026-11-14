"""Where listing photos live: Cloudflare R2 when it is configured, the database row otherwise.

Why R2: a campaign stores roughly 50 MB of photos, and Render's Postgres charges $0.30/GB-month
for those bytes while a 1 GB database is full after about twenty campaigns. R2's free tier is
10 GB of storage, 1M writes and 10M reads a month with no egress charge, at $0.015/GB-month
beyond it — so the switch costs nothing until roughly 200 campaigns are up, and about a tenth of
a cent per campaign a year after that.

The app must keep working with no object store at all. If the R2 environment is incomplete, or a
PUT fails for any reason, the bytes stay in the database row exactly as they do today and the
photo still shows. An object store is a cost optimisation here, never a dependency: a failed
upload must never lose an agent's listing photos.
"""
from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)

# Everything a deployment needs to use R2. The public base URL is separate because a bucket has
# to be exposed on a domain (or its r2.dev address) before a browser can load an image from it.
ENV_KEYS = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def enabled() -> bool:
    """True when every credential for R2 is present. Read on every call so a redeploy with new
    environment variables takes effect without touching code."""
    return all(_env(k) for k in ENV_KEYS)


def mode() -> str:
    return "r2" if enabled() else "database"


def public_base() -> str:
    return _env("R2_PUBLIC_BASE_URL").rstrip("/")


def note() -> str:
    """One sentence for the console: where photos are, and what that costs."""
    if not enabled():
        missing = [k for k in ENV_KEYS if not _env(k)]
        return ("Photos are stored in the database (add %s to move them to Cloudflare R2, which "
                "is free to 10 GB)." % ", ".join(missing))
    if not public_base():
        return ("R2 credentials are set but R2_PUBLIC_BASE_URL is empty, so uploaded images "
                "cannot be served; photos stay in the database until it is set.")
    return "Photos are stored in Cloudflare R2 (free to 10 GB, then $0.015/GB-month)."


def key_for(filename: str) -> str:
    return "campaigns/%s" % filename.strip().lstrip("/")


def public_url(key: str) -> str:
    base = public_base()
    return "%s/%s" % (base, key) if base else ""


def _client():
    """A boto3 S3 client pointed at R2, or None when anything about it is missing."""
    if not enabled() or not public_base():
        return None
    try:
        import boto3  # imported here so the app runs without the dependency installed
        from botocore.config import Config
    except ImportError:
        log.warning("R2 is configured but boto3 is not installed; photos stay in the database")
        return None
    account = _env("R2_ACCOUNT_ID")
    return boto3.client(
        "s3",
        endpoint_url="https://%s.r2.cloudflarestorage.com" % account,
        aws_access_key_id=_env("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=_env("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
        config=Config(signature_version="s3v4", retries={"max_attempts": 2, "mode": "standard"}),
    )


def put(filename: str, data: bytes, content_type: str = "application/octet-stream") -> str | None:
    """Upload one file and return its public URL, or None to say "keep the bytes in the row".

    None is the safe answer: every caller treats it as "store it the old way", so a misconfigured
    bucket degrades to today's behaviour instead of dropping a photo.
    """
    if not data:
        return None
    client = _client()
    if client is None:
        return None
    key = key_for(filename)
    try:
        client.put_object(Bucket=_env("R2_BUCKET"), Key=key, Body=data,
                          ContentType=content_type or "application/octet-stream",
                          CacheControl="public, max-age=31536000, immutable")
    except Exception as exc:  # noqa: BLE001 - any failure means "fall back to the database"
        log.warning("R2 upload failed for %s (%s: %s); keeping the bytes in the database",
                    key, type(exc).__name__, exc)
        return None
    return public_url(key) or None


def delete(filename: str) -> bool:
    """Remove the object for a file, if R2 is in use. Never raises."""
    client = _client()
    if client is None:
        return False
    try:
        client.delete_object(Bucket=_env("R2_BUCKET"), Key=key_for(filename))
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("R2 delete failed for %s (%s)", filename, type(exc).__name__)
        return False


def status() -> dict:
    """What the console shows about photo storage — no secrets, just which mode is live."""
    return {
        "mode": mode(),
        "enabled": enabled(),
        "bucket": _env("R2_BUCKET") or None,
        "public_base": public_base() or None,
        "missing": [k for k in ENV_KEYS if not _env(k)],
        "note": note(),
    }
