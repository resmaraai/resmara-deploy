"""The machine-token entrypoint for the onboarding emails, and the unsubscribe link they carry.

The clock (Render cron `resmara-publisher`, every 15 minutes) POSTs here; the run is idempotent,
so a missed or doubled clock tick can never send the same agent the same email twice.

Unsubscribe is a signed link, not a login: it has to work from an inbox on a phone that is not
signed in, and it must not be a way to flip someone else's switch.
"""
import hashlib
import hmac
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import Event, User, get_db
from app.services import onboarding_emails
from app.services.onboarding_emails import unsub_token

router = APIRouter()


@router.post("/admin/onboarding/emails/run")
def run_onboarding_emails(x_resmara_token: str = Header(default=""), db: Session = Depends(get_db)):
    """Send today's due onboarding emails. Same machine token as the rest of the clock."""
    expected = (getattr(settings, "PUBLISH_TOKEN", "") or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="RESMARA_PUBLISH_TOKEN is not configured")
    if not hmac.compare_digest(x_resmara_token, expected):
        raise HTTPException(status_code=403, detail="Bad machine token")
    return onboarding_emails.run_due(db)


@router.get("/unsubscribe", response_class=HTMLResponse)
def unsubscribe(u: int = 0, t: str = ""):
    """One click, no sign-in, works from any inbox."""
    if not u or not hmac.compare_digest(t or "", unsub_token(u)):
        raise HTTPException(status_code=400, detail="That unsubscribe link is not valid.")
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == u).first()
        if user is None:
            raise HTTPException(status_code=404, detail="That account no longer exists.")
        user.marketing_optin = False
        db.add(Event(user_id=user.id, event_type="unsubscribed", payload={"at": datetime.now(timezone.utc).isoformat()}))
        db.commit()
    finally:
        db.close()
    return ("<html><body style='font-family:system-ui;padding:40px;max-width:560px;margin:auto'>"
            "<h2>You're unsubscribed.</h2><p>No more onboarding emails will be sent. Replies to any earlier "
            "message still reach us.</p></body></html>")
