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
from app.services import analytics, team_access

log = logging.getLogger("resmara.marketing")

router = APIRouter()

MISSING = {
    "ad_spend": "Resmara's own Meta ad account is not connected (needs META_AD_ACCOUNT_ID + META_SYSTEM_TOKEN)",
    "visitors": "Google Analytics is not connected (needs GA4_PROPERTY_ID + a service-account key in GA4_SA_JSON)",
    "clarity": "Microsoft Clarity is not connected (needs CLARITY_PROJECT_ID + CLARITY_TOKEN)",
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
        # access_token is a decrypting property, not a column: it cannot be filtered in SQL, so
        # the newest rows are checked here. An account whose token will not decrypt is skipped.
        for account in (db.query(AdAccount)
                        .filter(AdAccount.user_id == owner.id)
                        .filter(AdAccount.platform == "meta")
                        .order_by(AdAccount.id.desc()).all()):
            try:
                if (account.access_token or "").strip():
                    return account
            except Exception:                                # noqa: BLE001 - an unreadable token
                continue
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

    # What our own database can say, and what only Meta can.
    insight = analytics.meta_insights(account, start, end)
    by_week_signups: Dict[str, int] = {}
    cursor = start
    while cursor < end:
        nxt = min(cursor + timedelta(days=7), end)
        by_week_signups[cursor.date().isoformat()] = sum(
            1 for u in agents if cursor <= (_created(u) or datetime.min) < nxt)
        cursor = nxt

    weeks: List[Dict[str, Any]] = [{"start": day, "leads": None, "spend_usd": None,
                                    "signups": value}
                                   for day, value in by_week_signups.items()]
    if insight["connected"]:
        # Merge Meta's own week starts over ours so a week carries both spend and sign-ups; a
        # week Meta reports that we did not compute still gets a row (0 sign-ups is the truth).
        merged: Dict[str, Dict[str, Any]] = {w["start"]: dict(w) for w in weeks}
        for row in insight["weeks"]:
            entry = merged.get(row["start"]) or {"start": row["start"], "leads": None,
                                                 "signups": 0, "spend_usd": None}
            entry["spend_usd"] = row["spend_usd"]
            entry["impressions"] = row["impressions"]
            entry["clicks"] = row["clicks"]
            merged[row["start"]] = entry
        weeks = [merged[k] for k in sorted(merged)]

    unavailable = []
    if not insight["connected"]:
        reason = insight["why"] or MISSING["ad_spend"]
        unavailable += [{"metric": "ad_spend", "reason": reason},
                        {"metric": "impressions", "reason": reason},
                        {"metric": "clicks", "reason": reason}]
    unavailable.append({"metric": "leads", "reason": MISSING["visitors"]})

    return {
        "connected": bool(insight["connected"]),
        "days": (end - start).days,
        "spend_usd": insight["spend_usd"],
        "impressions": insight["impressions"],
        "clicks": insight["clicks"],
        "leads": None,
        "signups": signups,
        "paying": int(paying),
        "campaigns_running": (
            db.query(func.count(Boost.id)).filter(Boost.status == "live").scalar() or 0
            if hasattr(Boost, "status") else 0),
        "weeks": weeks,
        "ad_account": ({"advertiser_id": insight["account_id"],
                        "name": (account.account_name if account is not None else None)}
                       if insight["account_id"] else None),
        "unavailable": unavailable,
        "note": ("Ad spend is Resmara's own Meta account." if insight["connected"] else
                 "Ad spend needs Resmara's own Meta account connected - set META_AD_ACCOUNT_ID and "
                 "META_SYSTEM_TOKEN on the service. Sign-ups and paying agents below are counted "
                 "from this database and are real."),
    }


def _pagespeed(url: str, strategy: str) -> tuple[Optional[int], str]:
    """The real Lighthouse score, or the sentence that says why there isn't one.

    Anonymous calls are heavily rate-limited (Google answers 429), so a free key is used when
    RESMARA_PAGESPEED_KEY is set. Either way the page is told the reason rather than shown a blank.
    """
    params = {"url": url, "strategy": strategy, "category": "performance"}
    key = (getattr(settings, "PAGESPEED_KEY", "") or "").strip()
    if key:
        params["key"] = key
    try:
        with httpx.Client(timeout=25.0) as client:
            response = client.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
                                  params=params)
        if response.status_code >= 400:
            log.info("pagespeed %s -> %s", strategy, response.status_code)
            if response.status_code == 429:
                return None, ("PageSpeed Insights is rate-limiting this service - a free "
                              "RESMARA_PAGESPEED_KEY fixes it" if not key
                              else "PageSpeed Insights is rate-limiting this service")
            return None, f"PageSpeed Insights said {response.status_code}"
        data = response.json()
        score = (((data.get("lighthouseResult") or {}).get("categories") or {})
                 .get("performance") or {}).get("score")
        if score is None:
            return None, "PageSpeed Insights answered without a score"
        return int(round(float(score) * 100)), ""
    except Exception as exc:                                    # noqa: BLE001 - a check, not a crash
        log.info("pagespeed failed: %s", exc)
        return None, f"PageSpeed Insights could not be reached ({type(exc).__name__})"
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
            user=Depends(team_access.needs("business")), db: Session = Depends(get_db)):
    """Visitors come from Google Analytics, sessions from Clarity, speed and tags from here."""
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    window_days = max(1, min(int(days or 30), 180))
    start, end = _window(window_days)
    checks = _tag_checks(base)
    mobile, why_mobile = _pagespeed(base + "/", "mobile")
    desktop, why_desktop = _pagespeed(base + "/", "desktop")
    checks.append({"name": "Page speed (phones)", "status":
                   "ok" if (mobile or 0) >= 90 else ("fail" if mobile is not None and mobile < 50 else "warn"),
                   "detail": f"Lighthouse performance {mobile}/100" if mobile is not None else why_mobile})
    checks.append({"name": "Page speed (desktop)", "status":
                   "ok" if (desktop or 0) >= 90 else ("warn" if desktop is not None else "warn"),
                   "detail": f"Lighthouse performance {desktop}/100" if desktop is not None else why_desktop})

    traffic = analytics.ga4_visitors(start, end)
    clarity = analytics.clarity_sessions()
    # "Sign-ups started" is ours to count: an account created in the window started signing up.
    # Counted in Python on purpose - created_at is a timestamptz on Postgres and a naive datetime
    # here, and a SQL comparison between the two dialects is exactly the kind of thing that works
    # on sqlite and 500s in production.
    operators = _operator_emails()
    signups_started = 0
    for person in db.query(User).all():
        if (person.email or "").lower() in operators:
            continue
        created = person.created_at
        if isinstance(created, datetime):
            created = created.replace(tzinfo=None)
            if created >= start:
                signups_started += 1

    unavailable = []
    if traffic.get("connected"):
        checks.insert(0, {"name": "Analytics", "status": "ok",
                          "detail": f"Google Analytics answered for the last {window_days} days"})
    else:
        unavailable.append({"metric": "visitors", "reason": traffic.get("why") or MISSING["visitors"]})
    if not clarity.get("connected"):
        unavailable.append({"metric": "clarity", "reason": clarity.get("why") or MISSING["clarity"]})

    return {
        "connected": bool(traffic.get("connected")),
        "days": window_days,
        "visitors": traffic.get("visitors"),
        "visitors_prev": traffic.get("visitors_prev"),
        "new_visitors": traffic.get("new_visitors"),
        "signups_started": int(signups_started),
        "signups": int(signups_started),
        "speed_mobile": mobile,
        "speed_desktop": desktop,
        "clarity_sessions": clarity.get("sessions"),
        "clarity_url": clarity.get("url"),
        "checks": checks,
        "sources": traffic.get("sources") or [],
        "pages": traffic.get("pages") or [],
        "unavailable": unavailable,
    }

