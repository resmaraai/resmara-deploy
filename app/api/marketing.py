"""Marketing: Resmara's own marketing, on one page and under it (Engine 9).

Marketing is the parent page. **Digital ads**, **Email campaigns** and **Website** sit under it
in the Team room's Business menu, each with its own numbers; Marketing brings them together and
answers one question: is each channel paying for itself?

The counting rules live in ``app/services/attribution.py`` and are repeated on the page in plain
words. The short version:

* Every sign-up is stamped with where it came from, once, when the account is made.
* Each paying agent counts once, for the last thing that got them to buy.
* Money back is every campaign those agents bought in the period, at what they paid.
* Ad spend is read from Meta; the Mailchimp plan and hosting are typed in once in Settings.
* **Working** = the agents a channel brought in paid more than it cost.

What cannot be measured is named, never filled in: with no Meta ad account, no Mailchimp key or
no Google Analytics, the page says which variable is missing and keeps the numbers that are
ours (sign-ups, paying agents, money back) on screen, because those are real.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.core.testdata import test_user_ids
from app.db.session import AdAccount, Boost, MarketingSetting, User, get_db
from app.services import analytics, attribution, mailchimp, marketing_ads, team_access

log = logging.getLogger("resmara.marketing")

router = APIRouter()

MISSING = {
    "ad_spend": "Resmara's own Meta ad account is not connected (needs META_AD_ACCOUNT_ID + META_SYSTEM_TOKEN)",
    "visitors": "Google Analytics is not connected (needs GA4_PROPERTY_ID + a service-account key in GA4_SA_JSON)",
    "clarity": "Microsoft Clarity is not connected (needs CLARITY_PROJECT_ID + CLARITY_TOKEN)",
    "email": "Mailchimp is not connected (needs MAILCHIMP_API_KEY + MAILCHIMP_AUDIENCE_ID)",
}

# The three series (Engine 9, section 2). The emails are built in Mailchimp in Resmara's look and
# approved by Adam; these names are how their reports are matched back to a series.
SERIES: List[Dict[str, Any]] = [
    # Every follow-up email is a Mailchimp series so each one is tracked (Adam, 25 Nov). The
    # emails are named in Mailchimp exactly as below; that name is how their numbers are found.
    {"key": "welcome", "name": "Welcome and check-ins", "audience": "signed up, no campaign yet",
     "when": "day 0, 3, 7 and 14; stops when they launch a campaign",
     "emails": ["Welcome — day 0", "Welcome — day 3", "Welcome — day 7", "Welcome — day 14"]},
    {"key": "tips", "name": "Tips and updates", "audience": "has run a campaign",
     "when": "every 2 weeks", "emails": ["Tips and updates"]},
    {"key": "past", "name": "Got a new listing?", "audience": "past client",
     "when": "60 days after their last campaign", "emails": ["Got a new listing?"]},
]

COST_KEYS = ("mailchimp_monthly_usd", "hosting_monthly_usd")


# --------------------------------------------------------------------------- small helpers
def _operator_emails() -> set:
    return {e.strip().lower() for e in (settings.ADMIN_EMAILS or "").split(",") if e.strip()}


def _window(days: int) -> tuple[datetime, datetime]:
    days = max(1, min(int(days or 30), 180))
    end = datetime.utcnow()
    return end - timedelta(days=days), end


def _naive(value: Any) -> Optional[datetime]:
    """A timestamptz on Postgres and a naive datetime on SQLite, read the same way.

    Every comparison in this module happens in Python for exactly this reason: a SQL comparison
    between the two dialects is the kind of thing that works on sqlite and 500s in production.
    """
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    return None


def _agents(db: Session) -> List[User]:
    """Real customer accounts: no operators, no test rows, test accounts left out."""
    operators = _operator_emails()
    tests = test_user_ids(db)
    return [u for u in db.query(User).all()
            if (u.email or "").lower() not in operators
            and (u.name or "").lower() != "test"
            and u.id not in tests]


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


def _boost_price(boost: Boost) -> float:
    """What this campaign was paid for. A prepaid balance reads as today's price.

    ``paid_amount_cents`` is 0 for a campaign built from a purchased pack (the money arrived
    when the pack was bought), so a zero is valued at the list price for that round rather than
    counted as a free campaign.
    """
    from app.services import billing
    cents = boost.paid_amount_cents or 0
    if cents and cents > 0:
        return round(cents / 100.0, 2)
    return round((billing.repeat_price_cents() if (boost.repeat_round or 0) > 0
                  else billing.price_cents()) / 100.0, 2)


def _settings(db: Session) -> MarketingSetting:
    row = db.query(MarketingSetting).first()
    if row is None:
        row = MarketingSetting(payload={})
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _as_money(value: Any) -> Optional[float]:
    try:
        if value is None or str(value).strip() == "":
            return None
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _costs(db: Session) -> Dict[str, Any]:
    """The two monthly costs, from Settings when typed in, else the env fallback.

    An unset cost is ``None`` and not 0: a channel whose cost nobody entered cannot be judged,
    and saying "$0 spent" would make every verdict read "Working".
    """
    payload = (_settings(db).payload or {})
    mailchimp_cost = _as_money(payload.get("mailchimp_monthly_usd"))
    hosting_cost = _as_money(payload.get("hosting_monthly_usd"))
    if mailchimp_cost is None:
        mailchimp_cost = _as_money(getattr(settings, "MAILCHIMP_MONTHLY_USD", ""))
    if hosting_cost is None:
        hosting_cost = _as_money(getattr(settings, "MARKETING_HOSTING_MONTHLY_USD", ""))
    return {
        "mailchimp_monthly_usd": mailchimp_cost,
        "hosting_monthly_usd": hosting_cost,
        "entered_in_settings": {k: _as_money(payload.get(k)) is not None for k in COST_KEYS},
    }


def _prorated(monthly: Optional[float], days: int) -> Optional[float]:
    """A monthly bill spread evenly across the window, to the day."""
    if monthly is None:
        return None
    return round(monthly * (days / 30.0), 2)


def _first_paid(boosts: List[Boost]) -> Dict[int, Boost]:
    """Each agent's first paid campaign: the one that carries their channel credit."""
    first: Dict[int, Boost] = {}
    for boost in sorted(boosts, key=lambda b: _naive(b.paid_at) or datetime.min):
        if boost.user_id not in first:
            first[boost.user_id] = boost
    return first


