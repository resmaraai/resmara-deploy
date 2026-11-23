"""Accounts: register, login, profile, and the password-reset flow."""
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db, User, PasswordReset, Event
from app.core.security import get_password_hash, verify_password, create_access_token, get_current_user
from app.schemas.resmara import UserCreate, UserOut, Token
from app.services import mail
from app.services.access import signup_block_reason, parse_allowlist

router = APIRouter()

RESET_TTL_MINUTES = 60
CONFIRM_TTL_HOURS = 48


def _public_base() -> str:
    base = (getattr(settings, "PUBLIC_BASE_URL", "") or "").rstrip("/")
    return base or "https://www.resmara.com"


def _confirm_link(token: str) -> str:
    return f"{_public_base()}/confirm?token={token}"


def _send_confirmation(user: User, db: Session) -> str:
    """Send the confirm link, or say honestly that there is no way to send it.

    "Email confirmation before first sign-in" (item 8) is only enforceable if an email actually
    went out; on a deploy with no mail provider the account is confirmed on the spot and the
    response says so, rather than locking a beta tester out of an inbox that will never be written
    to.
    """
    token = secrets.token_urlsafe(24)
    user.confirm_token_hash = _hash(token)
    user.confirm_sent_at = datetime.now(timezone.utc)
    ok = mail.send_email(user.email, "Confirm your Resmara email",
                         "Welcome to Resmara.\n\n"
                         "Confirm this address to finish setting up your account:\n"
                         f"{_confirm_link(token)}\n\n"
                         f"The link works for {CONFIRM_TTL_HOURS} hours. If this was not you, ignore this "
                         "message and nothing happens.\n\n- Resmara")
    if not ok:
        user.email_confirmed_at = datetime.now(timezone.utc)
        user.confirm_token_hash = None
    db.commit()
    return "sent" if ok else "not_configured"


@router.post("/register", response_model=UserOut, status_code=201)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    email = user_in.email.strip().lower()
    # Same rule the reset and change-password screens enforce, checked here too: an account
    # created over the API with a one-character password is a support ticket waiting to happen.
    if len(user_in.password or "") < 8:
        raise HTTPException(status_code=400, detail="Use at least 8 characters for the password")
    blocked = signup_block_reason(email, getattr(user_in, "invite_code", None),
                                  settings.SIGNUP_EMAILS, settings.SIGNUP_CODE,
                                  settings.ADMIN_EMAILS)
    if blocked:
        raise HTTPException(status_code=403, detail=blocked)
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=email, hashed_password=get_password_hash(user_in.password), name=user_in.name,
                is_admin=email in parse_allowlist(settings.ADMIN_EMAILS))
    db.add(user)
    db.flush()
    # Engine 9, section 1a: stamp where this sign-up came from, once, before anything else reads
    # the account. The stamp is what Marketing's channel rows are built on.
    from app.services import attribution
    attribution.stamp_signup(db, user, getattr(user_in, "source", None))
    # The activity log is what the operator console charts; a new account is the first
    # thing it should be able to show.
    # Email confirmation before first sign-in (item 8). When no provider is configured the
    # account is usable immediately and the response says the email did not go out.
    confirmation = _send_confirmation(user, db)
    db.add(Event(user_id=user.id, event_type="user_registered",
                 payload={"source": "password", "confirmation": confirmation}))
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username.strip().lower()).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        # Deactivating an account has to actually stop it signing in.
        raise HTTPException(status_code=403, detail="This account is disabled")
    if user.confirm_token_hash and not user.email_confirmed_at:
        # Only blocks accounts we actually emailed: an existing account with no pending token
        # keeps working, which is what makes this safe to ship on a deploy with no mail provider.
        raise HTTPException(status_code=403,
                            detail="Confirm your email address first - check your inbox for the "
                                   "Resmara link (it can be resent from the sign-in screen).")
    if not user.is_admin and user.email in parse_allowlist(settings.ADMIN_EMAILS):
        # Owners listed in RESMARA_ADMIN_EMAILS are operators from their first login, whether
        # the account predates the setting or not; no database edit needed to add a second one.
        user.is_admin = True
    user.last_login = datetime.utcnow()
    db.commit()
    token = create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/confirm")
def confirm_email(token: str = "", db: Session = Depends(get_db)):
    """The link in the confirmation email. Safe to call twice; the second says so."""
    if not token:
        raise HTTPException(status_code=400, detail="That link is missing its token")
    user = db.query(User).filter(User.confirm_token_hash == _hash(token)).first()
    if not user:
        raise HTTPException(status_code=400,
                            detail="That link has already been used or has expired - sign in and "
                                   "ask for a new one.")
    sent = user.confirm_sent_at
    if sent is not None:
        age = datetime.now(timezone.utc) - (sent if sent.tzinfo else sent.replace(tzinfo=timezone.utc))
        if age > timedelta(hours=CONFIRM_TTL_HOURS):
            raise HTTPException(status_code=400,
                                detail="That link has expired - sign in and ask for a new one.")
    user.email_confirmed_at = datetime.now(timezone.utc)
    user.confirm_token_hash = None
    db.add(Event(user_id=user.id, event_type="email_confirmed", payload={}))
    db.commit()
    return {"ok": True, "email": user.email}


