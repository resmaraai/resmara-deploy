"""The Team room's own data: campaigns, failed posts, connections and the activity log.

Everything here reads what the product already writes - boosts, posts, ad accounts, events.
Nothing is invented: a campaign with no plan comes back ``built: false`` and a post with no
failure comes back with an empty fail log, so an empty page means an empty database and not a
missing endpoint.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from app.core.config import settings
from app.core.security import get_current_user_optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import AdAccount, Asset, Boost, Event, Post, User, get_db
from app.services.lead_counts import lead_totals
from app.core.testdata import is_test_user
from app.services import team_access

log = logging.getLogger("resmara.console")

router = APIRouter()


# --------------------------------------------------------------------------- helpers
def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _dt(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None
    return None


def _day_of(boost: Boost, today: Optional[date] = None) -> int:
    """Which day of its campaign this is, 1..campaign_days.

    Read from the go-live date the agent was given rather than from when the build ran: the days
    are the agent's calendar days, and a paused campaign keeps counting from where it stopped.
    """
    today = today or datetime.utcnow().date()
    start = _dt(boost.go_live_date)
    if start is None and boost.paid_at is not None:
        start = _dt(boost.paid_at)
    total = int(boost.campaign_days or 14)
    if start is None:
        return 1
    day = (today - start.date()).days + 1 - int(boost.paused_days or 0)
    return max(1, min(total, day))


def _post_counts(db: Session, boost_ids: List[int]) -> Dict[int, Dict[str, int]]:
    if not boost_ids:
        return {}
    rows = (
        db.query(Post.boost_id, Post.publish_status, func.count(Post.id))
        .filter(Post.boost_id.in_(boost_ids))
        .group_by(Post.boost_id, Post.publish_status)
        .all()
    )
    out: Dict[int, Dict[str, int]] = {bid: {"total": 0, "published": 0, "failed": 0} for bid in boost_ids}
    for boost_id, status, count in rows:
        bucket = out.setdefault(boost_id, {"total": 0, "published": 0, "failed": 0})
        bucket["total"] += int(count or 0)
        if status == "posted":
            bucket["published"] += int(count or 0)
        elif status == "failed":
            bucket["failed"] += int(count or 0)
    return out


def _photo_index(db: Session, boost_ids: List[int]) -> tuple:
    """Cover url and photo count per campaign, in one pass.

    The Team room draws a campaign's own photos: a thumbnail on the row and the whole library
    inside it. Nothing here loads the image bytes — `Asset.data` is deferred, and the console
    only ever needs the path.
    """
    covers: Dict[int, str] = {}
    counts: Dict[int, int] = {}
    if not boost_ids:
        return covers, counts
    rows = (
        db.query(Asset.boost_id, Asset.url)
        .filter(Asset.boost_id.in_(boost_ids))
        .order_by(Asset.boost_id, Asset.id)
        .all()
    )
    for boost_id, url in rows:
        counts[boost_id] = counts.get(boost_id, 0) + 1
        covers.setdefault(boost_id, url)
    return covers, counts


def _ends_on(boost: Boost) -> Optional[str]:
    """The campaign's last day: go-live date plus its length, less one."""
    from datetime import date, timedelta
    start = boost.go_live_date
    if not start:
        return None
    try:
        d = start if isinstance(start, date) else date.fromisoformat(str(start)[:10])
    except ValueError:
        return None
    return (d + timedelta(days=int(boost.campaign_days or 14) - 1)).isoformat()


