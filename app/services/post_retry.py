"""What happens after a post fails: retry it, or say whose fault it is.

The publisher used to give a failed post one line - ``publish_status='failed'`` and
``last_error`` - and that was the end of it. Three very different incidents all looked
identical on the calendar:

  * we broke it (a missing upload, a template that renders nothing, a Graph call that timed
    out). Nothing for the agent to do; retrying usually works and, if it does not, it is ours
    to fix and repost.
  * the agent's Meta connection broke (token expired, scope dropped, 401/403/OAuth). Blind
    retries cannot heal that, and the person who *can* heal it is not watching. They get an
    email, a red banner, and the post goes out by itself the moment the token checks healthy
    again - reposting on reconnect is the whole point of the branch.
  * Meta rejected the post itself (policy, copy, media). Retrying the same caption is a lie
    to the agent: Meta will reject it again in 2, 10 and 30 minutes. They see Meta's own
    reason and can edit the post.

So every failure is classified into exactly one of three kinds, and the kind decides the
message and the action. Classification only ever uses evidence from the failure: Meta's
error code/type when Graph answered, our own literal configuration messages, and otherwise
"ours", because retrying an unclassified error costs nothing while refusing to retry a post
Meta would have accepted is the worse mistake.

Where the retries run: inside ``publish_due`` (the sweep the cron already runs every 15
minutes), gated by ``next_attempt_at`` on the post. No second scheduler exists, and the same
sweep that would have published the post publishes the retry.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.db.session import Boost, Event, Post, User

log = logging.getLogger("resmara.post_retry")

# The three kinds. Exactly these; ``failure_kind`` on the post is never anything else.
KIND_OUR_FAULT = "our_fault"
KIND_CONNECTION = "connection"
KIND_META_REJECTED = "meta_rejected"
KINDS = (KIND_OUR_FAULT, KIND_CONNECTION, KIND_META_REJECTED)

# Three retries over 30 minutes, measured from the first failure: the post is tried again 2,
# 10 and 30 minutes after it first failed. Stored as marks so the schedule reads as the
# owner asked for it; the waits between them are the differences.
RETRY_MARKS_MINUTES = (2, 10, 30)
MAX_ATTEMPTS = len(RETRY_MARKS_MINUTES) + 1   # the scheduled try, then the three retries
_GAPS_MINUTES = tuple(
    [RETRY_MARKS_MINUTES[0]] + [b - a for a, b in zip(RETRY_MARKS_MINUTES, RETRY_MARKS_MINUTES[1:])]
)

# Meta's codes for "this login may no longer act" - the same families token_health uses to
# call a connection broken. A retry cannot fix any of them, a reconnect can.
CONNECTION_CODES = {10, 102, 190, 200, 272, 273}
CONNECTION_SUBCODES = {458, 459, 460, 463, 467}

# Codes where Meta is judging the post itself, not our plumbing: 368 is the policy block,
# 36003 an unsupported aspect ratio, 2207026 an unsupported media file, 9004/9007 an
# Instagram container Meta refused to publish. These must NOT be retried.
REJECTED_CODES = {368, 352, 353, 36003, 36010, 9004, 9007, 2207026}

# Our own literal failure sentences that mean "the connection is not usable", not "the media
# is broken". They are configuration states the agent fixes by reconnecting Meta, so they are
# classified as a connection failure rather than retried into a wall.
_CONNECTION_PHRASES = (
    "no meta account connected",
    "no facebook page id configured",
    "no instagram account id configured",
)

# --------------------------------------------------------------------------- messages
OUR_FAULT_RETRYING = ("Didn't post yet. This one is on us and it is being retried "
                      "automatically (try {attempt} of {total}).")
OUR_FAULT_FINAL = ("This post didn't go out, and that is our fault rather than yours. We have "
                   "been told and will fix it and post it for you. You can also press Try "
                   "again now.")
CONNECTION_FINAL = ("This post didn't go out because your Meta connection stopped working. "
                    "We have emailed you about it: reconnect Meta and this post is published "
                    "by itself, with nothing for you to redo.")
META_REJECTED = ("Meta didn't accept this post: {reason} Edit the caption or the picture, "
                 "then post it again.")
META_REJECTED_NO_REASON = ("Meta didn't accept this post. Edit the caption or the picture, "
                           "then post it again.")

KIND_LABEL = {
    KIND_OUR_FAULT: "Our side",
    KIND_CONNECTION: "Meta connection",
    KIND_META_REJECTED: "Meta rejected it",
}

# What the calendar may offer for each kind. Try again is deliberately absent from a rejection:
# re-sending the identical post earns the identical refusal, so the only button that can change
# the outcome is edit_and_post (the editor saves the new copy, then reposts it).
ACTIONS = {
    KIND_OUR_FAULT: ["try_again", "edit_and_post", "skip"],
    KIND_CONNECTION: ["reconnect", "try_again", "skip"],
    KIND_META_REJECTED: ["edit_and_post", "skip"],
}

BANNER_LABEL = "Didn't post"


# --------------------------------------------------------------------------- helpers
def _as_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", ""))
            return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
        except ValueError:
            pass
    return datetime.utcnow()


def meta_message(error: Any) -> str:
    """Meta's own sentence(s) about an error, nothing added."""
    if not isinstance(error, dict):
        return str(error or "")[:300]
    parts = [error.get("message") or "", error.get("error_user_title") or "",
             error.get("error_user_msg") or ""]
    text = " - ".join(p for p in parts if p)
    if error.get("error_subcode"):
        text = f"{text} (subcode {error['error_subcode']})" if text else f"subcode {error['error_subcode']}"
    return text.strip()[:400]