def _credit_of(boost: Boost, user: Optional[User]) -> str:
    """The channel a purchase counts for: the stored credit, else the sign-up stamp."""
    stored = getattr(boost, "paid_source", None)
    if stored in attribution.CHANNELS:
        return str(stored)
    return attribution.channel_or_website(getattr(user, "signup_source", None))


def _verdict(cost: Optional[float], money_back: Optional[float]) -> Dict[str, Any]:
    """Working = the agents it brought in paid more than it cost. Nothing else counts."""
    if cost is None:
        return {"verdict": None, "text": "Cost not entered yet, so there is nothing to judge it against"}
    if money_back is None:
        return {"verdict": None, "text": "Money back is not readable yet"}
    if cost == 0:
        return {"verdict": None, "text": "It has cost nothing yet, so there is nothing to be wrong"}
    roi = round(money_back / cost, 2)
    return {"verdict": roi > 1,
            "text": ("Working: every $1 spent came back as $" + str(roi) if roi > 1 else
                     "Not working: every $1 spent came back as $" + str(roi) + " so far")}


# --------------------------------------------------------------------------- Marketing (parent)
@router.get("/admin/marketing")
def marketing(days: int = Query(30, ge=1, le=180),
              user=Depends(team_access.needs("business")), db: Session = Depends(get_db)):
    """One row per channel: cost, sign-ups, paying agents, money back and a verdict."""
    start, end = _window(days)
    window_days = (end - start).days
    account = _resmara_ad_account(db)
    insight = analytics.meta_insights(account, start, end)

    agents = _agents(db)
    by_id = {u.id: u for u in agents}

    # Sign-ups, stamped when the account was made.
    signups: Dict[str, int] = {k: 0 for k in attribution.CHANNELS}
    for person in agents:
        created = _naive(person.created_at)
        if created and created >= start:
            signups[attribution.channel_or_website(person.signup_source)] += 1

    # Every paid campaign in the window, and each agent's first-ever paid campaign (the credit).
    all_paid = (db.query(Boost).filter(Boost.paid_at.isnot(None))
                .filter(Boost.user_id.in_(list(by_id) or [-1])).all())
    first = _first_paid(all_paid)

    paying: Dict[str, int] = {k: 0 for k in attribution.CHANNELS}
    money_back: Dict[str, float] = {k: 0.0 for k in attribution.CHANNELS}
    campaigns: Dict[str, int] = {k: 0 for k in attribution.CHANNELS}
    for boost in all_paid:
        paid_at = _naive(boost.paid_at)
        if not paid_at or paid_at < start:
            continue
        credit = _credit_of(first.get(boost.user_id, boost), by_id.get(boost.user_id))
        money_back[credit] = round(money_back[credit] + _boost_price(boost), 2)
        campaigns[credit] += 1
        if first.get(boost.user_id) is boost:
            paying[credit] += 1

    # Costs: ad spend is measured, the other two are typed in once and spread to the day.
    costs = _costs(db)
    cost_by_channel: Dict[str, Optional[float]] = {
        "ad": insight["spend_usd"] if insight["connected"] else None,
        "email": _prorated(costs["mailchimp_monthly_usd"], window_days),
        "website": _prorated(costs["hosting_monthly_usd"], window_days),
    }
    cost_notes = {
        "ad": "read from Resmara's own Meta account" if insight["connected"]
              else "needs Resmara's own Meta ad account",
        "email": ("the Mailchimp plan, spread to the day" if cost_by_channel["email"] is not None
                  else "enter the Mailchimp plan in Settings"),
        "website": ("the website hosting, spread to the day" if cost_by_channel["website"] is not None
                    else "enter the hosting cost in Settings"),
    }

    channels = []
    for key in attribution.CHANNELS:
        cost = cost_by_channel[key]
        back = round(money_back[key], 2)
        per_agent = (round(cost / paying[key], 2) if cost is not None and paying[key] else None)
        judged = _verdict(cost, back)
        channels.append({
            "key": key,
            "name": attribution.LABELS[key],
            "cost_usd": cost,
            "cost_note": cost_notes[key],
            "signups": int(signups[key]),
            "paying": int(paying[key]),
            "campaigns": int(campaigns[key]),
            "per_paying_usd": per_agent,
            "money_back_usd": back,
            "back_per_dollar": (round(back / cost, 2) if cost else None),
            "verdict": judged["verdict"],
            "verdict_text": judged["text"],
            "go": {"ad": "digitalads", "email": "email", "website": "website"}[key],
        })

    known_costs = [c["cost_usd"] for c in channels if c["cost_usd"] is not None]
    total_cost = round(sum(known_costs), 2) if known_costs else None
    total_back = round(sum(c["money_back_usd"] for c in channels), 2)
    total_paying = int(sum(c["paying"] for c in channels))
    total_judged = _verdict(total_cost, total_back)
    total = {
        "cost_usd": total_cost,
        "cost_complete": all(c["cost_usd"] is not None for c in channels),
        "signups": int(sum(c["signups"] for c in channels)),
        "paying": total_paying,
        "campaigns": int(sum(c["campaigns"] for c in channels)),
        "per_paying_usd": (round(total_cost / total_paying, 2)
                           if total_cost is not None and total_paying else None),
        "money_back_usd": total_back,
        "back_per_dollar": (round(total_back / total_cost, 2) if total_cost else None),
        "verdict": total_judged["verdict"],
        "verdict_text": total_judged["text"],
    }

    # Paying agents each week, by channel, with that week's spend.
    weeks: List[Dict[str, Any]] = []
    cursor = start
    while cursor < end:
        nxt = min(cursor + timedelta(days=7), end)
        bucket = {"start": cursor.date().isoformat(), "ad": 0, "email": 0, "website": 0,
                  "total": 0, "signups": 0, "spend_usd": None}
        for person in agents:
            created = _naive(person.created_at)
            if created and cursor <= created < nxt:
                bucket["signups"] += 1
        for boost in all_paid:
            paid_at = _naive(boost.paid_at)
            if not paid_at or first.get(boost.user_id) is not boost:
                continue
            if cursor <= paid_at < nxt:
                credit = _credit_of(boost, by_id.get(boost.user_id))
                bucket[credit] += 1
                bucket["total"] += 1
        weeks.append(bucket)
        cursor = nxt

    # Meta reports its own week starts; merge them so a week carries both spend and agents.
    if insight["connected"]:
        merged: Dict[str, Dict[str, Any]] = {row["start"]: dict(row) for row in insight["weeks"]}
        for bucket in weeks:
            entry = merged.get(bucket["start"]) or {"start": bucket["start"], "leads": None,
                                                   "signups": 0, "spend_usd": None,
                                                   "impressions": 0, "clicks": 0}
            entry.update({k: bucket[k] for k in ("ad", "email", "website", "total")})
            entry["signups"] = bucket["signups"]
            merged[bucket["start"]] = entry
        series_weeks = [merged[k] for k in sorted(merged)]
    else:
        series_weeks = weeks

    unavailable = []
    if not insight["connected"]:
        reason = insight["why"] or MISSING["ad_spend"]
        unavailable += [{"metric": "ad_spend", "reason": reason},
                        {"metric": "impressions", "reason": reason},
                        {"metric": "clicks", "reason": reason}]
    if not mailchimp.configured():
        unavailable.append({"metric": "email", "reason": mailchimp.why_not()})
    if not costs["entered_in_settings"].get("mailchimp_monthly_usd"):
        unavailable.append({"metric": "email_cost",
                            "reason": "The Mailchimp plan is not typed into Settings, so Email's "
                                      "cost is unknown and it cannot be judged"})

    return {
        "connected": bool(insight["connected"]),
        "days": window_days,
        "spend_usd": insight["spend_usd"],
        "impressions": insight["impressions"],
        "clicks": insight["clicks"],
        "leads": None,
        "signups": int(sum(signups.values())),
        "paying": total_paying,
        "campaigns_running": (db.query(func.count(Boost.id))
                              .filter(Boost.stage == "LIVE").scalar() or 0),
        "weeks": series_weeks,
        "ad_account": ({"advertiser_id": insight["account_id"],
                        "name": (account.account_name if account is not None else None)}
                       if insight["account_id"] else None),
        "unavailable": unavailable,
        "note": ("Ad spend is Resmara's own Meta account." if insight["connected"] else
                 "Ad spend needs Resmara's own Meta account connected - set META_AD_ACCOUNT_ID and "
                 "META_SYSTEM_TOKEN on the service. Sign-ups and paying agents below are counted "
                 "from this database and are real."),
        # --- Engine 9 ---
        "channels": channels,
        "total": total,
        "money_back_usd": total_back,
        "rules": [
            "Every sign-up is stamped with where it came from when the account is made: the ad, "
            "an email, or the website on its own. It is never changed after that.",
            "Each paying agent counts once, for the last thing that got them to buy: the ad they "
            "came from, or an email they clicked in the 7 days before buying.",
            "Money back is every campaign those agents bought in the period, at what they paid. "
            "Nothing is counted twice, so the channel rows add up to the total.",
            "Ad spend is read from Meta on its own. The Mailchimp plan and the hosting are typed "
            "in once in Settings and spread evenly across the days.",
            "Working means the agents a channel brought in paid more than it cost. Under $1 back "
            "for every $1 spent is not working.",
        ],
        "costs": costs,
    }