def _campaign_row(boost: Boost, owner: Optional[User], counts: Dict[str, int],
                  cover: Optional[str] = None, photos: int = 0,
                  leads: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    return {
        "id": boost.id,
        "user_id": boost.user_id,
        "agent_name": (owner.name if owner else None) or (owner.email if owner else None) or "—",
        "agent_email": owner.email if owner else None,
        "address": boost.address,
        "stage": boost.stage or "PENDING",
        "built": bool(boost.plan),
        "day": _day_of(boost),
        "campaign_days": int(boost.campaign_days or 14),
        "photos_total": int(photos),
        "photo_cover": cover,
        "posts_total": counts.get("total", 0),
        "posts_published": counts.get("published", 0),
        "posts_failed": counts.get("failed", 0),
        "go_live_date": boost.go_live_date,
        "ends_on": _ends_on(boost),
        # Leads this campaign generated, by source. Removed ones still count (lead_counts).
        "leads": leads or {"ad": 0, "posts": 0, "website": 0, "total": 0, "removed": 0},
        "created_at": _iso(boost.created_at),
        "paid_at": _iso(boost.paid_at),
        "paid_amount_cents": boost.paid_amount_cents,
        "ad_budget_usd": boost.ad_budget_usd,
        "meta_campaign_id": boost.meta_campaign_id,
        "hidden": bool(boost.hidden),
        # The owner is a test account (test email or team-marked): Team room counts skip it.
        "is_test": is_test_user(owner),
        "paused_at": _iso(boost.paused_at),
        "listing_url": boost.listing_url,
    }


# --------------------------------------------------------------------------- campaigns
@router.get("/admin/campaigns")
def list_campaigns(include_hidden: bool = False, limit: int = 200,
                   user=Depends(team_access.needs("campaigns")), db: Session = Depends(get_db)):
    """Every campaign in the shop, newest first, with the counts the table shows."""
    query = db.query(Boost)
    if not include_hidden:
        query = query.filter(Boost.hidden.isnot(True))
    boosts = query.order_by(Boost.id.desc()).limit(max(1, min(limit, 500))).all()
    counts = _post_counts(db, [b.id for b in boosts])
    covers, photo_counts = _photo_index(db, [b.id for b in boosts])
    owners = {
        u.id: u
        for u in db.query(User).filter(User.id.in_({b.user_id for b in boosts} or {0})).all()
    }
    leads = lead_totals(db, [b.id for b in boosts])
    return [_campaign_row(b, owners.get(b.user_id), counts.get(b.id, {}),
                          covers.get(b.id), photo_counts.get(b.id, 0), leads.get(b.id)) for b in boosts]


@router.get("/admin/campaigns/{campaign_id}")
def campaign_detail(campaign_id: int, user=Depends(team_access.needs("campaigns")),
                    db: Session = Depends(get_db)):
    """One campaign and its posts, with the reason anything failed attached to the post."""
    boost = db.query(Boost).filter(Boost.id == campaign_id).first()
    if not boost:
        raise HTTPException(status_code=404, detail="No such campaign")
    owner = db.query(User).filter(User.id == boost.user_id).first()
    counts = _post_counts(db, [boost.id]).get(boost.id, {})
    covers, photo_counts = _photo_index(db, [boost.id])
    row = _campaign_row(boost, owner, counts, covers.get(boost.id), photo_counts.get(boost.id, 0),
                        lead_totals(db, [boost.id]).get(boost.id))
    # The campaign's own library, in the order the calendar will use it. A campaign with no
    # photos says so with an empty list — never a stand-in image from somewhere else.
    assets = (db.query(Asset).filter(Asset.boost_id == boost.id).order_by(Asset.id).all())
    row["photos"] = [
        {
            "id": a.id,
            "url": a.url,
            "room": a.room,
            "name": a.original_name,
            "kind": a.kind,
            "shape": a.shape,
            "tagged_by": a.tagged_by,
        }
        for a in assets
    ]
    posts = db.query(Post).filter(Post.boost_id == boost.id).order_by(Post.day, Post.slot).all()
    row["posts"] = [
        {
            "id": p.id,
            "day": p.day,
            "kind": p.kind,
            "target": p.publish_target,
            "caption": p.caption,
            "image_url": p.image_url,
            "title": p.title,
            "publish_status": p.publish_status,
            "scheduled_at": p.publish_at,
            "reason": p.failure_note,
            "last_error": p.last_error,
            "attempts": int(p.publish_attempts or 0),
            "failed_at": _iso(p.failed_at),
            "fail_log": list(p.fail_log or []),
        }
        for p in posts
    ]
    row["has_ads"] = bool(boost.ad_brief) or bool(boost.meta_campaign_id)
    return row


# --------------------------------------------------------------------------- failed posts
@router.get("/admin/posts/failed")
def failed_posts(limit: int = 100, user=Depends(team_access.needs("campaigns")),
                 db: Session = Depends(get_db)):
    """Posts that ran out of tries, worst first, with enough context to act without opening them."""
    rows = (
        db.query(Post, Boost, User)
        .join(Boost, Post.boost_id == Boost.id)
        .outerjoin(User, Boost.user_id == User.id)
        .filter(Post.publish_status == "failed")
        .order_by(Post.failed_at.desc().nullslast(), Post.id.desc())
        .limit(max(1, min(limit, 300)))
        .all()
    )
    out = []
    for post, boost, owner in rows:
        out.append({
            "post_id": post.id,
            "campaign_id": boost.id,
            "address": boost.address,
            "agent_name": (owner.name if owner else None) or (owner.email if owner else None) or "—",
            "agent_email": owner.email if owner else None,
            "user_id": boost.user_id,
            "day": post.day,
            "target": post.publish_target,
            "kind": post.failure_kind,
            "reason": post.failure_note or post.last_error,
            "error": post.last_error,
            "failed_at": _iso(post.failed_at),
            "attempts": int(post.publish_attempts or 0),
            "fail_log": list(post.fail_log or []),
        })
    return out


@router.post("/admin/posts/{post_id}/retry")
async def retry_post(post_id: int, user=Depends(team_access.needs("campaigns")),
                     db: Session = Depends(get_db)):
    """Put one failed post back in the queue and let the publish sweep take it now.

    The sweep is still the only thing that talks to Graph - this endpoint resets the ladder and
    asks it to run for this campaign, so a retry behaves exactly like a first publish.
    """
    from app.services.publisher import publish_due

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="No such post")
    boost = db.query(Boost).filter(Boost.id == post.boost_id).first()
    if not boost:
        raise HTTPException(status_code=404, detail="No such campaign")
    if post.publish_status == "posted":
        raise HTTPException(status_code=409, detail="That post has already been published")

    post.publish_status = "scheduled"
    post.publish_attempts = 0
    post.next_attempt_at = None
    post.failed_at = None
    post.failure_kind = None
    post.publish_at = datetime.utcnow().isoformat()
    db.add(Event(boost_id=boost.id, event_type="post_retry_requested",
                 payload={"post_id": post.id, "day": post.day, "by": user.email,
                          "previous_error": (post.last_error or "")[:400]}))
    db.commit()

    try:
        result = await publish_due(db, limit=5, boost_id=boost.id)
    except Exception as exc:                                # noqa: BLE001 - reported, not hidden
        log.warning("retry publish failed for post %s: %s", post.id, exc)
        return {"ok": False, "post_id": post.id, "campaign_id": boost.id,
                "message": f"The queue was reset but publishing failed: {exc}"}

    db.refresh(post)
    published = post.publish_status == "posted"
    return {
        "ok": published,
        "post_id": post.id,
        "campaign_id": boost.id,
        "publish_status": post.publish_status,
        "message": ("Published." if published else
                    (post.failure_note or "Still failing - see the fail log.")),
        "result": result,
    }


