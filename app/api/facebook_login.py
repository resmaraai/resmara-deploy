"""Engine 1 Part A: the account half of login, built to the brain doc.

``POST /api/auth/facebook/start`` -> the Facebook dialog URL (Terms box checked first).
``GET  /api/auth/facebook/callback`` -> code exchanged, account found or created, ticket minted.
``POST /api/auth/facebook/exchange`` -> one-time ticket becomes the same JWT the rest of the app uses.
``POST /api/auth/facebook/reactivate`` -> a closed account comes back, in one click.
``POST /api/auth/me/close`` / ``PATCH /api/auth/me/email`` -> the two account-lifecycle jobs the
brain doc splits apart ("Close my account" is reversible; "Delete my data" in auth.py is not).

Guardrails that are code, not AI: only Meta says who signed in; the same Facebook id always maps
to the same account; a second account cannot claim a Page (Engine 1 Part B); consent is stored
before the redirect and stamped on the account it creates.
"""
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, get_current_user, get_password_hash
from app.db.session import Event, FacebookLoginCode, User, get_db
from app.services import facebook_login as fb
from app.services import mail

router = APIRouter()

# A sign-in attempt is event-logged so "too many tries from one place" is a fact, not a vibe.
MAX_ATTEMPTS_PER_HOUR = int(os.getenv("RESMARA_FB_ATTEMPT_LIMIT", "30"))
TURNSTILE_SECRET = os.getenv("RESMARA_TURNSTILE_SECRET", "").strip()


def _public_base() -> str:
    return (getattr(settings, "PUBLIC_BASE_URL", "") or "").rstrip("/") or "https://www.resmara.com"


def _back(payload: dict, fmt: str = ""):
    """JSON when asked (?format=json), otherwise back to the app with the outcome in the query."""
    if fmt == "json":
        return payload
    query = "&".join(f"{k}={v}" for k, v in payload.items() if v is not None)
    return RedirectResponse(f"{_public_base()}/?{query}", status_code=302)


def _client_ip(request: Request) -> str:
    fwd = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    return fwd or (request.client.host if request.client else "") or ""


def _too_many_attempts(db: Session, ip: str) -> bool:
    if not ip:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    count = (db.query(Event)
             .filter(Event.event_type == "facebook_login_attempt", Event.created_at >= cutoff)
             .filter(Event.payload["ip"].as_string() == ip).count())
    return count >= MAX_ATTEMPTS_PER_HOUR


async def _turnstile_ok(token: str, ip: str) -> bool:
    """Cloudflare Turnstile's invisible bot check. Unset secret = not configured, not a pass."""
    if not TURNSTILE_SECRET:
        return True
    if not token:
        return False
    import httpx
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post("https://challenges.cloudflare.com/turnstile/v0/siteverify",
                              data={"secret": TURNSTILE_SECRET, "response": token, "remoteip": ip})
    return bool((r.json() or {}).get("success"))


def _mint_ticket(db: Session, user: User, purpose: str) -> str:
    code = secrets.token_urlsafe(32)
    db.add(FacebookLoginCode(code=code, user_id=user.id, purpose=purpose,
                             expires_at=datetime.now(timezone.utc) + timedelta(minutes=fb.TICKET_TTL_MINUTES)))
    return code


def _spend_ticket(db: Session, code: str, purpose: str) -> User:
    row = db.query(FacebookLoginCode).filter(FacebookLoginCode.code == (code or "")).first()
    if row is None or row.used_at is not None or row.purpose != purpose:
        raise HTTPException(status_code=400, detail="That sign-in link has expired or was already used. Try again.")
    expires = row.expires_at
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires is not None and expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="That sign-in link has expired. Try again.")
    row.used_at = datetime.now(timezone.utc)
    user = db.query(User).filter(User.id == row.user_id).first()
    if user is None:
        raise HTTPException(status_code=400, detail="That sign-in link names an account that no longer exists.")
    return user


def _notify_owner_new_account(db: Session, user: User, created: bool, meta_connected: bool) -> None:
    """Adam hears about every new sign-up (Engine 1 §7). Test accounts never trigger it."""
    if not created:
        return
    from app.core import testdata
    if getattr(user, "is_test", False) or testdata.is_test_email(user.email):
        return
    owners = [a.strip() for a in (settings.ADMIN_EMAILS or "").split(",") if a.strip()]
    if not owners:
        return
    ok = mail.send_email(owners[0], f"New Resmara sign-up: {user.name or user.email}",
                         f"A new agent signed up with Facebook.\n\n"
                         f"Name:  {user.name or '(not given)'}\n"
                         f"Email: {user.email}\n"
                         f"Meta connected: {'yes' if meta_connected else 'not yet'}\n\n"
                         f"- Resmara")
    db.add(Event(user_id=user.id, event_type="signup_alert",
                 payload={"to": owners[0], "sent": bool(ok)}))


