"""Engine 1 Part A §6-7: the four onboarding emails, and what makes each one honest.

Adam's spec: from support@resmara.com, signed by the Resmara team (Adam, 25 Nov: never by name), personal, short, one clear next step,
AI-written from the agent's *real* account facts - never a guess, never a promise. Four emails at
most (welcome, day 3, day 7, day 14), and they stop the moment a campaign launches, because from
then on the campaign itself is the relationship.

What is code here, on purpose:

  * the account facts (all read from the database, nothing inferred);
  * which of the six day-3 situations is true - the first that matches, so the email says the one
    thing that is actually in the way;
  * the stop rules: test accounts, closed accounts, unsubscribed accounts, launched campaigns;
  * "never twice", recorded as one event per step on the account.

The wording comes from templates that carry the facts. When a model is configured it rewrites the
template in the team's voice; if the model is unavailable or returns nothing, the template is what the
agent reads - a real email, not silence.

Since 25 Nov (Adam): once Mailchimp is connected, every follow-up email is a Mailchimp series, so
each one is tracked (sent, opened, clicked, bounced, unsubscribed). From then on this module sends
nothing: a new account goes onto the Mailchimp list at sign-up, tagged "signed up, no campaign yet",
and the "Welcome and check-ins" series (day 0, 3, 7, 14) runs there. Until Mailchimp is connected,
the emails below keep going out, so no new agent is ever left without them.
"""
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.session import Boost, Event, Lead, User
from app.services import mail

STEPS = (("welcome", 0), ("day3", 3), ("day7", 7), ("day14", 14))
FROM_NAME = "The Resmara team"

SITUATIONS = {
    "not_back": "Looks like you haven't been back yet. Need a hand getting started?",
    "no_meta": "Connecting Facebook is the one step left. It takes two minutes, or I can do it with you.",
    "meta_gap": "You're nearly set: one thing on your Facebook side still needs fixing.",
    "ready_no_campaign": "You're all set. Paste a listing link and Resmara builds the whole campaign.",
    "staged": "Your campaign is built and waiting for you.",
    "running": "Your campaign is live. Here's how it's doing so far.",
    "plain": "Just checking in to see how it's going.",
}


def _aware(value):
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def account_facts(db, user: User) -> dict:
    """Everything the emails are allowed to say, read from the account and nothing else."""
    boosts = db.query(Boost).filter(Boost.user_id == user.id).all()
    launched = [b for b in boosts if b.launched_at is not None]
    running = [b for b in launched if (b.stage or "").upper() == "LIVE"]
    staged = [b for b in boosts if b.launched_at is None]
    leads = 0
    if running:
        leads = db.query(Lead).filter(Lead.boost_id.in_([b.id for b in running])).count()
    return {
        "created_at": _aware(user.created_at),
        "last_login": _aware(user.last_login),
        "meta_connected": bool(user.meta_connected_at),
        "campaigns": len(boosts),
        "launched": len(launched),
        "running": len(running),
        "staged": len(staged),
        "first_staged_address": (staged[0].address if staged else None),
        "first_running_address": (running[0].address if running else None),
        "leads": leads,
        "opted_in": bool(getattr(user, "marketing_optin", True)),
        "closed": user.closed_at is not None,
        "test": bool(getattr(user, "is_test", False)),
        # The first open item on their setup to-do list (Engine 1, Part C 5a), named in the emails.
        "meta_todo": _first_setup_item(db, user),
    }


def _first_setup_item(db, user: User) -> dict | None:
    try:
        from app.services import meta_engine
        todo = meta_engine.status(db, user).get("todo") or []
    except Exception:  # noqa: BLE001 - an email never waits on the Meta check
        return None
    if not todo:
        return None
    first = todo[0]
    return {"key": first.get("key"), "line": first.get("line") or "", "means": first.get("means") or ""}


def situation(f: dict) -> str:
    """The first true situation, in the brain doc's order. Never a guess."""
    if f["created_at"] and f["last_login"] and f["last_login"] <= f["created_at"]:
        return "not_back"
    if not f["meta_connected"]:
        return "no_meta"
    if f.get("meta_todo") and not f["running"] and not f["launched"]:
        return "meta_gap"
    if f["running"]:
        return "running"
    if f["staged"]:
        return "staged"
    if not f["launched"]:
        return "ready_no_campaign"
    return "plain"


def _greeting(user: User) -> str:
    first = (user.name or "").strip().split(" ")[0]
    return f"Hi {first}," if first else "Hi,"


def unsub_token(user_id: int) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), f"{user_id}:unsubscribe".encode(), hashlib.sha256).hexdigest()[:32]


def unsub_link(user_id: int) -> str:
    return f"{settings.PUBLIC_BASE_URL}/api/unsubscribe?u={user_id}&t={unsub_token(user_id)}"


def _links() -> str:
    return ("Book a free setup session any time: " + settings.PUBLIC_BASE_URL + "/#setup-session\n"
            "Reply to this email and it comes straight to me.")


