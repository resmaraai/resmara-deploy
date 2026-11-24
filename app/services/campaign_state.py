"""Engine 6, sections 7 and 8: pause, resume, pending and sold, for the whole campaign at once.

Pausing stops the ad (in Meta) and the posts that haven't gone out (the publisher skips a paused
campaign), and the website stops taking showing requests when the reason is pending or sold
(listing_site.state reads boost.listing_status). Nothing is deleted. Resume gives back the days:
the ad's end date moves out and the remaining posts move forward by the time it was paused.

    paused_reason   agent    the agent pressed Pause ("Just pause it")
                    pending  under contract (detected, or the agent said so); can come back
                    sold     closed; final
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.db.session import Ad, Boost, Event, Post, User
from app.services import campaign_emails as emails
from app.services import listing_status as lst

log = logging.getLogger(__name__)
PENDING_WATCH_DAYS = 30
NO_READ_ALERT = timedelta(hours=24)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value):
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _kit(db, boost: Boost) -> Dict[str, Any]:
    owner = db.query(User).filter(User.id == boost.user_id).first()
    kit = dict((owner.brand if owner is not None else None) or {})
    if owner is not None:
        kit.setdefault("agent", owner.name or "")
    return kit


async def _ad(db, boost: Boost, state: str) -> list:
    ad = db.query(Ad).filter(Ad.boost_id == boost.id).first()
    if ad is None or not ad.meta_ad_id:
        return [{"ad": "none yet"}]
    from app.api.boost_control import _set_objects
    steps = await _set_objects(ad, state)
    ad.status = "paused" if state == "PAUSED" else "live"
    return steps


def ends_on(boost: Boost) -> Optional[datetime]:
    from app.services.listing_site import ends_on as site_end
    return site_end(boost)


def is_over(boost: Boost, now: Optional[datetime] = None) -> bool:
    end = ends_on(boost)
    return end is not None and end <= (now or _now())


async def pause(db, boost: Boost, reason: str = "agent", *, by: str = "agent") -> Dict[str, Any]:
    """Stop the ad and the remaining posts now. A second reason replaces the first (a paused
    campaign that then goes pending shows Paused · Pending)."""
    steps: list = []
    if boost.paused_at is None:
        steps = await _ad(db, boost, "PAUSED")
        boost.paused_at = _now()
    boost.paused_reason = reason
    if reason in ("pending", "sold"):
        boost.listing_status = reason
    db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="campaign_paused",
                 payload={"reason": reason, "by": by, "steps": steps}))
    db.commit()
    _site_changed(db, boost)
    return {"status": "paused", "reason": reason, "steps": steps}


def shift_posts(db, boost: Boost, delta: timedelta) -> int:
    """The posts that hadn't gone out move forward by the time the campaign was paused."""
    if delta.total_seconds() <= 0:
        return 0
    n = 0
    for post in db.query(Post).filter(Post.boost_id == boost.id,
                                      Post.publish_status.in_(("scheduled", "held"))).all():
        if not post.publish_at:
            continue
        try:
            at = datetime.fromisoformat(str(post.publish_at))
        except ValueError:
            continue
        post.publish_at = (at + delta).isoformat(timespec="seconds")
        n += 1
    db.commit()
    return n