def classify(error: Any, *, status_code: Optional[int] = None,
             graph_error: Optional[Dict[str, Any]] = None, refused: bool = False) -> str:
    """Exactly one of the three kinds, from the evidence in the failure.

    Order matters: a token/permission refusal is a connection problem even when Meta's text
    also sounds like a refusal, and a positive content judgement from Meta outranks "ours".
    """
    err = graph_error if isinstance(graph_error, dict) else {}
    code = err.get("code")
    subcode = err.get("error_subcode")
    etype = (err.get("type") or "")

    if code in CONNECTION_CODES or subcode in CONNECTION_SUBCODES or etype == "OAuthException":
        return KIND_CONNECTION
    if status_code in (401, 403):
        return KIND_CONNECTION

    if code in REJECTED_CODES:
        return KIND_META_REJECTED
    # Meta attaches a user-facing title/message only when the fix is in the post itself
    # (community standards, unsupported media). That is positive evidence of a rejection;
    # without it, a bare "invalid parameter" is far more likely to be our payload.
    if err and (err.get("error_user_title") or err.get("error_user_msg")) and code not in (1, 2, 4):
        return KIND_META_REJECTED

    text = str(error or "").lower()
    if any(phrase in text for phrase in _CONNECTION_PHRASES):
        return KIND_CONNECTION

    # Everything else is ours. That includes a pre-flight refusal (we built a post the platform
    # cannot take): it is final rather than retryable because the file will not change in ten
    # minutes, and ``record_failure`` reads ``refused`` to stop the ladder.
    return KIND_OUR_FAULT


def retry_delay_minutes(attempts: int) -> Optional[int]:
    """Wait before the next try, after ``attempts`` tries have just failed."""
    index = attempts - 1
    if index < 0 or index >= len(_GAPS_MINUTES):
        return None
    return _GAPS_MINUTES[index]


def next_attempt_at(attempts: int, now: Any) -> Optional[str]:
    delay = retry_delay_minutes(attempts)
    if delay is None:
        return None
    return (_as_dt(now) + timedelta(minutes=delay)).isoformat()