# --------------------------------------------------------------------------- connections
_CONN_OK = {"healthy", "ok", "working", "connected"}
_CONN_DEAD = {"needs_reconnect", "broken", "expired", "invalid", "revoked", "failed"}


def _connection_status(account: AdAccount, now: datetime) -> str:
    expires = _dt(account.token_expires_at)
    token = (account.token_status or "").strip().lower()
    if expires and expires < now:
        return "needs reconnect"
    if token in _CONN_DEAD:
        return "needs reconnect"
    if token == "expiring" or (expires and expires - now <= timedelta(days=7)):
        return "expiring soon"
    if not account.access_token or token == "simulated":
        return "not connected"
    return "working"


@router.get("/admin/connections")
def connections(user=Depends(team_access.needs("agents")), db: Session = Depends(get_db)):
    """Every agent's Meta login: whose Page, whether the token still works, and when it dies."""
    now = datetime.utcnow()
    rows = (
        db.query(AdAccount, User)
        .join(User, AdAccount.user_id == User.id)
        .order_by(AdAccount.user_id)
        .all()
    )
    out = []
    for account, owner in rows:
        out.append({
            "user_id": account.user_id,
            "agent_name": (owner.name or owner.email or "—") if owner else "—",
            "agent_email": owner.email if owner else None,
            "account_id": account.id,
            "advertiser_id": account.advertiser_id,
            "account_name": account.account_name,
            "page_id": account.page_id,
            "page_name": getattr(account, "page_name", None),
            "ig_username": getattr(account, "ig_username", None) if not str(
                getattr(account, "ig_username", "") or "").isdigit() else None,
            "status": _connection_status(account, now),
            "expires_at": _iso(account.token_expires_at),
            "checked_at": _iso(account.token_checked_at),
            "note": account.token_note,
            "funding_status": account.funding_status,
        })
    return out