async def resume(db, boost: Boost, *, by: str = "agent", override_pending: bool = False) -> Dict[str, Any]:
    """Turn it back on: the ad runs again, the paused days are given back, the website's banner goes."""
    if boost.paused_at is None:
        return {"status": "not_paused"}
    if (boost.listing_status or "") == "sold":
        return {"status": "sold", "message": "A sold home can't be turned back on. A new listing is a new campaign."}
    paused = _aware(boost.paused_at)
    delta = _now() - paused
    days = max(0, delta.days)
    steps = await _ad(db, boost, "ACTIVE")
    boost.paused_days = int(boost.paused_days or 0) + days
    boost.paused_at = None
    reason, boost.paused_reason = boost.paused_reason, None
    if reason == "pending":
        boost.listing_status = "active"
    moved = shift_posts(db, boost, delta)
    end_time = await _extend_adset(db, boost)
    if end_time:
        steps.append({"adset_end_time": end_time})
    emails.forget(db, boost, "pending", "back")
    if override_pending:
        # The agent turned it back on while the sites still say Pending: don't pause it again for
        # that same Pending. A later For Sale, then Pending, is a new event.
        notes = dict(boost.listing_notes or {})
        notes["agent_override"] = "pending"
        boost.listing_notes = notes
    db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="campaign_resumed",
                 payload={"by": by, "days_added": days, "posts_moved": moved, "steps": steps, "was": reason}))
    db.commit()
    _site_changed(db, boost)
    return {"status": "resumed", "days_added": days, "posts_moved": moved, "steps": steps}


async def _extend_adset(db, boost: Boost) -> Optional[str]:
    ad = db.query(Ad).filter(Ad.boost_id == boost.id).first()
    if ad is None or not ad.meta_adset_id or not boost.go_live_date:
        return None
    try:
        from app.services.ad_build import schedule
        from app.services.ad_platforms import get_platform_client
        from app.services.launch import resolve_ad_account
        window = schedule(boost.go_live_date) or {}
        if not window:
            return None
        end_time = (datetime.fromisoformat(window["end_time"]) + timedelta(days=int(boost.paused_days or 0))).isoformat()
        owner = db.query(User).filter(User.id == boost.user_id).first()
        account = resolve_ad_account(boost, owner, db) if owner else None
        if account:
            client = get_platform_client(account)
            if hasattr(client, "update_object"):
                await client.update_object(ad.meta_adset_id, {"end_time": end_time})
        return end_time
    except Exception as exc:  # noqa: BLE001 - reported, never hidden
        log.info("adset end time not moved for %s: %s", boost.id, exc)
        return None


def _site_changed(db, boost: Boost) -> None:
    try:
        from app.services import listing_site
        site = listing_site.site_for(db, boost, adopt=False)
        if site is not None:
            listing_site.clear_cache(site.slug)
    except Exception:  # noqa: BLE001
        pass


def card_state(boost: Boost, now: Optional[datetime] = None) -> str:
    """What the campaign card says: Active, Paused, Paused · Pending, Completed · Sold, Completed · Pending, Completed."""
    status = (boost.listing_status or "").lower()
    if status == "sold":
        return "Completed · Sold"
    if (boost.listing_notes or {}).get("renewal_hold") == "declined":
        return "Renewal on hold: card declined"
    if is_over(boost, now):
        return "Completed · Pending" if status == "pending" else "Completed"
    if boost.paused_at is not None:
        return "Paused · Pending" if (boost.paused_reason == "pending" or status == "pending") else "Paused"
    return "Active" if boost.launched_at else ""


