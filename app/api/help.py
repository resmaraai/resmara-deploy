"""Ask Resmara's answer library: what the chat could not answer, and what the team added.

The chat itself is `static/help-kb.js` — about fifty answers matched locally, no model and
no network in the path, so it is instant and cannot invent an answer. That design has one
obvious hole: the question it has never seen gets a shrug. This router closes the loop.

  * POST /api/help/misses      the chat logs a question it could not answer
  * GET  /api/help/answers     approved answers, fetched by the chat on load (no token:
                               they are customer-facing text and nothing account-specific)
  * GET  /api/admin/help/misses    the operator's work list, most-asked first
  * POST /api/admin/help/answers   "Add to Resmara's answers", usually straight from a
                                   support reply that already answered the question well

A miss is written by the customer's own browser and is therefore untrusted text: it is
stored, counted and shown to operators, never executed and never matched by `keys`.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_admin_user, get_current_user
from app.core.config import settings
from app.db.session import Event, HelpAnswer, HelpMiss, User, get_db
from app.services import llm, team_access

router = APIRouter()
log = logging.getLogger("resmara.help")

MAX_QUESTION = 400
MAX_ANSWER = 4000

# How many questions the chat may put to the model per account per hour. The chat falls back to
# the built-in library on a refusal, so a limit costs the agent nothing but a plainer answer.
ASK_LIMIT_PER_HOUR = 40

# The places the chat may tell an agent to go. Anything else is dropped rather than rendered as
# a button that leads nowhere.
GO_VIEWS = {"home", "dashboard", "campaigns", "campaign", "accounts", "support", "billing",
            "settings", "setup", "growth", "photos"}


class AskIn(BaseModel):
    question: str
    page: Optional[str] = None
    history: Optional[list[dict]] = None


class MissIn(BaseModel):
    question: str
    ticket_id: Optional[int] = None


class AnswerIn(BaseModel):
    question: str
    answer: str
    topic: Optional[str] = None
    keys: Optional[str] = None
    source_ticket_id: Optional[int] = None
    miss_ids: Optional[list[int]] = None


class AnswerPatch(BaseModel):
    answer: Optional[str] = None
    topic: Optional[str] = None
    keys: Optional[str] = None
    active: Optional[bool] = None


def _norm(question: str) -> str:
    """Compare questions the way a person would: case, spacing and punctuation aside."""
    text = " ".join(str(question or "").lower().split())
    return text.strip(" ?.!,")


def _shape(answer: HelpAnswer) -> dict:
    return {
        "id": answer.id,
        "q": answer.question,
        "a": answer.answer,
        "topic": answer.topic or "From our team",
        "keys": [k.strip() for k in (answer.keys or "").split(",") if k.strip()],
    }


# --- the customer's side ---------------------------------------------------------------

@router.post("/help/misses", status_code=201)
def log_miss(payload: MissIn, current_user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    """One row per distinct question, however many times it is asked.

    A duplicate is a priority signal rather than a second row: the operator's list is
    ordered by `asked_count`, so the question three agents asked is at the top without
    anyone reading a log.
    """
    question = (payload.question or "").strip()[:MAX_QUESTION]
    if not question:
        raise HTTPException(status_code=400, detail="A question is required")
    wanted = _norm(question)
    existing = None
    for row in db.query(HelpMiss).filter(HelpMiss.answer_id.is_(None)).all():
        if _norm(row.question) == wanted:
            existing = row
            break
    if existing:
        existing.asked_count = int(existing.asked_count or 1) + 1
        existing.last_asked_at = datetime.utcnow()
        if payload.ticket_id and not existing.ticket_id:
            existing.ticket_id = payload.ticket_id
        db.commit()
        return {"id": existing.id, "counted": True, "asked_count": existing.asked_count}
    row = HelpMiss(user_id=current_user.id, question=question,
                   ticket_id=payload.ticket_id, asked_count=1)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "counted": False, "asked_count": 1}


@router.get("/help/answers")
def approved_answers(db: Session = Depends(get_db)):
    """Deliberately unauthenticated.

    `static/help-kb.js` fetches this with plain `fetch` and no Authorization header, and a
    401 there would silently mean "the library never learns". The content is the same for
    every reader, so there is nothing to leak — but it also means nothing account-specific
    may ever be written into an answer.
    """
    rows = (db.query(HelpAnswer)
              .filter(HelpAnswer.active.is_(True))
              .order_by(HelpAnswer.created_at.desc())
              .limit(200).all())
    return [_shape(r) for r in rows]


# --- the chat itself ------------------------------------------------------------------

ASK_SYSTEM = """You answer questions from real estate agents using Resmara, inside the app.

