"""Campaign engine endpoints: AI content build -> client approval -> real Meta launch.

The launch half mirrors the Creatify ad flow the dashboard was reverse-engineered from
(see app/services/credits.py and app/services/ad_platforms.py): a two-layer approval gate
(budget precheck + copy approval) in front of campaign -> adset -> creative -> ad, driven
by the same PENDING -> PENDING_APPROVAL -> APPROVED -> DEPLOYED -> LIVE state machine.

The gate itself lives in app/services/launch.py so /api/resmara/launch and
/api/boosts/{id}/launch cannot drift apart. Nothing here spends money: the campaign is
created ACTIVE and held back by the ad set's start_time, which is the go-live date the agent
approved (Ad Engine §4.4).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import asyncio
import time
from datetime import datetime, timezone

from app.db.session import get_db, SessionLocal, User, Boost, AdAccount, Asset, Post, Event
from app.core.security import get_current_user
from app.services.credits import CampaignStage, CampaignAction
from app.api.billing import allow_build, charge_saved, is_locked, require_paid, require_unlocked

router = APIRouter()

# A real build runs four model calls and takes minutes, which is longer than a hosted
# platform's request timeout (Render answers 502 at ~100s and the client hangs up, cancelling
# the request task mid-build). So /build starts the run in the background and answers 202 at
# once; the UI and the deploy checks follow it through /build-status.
_BUILDS: dict = {}

# The event loop only holds a WEAK reference to a task, so a build started with a bare
# asyncio.create_task() can be garbage-collected mid-run: the boost stays "In Progress" for
# ever, no post is written and no error is logged (that is what killed the 9 Nov build).
# Keep a strong reference for as long as the task is alive.
_BUILD_TASKS: set = set()

# A build that has not finished in this long is not running any more. Without a deadline the
# status endpoint reports a dead run as "running" until the process restarts.
BUILD_DEADLINE_SECONDS = 15 * 60

INTERRUPTED_ERROR = (
    "The build stopped before it finished - the server restarted while it was running. "
    "Nothing was lost: start the build again."
)

# What a provider refusal looks like when the account behind the API key has run out of
# credit. A customer can do nothing about it, and the raw text they used to get was
# `Client error '429 Too Many Requests' ... insufficient_quota` — which reads like a Resmara
# bug and hides the one fact that matters: the campaign itself is intact.
_PROVIDER_QUOTA_MARKERS = ("insufficient_quota", "credit_balance_exhausted",
                           "no credits remaining", "exceeded your current quota")


def provider_error_text(raw: str) -> str:
    """A build failure in words the customer can act on; anything else passes through."""
    text = str(raw or "").strip()
    low = text.lower()
    if any(marker in low for marker in _PROVIDER_QUOTA_MARKERS):
        return ("Resmara's AI provider is out of credit, so this build stopped before it wrote any "
                "posts. Nothing else is missing - the campaign, its photos and the approved scope "
                "are saved, and the build runs again once the account is topped up.")
    return text



def _owned_boost(boost_id: int, current_user: User, db: Session) -> Boost:
    """Fetch a boost the caller may act on (owner, or an admin)."""
    q = db.query(Boost).filter(Boost.id == boost_id)
    if not current_user.is_admin:
        q = q.filter(Boost.user_id == current_user.id)
    boost = q.first()
    if not boost:
        raise HTTPException(status_code=404, detail="Boost not found")
    return boost


def _log(db: Session, current_user: User, boost_id: int, event_type: str, payload: dict):
    db.add(Event(user_id=current_user.id, boost_id=boost_id, event_type=event_type, payload=payload))


class BuildRequest(BaseModel):
    force: bool = False
    # Manual facts win over the AI (the spec's AI Notes / team corrections rule).
    openings: Optional[dict] = None
    # The agent ticked "I have permission to use these photos" before Build (item 9). The
    # timestamp it produces is what the campaign keeps; the flag itself is not stored.
    photo_permission: bool = False


async def _run_build(boost_id: int, user_id: int, force: bool, openings: Optional[dict]):
    """The actual engine run, on its own session so it outlives the request that started it."""
    from app.services.content_engine import build_campaign as run_engine

    state = _BUILDS.setdefault(boost_id, {})
    state.update({"status": "running", "started_at": time.time(), "error": None, "posts_created": 0})
    db = SessionLocal()
    try:
        boost = db.query(Boost).filter(Boost.id == boost_id).first()
        user = db.query(User).filter(User.id == user_id).first()
        if not boost or not user:
            state.update({"status": "error", "error": "boost or user disappeared mid-build"})
            return
        # Persist the start: if this process dies mid-build, /build-status can still tell the
        # difference between "never started" and "started and was cut off".
        _log(db, user, boost_id, "build_started", {"force": bool(force)})
        db.commit()
        from app.services import llm

        def progress(stage, **extra):
            """Told where the engine has got to; a poll reads it back as build_progress."""
            state["stage"] = stage
            _progress(db, user_id, boost_id, stage, **extra)

        result = await run_engine(boost, db, force=force, openings=openings, progress=progress)
        spent = llm.take_usage()
        state.update({
            "status": "done",
            "posts_created": result.get("posts_created") or 0,
            "source": result.get("source"),
            "violations": len(result.get("violations") or []),
            "notes": (result.get("notes") or [])[:6],
            # What this one campaign cost, as the provider counted it.
            "tokens": spent,
        })
        _log(db, user, boost_id, "campaign_built", {
            "source": result.get("source"), "posts": result.get("posts_created"),
            "violations": len(result.get("violations") or []),
            "tokens": spent.get("total_tokens"), "calls": spent.get("calls"),
        })
        db.commit()
        # A saved card unlocks the campaign as soon as it's built; without one (or declined) it
        # opens locked with the pay card on top.
        if result.get("posts_created") and is_locked(boost, user, db):
            try:
                state["unlock"] = await charge_saved(db, boost, user)
            except Exception as exc:  # noqa: BLE001 - a failed charge leaves it locked, never broken
                state["unlock"] = {"status": "declined", "message": type(exc).__name__}
    except Exception as e:  # noqa: BLE001 - the build may fail for a dozen reasons; record it
        db.rollback()
        state.update({"status": "error", "error": provider_error_text(e)[:400]})
        try:
            from app.services.llm import take_usage
            spent = take_usage()  # a failed run still burned tokens; say how many
            state["tokens"] = spent
            # A campaign that failed while still marked "In Progress" is the worst of both:
            # the customer waits for content that will never arrive. Say it failed.
            boost = db.query(Boost).filter(Boost.id == boost_id).first()
            if boost and (state.get("posts_created") or 0) == 0:
                boost.main_status = "Build failed"
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                _log(db, user, boost_id, "error", {
                    "where": "build_campaign", "error": provider_error_text(e)[:400],
                    "tokens": spent.get("total_tokens"), "calls": spent.get("calls"),
                })
                db.commit()
            # Paid and empty is not a state the agent should be left in (item 16): hand the
            # money back now rather than waiting for someone to notice.
            if boost and (state.get("posts_created") or 0) == 0:
                state["refund"] = await refund_after_failure_async(db, boost)
        except Exception:
            db.rollback()
    finally:
        state["finished_at"] = time.time()
        db.close()


@router.post("/boosts/{boost_id}/build", status_code=202)
async def build_campaign(boost_id: int, body: BuildRequest = BuildRequest(),
                         current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Start the content engine: research -> brand -> style recipe -> N-day plan -> posts.

    Answers 202 immediately and runs the engine in the background; poll /build-status for the
    outcome. Four model calls take minutes, which no hosted proxy will hold open.
    """
    boost = _owned_boost(boost_id, current_user, db)
    # Build first, then pay to unlock: no card is asked for before the build.
    allow_build(boost, current_user, db)
    if body.photo_permission and not boost.photo_permission_at:
        # Stored, not just acknowledged: the timestamp is the record, and it is taken once so
        # a later build cannot move it.
        boost.photo_permission_at = datetime.now(timezone.utc)
        db.commit()
    if not boost.photo_permission_at:
        photos_in_gallery = db.query(Asset).filter(Asset.boost_id == boost.id,
                                                   Asset.kind == "photo").count()
        if photos_in_gallery:
            raise HTTPException(status_code=409, detail={
                "error": "photo_permission_required",
                "message": ("Before we design your posts, confirm you have permission to use "
                            "the photos in this gallery."),
                "photos": photos_in_gallery,
            })
    running = _durable_build_state(db, boost)
    if running.get("status") == "running" and not body.force:
        return {"status": "running", "boost_id": boost.id,
                "started_at": running.get("started_at"), "stage": running.get("stage")}
    task = asyncio.create_task(_run_build(boost.id, current_user.id, body.force, body.openings))
    _BUILD_TASKS.add(task)          # strong reference: the loop's own reference is weak
    task.add_done_callback(_BUILD_TASKS.discard)
    _BUILDS[boost.id] = {"status": "running", "started_at": time.time(), "error": None}
    return {"status": "running", "boost_id": boost.id, "started_at": _BUILDS[boost.id]["started_at"]}


