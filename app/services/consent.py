"""Terms, renewal consent, and the three money emails.

One record with three readers, so it lives in one place:

* **Terms acceptance** (Engine 1 §1, Engine 10 §1). Which version of the Terms and Privacy
  Policy an account agreed to, when, from which IP and browser. The Facebook door already
  stamps it (``app/api/facebook_login.py``); the email-and-password door did not, and the
  server had no way to ask an account to re-accept after the words changed.
* **Renewal consent** (Engine 10 §8). "Run it until it sells" charges the card on file every
  14 days. Turning it on stores the agreement on the campaign — version, time, IP, browser —
  because an automatic charge that recurs without a record of the agreement is the one audit an
  agent would win. Turning it off keeps the record and stamps when it ended: three years, or
  one year after it is turned off, which is why nothing is deleted by the off switch.
* **The three emails**: the acknowledgment the moment it is switched on, a reminder every year
  it stays on, and 30 days' notice before any price change.

A mail failure never undoes a record: the consent that exists is the consent that matters, and
the caller is told ``mail: "not_configured"`` instead of the request failing.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import Boost, Event, Order, User
from app.services import billing, mail
from app.services.facebook_login import TERMS_VERSION

# A yearly reminder while the switch stays on, and 30 days before any price change. Both are
# stated in the Terms, so both have to be true in code.
REMINDER_DAYS = 365
NOTICE_DAYS = 30

_UA_MAX = 300
_IP_MAX = 64


def current_terms() -> str:
    """The version of the Terms this build presents. One constant, read everywhere."""
    return TERMS_VERSION


def client_facts(request: Optional[Request]) -> Dict[str, str]:
    """Who accepted, from where. Behind Render's proxy the client IP is the first XFF hop."""
    ip, ua = "", ""
    if request is not None:
        try:
            forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
            ip = forwarded or (request.client.host if request.client else "")
        except Exception:                      # a Request stub in a unit test has no headers
            ip = ""
        try:
            ua = request.headers.get("user-agent") or ""
        except Exception:
            ua = ""
    return {"ip": (ip or "")[:_IP_MAX], "ua": (ua or "")[:_UA_MAX]}


# ── terms ────────────────────────────────────────────────────────────────────────────
def terms_stale(user: Optional[User]) -> bool:
    """True when this account has not accepted the version now being presented.

    An account that never went through a terms screen (every account created before this
    existed) is stale rather than exempt: the first money-moving call asks it once.
    """
    if user is None:
        return False
    return (getattr(user, "terms_version", None) or "").strip() != current_terms()


def record_terms(db: Session, user: User, version: str, request: Optional[Request] = None,
                 source: str = "password") -> Dict[str, Any]:
    """Stamp the acceptance on the account and write the audit row.

    The account columns answer "is this current?" cheaply; the Event carries the IP and browser
    that a dispute would ask for. Both are written, in one commit by the caller.
    """
    facts = client_facts(request)
    now = datetime.now(timezone.utc)
    version = (version or current_terms()).strip()[:40]
    user.terms_version = version
    user.terms_accepted_at = now
    db.add(Event(user_id=user.id, event_type="terms_accepted",
                 payload={"source": source, "version": version, "ip": facts["ip"],
                          "user_agent": facts["ua"], "at": now.isoformat()}))
    return {"version": version, "accepted_at": now.isoformat(), "ip": facts["ip"]}


def require_current_terms(user: User) -> None:
    """Refuse a money-moving call until the account accepts the version now presented.

    409 with a machine-readable code (``terms_stale``) and the version to accept, because the
    page has to be able to open "the terms changed" without scraping a sentence.
    """
    if not terms_stale(user):
        return
    raise HTTPException(status_code=409, detail={
        "error": "terms_stale",
        "current": current_terms(),
        "accepted": getattr(user, "terms_version", None),
        "why": "The Terms and Privacy Policy changed. Accept the current version to continue.",
    })


# ── renewal consent ──────────────────────────────────────────────────────────────────
def renewal_price() -> int:
    """What one automatic round costs, in cents — read from the same place Checkout reads."""
    return billing.repeat_price_cents()


