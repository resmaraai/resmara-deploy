"""Which campaigns are due for their next round — and, when told to apply, the round itself.

"Run it until it sells" promises a brand-new 14-day round every two weeks until the listing is
pending or sold. This module is the whole promise in one place:

* ``review()`` decides *which* campaigns are due and which are held. Read-only, so it can be run
  as often as anyone likes and shown to an agent as "what tonight would do".
* ``apply()`` does the round (Engine 8, docs/engines/engine-8-brain.md): copy the campaign
  forward, BUILD it first, and charge the saved card only when the build succeeded (a failed build
  is never charged). Then it's approved automatically (the agent approved the series when they
  turned it on), launched to go live the day the current round ends, and the agent gets one email.

Rules, in the order they are applied:

* ``until_sold`` must be on. Off is off.
* Sold ends it: the flag is cleared and nothing is charged.
* Pending pauses it and it STAYS ON: no round is built or charged while it's paused; if the home
  comes back on the market with the same agent, Engine 6 resumes it and the renewals continue.
* ``paused_at`` set means the campaign is paused (by the agent or pending): held, no charge.
* The round runs from its go-live date (else ``launched_at``, else ``created_at``) for its days plus
  any paused days. It's due within ``BUILD_AHEAD_DAYS`` of its end.
* A declined card: nothing is charged, nothing goes live, the built round is kept (14 days); it's
  tried once a day up to 3 times, then one email with Check billing. As soon as a working card is
  saved, it's charged and the waiting round goes live.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import Boost

ROUND_DAYS = 14
BUILD_AHEAD_DAYS = 3
CHARGE_CENTS = 3900           # the $39 the explainer quotes; billing.price_for() is the source
ENDED_STATUSES = ("sold",)            # pending pauses (held), it doesn't end the series


def _aware(value: Optional[datetime]) -> Optional[datetime]:
    """Postgres hands back aware datetimes for timestamptz and sqlite gives naive ones."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def round_start(boost: Boost) -> Optional[datetime]:
    live = getattr(boost, "go_live_date", None)
    if live:
        try:
            return datetime.strptime(str(live)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return _aware(getattr(boost, "launched_at", None)) or _aware(getattr(boost, "created_at", None))


def round_ends_on(boost: Boost) -> Optional[datetime]:
    start = round_start(boost)
    days = int(getattr(boost, "campaign_days", None) or ROUND_DAYS) + int(getattr(boost, "paused_days", 0) or 0)
    return start + timedelta(days=days) if start else None


def _row(boost: Boost, now: datetime, why: Optional[str] = None) -> Dict[str, Any]:
    ends = round_ends_on(boost)
    starts = round_start(boost)
    days_left = None if ends is None else (ends - now).total_seconds() / 86400.0
    return {
        "boost_id": boost.id,
        "user_id": boost.user_id,
        "address": boost.address,
        "round": int(getattr(boost, "repeat_round", 0) or 0),
        "next_round": int(getattr(boost, "repeat_round", 0) or 0) + 1,
        "round_started_at": starts.isoformat() if starts else None,
        "round_ends_at": ends.isoformat() if ends else None,
        "days_left": None if days_left is None else round(days_left, 2),
        "charge_cents": CHARGE_CENTS,
        "why": why,
    }


def review(db: Session, now: Optional[datetime] = None,
           ahead_days: int = BUILD_AHEAD_DAYS) -> Dict[str, Any]:
    """Everything the renewal clock knows, split by what will happen to it.

    ``due`` is what a builder would act on tonight, ``held`` is paused (no charge), ``ending`` is a
    listing that went pending or sold and should have its flag cleared, and ``too_early`` is the
    rest of the running fleet - reported so a quiet night is visibly quiet rather than a bug.
    """
    now = _aware(now) or datetime.now(timezone.utc)
    due: List[Dict[str, Any]] = []
    held: List[Dict[str, Any]] = []
    ending: List[Dict[str, Any]] = []
    too_early: List[Dict[str, Any]] = []

    rows = db.query(Boost).filter(Boost.until_sold.is_(True)).all()
    for boost in rows:
        status = (getattr(boost, "listing_status", "") or "").strip().lower()
        if status in ENDED_STATUSES:
            ending.append(_row(boost, now, "listing is %s" % status))
            continue
        if status == "pending":
            held.append(_row(boost, now, "pending, so it waits (still on) and nothing is charged"))
            continue
        if getattr(boost, "paused_at", None) is not None:
            held.append(_row(boost, now, "paused, so the next round waits and nothing is charged"))
            continue
        ends = round_ends_on(boost)
        if ends is None:
            too_early.append(_row(boost, now, "no launch date yet, so there is nothing to renew"))
            continue
        days_left = (ends - now).total_seconds() / 86400.0
        if days_left <= ahead_days:
            due.append(_row(boost, now))
        else:
            too_early.append(_row(boost, now))

    return {
        "checked_at": now.isoformat(),
        "build_ahead_days": ahead_days,
        "round_days": ROUND_DAYS,
        "due": due,
        "held": held,
        "ending": ending,
        "too_early": too_early,
        "counts": {"due": len(due), "held": len(held), "ending": len(ending),
                   "too_early": len(too_early), "on_autopilot": len(rows)},
    }


# --------------------------------------------------------------------------- the money half

log = logging.getLogger("resmara.renewals")

def apply_enabled() -> bool:
    """Charging on the server's clock is switched on by Dan (RESMARA_RENEWALS_APPLY=1). Off, the
    clock only reports what it would do, so a mistyped schedule can never start charging cards."""
    return os.getenv("RESMARA_RENEWALS_APPLY", "").strip().lower() in ("1", "true", "yes", "on")


MAX_RENEWALS_PER_RUN = 3          # a runaway loop must not charge a card more than this
DECLINE_COOLDOWN_HOURS = 24       # a declined card is retried once a day, not every tick
DECLINE_TRIES = 3                 # then one email with Check billing, and it waits for a card
KEEP_BUILT_DAYS = 14              # a built round waiting on a card is rebuilt fresh after this


def _next_round(db: Session, boost: Boost, owner, go_live: Optional[datetime] = None) -> Boost:
    """Copy the campaign forward into round n+1: the house, the facts, the brand, the links and the
    photos; never anything that was paid for. It goes live the day the current round ends."""
    from app.db.session import Asset

    prior = (db.query(func.max(Boost.repeat_round))
             .filter(Boost.user_id == owner.id, Boost.address == boost.address).scalar())
    go_live = go_live or round_ends_on(boost) or (datetime.now(timezone.utc) + timedelta(days=1))
    fresh = Boost(user_id=owner.id, address=boost.address, tier=boost.tier,
                  campaign_days=boost.campaign_days, ad_budget_usd=boost.ad_budget_usd,
                  property_facts=boost.property_facts, brand_profile=boost.brand_profile or {},
                  main_status="In Progress", stage="PENDING",
                  listing_url=boost.listing_url, destination_url=boost.destination_url,
                  video_url=boost.video_url, listing_sources=list(boost.listing_sources or []),
                  go_live_date=go_live.strftime("%Y-%m-%d"),
                  budget_confirmed_at=getattr(boost, "budget_confirmed_at", None),
                  parent_boost_id=boost.id,
                  repeat_round=int(prior or 0) + 1,
                  until_sold=False)        # on only once it's paid, so an unpaid round is never "due"
    db.add(fresh)
    db.flush()
    for a in db.query(Asset).filter(Asset.boost_id == boost.id, Asset.kind == "photo").all():
        db.add(Asset(user_id=owner.id, boost_id=fresh.id, filename=a.filename, url=a.url,
                     original_name=a.original_name, kind=a.kind or "photo", room=a.room,
                     social_score=a.social_score, shape=a.shape, see=a.see, story=a.story,
                     tags=list(a.tags or []), content_type=a.content_type,
                     tagged_by=a.tagged_by or "none"))
    db.commit()
    db.refresh(fresh)
    return fresh


def waiting_round(db: Session, boost: Boost) -> Optional[Boost]:
    """A next round that was built but not paid for yet (its card was declined)."""
    return (db.query(Boost).filter(Boost.parent_boost_id == boost.id, Boost.paid_at.is_(None))
            .order_by(Boost.id.desc()).first())


def _events(db: Session, boost_id: int, kind: str):
    from app.db.session import Event
    return db.query(Event).filter(Event.boost_id == boost_id, Event.event_type == kind).order_by(Event.id.asc()).all()


def declines(db: Session, fresh: Boost) -> List[Any]:
    """Declines on this waiting round since the last time a card was saved."""
    rows = _events(db, fresh.id, "renewal_declined")
    saved = _events(db, fresh.id, "renewal_card_saved")
    if saved:
        last = _aware(saved[-1].created_at)
        rows = [r for r in rows if _aware(r.created_at) and last and _aware(r.created_at) > last]
    return rows


def _declined_recently(db: Session, boost_id: int, now: datetime) -> bool:
    from app.db.session import Event

    cutoff = now - timedelta(hours=DECLINE_COOLDOWN_HOURS)
    row = (db.query(Event).filter(Event.boost_id == boost_id,
                                  Event.event_type.in_(("renewal_declined", "renewal_card_saved")))
           .order_by(Event.id.desc()).first())
    if not row or row.event_type == "renewal_card_saved":
        return False
    when = _aware(getattr(row, "created_at", None))
    return bool(when and when >= cutoff)


def _drop(db: Session, fresh: Boost) -> None:
    from app.db.session import Asset, ListingSite, Post
    db.query(Post).filter(Post.boost_id == fresh.id).delete()
    db.query(Asset).filter(Asset.boost_id == fresh.id).delete()
    db.query(ListingSite).filter(ListingSite.boost_id == fresh.id).delete()
    db.delete(fresh)
    db.commit()


def stop_finished(db: Session, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Sold ends Run it until it sells. (Pending only pauses it: Engine 8, section 5.)"""
    from app.db.session import Event

    now = _aware(now) or datetime.now(timezone.utc)
    stopped = []
    for boost in db.query(Boost).filter(Boost.until_sold.is_(True)).all():
        status = (getattr(boost, "listing_status", "") or "").strip().lower()
        if status not in ENDED_STATUSES:
            continue
        boost.until_sold = False
        boost.until_sold_at = None
        db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="until_sold_stopped",
                     payload={"listing_status": status, "at": now.isoformat()}))
        stopped.append({"boost_id": boost.id, "address": boost.address, "listing_status": status})
    if stopped:
        db.commit()
    return stopped


def _weekday(day: str) -> str:
    try:
        d = datetime.strptime(day[:10], "%Y-%m-%d")
    except (TypeError, ValueError):
        return "soon"
    today = datetime.now(timezone.utc).date()
    if d.date() == today:
        return "today"
    if d.date() == today + timedelta(days=1):
        return "tomorrow"
    return d.strftime("%A")


async def _auto_launch(db: Session, fresh: Boost, owner, launch_fn: Optional[Callable]) -> Dict[str, Any]:
    """Approved automatically and launched to go live on its go-live date (Engine 8, section 3)."""
    from app.db.session import Event, Post
    for post in db.query(Post).filter(Post.boost_id == fresh.id).all():
        post.client_status = "approved"
    fresh.main_status = "Approved"
    fresh.stage = "APPROVED"
    db.add(Event(user_id=owner.id, boost_id=fresh.id, event_type="campaign_approved",
                 payload={"by": "run it until it sells", "auto": True}))
    db.commit()
    if launch_fn is None:
        from app.services.launch import launch_boost
        launch_fn = lambda b, u, d: launch_boost(b, u, d, auto_approve=False)
    try:
        result = await launch_fn(fresh, owner, db)
    except Exception as exc:  # noqa: BLE001 - the posts still go out; the ad waits with one fix
        result = {"status": "failed", "detail": f"{type(exc).__name__}: {exc}"[:300]}
    if not fresh.launched_at:
        fresh.launched_at = datetime.now(timezone.utc)
    db.commit()
    return result if isinstance(result, dict) else {"status": str(result)}


async def renew(db: Session, boost: Boost, owner, *, now: Optional[datetime] = None,
                go_live: Optional[datetime] = None, until_sold: bool = True,
                charge_fn: Optional[Callable] = None, cards_fn: Optional[Callable] = None,
                build_fn: Optional[Callable] = None, launch_fn: Optional[Callable] = None,
                send: bool = True) -> Dict[str, Any]:
    """One round: build first, charge only when the build succeeded, approve, launch, one email.
    Also the one-click Run it again ($39), with until_sold=False and go-live tomorrow."""
    from app.db.session import Event, Order
    from app.services import billing, campaign_emails, listing_site

    now = _aware(now) or datetime.now(timezone.utc)
    charge_fn = charge_fn or billing.charge_saved_card
    cards_fn = cards_fn or billing.list_cards

    fresh = waiting_round(db, boost)
    if fresh is not None and _aware(fresh.created_at) and now - _aware(fresh.created_at) > timedelta(days=KEEP_BUILT_DAYS):
        _drop(db, fresh)          # never stale: rebuilt fresh once the card works
        fresh = None
    built_now = False
    if fresh is None:
        fresh = _next_round(db, boost, owner, go_live=go_live)
        error = ""
        for attempt in (1, 2):
            try:
                if build_fn is not None:
                    await build_fn(fresh, db)
                else:
                    from app.services.content_engine import build_campaign
                    await build_campaign(fresh, db)
                error = ""
                break
            except Exception as exc:  # noqa: BLE001 - retried once, then the team is told
                error = f"{type(exc).__name__}: {exc}"[:300]
        if error:
            db.add(Event(user_id=owner.id, boost_id=boost.id, event_type="renewal_build_failed",
                         payload={"error": error}))
            db.commit()
            _drop(db, fresh)
            listing_site._alert_team(db, boost, f"A Run it until it sells round couldn't be built: {error}. Nothing was charged.")
            return {"status": "failed", "why": "the build failed twice, so nothing was charged: " + error}
        built_now = True

    if _declined_recently(db, fresh.id, now) and not built_now:
        return {"status": "skipped", "new_boost_id": fresh.id, "why": "declined in the last day; tried once a day"}
    if len(declines(db, fresh)) >= DECLINE_TRIES:
        return {"status": "on_hold", "new_boost_id": fresh.id, "why": "card declined 3 times; waiting for a card"}

    cents = billing.price_for(fresh)
    round_no = billing.round_of(fresh)
    cards = []
    try:
        cards = await cards_fn(getattr(owner, "stripe_customer_id", "") or "")
    except Exception as exc:  # noqa: BLE001 - unreadable cards = no cards
        log.info("renewal %s: card list failed: %s", boost.id, exc)
    charge = {"paid": False, "message": "no saved card"}
    if cards:
        try:
            charge = await charge_fn(customer_id=owner.stripe_customer_id, payment_method_id=cards[0]["id"],
                                     cents=cents, boost_id=fresh.id, user_id=owner.id,
                                     address=fresh.address or "", round_no=round_no)
        except Exception as exc:  # noqa: BLE001 - nothing was charged
            charge = {"paid": False, "message": f"{type(exc).__name__}: {exc}"[:300]}

    if not charge.get("paid"):
        db.add(Event(user_id=owner.id, boost_id=fresh.id, event_type="renewal_declined",
                     payload={"message": (charge.get("message") or "")[:300], "from_boost": boost.id,
                              "payment_intent": charge.get("payment_intent")}))
        db.commit()
        tries = len(declines(db, fresh))
        if tries >= DECLINE_TRIES:
            notes = dict(boost.listing_notes or {})
            notes["renewal_hold"] = "declined"
            boost.listing_notes = notes
            db.commit()
            if send:
                campaign_emails.declined(db, boost)
        return {"status": "declined", "new_boost_id": fresh.id, "tries": tries,
                "why": charge.get("message") or "the card was declined"}

    paid_at = datetime.now(timezone.utc)
    db.add(Order(user_id=owner.id, boost_id=fresh.id, amount_cents=cents, currency=billing.CURRENCY,
                 status="paid", paid_at=paid_at, stripe_payment_intent=charge.get("payment_intent"),
                 tax_cents=charge.get("tax_cents") or 0, kind="round" if until_sold else "run_again"))
    fresh.paid_at, fresh.paid_amount_cents = paid_at, cents
    # The waiting round goes live on its day, or the next morning if the old round already ended.
    live = round_start(fresh)
    if live is not None and live.date() < now.date() + timedelta(days=1) and not built_now:
        tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        from app.services.campaign_state import shift_posts
        shift_posts(db, fresh, tomorrow - live)
        fresh.go_live_date = tomorrow.strftime("%Y-%m-%d")
    fresh.until_sold = bool(until_sold)
    fresh.until_sold_at = paid_at if until_sold else None
    boost.until_sold, boost.until_sold_at = False, None
    notes = dict(boost.listing_notes or {})
    notes.pop("renewal_hold", None)
    boost.listing_notes = notes
    db.add(Event(user_id=owner.id, boost_id=fresh.id, event_type="renewal_charged",
                 payload={"from_boost": boost.id, "amount_cents": cents, "round": round_no,
                          "payment_intent": charge.get("payment_intent")}))
    db.commit()
    # The website: same link, the new round's story (Engine 5, section 9).
    try:
        listing_site.promote(db, fresh)
    except Exception as exc:  # noqa: BLE001
        log.info("renewal %s: website not refreshed: %s", fresh.id, exc)
    launched = await _auto_launch(db, fresh, owner, launch_fn)
    if send:
        campaign_emails.renewed(db, fresh, round_no + 1, _weekday(fresh.go_live_date))
    return {"status": "renewed", "new_boost_id": fresh.id, "amount_cents": cents, "round": round_no,
            "paid": True, "launch": launched.get("status"), "go_live": fresh.go_live_date,
            "why": "built, charged, approved, and goes live " + _weekday(fresh.go_live_date)}


async def apply(db: Session, now: Optional[datetime] = None, limit: int = MAX_RENEWALS_PER_RUN,
                *, charge_fn: Optional[Callable] = None, cards_fn: Optional[Callable] = None,
                build_fn: Optional[Callable] = None, launch_fn: Optional[Callable] = None,
                email_fn: Optional[Callable] = None, only_user: Optional[int] = None,
                send: bool = True) -> Dict[str, Any]:
    """Every campaign that's due (and every waiting round, when a card was just saved).

    Every external action is injectable so the whole path runs against stubs: the one thing that
    must never be guessed at is whether this code charges a card."""
    from app.db.session import Boost as B, User

    now = _aware(now) or datetime.now(timezone.utc)
    stopped = stop_finished(db, now)
    plan = review(db, now=now)
    results: List[Dict[str, Any]] = []
    rows = plan["due"]
    if only_user is not None:
        rows = [r for r in rows if r["user_id"] == only_user]
    for row in rows[:max(1, int(limit))]:
        boost = db.get(B, row["boost_id"])
        if boost is None or not boost.until_sold:
            continue
        owner = db.get(User, boost.user_id)
        if owner is None:
            results.append({**row, "status": "skipped", "why": "the campaign has no owner"})
            continue
        if getattr(owner, "billing_hold", None):
            # Engine 10, section 9: a chargeback pauses Run it until it sells and new charges.
            results.append({**row, "status": "skipped", "why": "payments on this account are paused (dispute)"})
            continue
        try:
            out = await renew(db, boost, owner, now=now, charge_fn=charge_fn, cards_fn=cards_fn,
                              build_fn=build_fn, launch_fn=launch_fn, send=send)
        except Exception as exc:  # noqa: BLE001 - the failure is the report
            db.rollback()
            out = {"status": "failed", "why": f"{type(exc).__name__}: {exc}"[:300]}
        results.append({**row, **out})
    count = lambda k: sum(1 for r in results if r["status"] == k)
    return {"checked_at": now.isoformat(), "applied": results, "stopped": stopped,
            "counts": {"due": len(plan["due"]), "renewed": count("renewed"), "declined": count("declined"),
                       "on_hold": count("on_hold"), "failed": count("failed"), "skipped": count("skipped")}}


async def card_saved(db: Session, user_id: int, **kw) -> Dict[str, Any]:
    """A working card was saved: every round waiting on a declined card is tried now."""
    from app.db.session import Event
    waiting = []
    for boost in db.query(Boost).filter(Boost.user_id == user_id, Boost.until_sold.is_(True)).all():
        fresh = waiting_round(db, boost)
        if fresh is not None and declines(db, fresh):
            db.add(Event(user_id=user_id, boost_id=fresh.id, event_type="renewal_card_saved", payload={}))
            waiting.append(boost.id)
    db.commit()
    if not waiting:
        return {"waiting": 0}
    return await apply(db, only_user=user_id, **kw)


async def run_again(db: Session, boost: Boost, owner, **kw) -> Dict[str, Any]:
    """Run it again · $39 (Engine 8, section 8): one click builds a fresh round the same way, charges
    the saved card, and it goes live the next morning (or when this round ends, if it's still running)."""
    status = (boost.listing_status or "").lower()
    if status in ("pending", "sold"):
        return {"status": "skipped", "why": f"the listing is {status}"}
    end = round_ends_on(boost)
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    go_live = end if end and end > tomorrow else tomorrow
    return await renew(db, boost, owner, go_live=go_live, until_sold=False, **kw)
