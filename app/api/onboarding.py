"""Onboarding state: what the account has actually done, and what it is still missing.

The owner's item 8 is a promise the product has to keep: the Meta connection is required and
cannot be skipped, every sign-in lands on Accounts until it is done, booking a setup session
stops the prompts but never unblocks "+ Campaign", and "Meta connected" plus "setup session
booked" are stored on the server rather than in a browser.

Everything here is read back from stored state — the account row, the OAuth callback's
timestamp, the booking — so a different browser, a cleared cache or a new device gives the same
answer. Nothing here claims a connection it cannot see.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import AdAccount, Boost, Event, User, get_db

router = APIRouter()

# The one sentence the agent sees when they close the Meta dialog without connecting.
META_REQUIRED_MESSAGE = "Please connect your Meta account so we can run campaigns for you."


def meta_connected(db: Session, user: User) -> bool:
    """Connected means: a Meta ad account with a live token we can act with.

    A demo/simulated account does not count as connected for the gate — it cannot publish, and
    treating it as done is how an agent reaches launch day with nothing connected.
    """
    if getattr(user, "meta_connected_at", None):
        return True
    account = (db.query(AdAccount)
               .filter(AdAccount.user_id == user.id, AdAccount.platform == "meta",
                       AdAccount.is_active.is_(True))
               .first())
    if not account:
        return False
    token = account.access_token or ""
    return bool(token) and not token.startswith("demo")


def state(db: Session, user: User) -> dict:
    connected = meta_connected(db, user)
    booked = getattr(user, "setup_booked_at", None)
    campaigns = db.query(Boost).filter(Boost.user_id == user.id).count()
    return {
        "meta_connected": connected,
        "meta_connected_at": getattr(user, "meta_connected_at", None),
        "setup_booked": bool(booked),
        "setup_booked_at": booked,
        "tour_seen": bool(getattr(user, "tour_seen_at", None)),
        "campaigns": campaigns,
        # + Campaign stays blocked until Meta is connected — a booked session is help, not a
        # substitute for the account Resmara has to post and spend through.
        "campaign_allowed": connected,
        "message": None if connected else META_REQUIRED_MESSAGE,
    }


class BookingIn(BaseModel):
    booked: bool = True
    when: Optional[str] = None
    reference: Optional[str] = None


@router.get("/onboarding/state")
def onboarding_state(db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    """What this account has done, for the sidebar, the Accounts page and the gate."""
    return state(db, current_user)


@router.post("/onboarding/setup-session")
def book_setup_session(body: BookingIn = BookingIn(), db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    """Record that the agent booked a setup session (the Calendly embed's confirmation).

    Kept separately from the Meta connection: the prompts stop, the campaign gate does not
    open. Booking is stored on the account so it survives a new browser.
    """
    if body.booked and not current_user.setup_booked_at:
        current_user.setup_booked_at = datetime.now(timezone.utc)
        db.add(Event(user_id=current_user.id, event_type="setup_session_booked",
                     payload={"when": body.when, "reference": body.reference}))
        db.commit()
    elif not body.booked and current_user.setup_booked_at:
        current_user.setup_booked_at = None
        db.commit()
    return state(db, current_user)


@router.post("/onboarding/tour-seen")
def tour_seen(db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    """The first-visit tour is shown once per account, not once per browser (step 3)."""
    if not current_user.tour_seen_at:
        current_user.tour_seen_at = datetime.now(timezone.utc)
        db.commit()
    return {"tour_seen": True}


@router.get("/onboarding/meta-audit")
async def meta_audit(db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    """The readiness audit behind step 1: page found, page admin, Instagram linked, card.

    Each line is measured with Meta's own answer. Anything we cannot measure says so instead of
    showing a tick, because a false tick here is the agent discovering it at launch.
    """
    from app.services.token_health import inspect_token, spend_readiness  # local: cycles

    account = (db.query(AdAccount)
               .filter(AdAccount.user_id == current_user.id, AdAccount.platform == "meta")
               .order_by(AdAccount.is_active.desc(), AdAccount.id.desc())
               .first())
    if not account:
        return {"connected": False, "message": META_REQUIRED_MESSAGE, "checks": [
            {"key": "page", "label": "Facebook Page found", "ok": False, "detail": "Not connected"},
            {"key": "page_admin", "label": "You are an admin of that Page", "ok": False,
             "detail": "Not connected"},
            {"key": "instagram", "label": "Instagram professional account linked", "ok": False,
             "detail": "Not connected"},
            {"key": "ad_account", "label": "Ad account with a payment method", "ok": False,
             "detail": "Not connected"},
        ], "book": "/api/onboarding/setup-session"}

    try:
        token_info = await inspect_token(account)
        spend = await spend_readiness(account)
    except Exception as exc:  # noqa: BLE001 - an unreadable account is reported, not guessed
        token_info, spend = {"error": f"{type(exc).__name__}: {exc}"[:300]}, {}

    token_ok = token_info.get("status") == "healthy" and not token_info.get("error")
    page_ok = bool(account.page_id) and token_ok
    ig_ok = bool(account.ig_user_id) and token_ok
    # Spend readiness is its own measured fact: account_status 1 means Meta considers the
    # account active, and the funding source is only claimed when Meta returned one.
    spend_ok = bool(spend.get("ok")) if spend else None
    checks = [
        {"key": "page", "label": "Facebook Page found", "ok": page_ok,
         "detail": account.page_id or "No Page on this connection",
         "fix": None if page_ok else "Choose a Page when you connect, or make one in Meta."},
        {"key": "page_admin", "label": "You are an admin of that Page", "ok": page_ok,
         "detail": "Meta returned this Page for your login" if page_ok else "Not confirmed",
         "fix": None if page_ok else "Ask the Page owner to make you an admin, then reconnect."},
        {"key": "instagram", "label": "Instagram professional account linked", "ok": ig_ok,
         "detail": account.ig_user_id or "No Instagram account on this Page",
         "fix": None if ig_ok else
         "Convert the Instagram account to a professional account and link it to the Page."},
        {"key": "ad_account", "label": "Ad account with a payment method", "ok": bool(spend_ok),
         "detail": (f"{account.advertiser_id} · {account.account_name or ''}".strip()
                    if spend_ok is not None else "Meta did not answer for this account"),
         "fix": None if spend_ok else
         "Add a payment method in Meta Ads Manager, then click Check again."},
    ]
    return {"connected": meta_connected(db, current_user), "checks": checks,
            "check_again": "/api/onboarding/meta-audit",
            "book": "/api/onboarding/setup-session",
            "note": "Once you've done this, come back here and click Check again."}


def require_meta(db: Session, user: User) -> None:
    """The gate itself. Called before a campaign can be created (item 8)."""
    if getattr(user, "is_admin", False) or getattr(user, "is_system", False):
        return
    if not meta_connected(db, user):
        raise HTTPException(status_code=409, detail={
            "error": "meta_required", "message": META_REQUIRED_MESSAGE,
            "connect": "/api/oauth/meta/connect",
            "book": "/api/onboarding/setup-session",
        })