def record_renewal_consent(db: Session, boost: Boost, version: str,
                           request: Optional[Request] = None) -> Dict[str, Any]:
    """Store the agreement behind an automatic renewal, on the campaign it applies to."""
    facts = client_facts(request)
    now = datetime.now(timezone.utc)
    boost.renewal_consent_at = now
    boost.renewal_consent_version = (version or current_terms()).strip()[:40]
    boost.renewal_consent_ip = facts["ip"]
    boost.renewal_consent_ua = facts["ua"]
    boost.renewal_consent_off_at = None      # switched back on: the old end date is history
    db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="renewal_consent",
                 payload={"on": True, "version": boost.renewal_consent_version,
                          "price_cents": renewal_price(), "ip": facts["ip"],
                          "user_agent": facts["ua"], "at": now.isoformat()}))
    return {"version": boost.renewal_consent_version, "at": now.isoformat(), "ip": facts["ip"]}


def end_renewal_consent(db: Session, boost: Boost,
                        request: Optional[Request] = None) -> Dict[str, Any]:
    """Turn it off without destroying the record: the consent stays, the end date is stamped.

    Retention is three years, or one year after it is turned off, so the off switch must not
    null the fields — that would leave a recurring charge with no record of why it stopped.
    """
    now = datetime.now(timezone.utc)
    boost.renewal_consent_off_at = now
    facts = client_facts(request)
    db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="renewal_consent",
                 payload={"on": False, "version": boost.renewal_consent_version,
                          "ip": facts["ip"], "user_agent": facts["ua"], "at": now.isoformat()}))
    return {"ended_at": now.isoformat()}


def _money(cents: int) -> str:
    return "$%d" % round(cents / 100.0) if cents % 100 == 0 else "$%.2f" % (cents / 100.0)


def _plain_date(value: Optional[datetime]) -> str:
    return value.strftime("%-d %B %Y (UTC)") if value else "an unknown date"


def send_renewal_acknowledgment(user: User, boost: Boost) -> str:
    """The email the Terms promise the moment automatic renewal is switched on.

    Says the price, the cadence, that it is charged to the card on file, and exactly how to
    stop it — the four things a customer is entitled to see in writing.
    """
    price = _money(renewal_price())
    days = int(boost.campaign_days or 14)
    ok = mail.send_email(
        user.email,
        "Run it until it sells is on — %s every %d days" % (price, days),
        "You turned on Run it until it sells for %s.\n\n"
        "What happens now: every %d days Resmara builds the next round for this listing and "
        "charges the card on file %s. It stops by itself when the listing is pending or sold. "
        "You can turn it off at any time in the campaign; nothing further is charged after "
        "that, and the round already running finishes.\n\n"
        "The agreement we hold: Terms version %s, accepted %s, from %s.\n\n"
        "We will email you again each year this stays on, and at least %d days before any price "
        "change.\n\n- Resmara\n"
        % (boost.address or "this listing", days, price,
           boost.renewal_consent_version or current_terms(),
           _plain_date(boost.renewal_consent_at), boost.renewal_consent_ip or "an unknown address",
           NOTICE_DAYS))
    return "sent" if ok else "not_configured"


