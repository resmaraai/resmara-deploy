"""Build room: who is working on what, and who has it claimed.

Two people work this product and they touch opposite halves of one repository — Adam the
front end (``static/``), Dan the back end (``app/``, ``scripts/``, ``render.yaml``). Their
failure modes are not mysterious: two people editing the same screen on the same evening, or
a task going quiet for a week because each assumed the other had it.

So this router is a claim board, not a chat:

  * a task is one piece of work — what, which half, when it is due, and whether it was tested
  * **claiming is a lock.** While a task carries a fresh claim, another person's edit is
    refused with 409 that names the holder and the age of the claim. The console turns that
    into "Adam has this since Tuesday" rather than a silently lost change.
  * a claim older than ``CLAIM_STALE_HOURS`` is stale (they went quiet, a laptop died) and may
    be taken over — with the takeover written into the row's notes, so nothing is silently
    stolen.
  * the summary counts what a human owes: open, blocked, overdue, untested. Every square on
    the console names one of those and nothing else.

Everything here is admin-only: this is the operators' board, not a customer surface.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_admin_user
from app.db.session import BuildroomTask, get_db

router = APIRouter()

AREAS = ("front_end", "back_end", "both")
STATUSES = ("todo", "doing", "review", "done", "blocked")
# Long enough to cover a working day, short enough that a claim does not outlive the person's
# interest in the task. Anything older is stale and can be taken over.
CLAIM_STALE_HOURS = 24


# ── helpers ──────────────────────────────────────────────────────────────────────────
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    """SQLite hands datetimes back naive; comparing one to an aware datetime raises."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def claim_age_hours(task: BuildroomTask) -> Optional[float]:
    at = _aware(task.claimed_at)
    if not at:
        return None
    return round((_utcnow() - at).total_seconds() / 3600, 1)


def claim_is_fresh(task: BuildroomTask) -> bool:
    age = claim_age_hours(task)
    return age is not None and age < CLAIM_STALE_HOURS


def _require_free(task: BuildroomTask, who: Optional[str], force: bool = False) -> None:
    """Refuse a write from anyone but the holder of a fresh claim.

    ``force`` exists because the console's operator has to be able to clear a claim whose
    holder has vanished, and waiting out the staleness clock to fix a blocked board is worse
    than the risk of a rare double-edit. A forced write says so in the row's notes.
    """
    if not task.claimed_by or not claim_is_fresh(task):
        return
    if force:
        return
    if who and who.strip().lower() == task.claimed_by.strip().lower():
        return
    raise HTTPException(
        status_code=409,
        detail={
            "held_by": task.claimed_by,
            "claimed_at": (_aware(task.claimed_at) or _utcnow()).isoformat(),
            "age_hours": claim_age_hours(task),
            "why": "Somebody else has this claimed. Release it, or wait for the claim to go stale "
                   f"({CLAIM_STALE_HOURS}h), before editing it.",
        },
    )


def _append_note(task: BuildroomTask, line: str) -> None:
    stamp = _utcnow().date().isoformat()
    task.notes = ((task.notes + "\n") if task.notes else "") + f"[{stamp}] {line}"


def _out(task: BuildroomTask) -> dict:
    today = date.today()
    overdue = bool(task.due_on and task.status != "done" and task.due_on < today)
    return {
        "id": task.id,
        "title": task.title,
        "area": task.area,
        "status": task.status,
        "notes": task.notes or "",
        "assigned_to": task.assigned_to,
        "claimed_by": task.claimed_by,
        "claimed_at": (_aware(task.claimed_at) or None).isoformat() if task.claimed_at else None,
        "claim_age_hours": claim_age_hours(task),
        "claim_fresh": claim_is_fresh(task),
        "due_on": task.due_on.isoformat() if task.due_on else None,
        "overdue": overdue,
        "tested_by": task.tested_by,
        "tested_at": (_aware(task.tested_at) or None).isoformat() if task.tested_at else None,
        "test_note": task.test_note or "",
        "created_by": task.created_by,
        "created_at": (_aware(task.created_at) or None).isoformat() if task.created_at else None,
        "updated_at": (_aware(task.updated_at) or None).isoformat() if task.updated_at else None,
    }


def _group(items: list[dict], key: str) -> dict[str, int]:
    """Count open tasks per person, for either the assignment or the claim."""
    out: dict[str, int] = {}
    for t in items:
        who = t.get(key)
        if who:
            out[who] = out.get(who, 0) + 1
    return out


