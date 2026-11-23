"""Where a sign-up and a purchase came from (Engine 9, section 1a).

Three rules, and this module is the only place they are decided:

1. **Every sign-up is stamped when the account is made**: the ad (its tracking tags on the
   link to resmara.com), an email click, or the website on its own. Saved on the account and
   never changed afterwards - a stamp that a later visit could rewrite would let a channel
   claim a customer it never brought in.
2. **Each paying agent counts once**, for the *last* thing that got them to buy their first
   campaign: the day-5 email they clicked four hours ago beats the ad they arrived from last
   month. That credit is written on the campaign they bought, at the moment it is paid, so
   every page after that reads one stored value instead of re-deriving it.
3. **Nothing is counted twice**: a channel is one of ``ad``, ``email`` or ``website``, the
   credit is one value per purchase, and the channel rows add up to the total.

Anything unknown falls back to ``website``, because every one of these people did land on the
site. It is the honest answer for somebody who typed the address in, and it does not invent an
ad or an email that never happened.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

log = logging.getLogger("resmara.attribution")

CHANNELS: Tuple[str, ...] = ("ad", "email", "website")
LABELS: Dict[str, str] = {"ad": "Digital ads", "email": "Email campaigns", "website": "Website"}

# How long after an email click a purchase still counts for Email (Engine 9: 7 days).
EMAIL_CLICK_WINDOW = timedelta(days=7)

_AD_SOURCES = {"meta", "facebook", "fb", "instagram", "ig", "meta_ads", "fbads", "paid"}
_AD_MEDIA = {"paid", "paid_social", "paidsocial", "cpc", "ppc", "display", "social-paid"}
_EMAIL_SOURCES = {"mailchimp", "email", "newsletter", "mail"}
_EMAIL_MEDIA = {"email", "newsletter", "mail"}

_DETAIL_KEYS = ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
                "fbclid", "gclid", "referrer", "landing", "ad_id", "campaign_id")


def _clean(value: Any) -> str:
    return str(value or "").strip()[:200]


def classify(payload: Optional[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    """``{"utm_source": "facebook", "utm_medium": "paid", ...}`` -> ``("ad", detail)``.

    Only the keys we understand are kept, so the stored detail is evidence a person can read
    rather than whatever a browser happened to append to the query string.
    """
    raw = payload if isinstance(payload, dict) else {}
    detail = {k: _clean(raw.get(k)) for k in _DETAIL_KEYS if _clean(raw.get(k))}
    source = (detail.get("utm_source") or "").lower()
    medium = (detail.get("utm_medium") or "").lower()

    if detail.get("fbclid") or detail.get("ad_id"):
        return "ad", detail
    if medium in _AD_MEDIA or source in _AD_SOURCES:
        return "ad", detail
    if detail.get("gclid"):
        # Google Ads is not where Resmara spends today (Meta is), but a click id is still a
        # paid click; counting it under Digital ads keeps the money side honest.
        return "ad", detail
    if medium in _EMAIL_MEDIA or source in _EMAIL_SOURCES:
        return "email", detail
    return "website", detail


def stamp_signup(db, user, payload: Optional[Dict[str, Any]]) -> str:
    """Write the stamp once. Returns the channel it stored.

    Called from ``/api/auth/register``. An account that somehow already carries a stamp keeps
    it: the rule is "never changed after", so a retried request cannot re-attribute a customer.
    """
    if getattr(user, "signup_source", None):
        return str(user.signup_source)
    channel, detail = classify(payload)
    user.signup_source = channel
    user.signup_source_detail = detail or None
    try:
        db.flush()
    except Exception as exc:                                     # noqa: BLE001 - a stamp, not a crash
        log.info("could not stamp sign-up source: %s", exc)
    return channel


def _mailchimp_clicked_recently(email: str, since: datetime) -> bool:
    """Did this address click a marketing email in the window? False when Mailchimp is unset.

    A Mailchimp that is not connected cannot know, and guessing "no" is right here: the credit
    then falls back to the sign-up stamp, which is a real observation.
    """
    try:
        from app.services import mailchimp
        return bool(mailchimp.clicked_since(email, since))
    except Exception as exc:                                     # noqa: BLE001 - never block a sale
        log.info("mailchimp click lookup failed: %s", exc)
        return False


def credit_channel(db, user, at: datetime) -> Tuple[str, Dict[str, Any]]:
    """The last thing that got this agent to buy, as of ``at``.

    Email beats the sign-up stamp only inside the 7-day window - a click last month is not what
    sold this campaign today. Everything else is the stamp, and anything blank is Website.
    """
    when = at if isinstance(at, datetime) else datetime.utcnow()
    detail: Dict[str, Any] = {"decided_at": when.replace(microsecond=0).isoformat()}

    if _mailchimp_clicked_recently(getattr(user, "email", "") or "", when - EMAIL_CLICK_WINDOW):
        detail["because"] = f"clicked a marketing email in the {EMAIL_CLICK_WINDOW.days} days before buying"
        return "email", detail

    stored = getattr(user, "signup_source", None)
    signup_detail = getattr(user, "signup_source_detail", None) or {}
    if isinstance(signup_detail, dict) and signup_detail:
        detail["signup"] = {k: signup_detail.get(k) for k in ("utm_source", "utm_medium",
                                                             "utm_campaign", "ad_id", "campaign_id")
                            if signup_detail.get(k)}
    if stored in CHANNELS:
        detail["because"] = "the stamp taken when they signed up"
        return str(stored), detail

    detail["because"] = "no stamp and no email click: they came to the site on their own"
    return "website", detail


def record_purchase(db, boost, at: Optional[datetime] = None) -> Optional[str]:
    """Stamp the campaign with its channel, once, when the payment lands.

    Deliberately idempotent: a Stripe webhook retry re-arrives with the same campaign, and the
    first credit must not be replaced by a second, later one.
    """
    if getattr(boost, "paid_source", None):
        return str(boost.paid_source)
    try:
        from app.db.session import User
        user = db.query(User).filter(User.id == boost.user_id).first()
        if user is None:
            return None
        channel, detail = credit_channel(db, user, at or datetime.utcnow())
        boost.paid_source = channel
        boost.paid_source_detail = detail
        db.flush()
        return channel
    except Exception as exc:                                     # noqa: BLE001 - never block a payment
        log.info("could not stamp purchase credit: %s", exc)
        return None


def channel_or_website(value: Optional[str]) -> str:
    return value if value in CHANNELS else "website"