def message_for(kind: str, *, retrying: bool = False, attempts: int = 0,
                 reason: str = "") -> str:
    """The sentence the agent reads on the calendar for this kind and state."""
    if kind == KIND_META_REJECTED:
        return META_REJECTED.format(reason=reason).strip() if reason else META_REJECTED_NO_REASON
    if kind == KIND_CONNECTION:
        return CONNECTION_FINAL
    if retrying:
        return OUR_FAULT_RETRYING.format(attempt=attempts, total=MAX_ATTEMPTS)
    return OUR_FAULT_FINAL


def failure_payload(post: Post) -> Optional[Dict[str, Any]]:
    """What the calendar shows for a post that did not go out (None when it is fine).

    Additive by design: every key here is new, so an older client that only reads
    ``publish_status``/``last_error`` keeps working unchanged.
    """
    kind = getattr(post, "failure_kind", None)
    status = (post.publish_status or "")
    retrying = bool(getattr(post, "next_attempt_at", None)) and status == "scheduled"
    # Only a post that is dead, or one that is still being retried, wears the banner. A skipped
    # or posted post keeps the kind as history but must not look broken on the calendar.
    if status != "failed" and not retrying:
        return None
    kind = kind or KIND_OUR_FAULT
    reason = (getattr(post, "last_error", None) or "").strip()
    return {
        "label": BANNER_LABEL,
        "kind": kind,
        "kind_label": KIND_LABEL.get(kind, KIND_LABEL[KIND_OUR_FAULT]),
        "message": (getattr(post, "failure_note", None)
                    or message_for(kind, retrying=retrying,
                                   attempts=int(getattr(post, "publish_attempts", 0) or 0),
                                   reason=reason)),
        "reason": reason,
        "actions": list(ACTIONS.get(kind, ACTIONS[KIND_OUR_FAULT])),
        "retrying": retrying,
        "attempts": int(getattr(post, "publish_attempts", 0) or 0),
        "max_attempts": MAX_ATTEMPTS,
        "next_attempt_at": getattr(post, "next_attempt_at", None),
        "emailed": getattr(post, "failure_notified_at", None) is not None,
    }


# --------------------------------------------------------------------------- recording
def _owner_email(db, boost: Optional[Boost]) -> str:
    if boost is None or not boost.user_id:
        return ""
    owner = db.query(User).filter(User.id == boost.user_id).first()
    return ((getattr(owner, "email", "") or "").strip().lower()) if owner else ""


def _email_connection_failure(db, post: Post, boost: Optional[Boost], reason: str,
                              now: datetime) -> Dict[str, Any]:
    """One email per post per connection incident, and only when a provider is configured.

    Sending nothing while pretending it was sent would leave the agent with a red banner and
    no idea why; ``failure_notified_at`` is set only on a real send so a later failure can try
    again once mail is configured.
    """
    from app.services import mail

    address = _owner_email(db, boost)
    outcome: Dict[str, Any] = {"to": address, "sent": False, "reason": ""}
    if not address:
        outcome["reason"] = "no email on the campaign owner"
        return outcome
    if getattr(post, "failure_notified_at", None) is not None:
        outcome["reason"] = "already emailed about this failure"
        return outcome
    if not mail.mail_configured():
        outcome["reason"] = "no mail provider configured"
        return outcome

    where = (getattr(boost, "address", "") or "your campaign")
    subject = "Resmara: we could not post to your Meta account - reconnect to fix it"
    # No deep link: the app has one Connections view and no hash route for it, so a made-up
    # URL would 404 and make the only email in the flow untrustworthy.
    from app.core.config import settings as _settings
    home = (_settings.PUBLIC_BASE_URL or "").rstrip("/")
    body = (
        f"Your Meta connection stopped working, so this post to {where} did not go out.\n\n"
        f"Post: day {post.day}, slot {post.slot}, {post.publish_target or 'both'}\n"
        f"Meta said: {reason or 'the connection is no longer valid'}\n\n"
        "Nothing is lost: as soon as you reconnect your Meta account in Resmara (Connections), "
        "this post is published by itself. There is nothing to redo and nothing to pay again.\n"
        + (f"\nResmara: {home}\n" if home else "")
    )
    try:
        sent = bool(mail.send_email(address, subject, body))
    except Exception as exc:  # a broken relay must not lose the failure record
        sent = False
        outcome["reason"] = f"send failed: {exc.__class__.__name__}"
    outcome["sent"] = sent
    if sent:
        post.failure_notified_at = now
    elif not outcome["reason"]:
        outcome["reason"] = (mail.last_attempt().get("reason")
                             or "the mail provider refused the message")[:300]
    return outcome