def _summary(items: list[dict]) -> dict:
    today = date.today()
    by_owner: dict[str, int] = {}
    for t in items:
        if t["status"] != "done" and t["claimed_by"] and t["claim_fresh"]:
            by_owner[t["claimed_by"]] = by_owner.get(t["claimed_by"], 0) + 1
    open_items = [t for t in items if t["status"] != "done"]
    return {
        "tasks": len(items),
        "open": len(open_items),
        "claimed": sum(1 for t in open_items if t["claimed_by"] and t["claim_fresh"]),
        "unclaimed": sum(1 for t in open_items if not (t["claimed_by"] and t["claim_fresh"])),
        "blocked": sum(1 for t in open_items if t["status"] == "blocked"),
        "review": sum(1 for t in open_items if t["status"] == "review"),
        "overdue": sum(1 for t in open_items if t["due_on"] and date.fromisoformat(t["due_on"]) < today),
        "tested": sum(1 for t in items if t["tested_at"]),
        "untested_and_done": sum(1 for t in items if t["status"] == "done" and not t["tested_at"]),
        "by_owner": by_owner,
        # Assignment is the plan (who should do it); the claim is the lock (who is on it now).
        # Both are counted because the question "is this anybody's?" is answered by the claim,
        # while "did we agree who owns this?" is answered by the assignment.
        "assigned": sum(1 for t in open_items if t["assigned_to"]),
        "unassigned": sum(1 for t in open_items if not t["assigned_to"]),
        "by_assignee": _group(open_items, "assigned_to"),
        "stale_claims": sum(1 for t in open_items if t["claimed_by"] and not t["claim_fresh"]),
        "stale_after_hours": CLAIM_STALE_HOURS,
    }


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        raise HTTPException(status_code=400, detail=f"{value!r} is not a date (YYYY-MM-DD)")


# ── payloads ─────────────────────────────────────────────────────────────────────────
class TaskIn(BaseModel):
    title: str
    area: str = "front_end"
    status: str = "todo"
    notes: Optional[str] = None
    due_on: Optional[str] = None
    assigned_to: Optional[str] = None
    claimed_by: Optional[str] = None
    created_by: Optional[str] = None


class TaskPatch(BaseModel):
    title: Optional[str] = None
    area: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    due_on: Optional[str] = None
    assigned_to: Optional[str] = None
    clear_assigned: bool = False
    tested_by: Optional[str] = None
    test_note: Optional[str] = None
    clear_tested: bool = False
    who: Optional[str] = None
    force: bool = False


class WhoIn(BaseModel):
    by: str
    force: bool = False


class TestedIn(BaseModel):
    by: str
    note: Optional[str] = None


# ── routes ───────────────────────────────────────────────────────────────────────────
@router.get("/admin/buildroom")
def list_tasks(db: Session = Depends(get_db), _admin=Depends(get_admin_user)):
    rows = db.query(BuildroomTask).order_by(
        BuildroomTask.status.desc(), BuildroomTask.due_on.is_(None), BuildroomTask.due_on,
        BuildroomTask.id.desc()).all()
    # done last regardless of its due date: the board is about what is left.
    items = [_out(t) for t in rows if t.status != "done"] + [_out(t) for t in rows if t.status == "done"]
    return {"items": items, "summary": _summary(items),
            "areas": list(AREAS), "statuses": list(STATUSES)}


@router.post("/admin/buildroom", status_code=201)
def create_task(payload: TaskIn, db: Session = Depends(get_db), _admin=Depends(get_admin_user)):
    title = (payload.title or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="A task needs a title")
    if payload.area not in AREAS:
        raise HTTPException(status_code=400, detail=f"area must be one of {', '.join(AREAS)}")
    if payload.status not in STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {', '.join(STATUSES)}")
    task = BuildroomTask(
        title=title[:240],
        area=payload.area,
        status=payload.status,
        notes=(payload.notes or None),
        due_on=_parse_date(payload.due_on),
        assigned_to=((payload.assigned_to or "").strip()[:160] or None),
        created_by=(payload.created_by or None),
    )
    if payload.claimed_by:
        task.claimed_by = payload.claimed_by.strip()[:160]
        task.claimed_at = _utcnow()
    db.add(task)
    db.commit()
    db.refresh(task)
    return _out(task)


