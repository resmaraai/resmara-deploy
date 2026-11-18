"""Which campaigns are due for their next round, and which are being held.

"Run it until it sells" promises a brand-new 14-day round every two weeks until the listing is
pending or sold. This module is the clock half of that promise: it decides *which* campaigns are
due, and it is the only place that answer is computed, so a cron, a console square and a test all
agree.

What it deliberately does not do: charge, build, or email. Those are the money half and they land
separately (the $39 charge needs a saved card and an off-session PaymentIntent). A planner that
also moved money would be impossible to run in dry-run mode, and the first thing anyone wants from
a renewal job is "show me what it would do tonight".

Rules, in the order they are applied:

* ``until_sold`` must be on. Off is off.
* A listing that is ``pending`` or ``sold`` is finished: it stops itself, and the caller clears the
  flag. Nothing is built or charged after that.
* ``paused_at`` set means the campaign is paused: the next round is held with no charge until it
  resumes, so a paused campaign never renews behind the agent's back.
* The round is 14 days from ``launched_at`` (``created_at`` when a campaign was never launched, so
  a draft cannot sit in "due" forever). A round is due once it is within ``BUILD_AHEAD_DAYS`` of
  its end, which is the "ready to look over 3 days before it starts" the explainer promises.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

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
