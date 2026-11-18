"""Which campaigns are due for their next round — and, when told to apply, the round itself.

"Run it until it sells" promises a brand-new 14-day round every two weeks until the listing is
pending or sold. This module is the whole promise in one place:

* ``review()`` decides *which* campaigns are due and which are held. Read-only, so it can be run
  as often as anyone likes and shown to an agent as "what tonight would do".
* ``apply()`` does the money: charge the saved card, copy the campaign forward as the next round
  (the same copy ``POST /boosts/{id}/again`` makes), build it, tell the agent. It charges through
  ``billing.charge_saved_card`` — the same tested off-session path Build uses — so a renewal can
  never be a different kind of payment from a campaign the agent bought themselves.

Rules, in the order they are applied:

* ``until_sold`` must be on. Off is off.
* A listing that is ``pending`` or ``sold`` is finished: the flag is cleared and nothing is
  charged. That is the "it stops by itself" the explainer promises.
* ``paused_at`` set means the campaign is paused: the next round is held with no charge until it
  resumes, so a paused campaign never renews behind the agent's back.
* The round is 14 days from ``launched_at`` (``created_at`` when a campaign was never launched, so
  a draft cannot sit in "due" forever). A round is due once it is within ``BUILD_AHEAD_DAYS`` of
  its end, which is the "ready to look over 3 days before it starts" the explainer promises.
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
ENDED_STATUSES = ("pending", "sold")


def _aware(value: Optional[datetime]) -> Optional[datetime]:
    """Postgres hands back aware datetimes for timestamptz and sqlite gives naive ones."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def round_start(boost: Boost) -> Optional[datetime]:
    return _aware(getattr(boost, "launched_at", None)) or _aware(getattr(boost, "created_at", None))


def round_ends_on(boost: Boost) -> Optional[datetime]:
    start = round_start(boost)
    return start + timedelta(days=ROUND_DAYS) if start else None


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

MAX_RENEWALS_PER_RUN = 3          # a runaway loop must not charge a card more than this
DECLINE_COOLDOWN_HOURS = 24       # a declined card is retried once a day, not every tick


def _next_round(db: Session, boost: Boost, owner) -> Boost:
    """Copy the campaign forward into round n+1 — the same copy ``/boosts/{id}/again`` makes.

    Round n+1 carries the house, the facts, the brand, the links and the photos, so nothing is
    retyped; what it does not carry is anything that was paid for. It is created unpaid, charged
    by the caller, and only then does it become a campaign someone can open.
    """
    from app.db.session import Asset

    prior = (db.query(func.max(Boost.repeat_round))
             .filter(Boost.user_id == owner.id, Boost.address == boost.address).scalar())
    fresh = Boost(user_id=owner.id, address=boost.address, tier=boost.tier,
                  campaign_days=boost.campaign_days, ad_budget_usd=boost.ad_budget_usd,
                  property_facts=boost.property_facts, brand_profile=boost.brand_profile or {},
                  main_status="In Progress", stage="PENDING",
                  listing_url=boost.listing_url, destination_url=boost.destination_url,
                  video_url=boost.video_url,
                  parent_boost_id=boost.id,
                  repeat_round=int(prior or 0) + 1,
                  until_sold=True,
                  until_sold_at=datetime.now(timezone.utc))
    db.add(fresh)
    db.flush()
    for a in db.query(Asset).filter(Asset.boost_id == boost.id).all():
        db.add(Asset(user_id=owner.id, boost_id=fresh.id, filename=a.filename, url=a.url,
                     original_name=a.original_name, kind=a.kind or "photo", room=a.room,
                     social_score=a.social_score, shape=a.shape, see=a.see, story=a.story,
                     tags=list(a.tags or []), content_type=a.content_type,
                     tagged_by=a.tagged_by or "none"))
    db.commit()
    db.refresh(fresh)
    return fresh


def _declined_recently(db: Session, boost_id: int, now: datetime) -> bool:
    from app.db.session import Event

    cutoff = now - timedelta(hours=DECLINE_COOLDOWN_HOURS)
    row = (db.query(Event).filter(Event.boost_id == boost_id,
                                  Event.event_type == "renewal_declined")
           .order_by(Event.id.desc()).first())
    if not row:
        return False
    when = getattr(row, "created_at", None)
    when = when if when is None or when.tzinfo else when.replace(tzinfo=timezone.utc)
    return bool(when and when >= cutoff)


