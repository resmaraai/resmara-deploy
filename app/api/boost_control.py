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
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.billing import require_paid
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


@router.post("/boosts/{boost_id}/pause")
async def pause_campaign(boost_id: int, db: Session = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    """Stop delivery now; the end date moves out by however long it stays paused (§4.5)."""
    boost = _owned(boost_id, current_user, db)
    ad = db.query(Ad).filter(Ad.boost_id == boost.id).first()
    if not ad or not ad.meta_ad_id:
        raise HTTPException(status_code=404, detail={
            "error": "no_live_ad", "message": "This campaign has not been launched yet."})
    if boost.paused_at:
        return {"status": "already_paused", "paused_at": boost.paused_at.isoformat()}
    steps = await _set_objects(ad, "PAUSED")
    boost.paused_at = datetime.now(timezone.utc)
    ad.status = "paused"
    db.add(Event(user_id=current_user.id, boost_id=boost.id, event_type="campaign_paused",
                 payload={"steps": steps}))
    db.commit()
    return {"status": "paused", "steps": steps,
            "paused_at": boost.paused_at.isoformat(),
            "note": "The end date moves out by the days it stays paused."}


@router.post("/boosts/{boost_id}/resume")
async def resume_campaign(boost_id: int, db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    """Restart delivery and give the seller back the days they lost (§4.5)."""
    boost = _owned(boost_id, current_user, db)
    ad = db.query(Ad).filter(Ad.boost_id == boost.id).first()
    if not ad or not ad.meta_ad_id:
        raise HTTPException(status_code=404, detail={"error": "no_live_ad",
                                                     "message": "Nothing to resume."})
    if not boost.paused_at:
        return {"status": "not_paused"}
    steps = await _set_objects(ad, "ACTIVE")
    paused = boost.paused_at
    if paused.tzinfo is None:
        paused = paused.replace(tzinfo=timezone.utc)
    days = max(0, (datetime.now(timezone.utc) - paused).days)
    boost.paused_days = int(boost.paused_days or 0) + days
    boost.paused_at = None
    # The run's clock is the ad set's end date, so the days it was paused are added there —
    # on Meta, not only in Resmara's database (§4.5).
    end_time = None
    if ad.meta_adset_id:
        from app.services.ad_build import schedule
        start = getattr(boost, "go_live_date", None)
        window = schedule(start) if start else {}
        if window:
            base = datetime.fromisoformat(window["end_time"])
            end_time = (base + timedelta(days=int(boost.paused_days))).isoformat()
            try:
                from app.services.launch import resolve_ad_account
                from app.services.ad_platforms import get_platform_client
                account = resolve_ad_account(boost, current_user, db)
                if account:
                    client = get_platform_client(account)
                    if hasattr(client, "update_object"):
                        await client.update_object(ad.meta_adset_id, {"end_time": end_time})
                        steps.append({"adset_end_time": end_time, "ok": True})
            except Exception as exc:  # noqa: BLE001 - report the failure instead of hiding it
                steps.append({"adset_end_time": end_time, "ok": False, "error": str(exc)[:200]})
    ad.status = "live"
    db.add(Event(user_id=current_user.id, boost_id=boost.id, event_type="campaign_resumed",
                 payload={"steps": steps, "days_added": days, "end_time": end_time}))
    db.commit()
    return {"status": "resumed", "steps": steps, "days_added": days, "end_time": end_time}


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
    """Daily listing check across every running campaign. Called by the scheduler.

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
