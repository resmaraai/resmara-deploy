"""Resmara's own Meta ad account: every campaign and ad, with its money (Engine 9, section 3).

This is *our* advertising (the campaigns Resmara runs to find agents), not an agent's listing
campaign - those live under Campaigns and use the same Graph API through
``app/services/analytics.py``.

Two rules:

* **No account, no numbers.** Until ``META_AD_ACCOUNT_ID`` and ``META_SYSTEM_TOKEN`` are set,
  every list comes back empty with a reason, and the page says "not connected". Spend is never
  reported as $0 when it is simply unread.
* **Pausing is the only write.** A status change is the single thing the console sends to Meta
  here; nothing is created, and nothing is deleted.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.services import analytics

log = logging.getLogger("resmara.marketing_ads")

TIMEOUT = 20.0
_STATUS = {"PAUSED": "paused", "ACTIVE": "running"}


def _params(token: str, start: datetime, end: datetime) -> Dict[str, Any]:
    return {
        "access_token": token,
        "time_range": json.dumps({"since": start.date().isoformat(),
                                  "until": end.date().isoformat()}),
    }


def _numbers(row: Dict[str, Any]) -> Dict[str, Any]:
    insights = (row.get("insights") or {}).get("data") or []
    spend = clicks = impressions = 0.0
    for item in insights:
        spend += float(item.get("spend") or 0)
        clicks += float(item.get("clicks") or 0)
        impressions += float(item.get("impressions") or 0)
    return {"spend_usd": round(spend, 2), "clicks": int(clicks),
            "impressions": int(impressions)}


def _list(account: Any, edge: str, fields: str, start: datetime, end: datetime,
          limit: int = 100) -> tuple[Optional[List[Dict[str, Any]]], str]:
    ad_account, token, why = analytics.meta_credentials(account)
    if not ad_account or not token:
        return None, why or "Resmara's own Meta ad account is not connected"
    url = f"{settings.graph_base}/act_{str(ad_account).lstrip('act_')}/{edge}"
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.get(url, params={**_params(token, start, end),
                                               "fields": fields, "limit": limit})
        if response.status_code >= 400:
            detail = ""
            try:
                detail = ((response.json().get("error") or {}).get("message") or "")[:160]
            except Exception:                                    # noqa: BLE001
                detail = response.text[:160]
            log.info("meta %s -> %s %s", edge, response.status_code, detail)
            return None, f"Meta answered {response.status_code}: {detail or 'no message'}"
        return (response.json() or {}).get("data") or [], ""
    except Exception as exc:                                     # noqa: BLE001 - a page, not a crash
        log.info("meta %s failed: %s", edge, exc)
        return None, f"Meta could not be reached ({type(exc).__name__})"


def campaigns(account: Any, start: datetime, end: datetime) -> Dict[str, Any]:
    """Every campaign on the account, with spend, clicks and status."""
    rows, why = _list(account, "campaigns",
                      "id,name,status,effective_status,objective,"
                      "insights{spend,clicks,impressions}", start, end)
    if rows is None:
        return {"connected": False, "why": why, "campaigns": []}
    out = []
    for row in rows:
        out.append({
            "id": row.get("id"),
            "name": row.get("name") or "Untitled campaign",
            "status": (row.get("effective_status") or row.get("status") or "").upper(),
            "status_word": _STATUS.get((row.get("status") or "").upper(), "running"),
            "objective": row.get("objective") or "",
            **_numbers(row),
        })
    return {"connected": True, "why": "", "campaigns": out}


def ads(account: Any, campaign_id: str, start: datetime, end: datetime) -> Dict[str, Any]:
    """The ads inside one campaign - each the same numbers, plus where it runs."""
    ad_account, token, why = analytics.meta_credentials(account)
    if not ad_account or not token:
        return {"connected": False, "why": why, "ads": []}
    url = f"{settings.graph_base}/{campaign_id}/ads"
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.get(url, params={
                **_params(token, start, end),
                "fields": "id,name,status,effective_status,adset{name},"
                          "insights{spend,clicks,impressions}", "limit": 100})
        if response.status_code >= 400:
            return {"connected": True, "why": f"Meta answered {response.status_code}", "ads": []}
        rows = (response.json() or {}).get("data") or []
    except Exception as exc:                                     # noqa: BLE001
        log.info("meta ads failed: %s", exc)
        return {"connected": True, "why": f"Meta could not be reached ({type(exc).__name__})",
                "ads": []}
    return {"connected": True, "why": "", "ads": [
        {"id": row.get("id"),
         "name": row.get("name") or "Untitled ad",
         "status": (row.get("effective_status") or row.get("status") or "").upper(),
         "where": ((row.get("adset") or {}).get("name") or ""),
         **_numbers(row)}
        for row in rows]}


def set_status(account: Any, object_id: str, run: bool) -> Dict[str, Any]:
    """Pause or run one campaign or ad. Returns what Meta says, not what we hoped."""
    _ad_account, token, why = analytics.meta_credentials(account)
    if not token:
        return {"ok": False, "why": why or "Resmara's own Meta ad account is not connected"}
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.post(f"{settings.graph_base}/{object_id}",
                                   data={"access_token": token,
                                         "status": "ACTIVE" if run else "PAUSED"})
        if response.status_code >= 400:
            detail = ""
            try:
                detail = ((response.json().get("error") or {}).get("message") or "")[:160]
            except Exception:                                    # noqa: BLE001
                detail = response.text[:160]
            return {"ok": False, "why": f"Meta answered {response.status_code}: {detail}"}
        return {"ok": True, "status": "ACTIVE" if run else "PAUSED"}
    except Exception as exc:                                     # noqa: BLE001
        return {"ok": False, "why": f"Meta could not be reached ({type(exc).__name__})"}