def _open_agent_ticket(db, post: Post, boost: Optional[Boost], reason: str, kind: str,
                       now: datetime) -> Dict[str, Any]:
    """One support ticket per failed post, opened in the agent's own Support tab.

    The agent's copy of this is otherwise a red banner with no next step and no human attached.
    The ticket carries the plain reason (not Meta's JSON) and a note that the team will retry, so
    the reply the agent gets is written by a person. Reassigning the JSON list, not appending in
    place, for the same reason as above.
    """
    try:
        owner_id = getattr(boost, "user_id", None)
        if not owner_id:
            return {}
        from app.db.session import SupportTicket

        where = getattr(boost, "address", "") or "your campaign"
        subject = f"A post to {where} did not go out"
        existing = None
        for row in (db.query(SupportTicket)
                      .filter(SupportTicket.user_id == owner_id)
                      .filter(SupportTicket.status != "closed")
                      .filter(SupportTicket.subject == subject).all()):
            for message in (row.messages or []):
                if isinstance(message, dict) and message.get("post_id") == post.id:
                    existing = row
                    break
            if existing:
                break

        text = (f"Day {post.day} did not go out: {reason[:300] or 'Meta gave no reason'}. "
                "The team has this on the list and will retry it.")
        message = {"role": "team", "text": text, "at": now.isoformat(), "unread": True,
                   "post_id": post.id, "kind": kind, "auto": True}
        if existing:
            messages = list(existing.messages or []) + [message]
            existing.messages = messages
            existing.status = "open"
            existing.updated_at = now
            db.add(existing)
            ticket_id, created = existing.id, False
        else:
            ticket = SupportTicket(user_id=owner_id, subject=subject, status="received",
                                   messages=[message])
            db.add(ticket)
            db.flush()
            ticket_id, created = ticket.id, True

        db.add(Event(boost_id=post.boost_id, event_type="ticket_created" if created else "ticket_updated",
                     payload={"ticket_id": ticket_id, "post_id": post.id, "auto": True}))
        return {"ticket_id": ticket_id, "created": created}
    except Exception as exc:                                    # noqa: BLE001 - never break a sweep
        log.warning("could not open a ticket for post %s: %s", getattr(post, "id", "?"), exc)
        return {}