# ------------------------------------------------------------------ acting on what the listing says
async def on_status(db, boost: Boost, status: Optional[str], reads: List[lst.Read], why: str,
                    *, send: bool = True) -> str:
    """Pending or sold pauses everything at once, then tells the agent (pending only). Back on the
    market with the same listing agent: Run it until it sells picks up by itself; otherwise one email
    with Turn it back on. Never restarts spending without the agent unless they chose set and forget."""
    if status is None:
        return "no_change"
    before = (boost.listing_status or "").lower()
    kit = _kit(db, boost)
    over = is_over(boost)

    if status == lst.SOLD:
        if before == "sold":
            return "still_sold"
        if not over:
            await pause(db, boost, "sold", by="listing check")
        boost.listing_status, boost.paused_reason = "sold", ("sold" if boost.paused_at else boost.paused_reason)
        boost.until_sold = False          # sold ends Run it until it sells (Engine 8, section 5)
        db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="listing_sold",
                     payload={"why": why[:300]}))
        db.commit()
        _site_changed(db, boost)
        return "sold"                     # no email (Adam, 22 Nov)

    notes = dict(boost.listing_notes or {})
    if status != lst.PENDING and notes.get("agent_override"):
        notes.pop("agent_override", None)
        boost.listing_notes = notes
        db.commit()
    if status == lst.PENDING:
        if before == "pending":
            return "still_pending"
        if notes.get("agent_override") == "pending":
            return "agent_turned_it_back_on"
        if over:
            boost.listing_status = "pending"
            db.commit()
            return "pending_after_end"
        agent_paused = boost.paused_at is not None and boost.paused_reason == "agent"
        await pause(db, boost, "pending", by="listing check")
        db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="listing_pending",
                     payload={"why": why[:300]}))
        db.commit()
        if send and not agent_paused:
            emails.forget(db, boost, "back")
            emails.pending(db, boost)
        return "pending"

    if status == lst.ACTIVE and before == "pending":
        mine = lst.same_agent(reads, kit)
        if mine is not True:
            # Another agent has it, or it can't be confirmed: never prompt this agent to market it.
            db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="listing_back_other_agent",
                         payload={"same_agent": mine}))
            db.commit()
            return "back_not_same_agent"
        if over:
            end = ends_on(boost)
            if end and _now() - end <= timedelta(days=PENDING_WATCH_DAYS) and send:
                emails.back_on_market(db, boost, running=False, ended=True)
            return "back_after_end"
        if boost.until_sold and boost.paused_reason == "pending":
            await resume(db, boost, by="listing check")
            if send:
                emails.back_on_market(db, boost, running=True)
            return "back_resumed"
        if send:
            emails.back_on_market(db, boost, running=False)
        return "back_emailed"

    if status == lst.ACTIVE and before in ("", "unknown", "active", "offline"):
        if before != "active":
            boost.listing_status = "active"
            db.commit()
        return "active"
    return "no_change"


def due(db, now: Optional[datetime] = None) -> List[Boost]:
    """Every launched campaign that's running, or paused pending, or finished pending within 30 days."""
    now = now or _now()
    rows = db.query(Boost).filter(Boost.launched_at.isnot(None)).all()
    out = []
    for b in rows:
        status = (b.listing_status or "").lower()
        if status == "sold" or not lst.sources_for(b):
            continue
        if b.paused_at is not None and b.paused_reason == "agent" and status != "pending":
            out.append(b)               # still watched: a paused home can go pending too
            continue
        end = ends_on(b)
        if end is None or end > now:
            out.append(b)
        elif status == "pending" and now - end <= timedelta(days=PENDING_WATCH_DAYS):
            out.append(b)
    return out


async def check(db, boost: Boost, *, fetcher=None, ai=None, send: bool = True) -> Dict[str, Any]:
    """One campaign: read every source, decide, act, and keep the price on the website honest."""
    urls = lst.sources_for(boost)
    reads = []
    for url in urls:
        reads.append(await lst.read_source(url, boost.address, fetcher=fetcher, ai=ai))
        if reads[-1].clear() and reads[-1].layer == "known" and len(reads) >= 2:
            break                       # two sources read, one by its status field: enough
    status, why = lst.decide(reads)
    notes = dict(boost.listing_notes or {})
    now = _now()
    if any(r.clear() for r in reads):
        notes.pop("unreadable_since", None)
        notes.pop("unreadable_alerted", None)
    else:
        since = _aware(notes.get("unreadable_since")) or now
        notes["unreadable_since"] = since.isoformat()
        if now - since >= NO_READ_ALERT and not notes.get("unreadable_alerted"):
            _alert_team(boost, f"No source for {boost.address} could be read for a day. Still checking.")
            notes["unreadable_alerted"] = now.isoformat()
    boost.listing_notes = notes
    boost.listing_reads = lst.reads_to_json(reads)
    boost.listing_checked_at = now
    db.commit()
    action = await on_status(db, boost, status, reads, why, send=send)
    price = None
    try:
        from app.services import listing_site
        site = listing_site.site_for(db, boost, adopt=False)
        if site is not None and any(r.clear() for r in reads):
            price = listing_site.apply_price_readings(db, site, lst.prices(reads), send=send)
    except Exception as exc:  # noqa: BLE001 - the status matters more than the price
        log.info("price readings for %s failed: %s", boost.id, exc)
    return {"boost_id": boost.id, "status": status, "why": why, "action": action, "price": price,
            "reads": [{"source": r.source, "status": r.status, "layer": r.layer, "http": r.http} for r in reads]}


