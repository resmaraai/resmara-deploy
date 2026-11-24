"""After the campaign exists: launch details, the pause, the numbers, and the re-run.

Ad Engine v1.3 splits a campaign's life into what happens before approval (§3, §6 — build,
review, approve) and what happens after it (§4.5 pause, §4.6 re-run, §5 the listing watcher,
§9 what the seller is told). This module is the after half. It is deliberately separate from
``engine.py`` so the money-spending launch path stays small enough to read in one sitting.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.billing import require_paid
from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import Ad, AdAccount, Boost, Event, Post, SessionLocal, User, get_db

router = APIRouter()

def _owned(boost_id: int, user: User, db: Session) -> Boost:
    q = db.query(Boost).filter(Boost.id == boost_id)
    if not getattr(user, "is_admin", False):
        q = q.filter(Boost.user_id == user.id)
    boost = q.first()
    if not boost:
        raise HTTPException(status_code=404, detail="Boost not found")
    return boost


def _is_url(value: str) -> bool:
    try:
        parts = urlsplit(value or "")
    except ValueError:
        return False
    return parts.scheme in ("http", "https") and bool(parts.netloc)


def check_link(url: str, *, timeout: int = 20) -> dict:
    """Is the agent's listing link actually a listing? (§3)

    A real check, not a regex: the URL is fetched the way a visitor would arrive, and a 404,
    a parked domain or an HTML error page is reported back instead of being pasted into an ad
    that runs for two weeks. Failure is a warning with the reason, never a silent pass.
    """
    if not _is_url(url):
        return {"ok": False, "status": 0, "detail": "That does not look like a web address."}
    try:
        resp = httpx.get(url, timeout=timeout, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0 (Resmara listing check)"})
    except Exception as exc:  # noqa: BLE001 - the reason is the answer
        return {"ok": False, "status": 0,
                "detail": f"The link could not be opened ({type(exc).__name__})."}
    if resp.status_code >= 400:
        return {"ok": False, "status": resp.status_code,
                "detail": f"The link answered {resp.status_code}."}
    body = (resp.text or "")[:20000].lower()
    signals = [word for word in ("for sale", "bed", "bath", "sq", "listing", "zillow",
                                 "realtor", "mls", "home", "property", "price")
               if word in body]
    if len(body) < 250 or not signals:
        return {"ok": False, "status": resp.status_code,
                "detail": "That page does not read like a listing - check the link."}
    return {"ok": True, "status": resp.status_code, "detail": "Listing link looks good.",
            "final_url": str(resp.url)}


class LaunchDetails(BaseModel):
    listing_url: Optional[str] = None
    destination_url: Optional[str] = None
    video_url: Optional[str] = None
    budget_usd: Optional[float] = None


@router.patch("/boosts/{boost_id}/launch-details")
async def launch_details(boost_id: int, body: LaunchDetails, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    """The three links launch needs, checked before they are stored (§3, §6.7)."""
    boost = _owned(boost_id, current_user, db)
    out = {"boost_id": boost.id, "checks": {}}

    if body.listing_url is not None:
        url = body.listing_url.strip()
        if url:
            result = await asyncio.to_thread(check_link, url)
            out["checks"]["listing_url"] = result
            if not result["ok"]:
                raise HTTPException(status_code=422, detail={
                    "error": "listing_link_unusable", "message": result["detail"],
                    "field": "listing_url", **result})
            # The same visit looks for the tour video (Post Engine §6.6): the link check tells
            # the agent what it found in one answer, instead of a separate step they forget.
            from app.services import listing_video
            found = await listing_video.find(url)
            out["checks"]["video"] = {"found": found["found"], "detail": found["detail"],
                                      "url": found.get("video_url")}
            if found["found"] and not boost.video_url:
                boost.video_url = found["video_url"]
                boost.video_found_at = datetime.now(timezone.utc)
        boost.listing_url = url or None
        boost.listing_checked_at = datetime.now(timezone.utc)

    if body.destination_url is not None:
        url = body.destination_url.strip()
        if url and not _is_url(url):
            raise HTTPException(status_code=422, detail={
                "error": "bad_url", "field": "destination_url",
                "message": "The click destination has to be a full http(s) address."})
        boost.destination_url = url or None

    if body.video_url is not None:
        url = body.video_url.strip()
        if url and not _is_url(url):
            raise HTTPException(status_code=422, detail={
                "error": "bad_url", "field": "video_url",
                "message": "The video has to be a full http(s) address."})
        boost.video_url = url or None

    if body.budget_usd is not None:
        from app.services.ad_build import clamp_budget
        boost.ad_budget_usd = clamp_budget(body.budget_usd)
        # The agent has seen and accepted the number the ad will spend.
        boost.budget_confirmed_at = datetime.now(timezone.utc)
        out["budget_usd"] = boost.ad_budget_usd

    db.add(Event(user_id=current_user.id, boost_id=boost.id, event_type="launch_details",
                 payload={"checks": out["checks"], "budget_usd": boost.ad_budget_usd}))
    db.commit()
    out.update({"listing_url": boost.listing_url, "destination_url": boost.destination_url,
                "video_url": boost.video_url})
    return out


@router.post("/boosts/{boost_id}/check-listing")
async def check_listing(boost_id: int, db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    """Re-check the listing link on demand (the daily watcher does this on its own)."""
    boost = _owned(boost_id, current_user, db)
    if not boost.listing_url:
        raise HTTPException(status_code=422, detail={
            "error": "no_listing_url", "message": "Add the listing link first."})
    result = await asyncio.to_thread(check_link, boost.listing_url)
    boost.listing_status = "active" if result["ok"] else "unknown"
    boost.listing_checked_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": result["ok"], **result}


# --------------------------------------------------------------------------- pause / resume

async def _set_objects(ad: Ad, state: str) -> list:
    """Pause or resume the whole chain, newest object first, and report each step."""
    from app.services.ad_platforms import get_platform_client
    from app.db.session import AdAccount
    from app.services.launch import resolve_ad_account

    db = SessionLocal()
    steps = []
    try:
        boost = db.query(Boost).filter(Boost.id == ad.boost_id).first()
        account = db.query(AdAccount).filter(AdAccount.id == ad.ad_account_id).first() \
            if getattr(ad, "ad_account_id", None) else None
        if not account and boost is not None:
            owner = db.query(User).filter(User.id == boost.user_id).first()
            account = resolve_ad_account(boost, owner, db) if owner else None
        if not account:
            return [{"error": "no ad account"}]
        client = get_platform_client(account)
        for label, object_id in (("ad", ad.meta_ad_id), ("adset", ad.meta_adset_id),
                                 ("campaign", ad.meta_campaign_id)):
            if not object_id:
                continue
            try:
                if not hasattr(client, "update_object"):
                    steps.append({label: object_id, "status": state, "ok": False,
                                  "error": "this platform cannot be paused from here"})
                    continue
                await client.update_object(object_id, {"status": state})
                steps.append({label: object_id, "status": state, "ok": True})
            except Exception as exc:  # noqa: BLE001 - report, do not hide
                steps.append({label: object_id, "status": state, "ok": False,
                              "error": str(exc)[:300]})
    finally:
        db.close()
    return steps


class PauseBody(BaseModel):
    # Engine 6, section 7: the Pause pop-up's choices. "pause" = Just pause it.
    why: str = "pause"


@router.post("/boosts/{boost_id}/pause")
async def pause_campaign(boost_id: int, body: Optional[PauseBody] = None, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    """Stop the ad and the remaining posts now (§4.5). It's pending / It sold are the agent's
    fail-safe: the listing sites can lag the MLS by a day, so this stops marketing immediately."""
    from app.services import campaign_state
    boost = _owned(boost_id, current_user, db)
    if not boost.launched_at and not db.query(Ad).filter(Ad.boost_id == boost.id, Ad.meta_ad_id.isnot(None)).first():
        raise HTTPException(status_code=404, detail={
            "error": "no_live_ad", "message": "This campaign has not been launched yet."})
    why = (body.why if body else "pause").lower()
    if why == "sold":
        from app.services import listing_status as lst
        await campaign_state.on_status(db, boost, lst.SOLD, [], "the agent said it sold", send=False)
        return {"status": "paused", "reason": "sold", "card_state": campaign_state.card_state(boost)}
    if why == "pending":
        if boost.until_sold:
            pass   # Run it until it sells stays on, paused (Engine 8, section 5)
        result = await campaign_state.pause(db, boost, "pending", by="agent")
        result["card_state"] = campaign_state.card_state(boost)
        return result
    if boost.paused_at:
        return {"status": "already_paused", "paused_at": boost.paused_at.isoformat(),
                "card_state": campaign_state.card_state(boost)}
    result = await campaign_state.pause(db, boost, "agent", by="agent")
    result["note"] = "The end date moves out by the days it stays paused."
    result["card_state"] = campaign_state.card_state(boost)
    return result


class ResumeBody(BaseModel):
    confirm: bool = False


@router.post("/boosts/{boost_id}/resume")
async def resume_campaign(boost_id: int, body: Optional[ResumeBody] = None, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    """Turn it back on: the ad and the remaining posts run again and the paused days come back (§4.5).
    If Resmara still reads the listing as pending, the agent confirms first (Engine 6, section 7)."""
    from app.services import campaign_state
    boost = _owned(boost_id, current_user, db)
    if not boost.paused_at:
        return {"status": "not_paused"}
    if (boost.listing_status or "") == "sold":
        raise HTTPException(status_code=409, detail={
            "error": "sold", "message": "This home sold, so the campaign can't be turned back on. A new listing is a new campaign."})
    still = [r for r in (boost.listing_reads or {}).values()
             if isinstance(r, dict) and r.get("status") == "pending" and r.get("layer") in ("known", "standard", "ai")]
    pending_now = boost.paused_reason == "pending" or (boost.listing_status or "") == "pending"
    if still and pending_now and not (body and body.confirm):
        raise HTTPException(status_code=409, detail={
            "error": "still_pending", "message": "Your listing still shows Pending. Turn it back on anyway?"})
    result = await campaign_state.resume(db, boost, by="agent", override_pending=bool(still and pending_now))
    result["card_state"] = campaign_state.card_state(boost)
    return result


# --------------------------------------------------------------------------- the numbers

@router.get("/boosts/{boost_id}/ad-performance")
async def ad_performance(boost_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    """What the ad did, in the seller's language (§9).

    Spend is included for the agent (it is their card) but the reach/clicks/leads are what the
    report leads with. Meta's own platform split is kept because the creative decision for the
    next campaign depends on which one worked.
    """
    boost = _owned(boost_id, current_user, db)
    ad = db.query(Ad).filter(Ad.boost_id == boost.id).first()
    if not ad or not ad.meta_ad_id:
        raise HTTPException(status_code=404, detail={
            "error": "no_live_ad", "message": "Nothing has run yet for this campaign."})
    from app.services.launch import resolve_ad_account
    from app.services.ad_platforms import get_platform_client

    account = resolve_ad_account(boost, current_user, db)
    if not account:
        raise HTTPException(status_code=409, detail={"error": "no_ad_account"})
    client = get_platform_client(account)
    try:
        raw = await client.get_ad_insights(ad.meta_ad_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail={
            "error": "insights_unavailable", "message": str(exc)[:300]})

    rows = (raw or {}).get("data") or []
    totals = {"impressions": 0, "reach": 0, "clicks": 0, "link_clicks": 0, "leads": 0,
              "spend": 0.0}
    platforms = {}
    for row in rows:
        for key in ("impressions", "reach", "clicks", "link_clicks"):
            totals[key] += int(float(row.get(key) or 0))
        totals["spend"] += float(row.get("spend") or 0)
        for action in row.get("actions") or []:
            if action.get("action_type") in ("lead", "offsite_conversion.fb_pixel_lead"):
                totals["leads"] += int(float(action.get("value") or 0))
        platform = row.get("publisher_platform") or "unknown"
        platforms[platform] = platforms.get(platform, 0) + int(float(row.get("impressions") or 0))
    totals["spend"] = round(totals["spend"], 2)
    totals["ctr_percent"] = round(totals["link_clicks"] / totals["impressions"] * 100, 2) \
        if totals["impressions"] else 0.0
    return {"boost_id": boost.id, "ad_id": ad.meta_ad_id, "format": ad.format,
            "status": ad.status, "totals": totals, "impressions_by_platform": platforms,
            "days_running": _days_running(boost)}


def _days_running(boost) -> int:
    if not boost.launched_at:
        return 0
    started = boost.launched_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    return max(0, (datetime.now(timezone.utc) - started).days)


# --------------------------------------------------------------------------- the watcher

@router.post("/admin/listings/sweep")
async def listings_sweep(x_resmara_token: str = Header(default=""),
                         db: Session = Depends(get_db)):
    """Hourly listing check across every running campaign (Engine 6, section 7). Called by the scheduler.

    Machine-called, so it uses the same shared token as the publisher; an unconfigured token
    refuses the call rather than letting anything on the internet trigger a pause.
    """
    from app.core.config import settings as _settings
    from app.services.listing_watch import sweep

    if not _settings.PUBLISH_TOKEN:
        raise HTTPException(status_code=503,
                            detail="RESMARA_PUBLISH_TOKEN is not configured")
    if x_resmara_token != _settings.PUBLISH_TOKEN:
        raise HTTPException(status_code=403, detail="Bad publish token")
    return await sweep(db)


# --------------------------------------------------------------------------- the old test posts

def _admin_only(user: User):
    if not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail={
            "error": "admin_only", "message": "This is an operator action."})


# auto_error=False is the whole point: an operator calling with X-Resmara-Token has no bearer
# token, and the default scheme would reject the request before the token was ever looked at.
_optional_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user_optional(token: Optional[str] = Depends(_optional_scheme),
                                    db: Session = Depends(get_db)) -> Optional[User]:
    """The signed-in operator, or None. Used where a machine token is also acceptable."""
    if not token:
        return None
    try:
        return await get_current_user(token=token, db=db)
    except HTTPException:
        return None


def _operator_or_token(user_ok: bool, token: str) -> None:
    """Admin session, or the machine token the sweep already uses.

    The old test posts have to be cleared before the publisher is switched on (item 7). Doing that
    from the dashboard is fine when someone is sitting in front of it; the deploy that clears them
    is not always a browser, so the same token that drives the listing sweep can drive this.
    """
    expected = (getattr(settings, "PUBLISH_TOKEN", "") or "").strip()
    if not expected:
        if user_ok:
            return
        raise HTTPException(status_code=503, detail={"error": "not_configured",
                                                    "message": "No publish token is configured."})
    if token and token == expected:
        return
    if user_ok:
        return
    raise HTTPException(status_code=403, detail={"error": "admin_only",
                                                "message": "This is an operator action."})


@router.get("/admin/posts/audit")
def posts_audit(db: Session = Depends(get_db),
                current_user: Optional[User] = Depends(get_current_user_optional),
                x_resmara_token: str = Header(default="")):
    """Every post on the site, grouped by campaign, with enough to recognise a test.

    The publisher stays off until the 126 old test posts are gone (owner item 7), and the only
    way to be sure it is safe to switch on is to look at what is actually stored. Read-only.
    """
    _operator_or_token(bool(current_user and getattr(current_user, "is_admin", False)),
                       x_resmara_token)
    rows = (db.query(Post, Boost).join(Boost, Post.boost_id == Boost.id)
            .order_by(Post.boost_id, Post.day, Post.slot).all())
    campaigns: dict = {}
    for post, boost in rows:
        entry = campaigns.setdefault(boost.id, {
            "boost_id": boost.id, "address": boost.address, "stage": boost.stage,
            "main_status": boost.main_status, "created_at": boost.created_at.isoformat()
            if boost.created_at else None, "posts": 0, "published": 0, "sample": []})
        entry["posts"] += 1
        if (post.publish_status or "").lower() in ("posted", "published", "live"):
            entry["published"] += 1
        if len(entry["sample"]) < 3:
            first_line = (post.caption or "").strip().split("\n")[0][:90]
            entry["sample"].append({"id": post.id, "day": post.day, "kind": post.kind,
                                    "status": post.publish_status, "caption": first_line})
    ordered = sorted(campaigns.values(), key=lambda c: (c["created_at"] or "", c["boost_id"]))
    return {"total_posts": sum(c["posts"] for c in ordered),
            "total_campaigns": len(ordered),
            "published_posts": sum(c["published"] for c in ordered),
            "campaigns": ordered}


@router.post("/admin/posts/purge")
def posts_purge(body: Optional[dict] = None, db: Session = Depends(get_db),
                current_user: Optional[User] = Depends(get_current_user_optional),
                x_resmara_token: str = Header(default="")):
    """Delete posts, but only when the operator has named what they are deleting.

    The confirmation string carries the number: a request that says "purge" without saying how
    many is exactly how the real campaign gets deleted by accident.
    """
    _operator_or_token(bool(current_user and getattr(current_user, "is_admin", False)),
                       x_resmara_token)
    body = body or {}
    count = db.query(Post).count()
    expected = body.get("expect_total")
    confirm = str(body.get("confirm") or "").strip().upper()
    if confirm != f"DELETE {count} POSTS":
        raise HTTPException(status_code=428, detail={
            "error": "confirmation_required",
            "message": f"There are {count} posts. To delete them, confirm with "
                       f"'DELETE {count} POSTS'.",
            "expect_confirm": f"DELETE {count} POSTS", "total_posts": count})
    if expected is not None and int(expected) != count:
        raise HTTPException(status_code=409, detail={
            "error": "count_changed", "message": "The number of posts changed since you looked.",
            "total_posts": count})
    keep = set(int(b) for b in (body.get("keep_boost_ids") or []))
    q = db.query(Post)
    if keep:
        q = q.filter(~Post.boost_id.in_(keep))
    deleted = q.delete(synchronize_session=False)
    # A machine-token purge has no user row to hang the event off; the event still gets written so
    # the dashboard's history shows who did what and when.
    db.add(Event(user_id=(current_user.id if current_user else None), event_type="posts_purged",
                 payload={"deleted": int(deleted), "kept_boost_ids": sorted(keep),
                          "via": "token" if current_user is None else "dashboard"}))
    db.commit()
    return {"deleted": int(deleted), "kept_boost_ids": sorted(keep), "remaining": db.query(Post).count()}


@router.post("/admin/listings/own-posts")
async def own_posts_sweep(x_resmara_token: str = Header(default=""), db: Session = Depends(get_db)):
    """Once a day: the agent's own business Page and Instagram, read for pending, sold and price
    posts about each running campaign's home (Engine 6, section 7.6). Called by the scheduler."""
    from app.core.config import settings as _settings
    from app.services.campaign_state import own_posts_sweep as run

    if not _settings.PUBLISH_TOKEN:
        raise HTTPException(status_code=503, detail="RESMARA_PUBLISH_TOKEN is not configured")
    if x_resmara_token != _settings.PUBLISH_TOKEN:
        raise HTTPException(status_code=403, detail="Bad publish token")
    return await run(db)