# The event types that tell a build's story, in order. Everything /build-status says is read
# back from these, not from a dict in memory: a free instance restarts, a deploy swaps the
# process, and an in-memory "running" flag then either lies for ever or — worse — makes a
# healthy build look dead the moment the poll lands in a process that never saw it start.
_LIFECYCLE_EVENTS = ("build_started", "build_progress", "campaign_built", "error")


def _as_utc(when):
    """A timestamp from the database, always comparable to now (UTC)."""
    if when is None:
        return None
    if when.tzinfo is None:
        return when.replace(tzinfo=timezone.utc)
    return when.astimezone(timezone.utc)


def _last_build_event(db: Session, boost_id: int):
    """The most recent build-lifecycle event for this boost, if any."""
    return (db.query(Event)
            .filter(Event.boost_id == boost_id, Event.event_type.in_(_LIFECYCLE_EVENTS))
            .order_by(Event.id.desc())
            .first())


def _durable_build_state(db: Session, boost: Boost) -> dict:
    """What this boost's last build is doing, read from the events so every worker agrees."""
    last = _last_build_event(db, boost.id)
    posts = db.query(Post).filter(Post.boost_id == boost.id).count()
    if last is None:
        return {"status": "done" if posts else "idle", "posts_created": posts}
    payload = last.payload or {}
    if last.event_type == "campaign_built":
        return {"status": "done", "posts_created": posts,
                "source": payload.get("source"),
                "violations": payload.get("violations") or 0}
    if last.event_type == "error":
        return {"status": "error", "posts_created": posts,
                "error": payload.get("error") or INTERRUPTED_ERROR}
    started = _as_utc(last.created_at)
    age = (datetime.now(timezone.utc) - started).total_seconds() if started else 0
    if age <= BUILD_DEADLINE_SECONDS:
        return {"status": "running", "stage": payload.get("stage"),
                "started_at": started.timestamp() if started else None}
    return {"status": "error", "error": INTERRUPTED_ERROR, "interrupted": True,
            "posts_created": posts}