@router.post("/facebook/start")
async def facebook_start(request: Request, payload: dict | None = None, db: Session = Depends(get_db)):
    """Begin "Log in with Facebook": consent first, then the Facebook dialog.

    The Terms box must be ticked before the button works (Engine 1 §2). The fact is signed into
    the OAuth state, so the callback can stamp the account even though no account exists yet.
    """
    payload = payload or {}
    if not fb.login_configured():
        raise HTTPException(status_code=503,
                            detail="Facebook login is not switched on for this server yet. "
                                   "Sign in with your email and password, or try again shortly.")
    if not payload.get("terms_accepted"):
        raise HTTPException(status_code=400,
                            detail="Tick the box agreeing to the Terms of Service and Privacy Policy first.")
    ip = _client_ip(request)
    if _too_many_attempts(db, ip):
        raise HTTPException(status_code=429, detail="Too many attempts from here. Wait a minute and try again.")
    if not await _turnstile_ok(payload.get("turnstile_token", ""), ip):
        raise HTTPException(status_code=400, detail="We couldn't confirm you're a person. Try again.")
    version = str(payload.get("terms_version") or fb.TERMS_VERSION)[:40]
    db.add(Event(event_type="facebook_login_attempt", payload={"ip": ip, "step": "start"}))
    db.commit()
    state = fb.make_state(version)
    return {"redirect_url": fb.dialog_url(state), "terms_version": version}


@router.get("/facebook/callback")
async def facebook_callback(request: Request, code: str = "", state: str = "", error: str = "",
                            error_description: str = "", format: str = "", db: Session = Depends(get_db)):
    """Facebook's return trip. Everything here is Meta's answer or a refusal; nothing is assumed."""
    if error:
        return _back({"fb": "cancelled", "reason": (error_description or error)[:120]}, format)
    try:
        consent = fb.read_state(state)
    except ValueError as exc:
        return _back({"fb": "error", "reason": str(exc)[:120]}, format)
    if not code:
        return _back({"fb": "error", "reason": "Facebook returned without a code."}, format)
    try:
        token_data = await fb.exchange_code(code)
        me = await fb.read_me(token_data["access_token"])
    except ValueError as exc:
        return _back({"fb": "error", "reason": str(exc)[:160]}, format)
    except Exception as exc:  # noqa: BLE001 - Meta unreachable must not be a 500 page
        return _back({"fb": "error", "reason": f"Facebook could not be reached ({type(exc).__name__})."}, format)

    fb_id = str(me.get("id"))
    name = (me.get("name") or "").strip() or None
    email = (me.get("email") or "").strip().lower() or ""
    ip, ua = _client_ip(request), (request.headers.get("user-agent") or "")[:300]

    user = db.query(User).filter(User.facebook_id == fb_id).first()
    created = False
    if user is None and email:
        user = db.query(User).filter(User.email == email).first()
        if user is not None and not user.facebook_id:
            # Same person, same address: link the Facebook to the account they already have.
            user.facebook_id = fb_id
            user.facebook_name = name
    if user is None:
        user = User(email=email or f"fb-{fb_id}@facebook.resmara.invalid",
                    hashed_password=get_password_hash(secrets.token_urlsafe(32)),
                    name=name, facebook_id=fb_id, facebook_name=name,
                    email_confirmed_at=datetime.now(timezone.utc) if email else None,
                    needs_email=not bool(email),
                    terms_accepted_at=datetime.now(timezone.utc),
                    terms_version=str(consent.get("v") or fb.TERMS_VERSION)[:40],
                    signup_ip=ip or None, signup_ua=ua or None,
                    is_admin=email in {a.strip().lower() for a in (settings.ADMIN_EMAILS or "").split(",") if a.strip()})
        db.add(user)
        db.flush()
        created = True
        try:
            from app.services import attribution
            attribution.stamp_signup(db, user, {"source": "facebook"})
        except Exception:  # noqa: BLE001 - attribution must never cost a sign-up
            pass
        db.add(Event(user_id=user.id, event_type="user_registered",
                     payload={"source": "facebook", "terms_version": user.terms_version,
                              "needs_email": bool(user.needs_email)}))
    else:
        user.facebook_name = name or user.facebook_name
        if user.needs_email and email:
            user.email = email
            user.needs_email = False
            user.email_confirmed_at = user.email_confirmed_at or datetime.now(timezone.utc)

    if user.closed_at is not None:
        # Not a silent sign-in: the brain doc asks them, once, whether to come back.
        ticket = _mint_ticket(db, user, "reactivate")
        db.commit()
        return _back({"fb": "closed", "ticket": ticket}, format)

    # Facebook log-in and Connect Meta are the same connection, never two (Engine 1 Part B §6):
    # every sign-in saves the login and runs the audit, so sign-up and audit are one step.
    try:
        from app.services import meta_engine
        db.commit()  # the account is saved first; nothing below can undo a sign-in
        token, expires_at = await meta_engine.long_lived(token_data["access_token"])
        meta_engine.save_login(db, user, token, expires_at=expires_at, fb_user_id=fb_id, fb_user_name=name)
        db.commit()
        await meta_engine.check(db, user, "connect", force=True)
    except Exception:  # noqa: BLE001 - the audit must never cost a sign-in
        db.rollback()

    if created:
        _notify_owner_new_account(db, user, created, bool(user.meta_connected_at))
        try:
            from app.services import onboarding_emails
            onboarding_emails.send_welcome(user, db)
        except Exception:  # noqa: BLE001 - a welcome email must never block a sign-in
            pass

    ticket = _mint_ticket(db, user, "login")
    db.commit()
    return _back({"fb": "login", "ticket": ticket,
                  "new": "1" if created else "0",
                  "needs_email": "1" if user.needs_email else "0"}, format)