# --------------------------------------------------------------------------- activity
# event_type -> (kind, label). The console groups by kind, so every event the product writes
# has to land in one of these buckets or it shows up as a bare string.
_ACTIVITY = {
    "campaign_drafted": ("build", "Campaign"),
    "build_progress": ("build", "Build"),
    "campaign_paid": ("money", "Payment"),
    "campaign_launched": ("build", "Launch"),
    "campaign_paused": ("build", "Campaign"),
    "campaign_resumed": ("build", "Campaign"),
    "campaign_repeated": ("build", "Campaign"),
    "launch_details": ("build", "Launch"),
    "post_published": ("publish", "Published"),
    "post_failed": ("publish", "Failed"),
    "post_retrying": ("publish", "Retrying"),
    "post_retry_requested": ("publish", "Retry"),
    "post_requeued": ("publish", "Requeued"),
    "post_skipped": ("publish", "Skipped"),
    "posts_purged": ("publish", "Cleaned up"),
    "photo_removed": ("build", "Photo"),
    "user_registered": ("account", "Sign-up"),
    "email_confirmed": ("account", "Email"),
    "checkout_started": ("money", "Checkout"),
    "stripe_customer_created": ("money", "Stripe"),
    "pack_paid": ("money", "Payment"),
    "listing_sold": ("money", "Sale"),
    "setup_session_booked": ("account", "Setup call"),
    "password_reset_sent": ("account", "Password"),
    "password_reset_unmailed": ("account", "Password"),
    "account_deleted": ("account", "Account"),
    "credit_consumed": ("money", "Credit"),
    "credit_returned": ("money", "Credit"),
    "ticket_created": ("support", "Ticket"),
    "ticket_replied": ("support", "Reply"),
    "ticket_updated": ("support", "Ticket"),
    "ticket_notified": ("support", "Ticket"),
    "ticket_reply_notified": ("support", "Ticket"),
    "error": ("system", "Error"),
}


def _activity_text(event_type: str, payload: Dict[str, Any]) -> str:
    payload = payload if isinstance(payload, dict) else {}
    bits = []
    for key in ("address", "day", "kind", "target", "subject", "from", "amount_usd",
                "amount_cents", "error", "reason", "note", "email"):
        value = payload.get(key)
        if value not in (None, "", [], {}):
            bits.append(f"{key}={value}")
    return " · ".join(bits)[:280] or event_type.replace("_", " ")