def _progress(db: Session, user_id: int, boost_id: int, stage: str, **extra):
    """Note where a long build has got to, so a poll can tell 'working' from 'gone'.

    Written on the build's own session. A second connection waits behind the build's open
    transaction (3.7s per note on SQLite, which held the 202 back by eleven seconds); the
    engine has committed its own work at every point this is called.
    """
    try:
        db.add(Event(user_id=user_id, boost_id=boost_id, event_type="build_progress",
                     payload=dict(stage=stage, **extra)))
        db.commit()
    except Exception:  # noqa: BLE001 - a lost progress note must never kill the build
        db.rollback()


def _mark_interrupted(db: Session, boost: Boost, reason: str, user_id: int | None = None):
    """Say out loud that a build died, once, so the next status read is honest.

    A build that dies is also a build the agent paid for and did not get, so the same call
    hands the money back (item 16) — once, because the refund leaves the campaign unpaid.
    """
    boost.main_status = "Build failed"
    uid = user_id or boost.user_id
    if uid:
        _log(db, User(id=uid), boost.id, "error", {"where": "build_campaign", "error": reason})
    db.commit()
    return refund_after_failure(db, boost)


async def refund_after_failure_async(db: Session, boost: Boost) -> dict:
    """The refund, awaited where the caller is already async."""
    try:
        from app.services.billing import refund_failed_build
        return await refund_failed_build(boost, db)
    except Exception as exc:  # noqa: BLE001
        db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="refund_failed",
                     payload={"error": f"{type(exc).__name__}: {exc}"[:300]}))
        db.commit()
        return {"refunded": False, "error": str(exc)[:300]}


