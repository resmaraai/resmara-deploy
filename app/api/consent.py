"""The two consent jobs a person should never have to remember.

* **``POST /api/admin/consent/reminders``** — the yearly reminder while "Run it until it sells"
  stays on (Engine 10 §8). Called by the clock once a day, machine token only.
* **``POST /api/admin/price-notice``** — 30 days' email notice before a price change, refused
  when the date is closer than that. Operator only (``money``), because it emails every paying
  account and cannot be undone.
* **``GET /api/admin/price-notice``** — the notices already sent, newest first, from the events.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services import consent, team_access

router = APIRouter()


def _require_system_token(x_resmara_token: str = Header(default="")) -> None:
    """The clock's token, the same one the build room sync and the publisher use."""
    if not settings.PUBLISH_TOKEN:
        raise HTTPException(status_code=503, detail="RESMARA_PUBLISH_TOKEN is not configured")
    if x_resmara_token != settings.PUBLISH_TOKEN:
        raise HTTPException(status_code=403, detail="Bad machine token")


class PriceNoticeIn(BaseModel):
    new_cents: int
    # YYYY-MM-DD. Refused when it is fewer than 30 days away — that is the promise in the Terms.
    effective_on: str
    note: str = ""


@router.post("/admin/consent/reminders")
def run_reminders(_tok=Depends(_require_system_token), db: Session = Depends(get_db)):
    """Send every yearly reminder that is due. Idempotent: an Event marks each send."""
    return consent.send_reminders(db)


@router.post("/admin/price-notice")
def send_notice(body: PriceNoticeIn, db: Session = Depends(get_db),
                _admin=Depends(team_access.needs("money"))):
    try:
        when = date.fromisoformat((body.effective_on or "")[:10])
    except ValueError:
        raise HTTPException(status_code=400,
                            detail="effective_on must be a date, YYYY-MM-DD")
    return consent.send_price_notice(db, body.new_cents, when, body.note)


@router.get("/admin/price-notice")
def notice_history(limit: int = 20, db: Session = Depends(get_db),
                   _admin=Depends(team_access.needs("money"))):
    return {"notices": consent.notices_sent(db, limit=max(1, min(limit, 100)))}