def _alert_team(boost: Boost, message: str) -> None:
    try:
        from app.services import listing_site, mail
        to = listing_site.team_email()
        if to:
            mail.send_email(to, f"Listing check: {boost.address}", message + f"\n\nCampaign {boost.id}.")
    except Exception:  # noqa: BLE001
        pass


def layout_changes(results: List[Dict[str, Any]]) -> List[str]:
    """A site whose known spot failed on every listing it served this hour has changed its layout."""
    by: Dict[str, List[str]] = {}
    for r in results:
        for read in r.get("reads") or []:
            if read["source"] in ("zillow", "redfin", "realtor", "trulia", "homes") and read["http"] == 200:
                by.setdefault(read["source"], []).append(read["layer"])
    return [site for site, layers in by.items() if len(layers) >= 3 and "known" not in layers]


async def sweep(db, *, limit: int = 200, fetcher=None, ai=None, send: bool = True) -> Dict[str, Any]:
    results = []
    for boost in due(db)[:limit]:
        try:
            results.append(await check(db, boost, fetcher=fetcher, ai=ai, send=send))
        except Exception as exc:  # noqa: BLE001 - one bad page never stops the rest
            db.rollback()
            results.append({"boost_id": boost.id, "error": str(exc)[:200]})
    changed = layout_changes(results)
    if changed:
        today = _now().strftime("%Y-%m-%d")
        seen = db.query(Event).filter(Event.event_type == "listing_layout_alert").order_by(Event.id.desc()).first()
        if not (seen and (seen.payload or {}).get("day") == today):
            _alert_team(Boost(address=", ".join(changed)),
                        "The usual status field stopped working on: " + ", ".join(changed)
                        + ". The standard spot, the AI and the other sources keep the checks running.")
            db.add(Event(event_type="listing_layout_alert", payload={"day": today, "sites": changed}))
            db.commit()
    count = lambda k: len([r for r in results if r.get("action") == k])
    return {"checked": len(results), "pending": count("pending"), "sold": count("sold"),
            "back": count("back_emailed") + count("back_resumed"), "layout_changed": changed, "details": results}


# ------------------------------------------------------------------ the agent's own posts (section 7.6)
PENDING_WORDS = re.compile(r"\b(under contract|pending|in escrow|contingent|accepted an offer|offer accepted)\b", re.I)
SOLD_WORDS = re.compile(r"\b(just sold|sold!|has sold|sold\b(?! out)|closed on|closing day|another one sold)", re.I)
PRICE_WORDS = re.compile(r"\b(price improve\w*|improved price|price (?:drop|reduc\w*|change\w*|adjust\w*)|new price|reduced)\b", re.I)


def about_this_home(text: str, boost: Boost, site_slug: str = "") -> bool:
    """A post counts only when it names this home: its street (number and name) or its link."""
    t = (text or "").lower()
    street = (boost.address or "").split(",")[0].lower().strip()
    m = re.match(r"(\d+)\s+(\w+)", street)
    if m and m.group(1) in t and m.group(2) in t:
        return True
    links = [u for u in [getattr(boost, "listing_url", None), site_slug and f"homes.resmara.com/{site_slug}"] if u]
    return any(u.lower().split("?")[0] in t for u in links)