@router.post("/confirm/resend")
def resend_confirmation(email: str, db: Session = Depends(get_db)):
    """Ask for the link again. Says the same thing whether or not the address exists."""
    user = db.query(User).filter(User.email == (email or "").strip().lower()).first()
    if not user or user.email_confirmed_at:
        return {"ok": True, "delivery": "sent"}
    delivery = _send_confirmation(user, db)
    return {"ok": True, "delivery": delivery}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_me(name: str = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if name is not None:
        current_user.name = name
        db.commit()
        db.refresh(current_user)
    return current_user


@router.post("/me/password")
def change_password(current_password: str, new_password: str,
                    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    current_user.hashed_password = get_password_hash(new_password)
    # Any outstanding reset link is now pointless.
    db.query(PasswordReset).filter(PasswordReset.user_id == current_user.id,
                                   PasswordReset.used_at.is_(None)).update({"used_at": datetime.utcnow()})
    db.commit()
    return {"status": "password_changed"}


@router.delete("/me")
def delete_me(password: str, current_user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    """Close the account and remove the personal details from it.

    The password has to be typed again: a stale token left in a browser must not be able to
    wipe an account. Orders are kept (they are the payment record), campaigns are kept for
    the operator's history, but the address, name, brand profile and password are removed
    and the account can never sign in again — a California customer has the right to ask
    for this, so the product has to be able to do it without a database edit.
    """
    if not verify_password(password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Password is incorrect")
    if current_user.is_admin:
        raise HTTPException(status_code=400,
                            detail="Operator accounts are removed from the console, not from the site.")
    user_id = current_user.id
    current_user.is_active = False
    current_user.email = f"deleted-{user_id}@resmara.invalid"
    current_user.name = "Deleted account"
    current_user.brand = {}
    current_user.hashed_password = get_password_hash(secrets.token_urlsafe(32))
    db.query(PasswordReset).filter(PasswordReset.user_id == user_id,
                                   PasswordReset.used_at.is_(None)).update({"used_at": datetime.utcnow()})
    db.add(Event(user_id=user_id, event_type="account_deleted", payload={"reason": "customer request"}))
    db.commit()
    return {"status": "deleted", "detail": "This account is closed and its details have been removed."}


@router.get("/me/brand")
def get_my_brand(current_user: User = Depends(get_current_user)):
    """The brand profile that belongs to this account, wherever it was typed."""
    return {"brand": current_user.brand or {}}


@router.put("/me/brand")
def put_my_brand(payload: dict, current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """Keep the profile on the account, not only in one browser's localStorage.

    Text fields only: a logo or headshot is an image the customer uploads, and those stay
    in the browser's own copy (the form says so). 32 KB is generous for eight text fields
    and small enough that a bad client cannot stuff the row.
    """
    brand = (payload or {}).get("brand")
    if not isinstance(brand, dict):
        raise HTTPException(status_code=400, detail="brand must be a JSON object")
    if len(json.dumps(brand)) > 32_000:
        raise HTTPException(status_code=413, detail="brand profile is too large (32 KB limit)")
    cleaned = {k: v for k, v in brand.items() if isinstance(k, str) and isinstance(v, (str, int, float, bool, list))}
    current_user.brand = cleaned
    db.commit()
    db.refresh(current_user)
    return {"brand": current_user.brand or {}}


@router.post("/me/brand/from-meta")
async def build_brand_from_meta(current_user: User = Depends(get_current_user),
                                db: Session = Depends(get_db)):
    """Build the brand kit from the agent's own Facebook Page (Brand Engine v1.0 §4).

    Meta is the source of the facts - name, category, about, phone, website, logo. Voice, palette
    and typeface are proposals from the model and come back marked ``confirmed: false``: the engine
    never overwrites what the agent typed. Nothing is saved here; the client shows the proposal and
    the agent presses save, so a wrong palette cannot silently become the brand.
    """
    from app.services import brand_engine

    token = ""
    try:
        from app.db.session import AdAccount
        acct = (db.query(AdAccount).filter(AdAccount.user_id == current_user.id)
                .order_by(AdAccount.id.desc()).first())
        token = (acct.access_token or "") if acct is not None else ""
    except Exception:  # noqa: BLE001
        token = ""
    if not token:
        raise HTTPException(status_code=400,
                            detail="Resmara is not connected to your Facebook account yet, so there "
                                   "is no Page to read. Connect in Connections and try again.")
    page = await brand_engine.read_page(token)
    if not page.get("ok"):
        raise HTTPException(status_code=502,
                            detail="Facebook did not return your Page: "
                                   + str(page.get("reason") or "unknown error"))
    kit = await brand_engine.brand_from_meta(page.get("page") or {}, page.get("business"))
    return kit


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _naive_utc(dt: datetime) -> datetime:
    """Normalise a stored timestamp so it can be compared with ``datetime.utcnow()``.

    Postgres gives back timezone-aware datetimes for ``timestamptz`` columns while this app
    writes and compares naive UTC, and comparing the two raises
    ``TypeError: can't compare offset-naive and offset-aware datetimes``. SQLite returns naive
    rows, so nothing local or in the suite ever saw it — in production it was a 500
    "Internal Server Error" on the reset page, the moment a real link was submitted.
    """
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


@router.post("/password-reset/request")
def request_reset(email: str, request: Request, db: Session = Depends(get_db)):
    """Start a reset. Always answers the same way, so this cannot be used to discover
    which email addresses have accounts.

    The reset link is emailed when a mail provider is configured. Until one is, the answer
    says ``delivery='not_configured'`` and the token goes nowhere near the response: it used
    to be handed back "so the flow could be exercised", which on the public site meant anyone
    who knew an address could reset that account's password. A locked-out customer now gets
    a link from support instead (an operator mints one in the console), so no token ever has
    to leave the server.
    """
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    delivery = "not_configured"
    if user and user.is_active:
        raw = secrets.token_urlsafe(32)
        db.add(PasswordReset(user_id=user.id, token_hash=_hash(raw),
                             expires_at=datetime.utcnow() + timedelta(minutes=RESET_TTL_MINUTES)))
        db.commit()
        link = reset_link(raw, request)
        if mail.send_email(user.email, "Reset your Resmara password",
                           f"Someone asked to reset the password for this account.\n\n"
                           f"Use this link within {RESET_TTL_MINUTES} minutes:\n{link}\n\n"
                           f"If this wasn't you, ignore this email."):
            delivery = "email"
            db.add(Event(user_id=user.id, event_type="password_reset_sent",
                         payload={"delivery": "email"}))
        else:
            # Say which provider refused and why. "no mail provider configured" was wrong as soon
            # as Resend/SMTP existed but errored, and it sent the operator looking for a missing
            # setting instead of an unverified domain.
            db.add(Event(user_id=user.id, event_type="password_reset_unmailed",
                         payload={"reason": mail.last_attempt().get("reason")
                                  or "no mail provider configured"}))
        db.commit()
    return {"status": "ok", "delivery": delivery, "expires_minutes": RESET_TTL_MINUTES,
            "detail": ("Check your email for the reset link." if delivery == "email"
                       else "We could not email a link. Contact support and we will send you one.")}


def reset_link(token: str, request: Request | None = None) -> str:
    """The page a reset token opens: a real path, not a hash route (mail clients and
    scanners strip fragments), on the host the customer is actually using.

    The host comes from the request rather than configuration, so a link minted on
    www.resmara.com is a www.resmara.com link — not the onrender.com host the platform
    happens to set, and not a laptop's tunnel URL.
    """
    return f"{site_base(request)}/reset?token={token}"


def site_base(request: Request | None = None) -> str:
    """The public origin of this request, honouring the proxy's forwarded headers."""
    if request is not None:
        proto = (request.headers.get("x-forwarded-proto") or request.url.scheme).split(",")[0].strip()
        host = (request.headers.get("x-forwarded-host") or request.headers.get("host")
                or request.url.netloc)
        if host:
            return f"{proto}://{host.split(',')[0].strip()}"
    return settings.PUBLIC_BASE_URL.rstrip("/")



@router.post("/password-reset/confirm")
def confirm_reset(token: str, new_password: str, db: Session = Depends(get_db)):
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    row = db.query(PasswordReset).filter(PasswordReset.token_hash == _hash(token)).first()
    if (not row or row.used_at is not None
            or _naive_utc(row.expires_at) < datetime.utcnow()):
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired")
    user = db.query(User).filter(User.id == row.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired")
    user.hashed_password = get_password_hash(new_password)
    row.used_at = datetime.utcnow()
    # Invalidate every other outstanding link for this account.
    db.query(PasswordReset).filter(PasswordReset.user_id == user.id, PasswordReset.id != row.id,
                                   PasswordReset.used_at.is_(None)).update({"used_at": datetime.utcnow()})
    db.commit()
    return {"status": "password_reset", "email": user.email}
