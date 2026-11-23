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
    """Connected means: a healthy login and a Page Resmara can post to (Meta spec, section 4).

    An agent connected before the connection record existed keeps their old answer until their
    first check builds one. A demo/simulated account never counts as connected.
    """
    from app.services import meta_engine
    conn = meta_engine.connection_for(db, user.id)
    if conn is not None and conn.last_checked_at:
        return bool((conn.capabilities or {}).get("fb_post"))
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


def campaigns_allowed(db: Session, user: User) -> bool:
    """Only a Facebook login is required: anything missing limits the campaign, never locks it."""
    from app.services import meta_engine
    if meta_engine.connection_for(db, user.id) is not None or getattr(user, "facebook_id", None):
        return True
    return meta_connected(db, user)


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
async def meta_audit(force: int = 0, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    """The audit (Engine 1 Part C): every line is Meta's own answer, by name, with photos.

    Called on every sign-in (cached for 10 minutes) and forced by Check again. Keeps the four-line
    ``checks`` shape the existing screens read, and adds the engine's full status: the outcome
    keys, at most three lines with Fix it now, the Page picker list and the setup to-do list.
    """
    from app.services import meta_engine
    st = await meta_engine.check(db, current_user, "check_again" if force else "sign_in", force=bool(force))
    if not st.get("facebook"):
        return {"connected": False, "message": META_REQUIRED_MESSAGE, "checks": [
            {"key": "page", "label": "Facebook Page found", "ok": False, "detail": "Not connected"},
            {"key": "page_admin", "label": "You have full control of that Page", "ok": False,
             "detail": "Not connected"},
            {"key": "instagram", "label": "Instagram business account linked", "ok": False,
             "detail": "Not connected"},
            {"key": "ad_account", "label": "Ad account with a payment method", "ok": False,
             "detail": "Not connected"},
        ], "book": "/api/onboarding/setup-session", **st, "connected": False}
    return {**st, "checks": meta_engine.legacy_checks(st),
            "check_again": "/api/onboarding/meta-audit?force=1",
            "book": "/api/onboarding/setup-session",
            "note": "Once you've done this, come back here and click Check again."}


@router.post("/onboarding/meta-page")
async def meta_choose_page(payload: dict, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    """Which Page is your business? / Change Page. Saves the pick, then re-checks that Page."""
    from app.services import meta_engine
    res = meta_engine.set_page(db, current_user, str((payload or {}).get("page_id") or ""))
    if not res.get("ok"):
        raise HTTPException(status_code=409 if res.get("error") == "page_taken" else 400, detail=res)
    st = await meta_engine.check(db, current_user, "check_again", force=True)
    return {**st, "checks": meta_engine.legacy_checks(st)}


def require_meta(db: Session, user: User) -> None:
    """The gate itself. Called before a campaign can be created (item 8)."""
    if getattr(user, "is_admin", False) or getattr(user, "is_system", False):
        return
    if not campaigns_allowed(db, user):
        raise HTTPException(status_code=409, detail={
            "error": "meta_required", "message": META_REQUIRED_MESSAGE,
            "connect": "/api/oauth/meta/connect",
            "book": "/api/onboarding/setup-session",
        })