@router.patch("/admin/buildroom/{task_id}")
def update_task(task_id: int, payload: TaskPatch, db: Session = Depends(get_db),
                _admin=Depends(get_admin_user)):
    task = db.get(BuildroomTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="No such task")
    # Assignment is routing, not a change to the work itself: deciding who *should* have
    # something is the operator's call, so an assignment-only edit is not blocked by a claim
    # somebody else is holding. Any other field still is.
    assignment_only = (
        (payload.assigned_to is not None or payload.clear_assigned)
        and payload.title is None and payload.area is None and payload.status is None
        and payload.notes is None and payload.due_on is None and payload.tested_by is None
        and payload.test_note is None and not payload.clear_tested
    )
    if not assignment_only:
        _require_free(task, payload.who, payload.force)
    if payload.force and task.claimed_by and payload.who and \
            task.claimed_by.strip().lower() != payload.who.strip().lower():
        _append_note(task, f"{payload.who} edited this while it was claimed by {task.claimed_by}")

    if payload.clear_assigned:
        if task.assigned_to:
            _append_note(task, f"{payload.who or 'operator'} unassigned it (was {task.assigned_to})")
        task.assigned_to = None
    elif payload.assigned_to is not None:
        new_who = payload.assigned_to.strip()[:160] or None
        if new_who != task.assigned_to:
            _append_note(task, f"{payload.who or 'operator'} assigned it to {new_who or 'nobody'}")
        task.assigned_to = new_who

    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise HTTPException(status_code=400, detail="A task needs a title")
        task.title = title[:240]
    if payload.area is not None:
        if payload.area not in AREAS:
            raise HTTPException(status_code=400, detail=f"area must be one of {', '.join(AREAS)}")
        task.area = payload.area
    if payload.status is not None:
        if payload.status not in STATUSES:
            raise HTTPException(status_code=400, detail=f"status must be one of {', '.join(STATUSES)}")
        # Finishing the work releases the lock: a done task is nobody's to hold.
        if payload.status == "done" and task.claimed_by:
            _append_note(task, f"{payload.who or task.claimed_by} marked it done")
            task.claimed_by, task.claimed_at = None, None
        task.status = payload.status
    if payload.notes is not None:
        task.notes = payload.notes or None
    if payload.due_on is not None:
        task.due_on = _parse_date(payload.due_on)
    if payload.clear_tested:
        task.tested_by, task.tested_at, task.test_note = None, None, None
    elif payload.tested_by is not None:
        task.tested_by = payload.tested_by.strip()[:160] or None
        task.tested_at = _utcnow() if task.tested_by else None
        if payload.test_note is not None:
            task.test_note = payload.test_note or None
    db.commit()
    db.refresh(task)
    return _out(task)


@router.post("/admin/buildroom/{task_id}/claim")
def claim_task(task_id: int, payload: WhoIn, db: Session = Depends(get_db),
               _admin=Depends(get_admin_user)):
    task = db.get(BuildroomTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="No such task")
    by = (payload.by or "").strip()
    if not by:
        raise HTTPException(status_code=400, detail="Say who is claiming it")
    if task.claimed_by and task.claimed_by.strip().lower() == by.lower() and claim_is_fresh(task):
        return _out(task)          # already theirs: claiming twice is not an error
    _require_free(task, by, payload.force)
    if task.assigned_to and task.assigned_to.strip().lower() != by.lower() and not payload.force:
        raise HTTPException(status_code=409, detail={
            "assigned_to": task.assigned_to,
            "why": f"This one is assigned to {task.assigned_to}. Reassign it first, or take it anyway.",
        })
    if task.claimed_by and task.claimed_by.strip().lower() != by.lower():
        _append_note(task, f"{by} took this over from {task.claimed_by} "
                           f"(claim {claim_age_hours(task)}h old)")
    task.claimed_by = by[:160]
    task.claimed_at = _utcnow()
    if task.status == "todo":
        task.status = "doing"
    db.commit()
    db.refresh(task)
    return _out(task)


@router.post("/admin/buildroom/{task_id}/release")
def release_task(task_id: int, payload: WhoIn, db: Session = Depends(get_db),
                 _admin=Depends(get_admin_user)):
    task = db.get(BuildroomTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="No such task")
    by = (payload.by or "").strip()
    if not task.claimed_by:
        return _out(task)          # nothing held: releasing it is already true
    if not payload.force and by and by.lower() != task.claimed_by.strip().lower():
        raise HTTPException(status_code=409,
                            detail={"held_by": task.claimed_by,
                                    "why": "Only the holder can release it, or pass force=true."})
    _append_note(task, f"{by or 'operator'} released it"
                       + (" (forced)" if payload.force and by.lower() != task.claimed_by.strip().lower() else ""))
    task.claimed_by, task.claimed_at = None, None
    if task.status == "doing":
        task.status = "todo"
    db.commit()
    db.refresh(task)
    return _out(task)


@router.post("/admin/buildroom/{task_id}/tested")
def mark_tested(task_id: int, payload: TestedIn, db: Session = Depends(get_db),
                _admin=Depends(get_admin_user)):
    task = db.get(BuildroomTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="No such task")
    by = (payload.by or "").strip()
    if not by:
        raise HTTPException(status_code=400, detail="Say who tested it")
    _require_free(task, by, force=True)   # testing is a check, not an edit of someone's work
    task.tested_by = by[:160]
    task.tested_at = _utcnow()
    task.test_note = (payload.note or None)
    db.commit()
    db.refresh(task)
    return _out(task)


@router.delete("/admin/buildroom/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), _admin=Depends(get_admin_user)):
    task = db.get(BuildroomTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="No such task")
    db.delete(task)
    db.commit()
    return {"deleted": task_id}
