"""The emails a running campaign sends the agent (Engines 6 and 8).

Short, one button each (a link line: the mail goes as plain text), and each one at most once per
event: the key is kept in `boost.listing_notes["sent"]`. Agents on Run it until it sells may not
open Resmara for months, so email is how Resmara talks to them (Engine 8, section 7).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.db.session import Boost, Event, User

log = logging.getLogger(__name__)


def street(boost: Boost) -> str:
    return (boost.address or "your listing").split(",")[0].strip()


def base() -> str:
    return (getattr(settings, "PUBLIC_BASE_URL", "") or "https://www.resmara.com").rstrip("/")


def campaign_link(boost: Boost) -> str:
    return f"{base()}/#campaign-{boost.id}"


def billing_link() -> str:
    return f"{base()}/#billing"


def report_link(boost: Boost, day: int) -> str:
    return f"{base()}/#campaign-{boost.id}-report-{day}"


def _sent(boost: Boost) -> dict:
    notes = dict(boost.listing_notes or {})
    return dict(notes.get("sent") or {})


def already(boost: Boost, key: str) -> bool:
    return key in _sent(boost)


def mark(db, boost: Boost, key: str) -> None:
    notes = dict(boost.listing_notes or {})
    sent = dict(notes.get("sent") or {})
    sent[key] = datetime.now(timezone.utc).isoformat()
    notes["sent"] = sent
    boost.listing_notes = notes
    db.commit()


def forget(db, boost: Boost, *prefixes: str) -> None:
    """A new episode (it went pending again, a new round): the old one-time keys no longer apply."""
    notes = dict(boost.listing_notes or {})
    sent = {k: v for k, v in (notes.get("sent") or {}).items() if not any(k.startswith(p) for p in prefixes)}
    notes["sent"] = sent
    boost.listing_notes = notes
    db.commit()


def send(db, boost: Boost, key: str, subject: str, body: str, button: str, link: str) -> bool:
    """One email, once per key. Returns True when it went (or had already gone)."""
    if already(boost, key):
        return True
    owner = db.query(User).filter(User.id == boost.user_id).first()
    if owner is None or not owner.email or getattr(owner, "needs_email", False):
        return False
    first = (owner.name or "").split(" ")[0] or "there"
    from app.services import mail
    text = f"Hi {first},\n\n{body}\n\n{button}: {link}\n\n- Resmara"
    try:
        ok = bool(mail.send_email(owner.email, subject, text))
    except Exception as exc:  # noqa: BLE001
        log.info("campaign email %s for %s failed: %s", key, boost.id, exc)
        ok = False
    db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="campaign_email",
                 payload={"key": key, "subject": subject, "sent": ok}))
    db.commit()
    if ok:
        mark(db, boost, key)
    return ok


# ------------------------------------------------------------------ Engine 6, section 7
def pending(db, boost: Boost) -> bool:
    s = street(boost)
    if boost.until_sold:   # Engine 8, section 5
        return send(db, boost, "pending", f"{s} went pending, so we paused your campaign",
                    f"Looks like {s} went pending, so we paused your campaign. We'll keep checking every day: "
                    "if it comes back on the market we'll pick up where we left off, and if it sells we'll close it out.",
                    "See the campaign", campaign_link(boost))
    return send(db, boost, "pending", f"{s} shows Pending, so we paused your campaign",
                "Your listing shows Pending, so we paused your ad, your posts and your website's showing requests. "
                "Fell through? Turn it back on anytime.", "Turn it back on", campaign_link(boost))


def back_on_market(db, boost: Boost, *, running: bool, ended: bool = False) -> bool:
    s = street(boost)
    if running:   # Run it until it sells picked up by itself
        return send(db, boost, "back", f"{s} is back on the market. Your campaign is running again",
                    f"{s} is back on the market, so your campaign is running again. Nothing to do.",
                    "See the campaign", campaign_link(boost))
    if ended:     # it closed as Completed · Pending, then came back with the same agent
        return send(db, boost, "back", f"{s} shows For Sale again",
                    "Your listing shows For Sale again. Want to market it again? A fresh 14-day campaign is $39, "
                    "built from what worked last time.", "Run it again · $39", campaign_link(boost))
    return send(db, boost, "back", f"{s} shows For Sale again",
                "Your listing shows For Sale again. Want to turn your campaign back on?",
                "Turn it back on", campaign_link(boost))


# ------------------------------------------------------------------ Engine 8, section 7
def renewed(db, boost: Boost, round_no: int, live_on: str) -> bool:
    s = street(boost)
    return send(db, boost, f"renewed-{round_no}", f"Round {round_no} for {s} goes live {live_on}",
                f"Round {round_no} for {s} is ready and goes live {live_on}. Fresh posts and a fresh ad, "
                "built from what worked last time. Nothing to do.", "See the campaign", campaign_link(boost))


def declined(db, boost: Boost) -> bool:
    s = street(boost)
    return send(db, boost, "declined", f"We couldn't renew your campaign for {s}",
                f"We couldn't renew your campaign for {s} because your card was declined. "
                "Please check your billing on Resmara. As soon as a working card is saved, the next round goes live.",
                "Check billing", billing_link())


def report_ready(db, boost: Boost, day: int) -> bool:
    s = street(boost)
    return send(db, boost, f"report-{day}", f"Your day {day} report for {s}",
                f"Your day {day} report for {s} is ready: reach, clicks, leads and what Resmara changed. "
                "There's a seller version you can download and send them too.", "See your report", report_link(boost, day))


def run_again(db, boost: Boost, *, final: bool = False) -> bool:
    s = street(boost)
    return send(db, boost, "again-final" if final else "again-12", f"Keep the momentum going on {s}",
                f"Your campaign for {s} {'has finished' if final else 'finishes in 2 days'}. Run it again for $39: "
                "fresh posts and a fresh ad built from what worked, live the next morning. Or turn on Run it until "
                "it sells and we'll keep it going every 2 weeks until it's under contract.",
                "Run it again · $39", campaign_link(boost))


def card_expiring(db, boost: Boost, label: str, ends: str) -> bool:
    """Engine 10, section 4: 30 days before the saved card expires, while Run it until it sells is on."""
    return send(db, boost, f"card-expiring-{ends}", "Your card on file expires soon",
                f"The {label} that pays for Run it until it sells on {street(boost)} expires at the end of "
                f"{ends}. Add your new card so the next round isn't held up.",
                "Update your card", billing_link())