# --------------------------------------------------------------------------- costs (Settings)
@router.get("/admin/marketing-costs")
def marketing_costs(user=Depends(team_access.needs("business")), db: Session = Depends(get_db)):
    return _costs(db)


@router.put("/admin/marketing-costs")
def save_marketing_costs(payload: Dict[str, Any],
                         user=Depends(team_access.needs("business")),
                         db: Session = Depends(get_db)):
    """Type the two monthly bills once. A blank field means "not known", not zero."""
    row = _settings(db)
    data = dict(row.payload or {})
    for key in COST_KEYS:
        if key not in payload:
            continue
        value = payload.get(key)
        if value is None or str(value).strip() == "":
            data.pop(key, None)
            continue
        money = _as_money(value)
        if money is None or money < 0:
            raise HTTPException(status_code=400, detail=f"{key} must be a number of dollars")
        data[key] = money
    row.payload = data
    db.commit()
    return _costs(db)


# --------------------------------------------------------------------------- Digital ads
@router.get("/admin/digital-ads")
def digital_ads(days: int = Query(30, ge=1, le=180),
                user=Depends(team_access.needs("business")), db: Session = Depends(get_db)):
    """Every campaign and ad on Resmara's own ad account, with the agents it brought in."""
    start, end = _window(days)
    window_days = (end - start).days
    account = _resmara_ad_account(db)
    listing = marketing_ads.campaigns(account, start, end)

    agents = _agents(db)
    by_id = {u.id: u for u in agents}
    all_paid = (db.query(Boost).filter(Boost.paid_at.isnot(None))
                .filter(Boost.user_id.in_(list(by_id) or [-1])).all())
    first = _first_paid(all_paid)

    # Sign-ups and paying agents matched to the ad they came from, by the campaign id the link
    # carried. Sign-ups with no campaign id are counted, but not under any campaign.
    signups_by_campaign: Counter = Counter()
    unmatched_signups = 0
    for person in agents:
        created = _naive(person.created_at)
        if not created or created < start:
            continue
        detail = person.signup_source_detail or {}
        cid = (str(detail.get("campaign_id") or detail.get("utm_campaign") or "")
               if isinstance(detail, dict) else "")
        if cid:
            signups_by_campaign[cid] += 1
        else:
            unmatched_signups += 1

    paying_by_campaign: Dict[str, int] = {}
    money_by_campaign: Dict[str, float] = {}
    campaigns_by_campaign: Dict[str, int] = {}
    for boost in all_paid:
        paid_at = _naive(boost.paid_at)
        if not paid_at or paid_at < start:
            continue
        if _credit_of(first.get(boost.user_id, boost), by_id.get(boost.user_id)) != "ad":
            continue
        owner = by_id.get(boost.user_id)
        credit_detail = (first.get(boost.user_id) or boost).paid_source_detail or {}
        signup_detail = owner.signup_source_detail if owner is not None else {}
        if not isinstance(signup_detail, dict):
            signup_detail = {}
        cid = str((credit_detail.get("signup") or {}).get("campaign_id")
                  or signup_detail.get("campaign_id") or signup_detail.get("utm_campaign") or "")
        if not cid:
            continue
        money_by_campaign[cid] = round(money_by_campaign.get(cid, 0.0) + _boost_price(boost), 2)
        campaigns_by_campaign[cid] = campaigns_by_campaign.get(cid, 0) + 1
        if first.get(boost.user_id) is boost:
            paying_by_campaign[cid] = paying_by_campaign.get(cid, 0) + 1

    rows = []
    for campaign in listing["campaigns"]:
        cid = str(campaign["id"])
        paying = int(paying_by_campaign.get(cid, 0))
        back = round(money_by_campaign.get(cid, 0.0), 2)
        judged = _verdict(campaign["spend_usd"], back)
        rows.append({**campaign,
                     "signups": int(signups_by_campaign[cid]),
                     "paying": paying,
                     "campaigns": int(campaigns_by_campaign.get(cid, 0)),
                     "per_paying_usd": (round(campaign["spend_usd"] / paying, 2)
                                        if paying and campaign["spend_usd"] is not None else None),
                     "money_back_usd": back,
                     "back_per_dollar": (round(back / campaign["spend_usd"], 2)
                                         if campaign["spend_usd"] else None),
                     "verdict": judged["verdict"],
                     "verdict_text": judged["text"]})

    total = {
        "spend_usd": (round(sum(r["spend_usd"] for r in rows), 2)
                      if listing["connected"] else None),
        "clicks": sum(r["clicks"] for r in rows) if listing["connected"] else None,
        "impressions": sum(r["impressions"] for r in rows) if listing["connected"] else None,
        # The two numbers that are ours even when Meta is not connected: every sign-up and every
        # paying agent credited to the ads in the window, whether or not it carries a campaign id.
        "signups": sum(1 for p in agents
                       if (_naive(p.created_at) or datetime.min) >= start
                       and attribution.channel_or_website(p.signup_source) == "ad"),
        "paying": sum(1 for uid, boost in first.items()
                      if (_naive(boost.paid_at) or datetime.min) >= start
                      and _credit_of(boost, by_id.get(uid)) == "ad"),
        "campaigns": int(sum(r["campaigns"] for r in rows)),
        "money_back_usd": round(sum(_boost_price(b) for b in all_paid
                                    if b.user_id in by_id
                                    and (_naive(b.paid_at) or datetime.min) >= start
                                    and _credit_of(first.get(b.user_id, b), by_id.get(b.user_id)) == "ad"), 2),
        "unmatched_signups": unmatched_signups,
    }
    total["per_paying_usd"] = (round(total["spend_usd"] / total["paying"], 2)
                               if total["spend_usd"] and total["paying"] else None)
    total["back_per_dollar"] = (round(total["money_back_usd"] / total["spend_usd"], 2)
                                if total["spend_usd"] else None)
    total.update(_verdict(total["spend_usd"], total["money_back_usd"]))

    unavailable = []
    if not listing["connected"]:
        unavailable.append({"metric": "campaigns", "reason": listing["why"] or MISSING["ad_spend"]})
    unavailable.append({"metric": "leads", "reason": MISSING["visitors"]})

    return {
        "connected": listing["connected"],
        "why": listing["why"],
        "days": window_days,
        "campaigns": rows,
        "total": total,
        "unmatched_signups": unmatched_signups,
        "unavailable": unavailable,
    }