def record_failure(db, post: Post, boost: Optional[Boost], outcome: Dict[str, Any],
                   now: Any = None) -> Dict[str, Any]:
    """Classify one failure and take its action. Called from the publish sweep.

    Returns a small dict the sweep can report: ``status`` is ``retrying`` or ``failed``.
    """
    now_dt = _as_dt(now)
    attempts = int(getattr(post, "publish_attempts", 0) or 0) + 1
    refused = bool(outcome.get("refused"))
    graph_error = outcome.get("graph_error") if isinstance(outcome.get("graph_error"), dict) else {}
    reason = (outcome.get("error") or "").strip()
    if not reason and graph_error:
        reason = meta_message(graph_error)
    kind = outcome.get("kind") or classify(reason, status_code=outcome.get("status_code"),
                                           graph_error=graph_error, refused=refused)

    # Only an error on our side is worth another try. A dead token will not heal in ten
    # minutes and a rejected caption will be rejected again, so those two end the ladder
    # immediately and go straight to the action the agent can take.
    retrying = (kind == KIND_OUR_FAULT and not refused and attempts < MAX_ATTEMPTS)

    post.publish_attempts = attempts
    post.failure_kind = kind
    post.last_error = reason[:2000] or None
    post.failure_note = message_for(kind, retrying=retrying, attempts=attempts, reason=reason)
    # Every attempt is kept, not just the last: the console's fail log shows what happened on
    # try 1 when try 3 is the one that ran out. Reassigned rather than appended in place because
    # SQLAlchemy's plain JSON column does not notice a mutation inside the value.
    history = list(post.fail_log or [])
    history.append({"at": now_dt.isoformat(), "error": (reason or "no message from Meta")[:600],
                    "attempt": attempts, "kind": kind})
    post.fail_log = history[-20:]

    email: Dict[str, Any] = {}
    ticket: Dict[str, Any] = {}
    if retrying:
        post.publish_status = "scheduled"   # still ours to publish; next_attempt_at gates it
        post.next_attempt_at = next_attempt_at(attempts, now_dt)
        post.failed_at = None
    else:
        post.publish_status = "failed"
        post.next_attempt_at = None
        post.failed_at = now_dt
        if kind == KIND_CONNECTION:
            email = _email_connection_failure(db, post, boost, reason, now_dt)
        ticket = _open_agent_ticket(db, post, boost, reason, kind, now_dt)

    db.add(Event(boost_id=post.boost_id, event_type="post_retrying" if retrying else "post_failed",
                 payload={"post_id": post.id, "day": post.day, "slot": post.slot,
                          "kind": kind, "attempts": attempts,
                          "next_attempt_at": post.next_attempt_at,
                          "error": (reason or "")[:400],
                          **(({"email": email} if email else {})),
                          **(({"ticket": ticket} if ticket else {}))}))
    db.commit()
    log.info("post %s %s (%s, attempt %s/%s)%s", post.id,
             "retrying" if retrying else "failed", kind, attempts, MAX_ATTEMPTS,
             f" next {post.next_attempt_at}" if retrying else "")
    return {"status": "retrying" if retrying else "failed", "kind": kind,
            "attempts": attempts, "next_attempt_at": post.next_attempt_at,
            "message": post.failure_note, "email": email}


# --------------------------------------------------------------------------- recovery
def requeue_connection_failures(db, ad_account) -> Dict[str, Any]:
    """Posts that failed on a broken connection, put back in the queue.

    Hooked into ``token_health.refresh_account`` at the point a connection checks healthy
    again: that is the only moment the posts become publishable, and it costs nothing when
    there are none. They are requeued, not published here - the publish sweep does that, so
    there is still exactly one place that talks to Graph for a post.
    """
    if ad_account is None or not getattr(ad_account, "id", None):
        return {"requeued": 0, "post_ids": []}
    rows: List[Post] = (
        db.query(Post)
        .join(Boost, Post.boost_id == Boost.id)
        .filter(Boost.ad_account_id == ad_account.id)
        .filter(Post.publish_status == "failed")
        .filter(Post.failure_kind == KIND_CONNECTION)
        .all()
    )
    now_dt = datetime.utcnow()
    for post in rows:
        # A fresh ladder: the connection it failed on no longer exists, so the 4 tries start
        # over rather than being already spent.
        post.publish_status = "scheduled"
        post.publish_attempts = 0
        post.next_attempt_at = None
        post.failure_kind = None
        post.failure_note = None
        # ``failed_at`` is kept: it is when this post ran out of tries, and the daily summary
        # counts the incident where it happened even though it has since been reposted.
        post.failure_notified_at = None
        db.add(Event(boost_id=post.boost_id, event_type="post_requeued",
                     payload={"post_id": post.id, "day": post.day,
                              "reason": "Meta connection is healthy again",
                              "at": now_dt.isoformat()}))
    if rows:
        db.commit()
        log.info("requeued %s post(s) after the Meta connection came back", len(rows))
    return {"requeued": len(rows), "post_ids": [p.id for p in rows]}


