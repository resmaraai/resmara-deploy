"""Social leads API (Post Engine §10.4).

The panel on a live campaign page had no endpoint behind it: it read sample comments from
``static/leads.js`` and stored what the agent typed in ``localStorage``. These routes are the
server side of it - the leads the scan found, the agent's own additions, and the two actions the
panel offers (mark handled, remove).

Ownership is checked on every call: a lead is reachable only through a campaign the signed-in
account owns, so an id guessed from another account's URL is a 404, not a peek.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import Boost, Lead, User, get_db
from app.core.security import get_current_user
from app.services import leads as leads_service
from app.services.lead_counts import lead_totals

router = APIRouter()

STATUSES = ("new", "handled", "removed")


class LeadOut(BaseModel):
    id: int
    boost_id: int
    platform: str
    channel: Optional[str] = None
    source: str = "comment"
    author_name: Optional[str] = None
    text: Optional[str] = None
    permalink: Optional[str] = None
    post_label: Optional[str] = None
    comment_at: Optional[datetime] = None
    status: str = "new"
    classified_by: Optional[str] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None
    notified_at: Optional[datetime] = None
    email_error: Optional[str] = None
    note: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    wants: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LeadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=4000)
    where: str = "Instagram"
    notify: bool = False


class LeadUpdate(BaseModel):
    status: Optional[str] = None
    note: Optional[str] = Field(default=None, max_length=2000)


def _owned_boost(boost_id: int, user: User, db: Session) -> Boost:
    boost = db.query(Boost).filter(Boost.id == boost_id, Boost.user_id == user.id).first()
    if not boost:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return boost


def _owned_lead(lead_id: int, user: User, db: Session) -> Lead:
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.user_id == user.id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


def _require_system_token(x_resmara_token: str = Header(default="")):
    """The scheduler is machine-called: shared token, refused outright when none is set."""
    if not settings.PUBLISH_TOKEN:
        raise HTTPException(status_code=503, detail="RESMARA_PUBLISH_TOKEN is not configured")
    if x_resmara_token != settings.PUBLISH_TOKEN:
        raise HTTPException(status_code=403, detail="Bad publish token")


@router.get("/boosts/{boost_id}/leads")
def list_leads(boost_id: int, include_removed: bool = False,
               current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """This campaign's leads, newest first, with the count the card badge shows.

    ``open`` is what the panel calls "new": not yet ticked off and not removed. ``scan`` tells
    the page when comments were last read and what Meta said, so an empty list can say whose
    fault the emptiness is.
    """
    boost = _owned_boost(boost_id, current_user, db)
    query = db.query(Lead).filter(Lead.boost_id == boost.id)
    if not include_removed:
        query = query.filter(Lead.status != "removed")
    rows = query.order_by(Lead.comment_at.is_(None), Lead.comment_at.desc(), Lead.id.desc()).all()
    open_count = len([r for r in rows if r.status == "new"])
    return {
        "boost_id": boost.id,
        "leads": [LeadOut.model_validate(r) for r in rows],
        "open": open_count,
        # Every lead ever flagged on this campaign, by source. Removed ones still count.
        "totals": lead_totals(db, [boost.id])[boost.id],
        "scan": {
            "checked_at": boost.leads_checked_at,
            "note": boost.leads_scan_note,
        },
    }


@router.post("/boosts/{boost_id}/leads", response_model=LeadOut, status_code=201)
def create_lead(boost_id: int, body: LeadCreate,
                current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """A lead the agent typed in. The server keeps it, so it survives a cleared browser."""
    boost = _owned_boost(boost_id, current_user, db)
    lead = leads_service.add_lead(db, boost, name=body.name, text=body.text, where=body.where,
                                  notify=body.notify)
    db.commit()
    db.refresh(lead)
    return LeadOut.model_validate(lead)


@router.patch("/leads/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, body: LeadUpdate,
                current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Tick a lead off (handled) or put it back to new, and/or save the agent's note on it.
    Removing has its own route."""
    if body.status is None and body.note is None:
        raise HTTPException(status_code=422, detail="Send a status, a note, or both")
    if body.status is not None and body.status not in STATUSES:
        raise HTTPException(status_code=422, detail=f"status must be one of {', '.join(STATUSES)}")
    lead = _owned_lead(lead_id, current_user, db)
    if body.status is not None:
        lead.status = body.status
    if body.note is not None:
        lead.note = body.note.strip() or None
    db.commit()
    db.refresh(lead)
    return LeadOut.model_validate(lead)


@router.delete("/leads/{lead_id}", response_model=LeadOut)
def remove_lead(lead_id: int,
                current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Not a lead. The row stays as `removed` so the next scan does not flag it again."""
    lead = _owned_lead(lead_id, current_user, db)
    lead.status = "removed"
    db.commit()
    db.refresh(lead)
    return LeadOut.model_validate(lead)


@router.post("/boosts/{boost_id}/leads/scan")
async def scan_one(boost_id: int,
                   current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Read this campaign's comments now, instead of waiting for the 15-minute run."""
    boost = _owned_boost(boost_id, current_user, db)
    return await leads_service.scan_boost(db, boost)


@router.post("/admin/leads/scan")
async def scan_all(x_resmara_token: str = Depends(_require_system_token),
                   db: Session = Depends(get_db)):
    """Every due campaign. Called by the scheduler after the publisher runs."""
    return await leads_service.scan_all(db)
