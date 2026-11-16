"""The three numbers the console cannot count itself: ad spend, visitors, and heat-map sessions.

Why this module exists: the Marketing and Website pages were honest but empty - "not connected"
is the right answer when there is nobody to ask, and the wrong answer forever. Each reader here
talks to one third party, returns what it actually got, and on any failure returns
``(None, why)`` so the page can name the reason instead of printing a zero.

Three credentials, all optional, all read from the environment:
  * ``META_AD_ACCOUNT_ID`` + ``META_SYSTEM_TOKEN`` - Resmara's own ad account, for spend,
    impressions and clicks (Graph ``insights``). A customer's own ``AdAccount`` row is used
    first when one exists, so an agency account works without any env var.
  * ``GA4_PROPERTY_ID`` + (``GA4_SA_JSON`` service-account key, or ``GA4_TOKEN`` bearer) - visitors,
    new visitors, channels and top pages (Analytics Data API).
  * ``CLARITY_PROJECT_ID`` + ``CLARITY_TOKEN`` - sessions from the last 3 days (Clarity's Data
    Export API only exposes a live window, so the page must say "last 3 days", not "this month").

Nothing here logs a credential, and no reader raises: a page that cannot reach a third party is a
warn with a sentence, never a 500.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

log = logging.getLogger("resmara.analytics")

GRAPH_BASE = f"https://graph.facebook.com/{os.getenv('META_API_VERSION', 'v26.0')}"
GA4_TOKEN_URL = "https://oauth2.googleapis.com/token"
GA4_DATA_BASE = "https://analyticsdata.googleapis.com/v1beta"
GA4_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
CLARITY_BASE = "https://www.clarity.ms/export-data/api/v1/project-live-insights"

_GA4_CACHE: Dict[str, Any] = {"token": "", "expires": 0.0}


def _env(name: str) -> str:
    """Read a setting, accepting the RESMARA_-prefixed spelling the rest of the app uses.

    The service's other secrets are all RESMARA_*, so both spellings are accepted here rather than
    making somebody guess which one this page wants.
    """
    return (os.getenv(name) or os.getenv("RESMARA_" + name) or "").strip()


# --------------------------------------------------------------------------- Meta ad spend
def meta_credentials(account: Any = None) -> Tuple[str, str, str]:
    """The ad account and token to spend-report with: the account's own row first, then env.

    Returns ``(ad_account_id, token, why_not)`` - the reason is only filled when there is no
    credential at all, so the caller can put the sentence on the page.
    """
    if account is not None:
        token = ""
        try:
            token = (account.access_token or "").strip()     # decrypted property on AdAccount
        except Exception:                                    # noqa: BLE001 - a bad row is not a crash
            token = ""
        if token and (account.advertiser_id or "").strip():
            return account.advertiser_id.strip(), token, ""
    ad_account = _env("META_AD_ACCOUNT_ID")
    token = _env("META_SYSTEM_TOKEN")
    if ad_account and token:
        return ad_account, token, ""
    missing = [n for n, v in (("META_AD_ACCOUNT_ID", ad_account), ("META_SYSTEM_TOKEN", token)) if not v]
    return "", "", "Resmara's own Meta ad account is not connected (needs " + " + ".join(missing) + ")"


def meta_insights(account: Any, start: datetime, end: datetime) -> Dict[str, Any]:
    """Spend, impressions and clicks from the Graph API, plus a week-by-week series.

    Returns ``{"connected": bool, "spend_usd", "impressions", "clicks", "weeks": [...],
    "account_id", "why"}``. A week with no delivery comes back as a real ``0.0``, because Meta
    genuinely spent nothing; a failed call comes back as ``None`` and a reason.
    """
    ad_account, token, why = meta_credentials(account)
    out: Dict[str, Any] = {"connected": False, "spend_usd": None, "impressions": None,
                           "clicks": None, "weeks": [], "account_id": ad_account or None, "why": why}
    if not ad_account or not token:
        return out

    params = {
        "fields": "spend,impressions,clicks",
        "time_range": json.dumps({"since": start.date().isoformat(), "until": end.date().isoformat()}),
        "time_increment": "7",
        "access_token": token,
    }
    url = f"{GRAPH_BASE}/act_{ad_account.lstrip('act_')}/insights"
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.get(url, params=params)
        if response.status_code >= 400:
            detail = ""
            try:
                detail = ((response.json().get("error") or {}).get("message") or "")[:160]
            except Exception:                                # noqa: BLE001
                detail = response.text[:160]
            log.info("meta insights -> %s %s", response.status_code, detail)
            out["why"] = f"Meta answered {response.status_code}: {detail or 'no message'}"
            return out
        rows = (response.json() or {}).get("data") or []
    except Exception as exc:                                 # noqa: BLE001 - a check, not a crash
        log.info("meta insights failed: %s", exc)
        out["why"] = f"Meta could not be reached ({type(exc).__name__})"
        return out

    spend = impressions = clicks = 0.0
    weeks: List[Dict[str, Any]] = []
    for row in rows:
        row_spend = float(row.get("spend") or 0)
        row_imp = float(row.get("impressions") or 0)
        row_clicks = float(row.get("clicks") or 0)
        spend += row_spend
        impressions += row_imp
        clicks += row_clicks
        weeks.append({
            "start": row.get("date_start") or "",
            "spend_usd": round(row_spend, 2),
            "impressions": int(row_imp),
            "clicks": int(row_clicks),
            "signups": None,          # filled by the caller, which owns the database
        })
    out.update({
        "connected": True,
        "spend_usd": round(spend, 2),
        "impressions": int(impressions),
        "clicks": int(clicks),
        "weeks": weeks,
    })
    return out


# --------------------------------------------------------------------------- Google Analytics 4
def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _ga4_access_token() -> Tuple[str, str]:
    """A GA4 bearer token from a service-account key, or a ready-made one.

    ``GA4_SA_JSON`` is the path to (or the literal JSON of) a service-account key: the token is
    minted here with RS256 and cached until a minute before it expires. ``GA4_TOKEN`` is accepted
    as-is for a short-lived token pasted by hand. Returns ``(token, why_not)``.
    """
    ready = _env("GA4_TOKEN")
    if ready:
        return ready, ""
    raw = _env("GA4_SA_JSON")
    if not raw:
        return "", "Google Analytics is not connected (needs GA4_SA_JSON or GA4_TOKEN)"
    if _GA4_CACHE["token"] and _GA4_CACHE["expires"] > time.time() + 60:
        return _GA4_CACHE["token"], ""
    try:
        key = json.loads(open(raw).read()) if raw.startswith("/") else json.loads(raw)
        from typing import cast

        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

        now = int(time.time())
        header = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
        claims = _b64(json.dumps({
            "iss": key["client_email"],
            "scope": GA4_SCOPE,
            "aud": GA4_TOKEN_URL,
            "iat": now,
            "exp": now + 3600,
        }).encode())
        signing_input = f"{header}.{claims}".encode()
        private_key = cast(RSAPrivateKey, serialization.load_pem_private_key(
            key["private_key"].encode(), password=None))
        signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
        assertion = f"{header}.{claims}.{_b64(signature)}"
        with httpx.Client(timeout=20.0) as client:
            response = client.post(GA4_TOKEN_URL, data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            })
        if response.status_code >= 400:
            log.info("ga4 token -> %s", response.status_code)
            return "", f"Google refused the service account ({response.status_code})"
        payload = response.json() or {}
        token = payload.get("access_token") or ""
        if not token:
            return "", "Google returned no access token"
        _GA4_CACHE.update({"token": token, "expires": time.time() + int(payload.get("expires_in") or 3600)})
        return token, ""
    except Exception as exc:                                 # noqa: BLE001
        log.info("ga4 token failed: %s", exc)
        return "", f"The Google service-account key could not be used ({type(exc).__name__})"


def _ga4_report(property_id: str, token: str, start: datetime, end: datetime,
                metrics: List[str], dimensions: Optional[List[str]] = None,
                limit: int = 6) -> Optional[List[Dict[str, Any]]]:
    body: Dict[str, Any] = {
        "dateRanges": [{"startDate": start.date().isoformat(), "endDate": end.date().isoformat()}],
        "metrics": [{"name": m} for m in metrics],
    }
    if dimensions:
        body["dimensions"] = [{"name": d} for d in dimensions]
        body["limit"] = limit
        body["orderBys"] = [{"metric": {"metricName": metrics[0]}, "desc": True}]
    try:
        with httpx.Client(timeout=25.0) as client:
            response = client.post(f"{GA4_DATA_BASE}/properties/{property_id}:runReport",
                                   headers={"Authorization": f"Bearer {token}"}, json=body)
        if response.status_code >= 400:
            log.info("ga4 report -> %s %s", response.status_code, response.text[:160])
            return None
        rows = (response.json() or {}).get("rows") or []
    except Exception as exc:                                 # noqa: BLE001
        log.info("ga4 report failed: %s", exc)
        return None
    out = []
    for row in rows:
        dims = [d.get("value") or "" for d in row.get("dimensionValues") or []]
        vals = [v.get("value") or "0" for v in row.get("metricValues") or []]
        out.append({"dims": dims, "vals": vals})
    return out


def ga4_visitors(start: datetime, end: datetime) -> Dict[str, Any]:
    """Visitors, new visitors, channels and top pages for the window, and the window before it."""
    property_id = _env("GA4_PROPERTY_ID")
    if not property_id:
        return {"connected": False, "why": "Google Analytics property id is not set (GA4_PROPERTY_ID)"}
    token, why = _ga4_access_token()
    if not token:
        return {"connected": False, "why": why}

    span = end - start
    totals = _ga4_report(property_id, token, start, end, ["totalUsers", "newUsers"])
    previous = _ga4_report(property_id, token, start - span, start, ["totalUsers"])
    channels = _ga4_report(property_id, token, start, end, ["totalUsers"],
                           dimensions=["sessionDefaultChannelGroup"])
    pages = _ga4_report(property_id, token, start, end, ["screenPageViews"], dimensions=["pagePath"])
    if totals is None:
        return {"connected": False, "why": "Google Analytics answered with an error"}

    def _num(row_list, index=0) -> int:
        try:
            return int(float((row_list or [{}])[0]["vals"][index]))
        except Exception:                                    # noqa: BLE001
            return 0

    return {
        "connected": True,
        "visitors": _num(totals, 0),
        "new_visitors": _num(totals, 1),
        "visitors_prev": _num(previous, 0) if previous is not None else None,
        "sources": [{"name": (r["dims"] or ["direct"])[0], "visitors": int(float(r["vals"][0] or 0))}
                    for r in (channels or [])],
        "pages": [{"name": (r["dims"] or ["/"])[0], "views": int(float(r["vals"][0] or 0))}
                  for r in (pages or [])],
        "why": "",
    }


# --------------------------------------------------------------------------- Microsoft Clarity
def clarity_sessions() -> Dict[str, Any]:
    """Sessions and people from Clarity's last three days - the only window its API exposes."""
    project_id = _env("CLARITY_PROJECT_ID")
    token = _env("CLARITY_TOKEN")
    if not project_id or not token:
        missing = [n for n, v in (("CLARITY_PROJECT_ID", project_id), ("CLARITY_TOKEN", token)) if not v]
        return {"connected": False, "sessions": None, "why":
                "Microsoft Clarity is not connected (needs " + " + ".join(missing) + ")"}
    try:
        with httpx.Client(timeout=25.0) as client:
            response = client.get(CLARITY_BASE, params={"numOfDays": 3},
                                  headers={"Authorization": f"Bearer {token}",
                                           "Content-Type": "application/json"})
        if response.status_code >= 400:
            log.info("clarity -> %s", response.status_code)
            return {"connected": False, "sessions": None,
                    "why": f"Clarity answered {response.status_code}"}
        data = response.json() or []
    except Exception as exc:                                 # noqa: BLE001
        log.info("clarity failed: %s", exc)
        return {"connected": False, "sessions": None,
                "why": f"Clarity could not be reached ({type(exc).__name__})"}

    sessions = 0
    people = 0
    for metric in data if isinstance(data, list) else []:
        if str(metric.get("metricName", "")).lower() != "traffic":
            continue
        for point in metric.get("information") or []:
            try:
                sessions += int(float(point.get("totalSessionCount") or 0))
                people += int(float(point.get("distantUserCount") or 0))
            except Exception:                                # noqa: BLE001
                continue
    return {
        "connected": True,
        "sessions": sessions,
        "people": people,
        "window_days": 3,
        "why": "",
        "url": f"https://clarity.microsoft.com/projects/view/{project_id}/dashboard",
    }