@router.get("/admin/digital-ads/{campaign_id}/ads")
def digital_ads_ads(campaign_id: str, days: int = Query(30, ge=1, le=180),
                    user=Depends(team_access.needs("business")), db: Session = Depends(get_db)):
    """The ads inside one campaign, with what each one cost and what it brought in."""
    start, end = _window(days)
    result = marketing_ads.ads(_resmara_ad_account(db), campaign_id, start, end)
    for ad in result.get("ads", []):
        judged = _verdict(ad.get("spend_usd"), None)
        ad["verdict_text"] = judged["text"]
        ad["back_per_dollar"] = None
    return result


@router.post("/admin/digital-ads/{object_id}/status")
def digital_ads_status(object_id: str, payload: Dict[str, Any],
                       user=Depends(team_access.needs("business")),
                       db: Session = Depends(get_db)):
    """Pause or run one ad or campaign. The page paints what Meta answered, not what we sent."""
    run = bool(payload.get("run"))
    result = marketing_ads.set_status(_resmara_ad_account(db), object_id, run)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("why") or "Meta refused the change")
    return result


# --------------------------------------------------------------------------- Email campaigns
def _in_window(stamp: Any, start: datetime, end: datetime) -> bool:
    try:
        seen = datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:                                            # noqa: BLE001
        return False
    return start <= seen <= end