def stop_finished(db: Session, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """Clear the flag on campaigns whose listing has gone pending or sold.

    This is the promise "it stops by itself". Doing it here rather than in the web app means it
    happens on the same clock that would otherwise charge, so there is no window where a sold
    listing renews.
    """
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


async def apply(db: Session, now: Optional[datetime] = None, limit: int = MAX_RENEWALS_PER_RUN,
                *, charge_fn: Optional[Callable] = None, cards_fn: Optional[Callable] = None,
                build_fn: Optional[Callable] = None,
                email_fn: Optional[Callable] = None) -> Dict[str, Any]:
    """Charge and build the next round for every campaign that is due.

    Every external action is injectable (``charge_fn``, ``cards_fn``, ``build_fn``,
    ``email_fn``) so the whole path can be exercised against stubs — the one thing that must
    never be guessed at is whether this code charges a card, and a test that needs a live
    Stripe account to prove it is a test nobody runs.

    Returns one entry per campaign considered: ``status`` is ``renewed``, ``no_card``,
    ``declined``, ``skipped`` or ``failed``, with the reason alongside.
    """
    from app.db.session import Boost as B, Event, Order, User
    from app.services import billing

    charge_fn = charge_fn or billing.charge_saved_card
    cards_fn = cards_fn or billing.list_cards
    email_fn = email_fn if email_fn is not None else _default_email
    skip_build = os.getenv("UNTIL_SOLD_BUILD", "1").strip() in ("0", "false", "no")

    async def _build(fresh, owner):
        if skip_build:
            return {"built": False, "why": "UNTIL_SOLD_BUILD is off"}
        if build_fn is not None:
            return await build_fn(fresh, db)
        from app.services.content_engine import build_campaign
        result = await build_campaign(fresh, db)
        return {"built": True, "posts": (result or {}).get("posts_created")}

    now = _aware(now) or datetime.now(timezone.utc)
    plan = review(db, now=now)
    results: List[Dict[str, Any]] = []

    for row in plan["due"][:max(1, int(limit))]:
        boost = db.get(B, row["boost_id"])
        if boost is None or not boost.until_sold:
            continue
        owner = db.get(User, boost.user_id)
        if owner is None:
            results.append({**row, "status": "skipped", "why": "the campaign has no owner"})
            continue
        if _declined_recently(db, boost.id, now):
            results.append({**row, "status": "skipped",
                            "why": "a card was declined in the last %d hours" % DECLINE_COOLDOWN_HOURS})
            continue

        cards = []
        try:
            cards = await cards_fn(getattr(owner, "stripe_customer_id", "") or "")
        except Exception as exc:                        # noqa: BLE001 - unreadable cards = no cards
            log.info("renewal %s: card list failed: %s", boost.id, exc)
        if not cards:
            results.append({**row, "status": "no_card",
                            "why": "no saved card, so no renewal was charged"})
            continue
        card = cards[0]

        fresh = None
        try:
            fresh = _next_round(db, boost, owner)
            cents = billing.price_for(fresh)
            round_no = billing.round_of(fresh)
            charge = await charge_fn(
                customer_id=owner.stripe_customer_id, payment_method_id=card["id"], cents=cents,
                boost_id=fresh.id, user_id=owner.id, address=fresh.address or "",
                round_no=round_no)
        except Exception as exc:                        # noqa: BLE001 - the failure is the report
            log.info("renewal %s: charge raised: %s", boost.id, exc)
            if fresh is not None:
                db.delete(fresh)
                db.commit()
            results.append({**row, "status": "failed", "why": "%s: %s" % (type(exc).__name__, exc)})
            continue

        if not charge.get("paid"):
            # Nothing was charged, so nothing is left behind: the next round is removed and a
            # declined card is not retried on every tick.
            db.delete(fresh)
            db.add(Event(user_id=owner.id, boost_id=boost.id, event_type="renewal_declined",
                         payload={"message": (charge.get("message") or "")[:300],
                                  "payment_intent": charge.get("payment_intent")}))
            db.commit()
            results.append({**row, "status": "declined",
                            "why": charge.get("message") or "the card was declined"})
            continue

        paid_at = datetime.now(timezone.utc)
        db.add(Order(user_id=owner.id, boost_id=fresh.id, amount_cents=cents,
                     currency=billing.CURRENCY, status="paid", paid_at=paid_at,
                     stripe_payment_intent=charge.get("payment_intent")))
        fresh.paid_at = paid_at
        fresh.paid_amount_cents = cents
        # The old round is finished: its flag comes off, so it can never be charged twice and
        # the campaign list shows one autopilot per listing.
        boost.until_sold = False
        boost.until_sold_at = None
        db.add(Event(user_id=owner.id, boost_id=fresh.id, event_type="renewal_charged",
                     payload={"from_boost": boost.id, "amount_cents": cents,
                              "round": round_no, "payment_intent": charge.get("payment_intent")}))
        db.commit()

        build = {"built": False, "why": "not attempted"}
        try:
            build = await _build(fresh, owner)
        except Exception as exc:                        # noqa: BLE001 - a paid round is not lost
            build = {"built": False, "why": "%s: %s" % (type(exc).__name__, exc)}
            db.add(Event(user_id=owner.id, boost_id=fresh.id, event_type="renewal_build_failed",
                         payload={"error": str(exc)[:400]}))
            db.commit()

        try:
            email_fn(owner.email, fresh, cents, build)
        except Exception as exc:                        # noqa: BLE001 - mail is a courtesy
            log.info("renewal %s: email failed: %s", fresh.id, exc)

        results.append({**row, "status": "renewed", "new_boost_id": fresh.id,
                        "amount_cents": cents, "round": round_no,
                        "paid": True, "build": build,
                        "why": "charged and the next round is ready"})

    return {"checked_at": now.isoformat(), "applied": results,
            "stopped": stop_finished(db, now),
            "counts": {"due": len(plan["due"]), "renewed": sum(1 for r in results if r["status"] == "renewed"),
                       "declined": sum(1 for r in results if r["status"] == "declined"),
                       "no_card": sum(1 for r in results if r["status"] == "no_card"),
                       "failed": sum(1 for r in results if r["status"] == "failed")}}


def _default_email(to: str, boost, cents: int, build: dict) -> bool:
    """Tell the agent their next round is ready. Best effort: a failed email never undoes a charge."""
    from app.services import billing, mail

    address = boost.address or "your listing"
    price = billing.price_label(cents)
    built = ("Its posts and ad are built, and it goes live when the current round ends."
             if build.get("built") else
             "Open the campaign to look over the new round before it goes live.")
    body = ("Your next campaign for %s is ready.\n\n"
            "We charged %s to the card on file for round %d, because you asked us to keep "
            "marketing the home until it is under contract.\n\n%s\n\n"
            "Turn it off any time from the campaign card - it also stops by itself when the "
            "listing shows pending or sold.\n\n- Resmara" %
            (address, price, int(getattr(boost, "repeat_round", 0) or 0) + 1, built))
    return mail.send_email(to, "Your next campaign for %s is ready" % address, body)