def try_again(db, post: Post, *, edited: bool = False) -> Dict[str, Any]:
    """The calendar's Try again and Edit-and-post buttons. Raises ValueError when refused.

    ``edited`` is how Edit-and-post says the caption or picture has changed. A rejected post
    needs it: without an edit this is the same request Meta already refused, and saying "we
    retried it" while the copy is unchanged would only earn the same refusal 30 minutes later.
    """
    if (post.publish_status or "") == "posted":
        raise ValueError("This post already went out.")
    rejected = (getattr(post, "failure_kind", None) == KIND_META_REJECTED
                and (post.publish_status or "") == "failed")
    if rejected and not edited:
        raise ValueError("Meta rejected this post, so the same post would be rejected again. "
                         "Edit the caption or the picture, then post it again.")
    post.publish_status = "scheduled"
    post.publish_attempts = 0
    post.next_attempt_at = None
    post.failure_kind = None
    post.failure_note = None
    post.last_error = None
    db.add(Event(boost_id=post.boost_id, event_type="post_retry_requested",
                 payload={"post_id": post.id, "day": post.day, "by": "agent"}))
    db.commit()
    return {"post_id": post.id, "publish_status": post.publish_status, "due_at": post.publish_at}


def skip(db, post: Post) -> Dict[str, Any]:
    """Take a post out of the calendar without publishing it. Raises ValueError if posted."""
    if (post.publish_status or "") == "posted":
        raise ValueError("This post already went out, so there is nothing to skip.")
    post.publish_status = "skipped"
    post.next_attempt_at = None
    post.failure_note = None
    db.add(Event(boost_id=post.boost_id, event_type="post_skipped",
                 payload={"post_id": post.id, "day": post.day, "slot": post.slot,
                          "kind": getattr(post, "failure_kind", None)}))
    db.commit()
    return {"post_id": post.id, "publish_status": post.publish_status}


# --------------------------------------------------------------------------- daily summary
def daily_summary(db, hours: int = 24) -> Dict[str, Any]:
    """The day's failed posts, counted by kind. Called from the existing admin sweep.

    Deliberately a function that returns numbers and a short list, not a scheduled email
    blast: the sweep already runs on a timer and already reports to us, so this is what it
    reports.

    Counted from the ``post_failed`` events rather than from the posts themselves, because a
    post that failed and was since fixed, skipped or requeued by a reconnect no longer carries
    the verdict - and the incident still happened. The event log is the record of it.
    """
    since = datetime.utcnow() - timedelta(hours=max(1, int(hours or 24)))
    rows = (db.query(Event)
            .filter(Event.event_type == "post_failed")
            .filter(Event.created_at.isnot(None))
            .filter(Event.created_at >= since)
            .order_by(Event.id.desc())
            .all())
    by_kind = {kind: 0 for kind in KINDS}
    for event in rows:
        payload = event.payload if isinstance(event.payload, dict) else {}
        kind = str(payload.get("kind") or "")
        by_kind[kind if kind in by_kind else KIND_OUR_FAULT] += 1

    boosts = {}
    if rows:
        ids = {e.boost_id for e in rows if e.boost_id}
        boosts = {b.id: b for b in db.query(Boost).filter(Boost.id.in_(ids)).all()}

    out = []
    for event in rows[:20]:
        payload = event.payload if isinstance(event.payload, dict) else {}
        out.append({
            "post_id": payload.get("post_id"), "boost_id": event.boost_id,
            "address": (getattr(boosts.get(event.boost_id), "address", "") or ""),
            "day": payload.get("day"), "slot": payload.get("slot"),
            "kind": payload.get("kind"), "attempts": payload.get("attempts"),
            "failed_at": event.created_at.isoformat() if event.created_at else None,
            "reason": (payload.get("error") or "")[:200],
        })

    return {
        "window_hours": int(hours or 24),
        "since": since.isoformat(),
        "total": len(rows),
        "by_kind": by_kind,
        "posts": out,
    }