def _series_state(db: Session) -> Dict[str, bool]:
    stored = ((_settings(db).payload or {}).get("series") or {})
    return {s["key"]: bool(stored.get(s["key"], True)) for s in SERIES}


def _series_with_reports(db: Session) -> Dict[str, Any]:
    """Each series and each email in it, with Mailchimp's sent/opened/clicked when it is on."""
    on = _series_state(db)

    def _blank(why: str) -> Dict[str, Any]:
        return {"connected": False, "why": why,
                "series": [{**s, "on": on[s["key"]],
                            "emails": [{"name": e, "sent": None, "opened": None,
                                        "clicked": None, "bounced": None, "unsubscribed": None,
                                        "open_rate": None, "click_rate": None, "bounce_rate": None,
                                        "sent_at": None, "in_mailchimp": False}
                                       for e in s["emails"]]}
                           for s in SERIES]}

    if not mailchimp.configured():
        return _blank(mailchimp.why_not())
    sent, why = mailchimp.reports()
    if sent is None:
        return _blank(why)

    def _match(name: str) -> List[Dict[str, Any]]:
        key = name.lower()
        return [r for r in sent if str(r.get("name") or "").lower().startswith(key)]

    series = []
    for definition in SERIES:
        emails = []
        for name in definition["emails"]:
            hits = _match(name)
            numbers = mailchimp.rates(hits)
            emails.append({
                "name": name,
                "sent": numbers["sent"], "opened": numbers["opened"], "clicked": numbers["clicked"],
                "bounced": numbers["bounced"], "unsubscribed": numbers["unsubscribed"],
                "open_rate": numbers["open_rate"], "click_rate": numbers["click_rate"],
                "bounce_rate": numbers["bounce_rate"],
                "sent_at": max((h.get("sent_at") or "" for h in hits), default="") or None,
                "in_mailchimp": bool(hits),
            })
        series.append({**definition, "on": on[definition["key"]], "emails": emails})
    return {"connected": True, "why": "", "series": series}