You may use ONLY the answer library given to you. Do not invent features, prices, dates or
policies. If the library does not answer the question, say so by returning sure=false.

Reply with ONE JSON object, nothing else:
{"answer": "1-3 short sentences, plain English, no markdown", "sure": true|false, "go": "view-or-null"}

"go" may be one of: home, dashboard, campaigns, campaign, accounts, support, billing, settings,
setup, growth, photos - only when sending the agent to that page genuinely helps, otherwise null.
If sure is false, answer must be an empty string."""


@router.post("/help/ask")
async def ask(payload: AskIn, current_user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    """The question the built-in library could not answer, put to the model over that library.

    The model is not allowed to invent: it is handed the approved answers and told to return
    ``sure: false`` when they do not cover the question. A false goes straight back to the
    library-then-a-person path the chat already had, so a bad model answer can never reach an
    agent - only a confident one built from text the team approved.
    """
    question = (payload.question or "").strip()[:500]
    if len(question) < 3:
        raise HTTPException(status_code=400, detail="A question is required")
    unavailable = {"answer": None, "sure": False, "go": None, "reason": "no_model"}
    if not llm.llm_available():
        return unavailable

    since = datetime.utcnow() - timedelta(hours=1)
    used = (db.query(Event)
            .filter(Event.user_id == current_user.id)
            .filter(Event.event_type == "help_ask")
            .filter(Event.created_at >= since)
            .count())
    if used >= ASK_LIMIT_PER_HOUR:
        return {"answer": None, "sure": False, "go": None, "reason": "rate_limited"}

    rows = (db.query(HelpAnswer)
            .filter(HelpAnswer.active.is_(True))
            .order_by(HelpAnswer.created_at.desc())
            .limit(80).all())
    library = "\n\n".join(f"Q: {r.question}\nA: {r.answer}" for r in rows)[:12000]
    if not library:
        return {"answer": None, "sure": False, "go": None, "reason": "empty_library"}

    history = ""
    for turn in (payload.history or [])[-4:]:
        if isinstance(turn, dict) and turn.get("q"):
            history += f"\nEarlier question: {str(turn.get('q'))[:200]}"

    prompt = (f"Page the agent is on: {payload.page or 'unknown'}{history}\n\n"
              f"Question: {question}\n\nAnswer library:\n{library}")
    try:
        data = await llm.chat_json(ASK_SYSTEM, prompt, model=settings.OPENAI_MODEL,
                                   max_completion_tokens=500, timeout=8.0)
    except Exception as exc:                                     # noqa: BLE001 - the chat falls back
        log.info("help ask failed: %s", exc)
        return {**unavailable, "reason": "model_error"}

    usage = llm.take_usage()
    answer = str(data.get("answer") or "").strip()[:1200]
    sure = bool(data.get("sure")) and bool(answer)
    go = data.get("go")
    go = go if isinstance(go, str) and go.strip().lower() in GO_VIEWS else None

    db.add(Event(user_id=current_user.id, event_type="help_ask",
                 payload={"question": question[:300], "sure": sure, "page": payload.page,
                          "usage": usage}))
    db.commit()

    if not sure:
        return {"answer": None, "sure": False, "go": None, "reason": "not_sure"}
    return {"answer": answer, "sure": True, "go": go}


# --- the operator's side ---------------------------------------------------------------

@router.get("/admin/help/misses")
def admin_misses(open_only: bool = True, limit: int = 100,
                 current_user: User = Depends(team_access.needs("agents")), db: Session = Depends(get_db)):
    q = db.query(HelpMiss)
    if open_only:
        q = q.filter(HelpMiss.answer_id.is_(None))
    rows = q.order_by(HelpMiss.asked_count.desc(), HelpMiss.last_asked_at.desc()).limit(limit).all()
    emails = {u.id: u.email for u in db.query(User).all()}
    return {
        "items": [{
            "id": r.id,
            "question": r.question,
            "asked_count": int(r.asked_count or 1),
            "asked_by": emails.get(r.user_id),
            "ticket_id": r.ticket_id,
            "answered": r.answer_id is not None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "last_asked_at": r.last_asked_at.isoformat() if r.last_asked_at else None,
        } for r in rows],
        "open": db.query(HelpMiss).filter(HelpMiss.answer_id.is_(None)).count(),
        "answered": db.query(HelpMiss).filter(HelpMiss.answer_id.isnot(None)).count(),
    }


@router.get("/admin/help/answers")
def admin_answers(current_user: User = Depends(team_access.needs("agents")), db: Session = Depends(get_db)):
    rows = db.query(HelpAnswer).order_by(HelpAnswer.created_at.desc()).all()
    return [dict(_shape(r), active=bool(r.active), created_by=r.created_by,
                 source_ticket_id=r.source_ticket_id,
                 created_at=r.created_at.isoformat() if r.created_at else None) for r in rows]


@router.post("/admin/help/answers", status_code=201)
def add_answer(payload: AnswerIn, current_user: User = Depends(team_access.needs("agents")),
               db: Session = Depends(get_db)):
    """Approve an answer for the chat.

    This is normally one click on a support reply that already answered the question, so
    `source_ticket_id` keeps the provenance and the same text does not have to be typed
    again. `miss_ids` closes the misses it answers, which is what takes them off the list.
    """
    question = (payload.question or "").strip()[:MAX_QUESTION]
    answer = (payload.answer or "").strip()[:MAX_ANSWER]
    if not question or not answer:
        raise HTTPException(status_code=400, detail="A question and an answer are both required")
    row = HelpAnswer(question=question, answer=answer, topic=(payload.topic or "").strip()[:120] or None,
                     keys=(payload.keys or "").strip()[:400] or None,
                     source_ticket_id=payload.source_ticket_id,
                     created_by=current_user.email, active=True)
    db.add(row)
    db.flush()
    closed = 0
    if payload.miss_ids:
        for miss in db.query(HelpMiss).filter(HelpMiss.id.in_(payload.miss_ids)).all():
            miss.answer_id = row.id
            closed += 1
    db.commit()
    db.refresh(row)
    return dict(_shape(row), active=True, miss_ids_closed=closed)


@router.patch("/admin/help/answers/{answer_id}")
def edit_answer(answer_id: int, payload: AnswerPatch,
                current_user: User = Depends(team_access.needs("agents")), db: Session = Depends(get_db)):
    row = db.query(HelpAnswer).filter(HelpAnswer.id == answer_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Answer not found")
    if payload.answer is not None:
        row.answer = payload.answer.strip()[:MAX_ANSWER] or row.answer
    if payload.topic is not None:
        row.topic = (payload.topic or "").strip()[:120] or None
    if payload.keys is not None:
        row.keys = (payload.keys or "").strip()[:400] or None
    if payload.active is not None:
        row.active = bool(payload.active)
    db.commit()
    db.refresh(row)
    return dict(_shape(row), active=bool(row.active))
