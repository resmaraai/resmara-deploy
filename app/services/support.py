"""Engine 11: support requests - the 1 business day promise, the four statuses, auto-close.

1 business day: a request sent before 5 PM Pacific on a business day is answered by 5 PM the next
business day. Weekends and US federal holidays don't count.

Statuses (what the agent and the team read): Received, Answered, Waiting on you, Closed.
Stored as received / answered / waiting / closed; older rows (open, in_progress, resolved) read the
same way through `status_of`.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")
CUTOFF = time(17, 0)
CLOSE_AFTER_DAYS = 7
STATUSES = ("received", "answered", "waiting", "closed")
LABELS = {"received": "Received", "answered": "Answered", "waiting": "Waiting on you", "closed": "Closed"}
_LEGACY = {"open": "received", "in_progress": "received", "resolved": "closed"}


def status_of(stored: Optional[str]) -> str:
    s = (stored or "received").lower()
    return _LEGACY.get(s, s if s in STATUSES else "received")


def label(stored: Optional[str]) -> str:
    return LABELS[status_of(stored)]


# ---------------------------------------------------------------- business days
def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7)
    return d + timedelta(weeks=n - 1)


def _last_weekday(year: int, month: int, weekday: int) -> date:
    d = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def _observed(d: date) -> date:
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def holidays(year: int) -> set:
    """US federal holidays, as observed."""
    return {
        _observed(date(year, 1, 1)), _nth_weekday(year, 1, 0, 3), _nth_weekday(year, 2, 0, 3),
        _last_weekday(year, 5, 0), _observed(date(year, 6, 19)), _observed(date(year, 7, 4)),
        _nth_weekday(year, 9, 0, 1), _nth_weekday(year, 10, 0, 2), _observed(date(year, 11, 11)),
        _nth_weekday(year, 11, 3, 4), _observed(date(year, 12, 25)),
        _observed(date(year + 1, 1, 1)),   # Jan 1 on a Saturday is observed on Dec 31
    }


def is_business_day(d: date) -> bool:
    return d.weekday() < 5 and d not in holidays(d.year)


def _next_business_day(d: date) -> date:
    d += timedelta(days=1)
    while not is_business_day(d):
        d += timedelta(days=1)
    return d


def reply_by(sent: Optional[datetime] = None) -> datetime:
    """When the team promises an answer, in UTC."""
    sent = sent or datetime.now(timezone.utc)
    if sent.tzinfo is None:
        sent = sent.replace(tzinfo=timezone.utc)
    local = sent.astimezone(PACIFIC)
    day = local.date()
    if not is_business_day(day) or local.time() >= CUTOFF:
        # Counted from the next business day's morning.
        day = _next_business_day(day)
    due = datetime.combine(_next_business_day(day), CUTOFF, tzinfo=PACIFIC)
    return due.astimezone(timezone.utc)


def reply_by_label(due: Optional[datetime], now: Optional[datetime] = None) -> str:
    """"Tuesday at 5 PM" within the week, otherwise "Tue, Dec 2 at 5 PM"."""
    if due is None:
        return ""
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    local = due.astimezone(PACIFIC)
    hour = local.strftime("%-I %p") if local.minute == 0 else local.strftime("%-I:%M %p")
    if (local.date() - now.astimezone(PACIFIC).date()).days < 7:
        return f"{local.strftime('%A')} at {hour}"
    return f"{local.strftime('%a, %b %-d')} at {hour}"


def due_state(due: Optional[datetime], status: Optional[str], now: Optional[datetime] = None) -> str:
    """For the Team room: "late" (orange), "soon" (within 2 hours), or ""."""
    if due is None or status_of(status) != "received":
        return ""
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    if now > due:
        return "late"
    return "soon" if due - now <= timedelta(hours=2) else ""


# ---------------------------------------------------------------- snapshot and auto-close
def snapshot(db, user) -> Dict[str, Any]:
    """What the team needs so they don't have to ask (the agent's own account only)."""
    from app.db.session import Boost, MetaConnection, Post
    boosts = db.query(Boost).filter(Boost.user_id == user.id).all()
    conn = db.query(MetaConnection).filter(MetaConnection.user_id == user.id).first()
    ids = [b.id for b in boosts]
    failed = db.query(Post).filter(Post.boost_id.in_(ids), Post.publish_status == "failed").count() if ids else 0
    return {
        "campaigns": len(boosts),
        "live": sum(1 for b in boosts if b.launched_at and not b.paused_at),
        "until_sold": sum(1 for b in boosts if b.until_sold),
        "facebook": bool(conn and conn.fb_user_id),
        "page": getattr(conn, "page_name", None),
        "instagram": getattr(conn, "ig_username", None),
        "card": bool(user.stripe_customer_id),
        "failed_posts": failed,
    }


def _at(m: dict) -> Optional[datetime]:
    try:
        v = datetime.fromisoformat(str(m.get("at")))
    except (TypeError, ValueError):
        return None
    return v if v.tzinfo else v.replace(tzinfo=timezone.utc)


def auto_close(db, now: Optional[datetime] = None) -> int:
    """Answered or Waiting on you, and the agent hasn't written in 7 days: Closed."""
    from app.db.session import Event, SupportTicket
    now = now or datetime.now(timezone.utc)
    closed = 0
    for t in db.query(SupportTicket).filter(SupportTicket.status.in_(("answered", "waiting", "resolved"))).all():
        msgs = [m for m in (t.messages or []) if isinstance(m, dict)]
        last = msgs[-1] if msgs else {}
        when = _at(last)
        if last.get("from") != "admin" or when is None or now - when < timedelta(days=CLOSE_AFTER_DAYS):
            continue
        t.status = "closed"
        db.add(Event(user_id=t.user_id, event_type="ticket_auto_closed", payload={"ticket_id": t.id}))
        closed += 1
    db.commit()
    return closed
