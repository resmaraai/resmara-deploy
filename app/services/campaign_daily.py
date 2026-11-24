"""Once a day: the emails a running campaign sends on a schedule (Engines 6 and 8).

  * Day 7 and day 14: "Your day 7 report for 1248 Oakridge Drive" (Engine 6, section 9).
  * Day 12, without Run it until it sells: "Keep the momentum going" with Run it again · $39, and
    once more when it completes if they haven't acted (Engine 8, section 8). Never when Run it until
    it sells is on, or when the listing is pending or sold.

Each one goes once (campaign_emails keeps the keys), and only inside a short window, so a deploy
never sends a stack of old reminders.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.db.session import Boost
from app.services import campaign_emails as emails


def day_of(boost: Boost, now: Optional[datetime] = None) -> Optional[int]:
    """Day N of the campaign (day 1 is the go-live date), paused days not counted."""
    from app.services.renewals import round_start
    start = round_start(boost) if (boost.go_live_date or boost.launched_at) else None
    if start is None:
        return None
    now = now or datetime.now(timezone.utc)
    if boost.paused_at is not None:
        paused = boost.paused_at if boost.paused_at.tzinfo else boost.paused_at.replace(tzinfo=timezone.utc)
        now = min(now, paused)
    return (now - start).days + 1 - int(boost.paused_days or 0)


def run(db, now: Optional[datetime] = None) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    sent = {"reports": 0, "run_again": 0}
    for boost in db.query(Boost).filter(Boost.launched_at.isnot(None), Boost.paid_at.isnot(None)).all():
        day = day_of(boost, now)
        if day is None:
            continue
        for report in (7, 14):
            if report <= day < report + 3 and not emails.already(boost, f"report-{report}"):
                sent["reports"] += int(emails.report_ready(db, boost, report))
        status = (boost.listing_status or "").lower()
        if boost.until_sold or status in ("pending", "sold"):
            continue
        acted = db.query(Boost).filter(Boost.parent_boost_id == boost.id, Boost.paid_at.isnot(None)).first()
        if acted is not None:
            continue
        if 12 <= day < 14 and not emails.already(boost, "again-12"):
            sent["run_again"] += int(emails.run_again(db, boost))
        elif 14 < day <= 17 and not emails.already(boost, "again-final"):
            sent["run_again"] += int(emails.run_again(db, boost, final=True))
    return sent