@router.get("/admin/activity")
def activity(limit: int = 60, kind: Optional[str] = None,
             user=Depends(team_access.needs("system")), db: Session = Depends(get_db)):
    """What the shop did recently, newest first, in the words the console uses."""
    limit = max(1, min(int(limit or 60), 200))
    query = db.query(Event, Boost, User).outerjoin(Boost, Event.boost_id == Boost.id)
    query = query.outerjoin(User, Boost.user_id == User.id)
    wanted = [t for t, (k, _l) in _ACTIVITY.items() if not kind or k == kind]
    if kind:
        query = query.filter(Event.event_type.in_(wanted or [""]))
    rows = query.order_by(Event.id.desc()).limit(limit).all()
    out = []
    for event, boost, owner in rows:
        bucket, label = _ACTIVITY.get(event.event_type, ("system", event.event_type.replace("_", " ").title()))
        out.append({
            "id": event.id,
            "at": _iso(event.created_at) or _iso(getattr(event, "at", None)),
            "kind": bucket,
            "kind_label": label,
            "event_type": event.event_type,
            "text": _activity_text(event.event_type, event.payload or {}),
            "agent": (owner.name or owner.email) if owner else None,
            "agent_email": owner.email if owner else None,
            "campaign_id": event.boost_id,
            "address": boost.address if boost else None,
        })
    return out


@router.get("/admin/connections/setup")
def setup_stuck(user=Depends(team_access.needs("agents")), db: Session = Depends(get_db)):
    """Engine 1, Part C 5a: how many agents are stuck on each setup item, most first."""
    from app.services import meta_engine
    counts = meta_engine.team_counts(db)
    rows = [{"key": k, "line": meta_engine.OUTCOMES.get(k, {}).get("line", k), "agents": n}
            for k, n in counts.items() if k != "ok"]
    rows.sort(key=lambda r: (-r["agents"], meta_engine.OUTCOMES.get(r["key"], {}).get("rank", 99)))
    return {"items": rows, "all_set": counts.get("ok", 0)}


# ---------------------------------------------------------------- Engine 1, Part B 7: weekly Meta review
@router.get("/admin/meta/weekly-review")
def meta_weekly_review(user=Depends(team_access.needs("agents")), db: Session = Depends(get_db)):
    """The latest Weekly Meta review (or none yet)."""
    from app.db.session import Event
    ev = (db.query(Event).filter(Event.event_type == "meta_weekly_review").order_by(Event.id.desc()).first())
    return {"review": ({"id": ev.id, "created_at": ev.created_at.isoformat() if ev.created_at else None,
                        **(ev.payload or {})} if ev else None)}


class _ReviewDecision(BaseModel):
    index: int
    approve: bool


@router.post("/admin/meta/weekly-review/{review_id}/decide")
def meta_review_decide(review_id: int, body: _ReviewDecision, user=Depends(team_access.needs("agents")),
                       db: Session = Depends(get_db)):
    from app.services import meta_engine
    try:
        return meta_engine.decide_suggestion(db, review_id, body.index, body.approve,
                                             who=(user.name or user.email or ""))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/admin/meta/weekly-review/run")
async def meta_review_run(x_resmara_token: str = Header(default=""), db: Session = Depends(get_db),
                          user=Depends(get_current_user_optional)):
    """Run by the clock on Mondays (or by an operator). Saves one review per week."""
    ok_token = bool(settings.PUBLISH_TOKEN) and x_resmara_token == settings.PUBLISH_TOKEN
    if not ok_token and not (user is not None and getattr(user, "is_admin", False)):
        raise HTTPException(status_code=403, detail="Operator only")
    from app.services import meta_engine
    return await meta_engine.weekly_review(db)


@router.post("/admin/platform-rules/refresh")
async def platform_rules_refresh(force: bool = False, x_resmara_token: str = Header(default=""),
                                 db: Session = Depends(get_db), user=Depends(get_current_user_optional)):
    """Engine 4, 9b: the monthly re-read of the platforms' rules (banned hashtags, Meta's housing
    ad rules). Run by the clock on the 1st, or by an operator."""
    ok_token = bool(settings.PUBLISH_TOKEN) and x_resmara_token == settings.PUBLISH_TOKEN
    if not ok_token and not (user is not None and getattr(user, "is_admin", False)):
        raise HTTPException(status_code=403, detail="Operator only")
    from app.services import learning_library
    return await learning_library.refresh_platform_rules(db, force=force)
