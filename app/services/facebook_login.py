"""Engine 1 Part A, part 1: the Facebook door.

Adam's spec (docs/engines/engine-1-brain.md, 22 Nov) makes "Log in with Facebook" the way in:
one pop-up for new and returning clients, a Terms box that must be ticked before the button
works, and the same Facebook account always landing on the same Resmara account.

The email/password form stays as a fallback until Meta's App Review approves the ``email``
permission; after that the same code path serves customers with nothing else to build. That
gate is stated on screen rather than hidden.

What lives here, so the router stays readable:

  * signed ``state`` (HMAC with SECRET_KEY) carrying the consent facts, so a browser cannot
    invent "they ticked the box" on the way back from Facebook;
  * the code -> token exchange and the /me read, against the same Graph base the rest of the
    app uses (a mock server in tests);
  * one-time login tickets: the JWT never rides in a URL that ends up in a referrer log.
"""
import base64
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timezone

import httpx

from app.core.config import settings

# Consent wording is versioned so a change to the Terms can ask returning clients again.
TERMS_VERSION = os.getenv("RESMARA_TERMS_VERSION", "2026-11-22").strip() or "2026-11-22"
STATE_TTL_SECONDS = 15 * 60
TICKET_TTL_MINUTES = 10


def login_configured() -> bool:
    """True when this deploy can actually talk to Facebook on the customer's behalf."""
    return bool(getattr(settings, "META_CLIENT_ID", "") and getattr(settings, "META_CLIENT_SECRET", ""))


def login_redirect_uri() -> str:
    return (getattr(settings, "FB_LOGIN_REDIRECT_URI", "") or
            settings.PUBLIC_BASE_URL + "/api/auth/facebook/callback")


def login_scopes() -> str:
    # Facebook Login for an account needs nothing beyond the identity; the Page/Instagram/ad
    # permissions are asked for in the same dialog only once App Review has them.
    return getattr(settings, "FB_LOGIN_SCOPES", "") or "public_profile,email"


def graph_base() -> str:
    return settings.graph_base


def _mac(raw: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), raw.encode(), "sha256").hexdigest()


def make_state(terms_version: str) -> str:
    """Signed state: names the consent it was issued under and when."""
    payload = {"n": secrets.token_urlsafe(8), "v": terms_version, "ts": int(time.time())}
    raw = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    return raw + "." + _mac(raw)


def read_state(state: str) -> dict:
    """Refuse anything this server did not sign, and anything old enough to replay."""
    try:
        raw, mac = (state or "").split(".", 1)
    except ValueError:
        raise ValueError("bad state")
    if not hmac.compare_digest(_mac(raw), mac):
        raise ValueError("state does not match this app")
    pad = "=" * (-len(raw) % 4)
    payload = json.loads(base64.urlsafe_b64decode(raw + pad))
    if int(time.time()) - int(payload.get("ts") or 0) > STATE_TTL_SECONDS:
        raise ValueError("state has expired - start the sign-in again")
    return payload


def dialog_url(state: str) -> str:
    params = {
        "client_id": settings.META_CLIENT_ID,
        "redirect_uri": login_redirect_uri(),
        "scope": login_scopes(),
        "state": state,
        "response_type": "code",
    }
    return f"https://www.facebook.com/{settings.META_API_VERSION}/dialog/oauth?" + "&".join(
        f"{k}={httpx.QueryParams({k: v})[k]}" for k, v in params.items())


async def exchange_code(code: str) -> dict:
    """Trade the one-time code for a user token. Raises ValueError with Meta's own reason."""
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(f"{graph_base()}/oauth/access_token", params={
            "client_id": settings.META_CLIENT_ID,
            "client_secret": settings.META_CLIENT_SECRET,
            "redirect_uri": login_redirect_uri(),
            "code": code,
        })
    data = r.json() if r.content else {}
    if r.status_code >= 400 or not data.get("access_token"):
        reason = (data.get("error") or {}).get("message") or f"HTTP {r.status_code}"
        raise ValueError(f"Facebook refused the sign-in: {reason}")
    return data


async def read_me(access_token: str) -> dict:
    """Who just signed in, according to Meta - never according to the browser."""
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(f"{graph_base()}/me", params={
            "fields": "id,name,email", "access_token": access_token})
    data = r.json() if r.content else {}
    if r.status_code >= 400 or not data.get("id"):
        reason = (data.get("error") or {}).get("message") or f"HTTP {r.status_code}"
        raise ValueError(f"Facebook would not say who signed in: {reason}")
    return data


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
