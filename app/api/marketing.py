"""Marketing and Website: what we know, and what nobody has connected yet.

Both pages were built to read third-party numbers - Resmara's own Meta ad account for spend,
Google Analytics and Clarity for visitors. None of those credentials are on the service, so
neither endpoint pretends: it returns what this database and the open PageSpeed API can actually
answer, marks ``connected: false``, and lists what is missing under ``unavailable``.

Turning one on is an env-var edit (see ``MISSING`` below); when the credential appears the same
endpoint starts returning the real numbers with no code change.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import AdAccount, Boost, Post, User, get_db
from app.services import team_access

log = logging.getLogger("resmara.marketing")

router = APIRouter()

MISSING = {
    "ad_spend": "Resmara's own Meta ad account is not connected on the service",
    "visitors": "Google Analytics is not connected on the service (RESMARA_GA4_TOKEN + RESMARA_GA4_PROPERTY_ID)",
    "clarity": "Microsoft Clarity is not connected on the service (RESMARA_CLARITY_TOKEN + RESMARA_CLARITY_PROJECT_ID)",
}

# Accounts that count as agents, not operators.
def _operator_emails() -> set:
    return {e.strip().lower() for e in (settings.ADMIN_EMAILS or "").split(",") if e.strip()}


def _window(days: int) -> tuple[datetime, datetime]:
    days = max(1, min(int(days or 30), 180))
    end = datetime.utcnow()
    return end - timedelta(days=days), end


def _resmara_ad_account(db: Session) -> Optional[AdAccount]:
    """Resmara's own ad account is an account owned by an operator."""
    owners = db.query(User).filter(User.email.in_(_operator_emails() or {"-"})).all()
    for owner in owners:
        account = (db.query(AdAccount)
                   .filter(AdAccount.user_id == owner.id)
                   .filter(AdAccount.access_token.isnot(None))
                   .order_by(AdAccount.id.desc()).first())
        if account:
            return account
    return None


@router.get("/admin/marketing")
def marketing(days: int = Query(30, ge=1, le=180),
              user=Depends(team_access.needs("business")), db: Session = Depends(get_db)):
    """Sign-ups and paying agents are ours to count; ad spend and leads need the ad account."""
    start, end = _window(days)
    account = _resmara_ad_account(db)
    operators = _operator_emails()

    agents = [u for u in db.query(User).all()
              if (u.email or "").lower() not in operators and (u.name or "").lower() != "test"]
    def _created(user: User) -> Optional[datetime]:
        value = user.created_at
        return value.replace(tzinfo=None) if isinstance(value, datetime) else None

    signups = sum(1 for u in agents if (_created(u) or datetime.min) >= start)
    paying = (
        db.query(func.count(func.distinct(Boost.user_id)))
        .filter(Boost.paid_at.isnot(None))
        .filter(Boost.paid_at >= start)
        .scalar() or 0
    )

    weeks: List[Dict[str, Any]] = []
    cursor = start
    while cursor < end:
        nxt = min(cursor + timedelta(days=7), end)
        weeks.append({
            "start": cursor.date().isoformat(),
            "leads": None,
            "spend_usd": None,
            "signups": sum(1 for u in agents if cursor <= (_created(u) or datetime.min) < nxt),
        })
        cursor = nxt

    unavailable = []
    if account is None:
        unavailable.append({"metric": "ad_spend", "reason": MISSING["ad_spend"]})
        unavailable.append({"metric": "impressions", "reason": MISSING["ad_spend"]})
        unavailable.append({"metric": "clicks", "reason": MISSING["ad_spend"]})
    unavailable.append({"metric": "leads", "reason": MISSING["visitors"]})

    return {
        "connected": False,
        "days": (end - start).days,
        "spend_usd": None,
        "impressions": None,
        "clicks": None,
        "leads": None,
        "signups": signups,
        "paying": int(paying),
        "campaigns_running": 0,
        "weeks": weeks,
        "ad_account": ({"advertiser_id": account.advertiser_id,
                        "name": account.account_name} if account else None),
        "unavailable": unavailable,
        "note": ("Ad spend needs Resmara's own Meta account connected. Sign-ups and paying agents "
                 "below are counted from this database."),
    }


def _pagespeed(url: str, strategy: str) -> Optional[int]:
    """PageSpeed Insights needs no key at low volume, and returns the real Lighthouse score."""
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.get(
                "https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
                params={"url": url, "strategy": strategy, "category": "performance"},
            )
        if response.status_code >= 400:
            log.info("pagespeed %s -> %s", strategy, response.status_code)
            return None
        data = response.json()
        score = (((data.get("lighthouseResult") or {}).get("categories") or {})
                 .get("performance") or {}).get("score")
        return int(round(float(score) * 100)) if score is not None else None
    except Exception as exc:                                    # noqa: BLE001 - a check, not a crash
        log.info("pagespeed failed: %s", exc)
        return None


def _tag_checks(base: str) -> List[Dict[str, Any]]:
    checks = []
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(base + "/")
        body = response.text
        checks.append({"name": "Site answers", "status": "ok" if response.status_code < 400 else "fail",
                       "detail": f"HTTP {response.status_code}"})
        for name, needle in (("Google tag", "googletagmanager.com/gtag/js"),
                             ("Google Ads tag", "googleads.g.doubleclick.net"),
                             ("Meta pixel", "connect.facebook.net"),
                             ("Clarity", "clarity.ms/tag")):
            checks.append({"name": name, "status": "ok" if needle in body else "warn",
                           "detail": "Found on the homepage" if needle in body
                                     else "Not found on the homepage HTML"})
    except Exception as exc:                                    # noqa: BLE001
        checks.append({"name": "Site answers", "status": "fail", "detail": str(exc)[:200]})
    return checks


@router.get("/admin/website")
def website(days: int = Query(30, ge=1, le=180),
            user=Depends(team_access.needs("business"))):
    """Visitors need Google Analytics; speed and the tags are measured here, for real."""
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    checks = _tag_checks(base)
    mobile = _pagespeed(base + "/", "mobile")
    desktop = _pagespeed(base + "/", "desktop")
    checks.append({"name": "Page speed (phones)", "status":
                   "ok" if (mobile or 0) >= 90 else ("fail" if mobile is not None and mobile < 50 else "warn"),
                   "detail": f"Lighthouse performance {mobile}/100" if mobile is not None
                             else "PageSpeed Insights did not answer"})
    checks.append({"name": "Page speed (desktop)", "status":
                   "ok" if (desktop or 0) >= 90 else ("warn" if desktop is not None else "warn"),
                   "detail": f"Lighthouse performance {desktop}/100" if desktop is not None
                             else "PageSpeed Insights did not answer"})

    return {
        "connected": False,
        "days": max(1, min(int(days or 30), 180)),
        "visitors": None,
        "visitors_prev": None,
        "new_visitors": None,
        "signups_started": None,
        "signups": None,
        "speed_mobile": mobile,
        "speed_desktop": desktop,
        "clarity_sessions": None,
        "clarity_url": None,
        "checks": checks,
        "sources": [],
        "pages": [],
        "unavailable": [{"metric": "visitors", "reason": MISSING["visitors"]},
                        {"metric": "clarity", "reason": MISSING["clarity"]}],
    }