# ── yearly reminder ─────────────────────────────────────────────────────────────────
def _aware(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _last_event(db: Session, boost_id: int, kind: str) -> Optional[datetime]:
    row = (db.query(Event).filter(Event.boost_id == boost_id, Event.event_type == kind)
           .order_by(Event.id.desc()).first())
    return _aware(row.created_at) if row else None


def reminder_due(db: Session, boost: Boost, now: Optional[datetime] = None) -> bool:
    """A campaign that has run on automatic renewal for a year without being asked again."""
    now = now or datetime.now(timezone.utc)
    if not boost.until_sold:
        return False
    since = _aware(boost.renewal_consent_at)
    if not since or (now - since) < timedelta(days=REMINDER_DAYS):
        return False
    last = _last_event(db, boost.id, "renewal_reminder")
    return not last or (now - last) >= timedelta(days=REMINDER_DAYS)


def send_yearly_reminder(user: User, boost: Boost) -> str:
    price = _money(renewal_price())
    days = int(boost.campaign_days or 14)
    ok = mail.send_email(
        user.email,
        "Still running: %s every %d days for %s" % (price, days, boost.address or "your listing"),
        "Run it until it sells is still on for %s.\n\n"
        "You turned it on %s. It charges the card on file %s every %d days and stops by itself "
        "when the listing is pending or sold. Turn it off any time in the campaign.\n\n"
        "You are getting this because it has been on for a year — we remind you every year, and "
        "at least %d days before any price change.\n\n- Resmara\n"
        % (boost.address or "your listing", _plain_date(boost.renewal_consent_at), price, days,
           NOTICE_DAYS))
    return "sent" if ok else "not_configured"


def send_reminders(db: Session, now: Optional[datetime] = None) -> Dict[str, Any]:
    """Every campaign whose yearly reminder is due. One email each, one Event as the marker."""
    now = now or datetime.now(timezone.utc)
    sent: List[Dict[str, Any]] = []
    for boost in db.query(Boost).filter(Boost.until_sold.is_(True)).all():
        if not reminder_due(db, boost, now):
            continue
        user = db.get(User, boost.user_id)
        if not user or not getattr(user, "is_active", True):
            continue
        status = send_yearly_reminder(user, boost)
        db.add(Event(user_id=user.id, boost_id=boost.id, event_type="renewal_reminder",
                     payload={"mail": status, "price_cents": renewal_price(),
                              "at": now.isoformat()}))
        sent.append({"boost_id": boost.id, "to": user.email, "mail": status})
    db.commit()
    return {"due": len(sent), "sent": sent}


# ── price change notice ─────────────────────────────────────────────────────────────
def notice_recipients(db: Session) -> List[User]:
    """Everyone a price change can actually reach: anybody who paid, or who is being renewed."""
    paid = {row[0] for row in db.query(Order.user_id).filter(Order.status == "paid").all()}
    renewing = {row[0] for row in db.query(Boost.user_id).filter(Boost.until_sold.is_(True)).all()}
    ids = paid | renewing
    if not ids:
        return []
    return db.query(User).filter(User.id.in_(ids), User.is_active.is_(True)).all()


def send_price_notice(db: Session, new_cents: int, effective_on: date,
                      note: str = "", now: Optional[datetime] = None) -> Dict[str, Any]:
    """Email every paying account at least 30 days before a price change takes effect.

    Refused with 400 when the date is closer than that: the promise in the Terms is 30 days of
    notice, so a tool that quietly allowed 10 would be the way that promise breaks.
    """
    now = now or datetime.now(timezone.utc)
    earliest = (now.date() + timedelta(days=NOTICE_DAYS))
    if effective_on < earliest:
        raise HTTPException(status_code=400, detail={
            "error": "notice_too_short",
            "why": "A price change needs %d days' notice; the earliest allowed date is %s."
                   % (NOTICE_DAYS, earliest.isoformat()),
            "earliest": earliest.isoformat(),
        })
    if new_cents <= 0:
        raise HTTPException(status_code=400, detail="A price has to be more than zero")

    old_cents = billing.price_cents()
    old_repeat = renewal_price()
    recipients = notice_recipients(db)
    delivered, failed = [], []
    for user in recipients:
        ok = mail.send_email(
            user.email,
            "Resmara pricing is changing on %s" % effective_on.strftime("%-d %B %Y"),
            "Resmara's prices change on %s.\n\n"
            "Today a campaign is %s and an automatic round of Run it until it sells is %s. "
            "From %s a campaign is %s. A round already paid for runs to the end at the price you "
            "paid; a campaign you buy after %s is charged the new price.\n\n"
            "%s"
            "Nothing changes before %s, and you can turn off Run it until it sells at any time in "
            "the campaign.\n\n- Resmara\n"
            % (effective_on.strftime("%-d %B %Y"), _money(old_cents), _money(old_repeat),
               effective_on.strftime("%-d %B %Y"), _money(new_cents),
               effective_on.strftime("%-d %B %Y"),
               ("%s\n\n" % note.strip()) if note else "",
               effective_on.strftime("%-d %B %Y")))
        db.add(Event(user_id=user.id, event_type="price_notice",
                     payload={"new_cents": new_cents, "old_cents": old_cents,
                              "effective_on": effective_on.isoformat(), "mail": "sent" if ok else "not_configured",
                              "note": note or ""}))
        (delivered if ok else failed).append(user.email)
    db.commit()
    return {"effective_on": effective_on.isoformat(), "old_cents": old_cents,
            "new_cents": new_cents, "recipients": len(recipients),
            "delivered": delivered, "failed": failed,
            "mail": "sent" if delivered else ("not_configured" if recipients else "no_recipients")}


def notices_sent(db: Session, limit: int = 20) -> List[Dict[str, Any]]:
    """The price notices already sent, newest first — one row per recipient."""
    rows = (db.query(Event).filter(Event.event_type == "price_notice")
            .order_by(Event.id.desc()).limit(limit).all())
    return [{"at": (r.created_at.isoformat() if r.created_at else None),
             "user_id": r.user_id, "payload": r.payload or {}} for r in rows]