def _setup_item_lines(f: dict) -> str:
    """The exact thing still in the way, from their setup to-do list, and what it means."""
    item = f.get("meta_todo") or {}
    if not item.get("line"):
        return "The Accounts page shows exactly what's left and what to do.\n\n"
    out = f"Here's what's left: {item['line']}"
    if item.get("means"):
        out += f" {item['means']}"
    return out + f"\n\nFix it from Accounts: {settings.PUBLIC_BASE_URL}/#accounts\n\n"


def compose(step: str, user: User, f: dict) -> tuple[str, str]:
    """Subject and body from the facts. One next step, no promises."""
    hi = _greeting(user)
    sit = situation(f) if step != "welcome" else ""
    if step == "welcome":
        subject = "Welcome to Resmara"
        body = (f"{hi}\n\n"
                f"Thanks for joining Resmara. We're glad you're here.\n\n"
                f"The first thing to do is connect your Facebook Page, Instagram and ad account, "
                f"because that's what lets Resmara post and run ads for you. "
                f"{'You already have that done - nice.' if f['meta_connected'] else 'It takes about two minutes.'}\n\n"
                f"Then paste a listing link and Resmara builds the whole campaign - posts, the ad and the reports.\n\n"
                f"{_links()}\n\n{FROM_NAME}")
        return subject, body
    if step == "day3":
        subject = "How's it going?"
        line = SITUATIONS[sit]
        body = (f"{hi}\n\n{line}\n\n")
        if sit == "meta_gap":
            body += _setup_item_lines(f)
        if sit == "running":
            body += (f"Your campaign for {f['first_running_address'] or 'your listing'} is live, with "
                     f"{f['leads']} lead{'s' if f['leads'] != 1 else ''} so far.\n\n")
        body += f"{_links()}\n\n{FROM_NAME}"
        return subject, body
    if step == "day7":
        subject = "One thing still in the way"
        line = SITUATIONS[sit]
        if sit == "meta_gap":
            line += "\n\n" + _setup_item_lines(f).strip()
        body = (f"{hi}\n\n{line}\n\nIf it would help to do it together, book a session and we'll do it "
                f"with you - it's free.\n\n{_links()}\n\n{FROM_NAME}")
        return subject, body
    subject = "I'm here when you're ready"
    body = (f"{hi}\n\nNo pressure at all - I'll leave you to it. If you'd like a hand getting your first "
            f"campaign live, just reply, or book a session and we'll do it together.\n\n{_links()}\n\n{FROM_NAME}")
    return subject, body


def _already_sent(db, user: User, step: str) -> bool:
    rows = db.query(Event).filter(Event.user_id == user.id,
                                  Event.event_type == "onboarding_email").all()
    return any((r.payload or {}).get("step") == step for r in rows)


def _send(db, user: User, step: str, f: dict) -> dict:
    subject, body = compose(step, user, f)
    # Every onboarding email carries the one-click way out (Engine 1 §6 guardrails).
    body = body + "\n\n--\nUnsubscribe from these emails: " + unsub_link(user.id)
    ok = mail.send_email(user.email, subject, body)
    db.add(Event(user_id=user.id, event_type="onboarding_email",
                 payload={"step": step, "sent": bool(ok), "situation": situation(f)}))
    return {"step": step, "to": user.email, "sent": bool(ok), "subject": subject}


def mailchimp_owns() -> bool:
    """Mailchimp sends the follow-ups once it is connected (Adam, 25 Nov)."""
    from app.services import mailchimp
    return mailchimp.configured()


def send_welcome(user: User, db) -> dict:
    """The first email, at the moment the account exists. Never to a test or closed account.
    With Mailchimp connected, the account goes onto the list instead and its series sends it."""
    if mailchimp_owns():
        from app.services import mailchimp
        return {"step": "welcome", "sent": False, "reason": "mailchimp", "list": mailchimp.add_signup(db, user)}
    f = account_facts(db, user)
    if f["test"] or f["closed"] or not f["opted_in"] or _already_sent(db, user, "welcome"):
        return {"step": "welcome", "sent": False, "reason": "not eligible"}
    return _send(db, user, "welcome", f)


def run_due(db, now: datetime | None = None) -> dict:
    """Send every onboarding email whose day has come. Idempotent: one email per step, ever."""
    if mailchimp_owns():
        return {"sent": [], "skipped": 0, "stopped_after_launch": 0, "owner": "mailchimp"}
    now = now or datetime.now(timezone.utc)
    sent, skipped, stopped = [], 0, []
    users = db.query(User).all()
    for user in users:
        f = account_facts(db, user)
        if f["test"] or f["closed"] or not f["opted_in"]:
            skipped += 1
            continue
        # The emails stop as soon as a campaign launches (Engine 1 §6).
        if f["launched"]:
            stopped.append(user.id)
            continue
        age = (now - f["created_at"]).days if f["created_at"] else 0
        for step, day in STEPS:
            if age < day or _already_sent(db, user, step):
                continue
            sent.append(_send(db, user, step, f))
    db.commit()
    return {"ok": True, "sent": sent, "skipped": skipped, "stopped_after_launch": len(stopped)}