def refund_after_failure(db: Session, boost: Boost) -> dict:
    """Refund a paid build that failed, without ever raising into the failure path."""
    try:
        from app.services.billing import refund_failed_build
        return asyncio.run(refund_failed_build(boost, db))
    except Exception as exc:  # noqa: BLE001 - the failure is already being reported
        db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="refund_failed",
                     payload={"error": f"{type(exc).__name__}: {exc}"[:300]}))
        db.commit()
        return {"refunded": False, "error": str(exc)[:300]}


@router.patch("/boosts/{boost_id}/photo-permission")
def photo_permission(boost_id: int, body: Optional[dict] = None,
                     current_user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """Record the agent's permission to use the gallery's photos, with the moment (item 9).

    Taken once and kept: a ticked box is an answer about the photographs, and it does not stop
    being true because the campaign was rebuilt.
    """
    boost = _owned_boost(boost_id, current_user, db)
    body = body or {}
    if not body.get("granted"):
        return {"boost_id": boost.id, "granted": False,
                "photo_permission_at": boost.photo_permission_at.isoformat()
                if boost.photo_permission_at else None}
    if not boost.photo_permission_at:
        boost.photo_permission_at = datetime.now(timezone.utc)
        _log(db, current_user, boost.id, "photo_permission", {})
        db.commit()
    return {"boost_id": boost.id, "granted": True,
            "photo_permission_at": boost.photo_permission_at.isoformat()}


@router.get("/boosts/{boost_id}/build-status")
def build_status(boost_id: int, current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """How the last build for this boost is going (the UI polls this instead of holding a request)."""
    boost = _owned_boost(boost_id, current_user, db)
    state = _durable_build_state(db, boost)
    if state.get("interrupted"):
        # Started, never finished, and long past any real run: a dead run, not a slow one.
        _mark_interrupted(db, boost, "the build started but never finished (%d minute deadline)"
                          % (BUILD_DEADLINE_SECONDS // 60))
        _BUILDS[boost.id] = {"status": "error", "error": INTERRUPTED_ERROR, "interrupted": True}
    # The events carry the outcome; the in-memory run carries the detail nobody stores
    # (notes, token spend, which posts were repaired).
    run = _BUILDS.get(boost.id) or {}
    if run and run.get("status") == state.get("status") == "done":
        state.update({k: v for k, v in run.items() if k in ("notes", "tokens", "source", "violations")})
    state["boost_id"] = boost.id
    started = state.get("started_at")
    if started:
        state["seconds"] = round(time.time() - started, 1)
    # Built and waiting for payment: the campaign opens blurred with the pay card on top.
    if state.get("status") == "done":
        state["locked"] = is_locked(boost, current_user, db)
        if run.get("unlock"):
            state["unlock"] = run["unlock"]
    return state


@router.get("/boosts/{boost_id}/plan")
def get_plan(boost_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    boost = _owned_boost(boost_id, current_user, db)
    if is_locked(boost, current_user, db):
        return {"boost_id": boost.id, "address": boost.address, "stage": boost.stage,
                "main_status": boost.main_status, "locked": True, "plan": {}, "brand_profile": {},
                "ad_brief": {}}
    return {
        "boost_id": boost.id,
        "address": boost.address,
        "stage": boost.stage,
        "main_status": boost.main_status,
        "plan": boost.plan or {},
        "brand_profile": boost.brand_profile or {},
        "ad_brief": boost.ad_brief or {},
    }


@router.get("/boosts/{boost_id}/posts")
def list_posts(boost_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The campaign's posts with the engine's scheduling and publishing state.

    ``failure`` is what the calendar's red "Didn't post" is drawn from: the kind, Meta's own
    reason, and the buttons that kind allows. None for a post that has not failed.
    """
    from app.services.post_retry import failure_payload
    boost = _owned_boost(boost_id, current_user, db)
    posts = db.query(Post).filter(Post.boost_id == boost.id).order_by(Post.day, Post.slot).all()
    if is_locked(boost, current_user, db):
        # Locked: the blurred preview gets three pictures and nothing to read or download.
        return [{"id": p.id, "day": p.day, "slot": p.slot, "kind": p.kind, "locked": True,
                 "image_url": p.image_url if i < 3 else None, "caption": None,
                 "client_status": p.client_status, "publish_status": p.publish_status}
                for i, p in enumerate(posts)]
    return [{
        "id": p.id, "day": p.day, "slot": p.slot, "kind": p.kind, "caption": p.caption,
        "hashtags": p.hashtags, "cta": p.cta, "image_url": p.image_url,
        "title": p.title, "kicker": p.kicker, "overlay_text": p.overlay_text,
        "photo_room": p.photo_room, "photo_file": p.photo_file, "post_type": p.post_type,
        "client_status": p.client_status, "publish_status": p.publish_status,
        "publish_at": p.publish_at, "publish_target": p.publish_target,
        "fb_post_id": p.fb_post_id, "ig_media_id": p.ig_media_id, "last_error": p.last_error,
        "attempts": p.publish_attempts or 0, "next_attempt_at": p.next_attempt_at,
        "failure": failure_payload(p),
        "caption_ig": p.caption_ig, "hashtags_fb": p.hashtags_fb, "design_style": p.design_style,
        "rating": p.rating, "needs_look": bool(p.needs_look),
    } for p in posts]


@router.post("/boosts/{boost_id}/approve")
def approve_campaign(boost_id: int, body: dict = None,
                     current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Client approval. Approving the posts is what unblocks the publisher, so this is the
    copy-approval half of the two-layer gate."""
    boost = _owned_boost(boost_id, current_user, db)
    require_unlocked(boost, current_user, db)
    body = body or {}
    # "No go-live without review" (owner's item 20). The UI knows which posts were actually
    # opened; if it says something on screen was never read, approval needs a second answer.
    # Silently approving 14 unseen posts is exactly the failure this gate exists to stop.
    unreviewed = int(body.get("unreviewed") or 0)
    if unreviewed > 0 and not body.get("confirm"):
        raise HTTPException(status_code=409, detail={
            "error": "review_required",
            "message": "You haven't reviewed everything — are you sure?",
            "unreviewed": unreviewed,
            "confirm_with": {"confirm": True},
        })
    only_ids = set(body.get("post_ids") or [])
    posts = db.query(Post).filter(Post.boost_id == boost.id).all()
    if not posts:
        raise HTTPException(status_code=409, detail={
            "error": "nothing_to_approve",
            "message": "There is nothing to review yet - build the campaign first."})
    approved = 0
    for p in posts:
        if only_ids and p.id not in only_ids:
            continue
        p.client_status = "approved"
        approved += 1
    boost.main_status = "Approved"
    if CampaignStage.can_transition(boost.stage or CampaignStage.PENDING, CampaignStage.APPROVED):
        boost.stage = CampaignStage.APPROVED
    _log(db, current_user, boost.id, "campaign_approved", {"posts_approved": approved})
    db.commit()
    return {"status": "approved", "boost_id": boost.id, "posts_approved": approved, "stage": boost.stage}


@router.post("/boosts/{boost_id}/launch")
async def launch(boost_id: int, body: dict = None,
                 current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Launch this boost's Meta campaign for real.

    Gate: budget precheck (subscription + ad-account budget) AND copy approval — every post
    approved by a human. Objects are created ACTIVE against the ad set's go-live time, so an
    approved campaign actually delivers (Ad Engine §4.4).
    """
    from app.services import consent
    from app.services.launch import launch_boost
    boost = _owned_boost(boost_id, current_user, db)
    require_paid(boost, current_user, db)
    # Going live in public is a money-moving, terms-bearing call: an account that has not
    # accepted the Terms now presented is asked first (Engine 10 §1).
    consent.require_current_terms(current_user)
    body = body or {}
    # There is no auto-approve path any more, for a launch or a re-run: approval is a human
    # reading the posts, and an API flag that skips it is the same "go live without review"
    # choice the owner ruled out (item 20).
    result = await launch_boost(
        boost, current_user, db,
        budget_usd=body.get("budget_usd"),
        auto_approve=False,
        action=body.get("action") or CampaignAction.LAUNCH_NEW_CAMPAIGN,
        custom_configs=body.get("meta_custom_configs") or {},
        no_delivery=bool(body.get("no_delivery") or body.get("build_paused")),
    )
    if result.get("status") == "failed":
        raise HTTPException(status_code=502, detail=result.get("detail"))
    return result


class PrecheckRequest(BaseModel):
    platform: str = "meta"
    advertiser_id: Optional[str] = None
    budget: float = 0.0


# The Creatify-style /adflow/credits/precheck/ endpoint is gone with the credit system: a
# campaign is bought outright, so there is no balance to pre-check. See app/api/billing.py.


# --------------------------------------------------------------------------- Engine 4: edits, swaps, thumbs
def _owned_post(boost_id: int, post_id: int, current_user: User, db: Session):
    boost = _owned_boost(boost_id, current_user, db)
    post = db.query(Post).filter(Post.id == post_id, Post.boost_id == boost.id).first()
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return boost, post


class PostEdit(BaseModel):
    title: Optional[str] = None
    caption: Optional[str] = None
    overlay_text: Optional[str] = None


@router.patch("/boosts/{boost_id}/posts/{post_id}")
def edit_post(boost_id: int, post_id: int, body: PostEdit, current_user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    """Save the agent's edit to a post, server-side, so what goes out is what they approved.

    Fair Housing runs on every edit (Engine 4, 9f): a non-compliant edit can't be saved and is never
    learned. An edit counts as a signal for the next campaign (it's recorded on the post).
    """
    from app.services import ad_rulebook, post_rules
    boost, post = _owned_post(boost_id, post_id, current_user, db)
    require_unlocked(boost, current_user, db)
    changed = {}
    for field in ("title", "caption", "overlay_text"):
        value = getattr(body, field)
        if value is not None and value != (getattr(post, field) or ""):
            changed[field] = value
    words = " ".join(changed.values())
    issues = ad_rulebook.fair_housing_issues(words)
    if issues:
        raise HTTPException(status_code=422, detail={
            "error": "fair_housing",
            "message": "This can't be saved: it describes who the home is for, which Fair Housing law "
                       "doesn't allow. " + "; ".join(issues[:2]) + ".",
            "issues": issues})
    if "caption" in changed:
        body_text = post_rules.strip_tags(changed["caption"])
        tags = (post.hashtags or "").strip()
        post.caption = body_text + (("\n\n" + tags) if tags else "")
        post.caption_ig = post_rules.instagram_caption(body_text, post.day or 0)
    if "title" in changed:
        post.title = changed["title"][:120]
    if "overlay_text" in changed:
        post.overlay_text = changed["overlay_text"][:200]
    if changed:
        feats = dict(post.features or {})
        feats["edited"] = sorted(set(feats.get("edited") or []) | set(changed))
        post.features = feats
        _log(db, current_user, boost.id, "post_edited", {"post_id": post.id, "fields": sorted(changed)})
    db.commit()
    return {"id": post.id, "caption": post.caption, "caption_ig": post.caption_ig, "title": post.title,
            "overlay_text": post.overlay_text, "edited": sorted(changed)}


class PostRating(BaseModel):
    value: int  # 1 thumbs up, -1 thumbs down, 0 clears it


@router.post("/boosts/{boost_id}/posts/{post_id}/rating")
def rate_post(boost_id: int, post_id: int, body: PostRating, current_user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    """👍 / 👎 on any post: one tap, no reason asked. The learner works out the why (Engine 4, 5)."""
    boost, post = _owned_post(boost_id, post_id, current_user, db)
    value = 1 if body.value > 0 else -1 if body.value < 0 else None
    post.rating = value
    _log(db, current_user, boost.id, "post_rated", {"post_id": post.id, "value": value,
                                                     "style": post.design_style})
    db.commit()
    return {"id": post.id, "rating": post.rating}


class PhotoSwap(BaseModel):
    asset_id: int


@router.post("/boosts/{boost_id}/posts/{post_id}/photo")
async def swap_photo(boost_id: int, post_id: int, body: PhotoSwap, current_user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """Swap a post's photo and redesign the post on it (Engine 4, 9f): same words, style and agent
    details, same checks. Never a plain photo: the fallback design if the model can't."""
    from app.services import design as design_step
    from app.services.content_engine import _asset_bytes, _owner_kit, _store_design
    boost, post = _owned_post(boost_id, post_id, current_user, db)
    require_unlocked(boost, current_user, db)
    asset = db.query(Asset).filter(Asset.id == body.asset_id, Asset.boost_id == boost.id).first()
    if asset is None:
        raise HTTPException(status_code=404, detail="That photo isn't in this home's photos")
    raw = _asset_bytes(asset)
    if not raw:
        raise HTTPException(status_code=409, detail="That photo file can't be read. Pick another.")
    kit = _owner_kit(db, boost)
    details = " · ".join(x for x in [kit.get("agent"), kit.get("phone"),
                                     (f"Lic. {kit['license']}" if kit.get("license") else ""),
                                     kit.get("company") or kit.get("brokerage")] if x)
    brief = {"overlay": post.overlay_text or post.title or "", "caption": post.caption or "",
             "room": asset.room or "", "style": post.design_style or "", "treatment": post.details_treatment or "",
             "details": details}
    made = await design_step.design_posts([brief], boost, {k: kit.get(k) for k in ("palette", "fonts")},
                                          lambda _p: (raw, asset.content_type or "image/jpeg"))
    item = (made.get("designed") or [None])[0]
    if item is None:
        raise HTTPException(status_code=502, detail="The post couldn't be redrawn on that photo. Try another.")
    post.image_url = _store_design(db, boost, post, item["bytes"])
    post.photo_file = asset.filename
    post.photo_room = asset.room or post.photo_room
    post.needs_look = bool(item.get("needs_look"))
    feats = dict(post.features or {})
    feats["swapped"] = True
    post.features = feats
    _log(db, current_user, boost.id, "post_photo_swapped", {"post_id": post.id, "asset_id": asset.id,
                                                            "fallback": bool(item.get("needs_look"))})
    db.commit()
    return {"id": post.id, "image_url": post.image_url, "needs_look": post.needs_look}


@router.get("/me/style-profile")
def my_style_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """What Resmara learned about you, in plain words (shown on My Brand)."""
    from app.services.content_engine import learned_summary, style_profile
    prof = style_profile(db, current_user.id)
    return {"lines": learned_summary(prof), "liked": prof["liked"], "avoid": prof["avoid"]}