@router.post("/facebook/exchange")
def facebook_exchange(payload: dict | None = None, db: Session = Depends(get_db)):
    """Swap the one-time ticket for a session, and say what the app still has to ask."""
    payload = payload or {}
    user = _spend_ticket(db, str(payload.get("ticket") or ""), "login")
    if user.closed_at is not None:
        raise HTTPException(status_code=403, detail="This account has been closed.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is disabled.")
    user.last_login = datetime.now(timezone.utc)
    db.add(Event(user_id=user.id, event_type="facebook_login", payload={"needs_email": bool(user.needs_email)}))
    db.commit()
    return {"access_token": create_access_token({"sub": user.email}), "token_type": "bearer",
            "needs_email": bool(user.needs_email),
            "name": user.name or "", "terms_version": fb.TERMS_VERSION}


@router.post("/facebook/reactivate")
def facebook_reactivate(payload: dict | None = None, db: Session = Depends(get_db)):
    """"This account has been closed. Would you like to reactivate it?" - one click, all back."""
    payload = payload or {}
    user = _spend_ticket(db, str(payload.get("ticket") or ""), "reactivate")
    user.closed_at = None
    user.is_active = True
    user.last_login = datetime.now(timezone.utc)
    db.add(Event(user_id=user.id, event_type="account_reactivated", payload={}))
    db.commit()
    return {"access_token": create_access_token({"sub": user.email}), "token_type": "bearer",
            "needs_email": bool(user.needs_email), "name": user.name or ""}


@router.post("/me/close")
def close_my_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Close my account: reversible, and it stops anything scheduled. Campaigns are kept."""
    if current_user.is_admin:
        raise HTTPException(status_code=400,
                            detail="Operator accounts are removed from the console, not closed from the site.")
    current_user.closed_at = datetime.now(timezone.utc)
    current_user.is_active = False
    db.add(Event(user_id=current_user.id, event_type="account_closed", payload={"kept": "campaigns, leads, reports"}))
    db.commit()
    return {"status": "closed",
            "detail": "Your account is closed and nothing more will be sent. Log in with Facebook any time "
                      "to reactivate it."}


@router.patch("/me/email")
def set_my_email(payload: dict | None = None, current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """Facebook hid the email, so we ask once - for receipts and updates, never to sign in."""
    email = str((payload or {}).get("email") or "").strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=400, detail="That does not look like an email address.")
    taken = (db.query(User)
             .filter(User.email == email, User.id != current_user.id).first())
    if taken is not None:
        raise HTTPException(status_code=409,
                            detail="That address already has a Resmara account. Sign in with the Facebook "
                                   "you used for it, or contact us.")
    current_user.email = email
    current_user.needs_email = False
    current_user.email_confirmed_at = datetime.now(timezone.utc)
    db.add(Event(user_id=current_user.id, event_type="email_set", payload={"source": "facebook_signup"}))
    db.commit()
    return {"ok": True, "email": email}