def _email_brought_in(db: Session, agents: List[User]) -> Dict[str, Any]:
    """What the emails brought in: paying agents, campaigns and money back, per series.

    The series is read from the last marketing email the agent clicked before buying. When
    Mailchimp is not connected the total still stands (the credit is stored); only the split by
    series is unknown, and that is said rather than guessed.
    """
    by_id = {u.id: u for u in agents}
    all_paid = (db.query(Boost).filter(Boost.paid_at.isnot(None))
                .filter(Boost.user_id.in_(list(by_id) or [-1])).all())
    first = _first_paid(all_paid)

    by_series: Dict[str, Dict[str, Any]] = {s["key"]: {"key": s["key"], "name": s["name"],
                                                       "paying": 0, "campaigns": 0,
                                                       "money_back_usd": 0.0}
                                            for s in SERIES}
    unknown = {"key": "unknown", "name": "A marketing email (series not readable)",
               "paying": 0, "campaigns": 0, "money_back_usd": 0.0}

    # One activity lookup per paying agent who was credited to Email - a handful of calls, not a
    # page full of them.
    clicks_by_agent: Dict[int, str] = {}
    for uid, boost in first.items():
        if _credit_of(boost, by_id.get(uid)) != "email":
            continue
        owner = by_id.get(uid)
        paid_at = _naive(boost.paid_at) or datetime.utcnow()
        title = ""
        if mailchimp.configured() and owner is not None:
            clicks, _why = mailchimp.click_events(owner.email or "", paid_at - timedelta(days=7))
            title = clicks[0]["title"] if clicks else ""
        clicks_by_agent[uid] = title

    for boost in all_paid:
        paid_at = _naive(boost.paid_at)
        if not paid_at:
            continue
        credit_boost = first.get(boost.user_id)
        if credit_boost is None or _credit_of(credit_boost, by_id.get(boost.user_id)) != "email":
            continue
        latest = clicks_by_agent.get(boost.user_id, "")
        bucket = unknown
        for definition in SERIES:
            stem = definition["emails"][0].split(" — ")[0].lower()
            if latest and latest.lower().startswith(stem):
                bucket = by_series[definition["key"]]
                break
        bucket["campaigns"] += 1
        bucket["money_back_usd"] = round(bucket["money_back_usd"] + _boost_price(boost), 2)
        if credit_boost is boost:
            bucket["paying"] += 1

    rows = list(by_series.values()) + ([unknown] if unknown["campaigns"] else [])
    return {
        "paying": sum(r["paying"] for r in rows),
        "campaigns": sum(r["campaigns"] for r in rows),
        "money_back_usd": round(sum(r["money_back_usd"] for r in rows), 2),
        "by_series": rows,
    }


