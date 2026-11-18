"""Filings: the paperwork with a clock on it, and what each one costs.

Resmara is a California general partnership, so it has almost no state filing — and that is
exactly how a deadline gets missed. The little it does have is date-driven:

  * a Fictitious Business Name statement, inside 40 days of starting business
  * the newspaper run for it, starting inside 45 days of the filing
  * Form 1065 (IRS) and Form 565 (CA FTB) every spring

None of those live in a calendar, and a missed window means paying the fee twice (an FBN
filed late has to be filed again). So this router keeps one row per obligation:

  * ``due_on`` is the hard date; ``window_opens_on`` is the earliest it may be filed
  * ``cost_cents`` is nullable — NULL is "nobody has quoted it yet", which is a different
    fact from 0 ("free") and is never summed as zero
  * ``blocked_on`` names what the row is waiting on, so "not done" is never a mystery
  * marking a recurring row done **rolls it forward**: a fresh open row appears with the
    next date, so the following window exists before this one closes

Admin-only. This is the operators' compliance board, not a customer surface.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import Filing, get_db
from app.services import team_access

router = APIRouter()

KINDS = ("filing", "publication", "tax", "renewal", "report", "other")
STATUSES = ("open", "done", "not_needed")
RECURRENCES = ("one_off", "annual", "every_5_years")
# A filing whose date is inside this many days is "due soon": enough notice to gather the
# money and the signature, not so much that everything looks urgent.
DUE_SOON_DAYS = 30


# ── dates ────────────────────────────────────────────────────────────────────────────
def add_years(d: date, years: int) -> date:
    """Same day-of-year, clamped to the end of the month (29 Feb → 28 Feb)."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(year=d.year + years, day=28)


def _recurrence_years(recurrence: str) -> int:
    return {"annual": 1, "every_5_years": 5}.get(recurrence or "one_off", 0)


def _parse_date(value) -> Optional[date]:
    if value in (None, ""):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{value!r} is not a date (YYYY-MM-DD)")


def _money(cents: Optional[int]) -> Optional[float]:
    return None if cents is None else round(cents / 100.0, 2)


# ── shapes ───────────────────────────────────────────────────────────────────────────
class FilingIn(BaseModel):
    title: str
    kind: str = "filing"
    jurisdiction: Optional[str] = None
    due_on: Optional[str] = None
    window_opens_on: Optional[str] = None
    recurrence: str = "one_off"
    cost_cents: Optional[int] = None
    cost_note: Optional[str] = None
    status: str = "open"
    blocked_on: Optional[str] = None
    owner: Optional[str] = None
    link: Optional[str] = None
    notes: Optional[str] = None


class FilingPatch(BaseModel):
    title: Optional[str] = None
    kind: Optional[str] = None
    jurisdiction: Optional[str] = None
    due_on: Optional[str] = None
    clear_due_on: bool = False
    window_opens_on: Optional[str] = None
    clear_window_opens_on: bool = False
    recurrence: Optional[str] = None
    cost_cents: Optional[int] = None
    clear_cost_cents: bool = False
    cost_note: Optional[str] = None
    status: Optional[str] = None
    done_on: Optional[str] = None
    paid_cents: Optional[int] = None
    confirmation: Optional[str] = None
    blocked_on: Optional[str] = None
    clear_blocked_on: bool = False
    owner: Optional[str] = None
    link: Optional[str] = None
    notes: Optional[str] = None
    who: Optional[str] = None


def _out(row: Filing, today: Optional[date] = None) -> dict:
    today = today or date.today()
    due = row.due_on
    open_row = (row.status == "open")
    days_left = (due - today).days if due else None
    return {
        "id": row.id,
        "title": row.title,
        "kind": row.kind,
        "jurisdiction": row.jurisdiction,
        "due_on": due.isoformat() if due else None,
        "window_opens_on": row.window_opens_on.isoformat() if row.window_opens_on else None,
        "recurrence": row.recurrence,
        "cost_cents": row.cost_cents,
        "cost_usd": _money(row.cost_cents),
        "cost_note": row.cost_note,
        "status": row.status,
        "done_on": row.done_on.isoformat() if row.done_on else None,
        "paid_cents": row.paid_cents,
        "paid_usd": _money(row.paid_cents),
        "confirmation": row.confirmation,
        "blocked_on": row.blocked_on,
        "owner": row.owner,
        "link": row.link,
        "notes": row.notes or "",
        "rolled_from": row.rolled_from,
        "days_left": days_left,
        "overdue": bool(open_row and days_left is not None and days_left < 0),
        "due_soon": bool(open_row and days_left is not None and 0 <= days_left <= DUE_SOON_DAYS),
    }