async def _recent_posts(target, since: datetime) -> List[Dict[str, str]]:
    """New posts on the agent's business Page and Instagram since the last look."""
    import httpx
    from app.core.config import settings
    out: List[Dict[str, str]] = []
    async with httpx.AsyncClient(timeout=20) as client:
        if target.page_id and target.page_access_token:
            try:
                r = await client.get(f"{settings.graph_base}/{target.page_id}/posts", params={
                    "fields": "message,created_time,permalink_url", "since": int(since.timestamp()),
                    "limit": 25, "access_token": target.page_access_token})
                for p in (r.json().get("data") or []) if r.status_code == 200 else []:
                    out.append({"where": "Facebook", "text": p.get("message") or "", "link": p.get("permalink_url") or ""})
            except Exception as exc:  # noqa: BLE001
                log.info("page posts unreadable: %s", exc)
        if target.ig_user_id and target.access_token:
            try:
                r = await client.get(f"{settings.graph_base}/{target.ig_user_id}/media", params={
                    "fields": "caption,timestamp,permalink", "limit": 25, "access_token": target.access_token})
                for p in (r.json().get("data") or []) if r.status_code == 200 else []:
                    at = _aware(p.get("timestamp", "").replace("+0000", "+00:00"))
                    if at is None or at >= since:
                        out.append({"where": "Instagram", "text": p.get("caption") or "", "link": p.get("permalink") or ""})
            except Exception as exc:  # noqa: BLE001
                log.info("instagram posts unreadable: %s", exc)
    return out


async def own_posts(db, boost: Boost, *, posts: Optional[List[Dict[str, str]]] = None,
                    send: bool = True) -> Dict[str, Any]:
    """Once a day: "Under contract!" or "Just sold!" about THIS home pauses everything; "Price
    improved" takes the price off the website. It quotes the post it found; another home never counts.
    Resmara's own posts (they carry the website link) are skipped."""
    from app.services import listing_site
    site = listing_site.site_for(db, boost, adopt=False)
    notes = dict(boost.listing_notes or {})
    since = _aware(notes.get("own_posts_at")) or (_now() - timedelta(days=2))
    if posts is None:
        from app.services import meta_engine
        target = meta_engine.publish_target(db, boost)
        posts = await _recent_posts(target, since) if target is not None else []
    notes["own_posts_at"] = _now().isoformat()
    boost.listing_notes = notes
    db.commit()
    found = []
    for p in posts:
        text = p.get("text") or ""
        if "homes.resmara.com" in text or not about_this_home(text, boost, site.slug if site else ""):
            continue
        quote = text.strip().replace("\n", " ")[:200]
        if PENDING_WORDS.search(text):
            r = lst.Read(source="own_" + p.get("where", "post").lower(), url=p.get("link", ""), status=lst.PENDING,
                         layer="known", quote=quote)
            found.append({"kind": "pending", "quote": quote, "where": p.get("where")})
            await on_status(db, boost, lst.PENDING, [r], f"your post on {p.get('where')}: {quote}", send=send)
        elif SOLD_WORDS.search(text):
            r = lst.Read(source="own_" + p.get("where", "post").lower(), url=p.get("link", ""), status=lst.SOLD,
                         layer="known", quote=quote)
            found.append({"kind": "sold", "quote": quote, "where": p.get("where")})
            await on_status(db, boost, lst.SOLD, [r], f"your post on {p.get('where')}: {quote}", send=send)
        elif PRICE_WORDS.search(text) and site is not None:
            found.append({"kind": "price", "quote": quote, "where": p.get("where")})
            listing_site.suspect_price_change(
                db, site, f"your post on {p.get('where')} says the price on this home has improved", send=send, boost=boost)
    if found:
        db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="own_posts_read", payload={"found": found}))
        db.commit()
    return {"boost_id": boost.id, "found": found}


async def own_posts_sweep(db, *, send: bool = True) -> Dict[str, Any]:
    out = []
    for boost in due(db):
        if (boost.listing_status or "") == "sold":
            continue
        try:
            out.append(await own_posts(db, boost, send=send))
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            out.append({"boost_id": boost.id, "error": str(exc)[:200]})
    return {"checked": len(out), "found": sum(len(r.get("found") or []) for r in out)}