@router.get("/admin/email-campaigns")
def email_campaigns(days: int = Query(30, ge=1, le=180),
                    user=Depends(team_access.needs("business")), db: Session = Depends(get_db)):
    """The list, the series we run, and what the emails brought in."""
    start, end = _window(days)
    window_days = (end - start).days
    agents = _agents(db)
    audience = mailchimp.audience()
    members, members_why = mailchimp.members()
    reports, reports_why = (mailchimp.reports() if mailchimp.configured()
                            else (None, mailchimp.why_not()))
    brought_in = _email_brought_in(db, agents)

    # The top band covers the emails sent in the window, the way the rest of the page does.
    in_window = [r for r in (reports or []) if _in_window(r.get("sent_at"), start, end)]
    totals = mailchimp.rates(in_window) if reports is not None else None
    opened = totals["opened"] if totals else None
    clicked = totals["clicked"] if totals else None
    tags = mailchimp.tag_counts(members) if members is not None else []

    # Consent: our own column is the record; Mailchimp's unsubscribe is the final word.
    unsubscribed_in_mailchimp = {row["email"] for row in (members or [])
                                 if row.get("status") == "unsubscribed"}
    opted_out = sum(1 for u in agents if getattr(u, "marketing_optin", True) is False)
    if members is None:
        unsubscribed: Optional[int] = None
    else:
        unsubscribed = len(unsubscribed_in_mailchimp) + sum(
            1 for u in agents
            if getattr(u, "marketing_optin", True) is False
            and (u.email or "").lower() not in unsubscribed_in_mailchimp)
        if not unsubscribed:
            unsubscribed = int(audience.get("unsubscribed") or 0)

    series = _series_with_reports(db)
    costs = _costs(db)
    cost = _prorated(costs["mailchimp_monthly_usd"], window_days)
    judged = _verdict(cost, brought_in["money_back_usd"])

    unavailable = []
    if not mailchimp.configured():
        unavailable.append({"metric": "audience", "reason": mailchimp.why_not()})
    elif members is None:
        unavailable.append({"metric": "audience", "reason": members_why})
    if mailchimp.configured() and reports is None:
        unavailable.append({"metric": "reports", "reason": reports_why})
    if cost is None:
        unavailable.append({"metric": "cost",
                            "reason": "The Mailchimp plan is not typed into Settings, so this "
                                      "channel has no cost yet"})

    return {
        "connected": bool(mailchimp.configured()),
        "why": mailchimp.why_not(),
        "days": window_days,
        "list_size": audience.get("contacts"),
        "audience": audience,
        "sent": totals["sent"] if totals else None,
        "opened": opened,
        "clicked": clicked,
        "bounced": totals["bounced"] if totals else None,
        "open_rate": totals["open_rate"] if totals else None,
        "click_rate": totals["click_rate"] if totals else None,
        "bounce_rate": totals["bounce_rate"] if totals else None,
        "paying": brought_in["paying"],
        "campaigns": brought_in["campaigns"],
        "money_back_usd": brought_in["money_back_usd"],
        "unsubscribed": unsubscribed,
        "opted_out_here": opted_out,
        "cost_usd": cost,
        "verdict": judged["verdict"],
        "verdict_text": judged["text"],
        "series": series["series"],
        "series_connected": series["connected"],
        "series_why": series.get("why", ""),
        "brought_in": brought_in,
        "tags": tags,
        "members_synced": members is not None,
        "export_csv": "/api/admin/email-campaigns/export.csv",
        "mailchimp_url": "https://admin.mailchimp.com/lists/",
        "unavailable": unavailable,
    }


@router.post("/admin/email-campaigns/sync")
def sync_email_audience(user=Depends(team_access.needs("business")),
                        db: Session = Depends(get_db)):
    """Put every real client in the audience with the tag that describes them."""
    result = mailchimp.sync(db)
    if not result.get("synced"):
        return {"synced": False, "why": result.get("why") or mailchimp.why_not()}
    return result


@router.post("/admin/email-campaigns/sync/run")
def sync_email_audience_clock(x_resmara_token: str = Header(default=""), db: Session = Depends(get_db)):
    """The Render clock's daily sync: new tags (has run a campaign, past client) reach Mailchimp
    the same day, so the right series starts and the wrong one stops. Machine token only."""
    import hmac
    expected = (getattr(settings, "PUBLISH_TOKEN", "") or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="RESMARA_PUBLISH_TOKEN is not configured")
    if not hmac.compare_digest(x_resmara_token or "", expected):
        raise HTTPException(status_code=403, detail="Bad machine token")
    return mailchimp.sync(db)


@router.put("/admin/email-campaigns/series/{key}")
def set_series(key: str, payload: Dict[str, Any],
               user=Depends(team_access.needs("business")), db: Session = Depends(get_db)):
    """Switch one series on or off. Off means the emails stay built but stop starting."""
    if key not in {s["key"] for s in SERIES}:
        raise HTTPException(status_code=404, detail="No such series")
    row = _settings(db)
    data = dict(row.payload or {})
    series = dict(data.get("series") or {})
    series[key] = bool(payload.get("on"))
    data["series"] = series
    row.payload = data
    db.commit()
    return {"key": key, "on": series[key]}


@router.get("/admin/email-campaigns/export.csv")
def export_emails(user=Depends(team_access.needs("business")), db: Session = Depends(get_db)):
    """The backup export: real clients only, unsubscribes marked."""
    body = mailchimp.csv_text(db)
    stamp = datetime.utcnow().date().isoformat()
    return PlainTextResponse(body, media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition":
                                      f'attachment; filename="resmara-clients-{stamp}.csv"'})


@router.patch("/marketing/consent")
def set_marketing_consent(payload: Dict[str, Any], db: Session = Depends(get_db),
                          user=Depends(get_current_user)):
    """The agent's own on/off switch for tips and updates (Engine 9, section 2, Consent).

    Off is stored here as well as pushed to Mailchimp on the next sync, so an unsubscribe
    survives a sync that has not run yet.
    """
    account = db.query(User).filter(User.email == user.email).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    account.marketing_optin = bool(payload.get("on", True))
    db.commit()
    return {"marketing_optin": bool(account.marketing_optin)}


# --------------------------------------------------------------------------- Website
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