def _summary(items: list[dict]) -> dict:
    open_rows = [i for i in items if i["status"] == "open"]
    dated = [i for i in open_rows if i["due_on"]]
    known = sum(i["cost_cents"] for i in open_rows if i["cost_cents"] is not None)
    unknown = sum(1 for i in open_rows if i["cost_cents"] is None)
    upcoming = sorted(dated, key=lambda i: i["due_on"])
    nxt = upcoming[0] if upcoming else None
    in_year = [i for i in dated if 0 <= i["days_left"] <= 365]
    return {
        "total": len(items),
        "open": len(open_rows),
        "done": sum(1 for i in items if i["status"] == "done"),
        "not_needed": sum(1 for i in items if i["status"] == "not_needed"),
        "overdue": sum(1 for i in open_rows if i["overdue"]),
        "due_soon": sum(1 for i in open_rows if i["due_soon"]),
        "due_soon_days": DUE_SOON_DAYS,
        "no_deadline": sum(1 for i in open_rows if not i["due_on"]),
        "blocked": sum(1 for i in open_rows if i["blocked_on"]),
        "next": ({"id": nxt["id"], "title": nxt["title"], "due_on": nxt["due_on"],
                  "days_left": nxt["days_left"]} if nxt else None),
        # Known money and unpriced rows are reported separately: adding an unpriced filing as
        # zero is how a board says "$93" while two more fees are still an unknown.
        "open_cost_cents": known,
        "open_cost_usd": _money(known),
        "open_cost_unknown": unknown,
        "next_year_cost_cents": sum(i["cost_cents"] for i in in_year if i["cost_cents"] is not None),
        "next_year_cost_unknown": sum(1 for i in in_year if i["cost_cents"] is None),
        "as_of": date.today().isoformat(),
    }


def _check_choice(value: str, allowed: tuple, field: str) -> str:
    if value not in allowed:
        raise HTTPException(status_code=400, detail=f"{field} must be one of {', '.join(allowed)}")
    return value


def _roll_forward(db: Session, row: Filing) -> Optional[Filing]:
    """A recurring obligation gets its next cycle the moment this one is closed.

    The alternative — leaving one row that somebody must remember to re-date — is the exact
    failure this board exists to prevent, so the next window is created rather than promised.
    """
    years = _recurrence_years(row.recurrence)
    if not years:
        return None
    base = row.due_on or row.done_on or date.today()
    nxt = db.query(Filing).filter(Filing.rolled_from == row.id).first()
    if nxt:                       # already rolled: marking it done twice must not double it
        return nxt
    nxt = Filing(
        title=row.title, kind=row.kind, jurisdiction=row.jurisdiction,
        due_on=add_years(base, years),
        window_opens_on=add_years(row.window_opens_on, years) if row.window_opens_on else None,
        recurrence=row.recurrence, cost_cents=row.cost_cents, cost_note=row.cost_note,
        status="open", owner=row.owner, link=row.link,
        notes=f"[auto] Next cycle, rolled forward from #{row.id} "
              f"({row.recurrence.replace('_', ' ')}).",
        rolled_from=row.id,
    )
    db.add(nxt)
    return nxt


def _mark_done(db: Session, row: Filing, done_on: date, paid_cents: Optional[int],
               confirmation: Optional[str]) -> Optional[Filing]:
    row.status = "done"
    row.done_on = done_on
    if paid_cents is not None:
        row.paid_cents = paid_cents
    if confirmation is not None:
        row.confirmation = (confirmation or None)
    return _roll_forward(db, row)


# ── routes ───────────────────────────────────────────────────────────────────────────
@router.get("/admin/filings")
def list_filings(db: Session = Depends(get_db), _admin=Depends(team_access.needs("money"))):
    rows = db.query(Filing).all()
    items = [_out(r) for r in rows]
    # Open first, then soonest deadline; closed rows last because the board is about what
    # is still owed. An undated open row sorts after the dated ones: it is a gap, not a due date.
    items.sort(key=lambda i: (
        i["status"] != "open",
        i["due_on"] is None,
        i["due_on"] or "9999-12-31",
        i["id"],
    ))
    return {"items": items, "summary": _summary(items),
            "kinds": list(KINDS), "recurrences": list(RECURRENCES), "statuses": list(STATUSES)}


