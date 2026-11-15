"""The Team page: who can sign in to the Team room, and what each of them may read.

Two rules shape this file:

  * Removing someone from the team must not delete their business. A team member may also be a
    customer with campaigns, so "remove" clears console access and leaves the account and its
    campaigns alone. Only an account that has nothing of its own is switched off.
  * The operator accounts (RESMARA_ADMIN_EMAILS) can never be demoted or removed from here.
    They are the way back in if a team edit goes wrong.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.auth import RESET_TTL_MINUTES, reset_link
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import Boost, PasswordReset, User, get_db
from app.services import mail, team_access

log = logging.getLogger("resmara.team")

router = APIRouter()


def _owners() -> set:
    return {e.strip().lower() for e in (settings.ADMIN_EMAILS or "").split(",") if e.strip()}


def _is_owner(user: User) -> bool:
    return (user.email or "").strip().lower() in _owners()


def _row(user: User) -> Dict[str, Any]:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "super_admin": bool(user.team_super_admin or user.is_admin),
        "owner": _is_owner(user),
        "access": team_access.sanitise_access(user.team_access or []),
        "status": "invited" if user.last_login is None else "active",
        "last_login": user.last_login.isoformat() if user.last_login else None,
        "invited_at": user.team_invited_at.isoformat() if user.team_invited_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "is_active": bool(user.is_active),
        "campaigns": 0,
    }


def _mint_invite(db: Session, user: User, request: Optional[Request]) -> Dict[str, Any]:
    raw = secrets.token_urlsafe(32)
    db.add(PasswordReset(user_id=user.id,
                         token_hash=hashlib.sha256(raw.encode()).hexdigest(),
                         expires_at=datetime.utcnow() + timedelta(minutes=RESET_TTL_MINUTES)))
    user.team_invited_at = datetime.utcnow()
    db.commit()
    link = reset_link(raw, request)
    sent = False
    if mail.mail_configured():
        sent = bool(mail.send_email(
            user.email, "You are on the Resmara Team room",
            "Use this link to choose your own password and sign in to the Resmara Team room:\n"
            f"{link}\n\nIt expires in {RESET_TTL_MINUTES} minutes. "
            "If you were not expecting this, ignore this email."))
    # The console reads `invite_link` (that is what it puts in front of the operator), so that is
    # the name; `link` stays as an alias for anything that already read it that way.
    return {"invite_link": link, "link": link, "emailed": sent,
            "expires_minutes": RESET_TTL_MINUTES}


@router.get("/admin/team")
def list_team(user=Depends(team_access.needs("team")), db: Session = Depends(get_db)):
    """Everyone with console access: the operators, the team, and invites not yet accepted."""
    if not team_access.is_super(user):
        raise HTTPException(status_code=403, detail="Only a super admin can see the team")
    rows = (
        db.query(User)
        .filter((User.is_admin.is_(True)) | (User.team_super_admin.is_(True))
                | (User.team_access.isnot(None)))
        .order_by(User.is_admin.desc(), User.id)
        .all()
    )
    out = []
    for person in rows:
        # Removing someone clears their access but leaves the row (their account and campaigns are
        # theirs). The list is "who is in the room", so a member with no group and no operator flag
        # is not in it - otherwise a removed person keeps sitting on the page with a blank access.
        if not person.is_admin and not person.team_super_admin and not (person.team_access or []):
            continue
        row = _row(person)
        row["campaigns"] = db.query(Boost).filter(Boost.user_id == person.id).count()
        out.append(row)
    return out


@router.post("/admin/team")
def add_member(payload: Dict[str, Any] = Body(...), request: Request = None,
               user=Depends(team_access.needs("team")), db: Session = Depends(get_db)):
    """Add someone to the team, or give console access to an account that already exists."""
    if not team_access.is_super(user):
        raise HTTPException(status_code=403, detail="Only a super admin can change the team")
    email = str(payload.get("email") or "").strip().lower()
    name = str(payload.get("name") or "").strip() or None
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=422, detail="That does not look like an email address")
    access = team_access.sanitise_access(payload.get("access"))
    super_admin = bool(payload.get("super_admin"))

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        # An existing customer promoted to the team keeps their account and their campaigns.
        existing.team_access = access
        existing.team_super_admin = super_admin
        existing.is_admin = bool(existing.is_admin or _is_owner(existing))
        if name and not existing.name:
            existing.name = name
        db.commit()
        invite = _mint_invite(db, existing, request)
        return {"id": existing.id, "email": existing.email, "created": False, **invite}

    member = User(
        email=email,
        name=name,
        hashed_password=get_password_hash(secrets.token_urlsafe(32)),
        is_active=True,
        is_admin=_is_owner_by_email(email),
        team_access=access,
        team_super_admin=super_admin,
        subscription_status="inactive",
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    invite = _mint_invite(db, member, request)
    log.info("team member %s added by %s (%s)", email, user.email, access)
    return {"id": member.id, "email": member.email, "created": True, **invite}


def _is_owner_by_email(email: str) -> bool:
    return email.strip().lower() in _owners()


@router.patch("/admin/team/{member_id}")
def update_member(member_id: int, payload: Dict[str, Any] = Body(...),
                  user=Depends(team_access.needs("team")), db: Session = Depends(get_db)):
    """Change what one person may read, or make them a super admin."""
    if not team_access.is_super(user):
        raise HTTPException(status_code=403, detail="Only a super admin can change the team")
    member = db.query(User).filter(User.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="No such team member")
    if "access" in payload:
        member.team_access = team_access.sanitise_access(payload.get("access"))
    if "super_admin" in payload:
        wants_super = bool(payload.get("super_admin"))
        if not wants_super and member.id == user.id:
            raise HTTPException(status_code=400, detail="You cannot remove your own super admin access")
        if not wants_super and _is_owner(member):
            raise HTTPException(status_code=400, detail="That account is an owner in the service settings")
        member.team_super_admin = wants_super
    db.commit()
    return _row(member)


@router.post("/admin/team/{member_id}/invite")
def resend_invite(member_id: int, request: Request = None,
                  user=Depends(team_access.needs("team")), db: Session = Depends(get_db)):
    """A fresh link for someone who never signed in (or lost the first one)."""
    if not team_access.is_super(user):
        raise HTTPException(status_code=403, detail="Only a super admin can change the team")
    member = db.query(User).filter(User.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="No such team member")
    invite = _mint_invite(db, member, request)
    return {"email": member.email, **invite}


@router.delete("/admin/team/{member_id}")
def remove_member(member_id: int, user=Depends(team_access.needs("team")), db: Session = Depends(get_db)):
    """Take console access away. Their account and campaigns stay unless it has nothing of its own."""
    if not team_access.is_super(user):
        raise HTTPException(status_code=403, detail="Only a super admin can change the team")
    member = db.query(User).filter(User.id == member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="No such team member")
    if member.id == user.id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself")
    if _is_owner(member):
        raise HTTPException(status_code=400, detail="That account is an owner in the service settings")

    has_business = db.query(Boost).filter(Boost.user_id == member.id).count() > 0
    member.team_access = []
    member.team_super_admin = False
    member.is_admin = False
    if not has_business:
        member.is_active = False
    db.commit()
    return {"id": member.id, "email": member.email, "deactivated": not has_business,
            "message": ("Removed. The account had nothing of its own, so it is switched off."
                        if not has_business else
                        "Removed from the team. Their account and campaigns are untouched.")}