def _tag_rows(body: str) -> List[Dict[str, Any]]:
    """One row per tag, decided by the ids the service actually holds.

    ``static/tags.js`` installs the GA4, Meta pixel and Clarity snippets from ``/api/public/tags``
    at run time, so grepping the homepage HTML for a vendor snippet reports "not found" about a
    tag that is running on every page. The ids are the truth; the HTML only has to load ``tags.js``.
    """
    from app.api import public as public_tags                       # same process, same settings

    try:
        ids = public_tags.tags()
    except Exception:                                               # noqa: BLE001 - a check, not a crash
        ids = {}
    loads = "tags.js" in (body or "")

    # Google Ads is the one tag that is still pasted into a page rather than injected by id.
    ads = "googleads.g.doubleclick.net" in (body or "")
    ads_row: Dict[str, Any] = {
        "name": "Google Ads tag", "status": "ok" if ads else "warn",
        "detail": "Found on the homepage" if ads
                  else "No Ads conversion tag on the homepage (optional: ad spend is read from Meta)",
    }
    rows: List[Dict[str, Any]] = []
    for name, key, env in (("Google tag", "ga4", "GA4_MEASUREMENT_ID"),
                           ("Meta pixel", "meta_pixel", "META_PIXEL_ID"),
                           ("Clarity", "clarity", "CLARITY_PROJECT_ID")):
        ident = (ids.get(key) or "").strip()
        if ident and loads:
            rows.append({"name": name, "status": "ok",
                         "detail": f"{ident} installed on every page by tags.js"})
        elif ident:
            rows.append({"name": name, "status": "warn",
                         "detail": f"{ident} is set, but the homepage does not load tags.js"})
        else:
            rows.append({"name": name, "status": "warn",
                         "detail": f"No id on the service ({env})"})
    rows.insert(1, ads_row)          # the console has always listed Ads right under Google tag
    return rows


def _tag_checks(base: str) -> List[Dict[str, Any]]:
    checks = []
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(base + "/")
        checks.append({"name": "Site answers", "status": "ok" if response.status_code < 400 else "fail",
                       "detail": f"HTTP {response.status_code}"})
        checks.extend(_tag_rows(response.text))
    except Exception as exc:                                    # noqa: BLE001
        checks.append({"name": "Site answers", "status": "fail", "detail": str(exc)[:200]})
    return checks


def _came_from(channel_group: str) -> str:
    """GA4's channel group -> the channel that gets the credit (Engine 9, section 3a)."""
    name = (channel_group or "").strip().lower()
    if "paid" in name:
        return "ad"
    if "email" in name or "newsletter" in name:
        return "email"
    return "website"


@router.get("/admin/website")
def website(days: int = Query(30, ge=1, le=180),
            user=Depends(team_access.needs("business")), db: Session = Depends(get_db)):
    """Visitors come from Google Analytics, sessions from Clarity, speed and tags from here.

    Plus the split the Marketing page needs: who came from an ad, on their own, or from an
    email - visitors, sign-ups and paying agents each. Everyone lands on the site, so this page
    shows all of it; the Website row on Marketing only counts the people who came on their own.
    """
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

    agents = _agents(db)
    by_id = {u.id: u for u in agents}
    signups_started = sum(1 for p in agents
                          if (_naive(p.created_at) or datetime.min) >= start)
    came_on_own = sum(1 for p in agents
                      if (_naive(p.created_at) or datetime.min) >= start
                      and attribution.channel_or_website(p.signup_source) == "website")

    all_paid = (db.query(Boost).filter(Boost.paid_at.isnot(None))
                .filter(Boost.user_id.in_(list(by_id) or [-1])).all())
    first = _first_paid(all_paid)
    paying_by_channel: Counter = Counter()
    for boost in all_paid:
        paid_at = _naive(boost.paid_at)
        if not paid_at or paid_at < start or first.get(boost.user_id) is not boost:
            continue
        paying_by_channel[_credit_of(boost, by_id.get(boost.user_id))] += 1

    # Visitors per channel: GA4's own channel groups, collapsed onto our three.
    visitors_by_channel: Dict[str, Optional[int]] = {k: None for k in attribution.CHANNELS}
    if traffic.get("connected"):
        visitors_by_channel = {k: 0 for k in attribution.CHANNELS}
        for row in traffic.get("sources") or []:
            visitors_by_channel[_came_from(row.get("name"))] += int(row.get("visitors") or 0)

    channel_split = [
        {"key": key,
         "name": {"ad": "Clicked an ad", "website": "Came on their own",
                  "email": "Clicked an email"}[key],
         "visitors": visitors_by_channel.get(key),
         "signups": sum(1 for p in agents
                        if (_naive(p.created_at) or datetime.min) >= start
                        and attribution.channel_or_website(p.signup_source) == key),
         "paying": int(paying_by_channel[key])}
        for key in attribution.CHANNELS
    ]

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
        "came_on_their_own": int(came_on_own),
        "paying": int(paying_by_channel["website"]),
        "speed_mobile": mobile,
        "speed_desktop": desktop,
        "clarity_sessions": clarity.get("sessions"),
        "clarity_url": clarity.get("url"),
        "checks": checks,
        "sources": traffic.get("sources") or [],
        "pages": traffic.get("pages") or [],
        "channel_split": channel_split,
        "unavailable": unavailable,
    }