@router.post("/admin/filings", status_code=201)
def create_filing(payload: FilingIn, db: Session = Depends(get_db),
                  _admin=Depends(team_access.needs("money"))):
    title = (payload.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="A filing needs a title")
    _check_choice(payload.kind, KINDS, "kind")
    _check_choice(payload.status, STATUSES, "status")
    _check_choice(payload.recurrence, RECURRENCES, "recurrence")
    if payload.cost_cents is not None and payload.cost_cents < 0:
        raise HTTPException(status_code=422, detail="The cost has to be zero or more, in cents")
    row = Filing(
        title=title[:240], kind=payload.kind,
        jurisdiction=(payload.jurisdiction or "").strip()[:120] or None,
        due_on=_parse_date(payload.due_on),
        window_opens_on=_parse_date(payload.window_opens_on),
        recurrence=payload.recurrence, cost_cents=payload.cost_cents,
        cost_note=(payload.cost_note or "").strip()[:240] or None,
        status=payload.status,
        blocked_on=(payload.blocked_on or "").strip()[:240] or None,
        owner=(payload.owner or "").strip()[:160] or None,
        link=(payload.link or "").strip()[:400] or None,
        notes=payload.notes or None,
    )
    if row.status == "done":
        row.done_on = date.today()
    db.add(row)
    db.commit()
    db.refresh(row)
    return _out(row)


@router.patch("/admin/filings/{filing_id}")
def patch_filing(filing_id: int, payload: FilingPatch, db: Session = Depends(get_db),
                 _admin=Depends(team_access.needs("money"))):
    row = db.get(Filing, filing_id)
    if not row:
        raise HTTPException(status_code=404, detail="No such filing")

    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="A filing needs a title")
        row.title = title[:240]
    if payload.kind is not None:
        row.kind = _check_choice(payload.kind, KINDS, "kind")
    if payload.recurrence is not None:
        row.recurrence = _check_choice(payload.recurrence, RECURRENCES, "recurrence")
    if payload.jurisdiction is not None:
        row.jurisdiction = payload.jurisdiction.strip()[:120] or None
    if payload.clear_due_on:
        row.due_on = None
    elif payload.due_on is not None:
        row.due_on = _parse_date(payload.due_on)
    if payload.clear_window_opens_on:
        row.window_opens_on = None
    elif payload.window_opens_on is not None:
        row.window_opens_on = _parse_date(payload.window_opens_on)
    # An explicit null is the instruction "nobody has priced this" — different from leaving
    # the field alone, which is why it needs its own flag.
    if payload.clear_cost_cents:
        row.cost_cents = None
    elif payload.cost_cents is not None:
        if payload.cost_cents < 0:
            raise HTTPException(status_code=422, detail="The cost has to be zero or more, in cents")
        row.cost_cents = payload.cost_cents
    if payload.cost_note is not None:
        row.cost_note = payload.cost_note.strip()[:240] or None
    if payload.clear_blocked_on:
        row.blocked_on = None
    elif payload.blocked_on is not None:
        row.blocked_on = payload.blocked_on.strip()[:240] or None
    if payload.owner is not None:
        row.owner = payload.owner.strip()[:160] or None
    if payload.link is not None:
        row.link = payload.link.strip()[:400] or None
    if payload.notes is not None:
        row.notes = payload.notes or None
    if payload.paid_cents is not None:
        row.paid_cents = payload.paid_cents
    if payload.confirmation is not None:
        row.confirmation = payload.confirmation.strip()[:240] or None

    rolled = None
    if payload.status is not None:
        status = _check_choice(payload.status, STATUSES, "status")
        if status == "done" and row.status != "done":
            done_on = _parse_date(payload.done_on) or date.today()
            rolled = _mark_done(db, row, done_on, payload.paid_cents, payload.confirmation)
        else:
            row.status = status
            if status != "done":
                row.done_on = None

    db.commit()
    db.refresh(row)
    if rolled is not None:
        db.refresh(rolled)
    return {"item": _out(row), "next": _out(rolled) if rolled is not None else None}


@router.delete("/admin/filings/{filing_id}")
def delete_filing(filing_id: int, db: Session = Depends(get_db),
                  _admin=Depends(team_access.needs("money"))):
    row = db.get(Filing, filing_id)
    if not row:
        raise HTTPException(status_code=404, detail="No such filing")
    db.delete(row)
    db.commit()
    return {"deleted": filing_id}
