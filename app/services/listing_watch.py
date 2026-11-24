"""The listing watcher (Ad Engine §5), now hourly and status-field based (Engine 6, section 7).

A campaign runs for fourteen days on a house that can sell on day three. When it does, the
agent is paying Meta to advertise a listing that is gone. This sweeper reads the listing link
once a day, records what it found, and stops delivery the moment the page says the property
is sold — then tells the agent, because they are the one who knows whether it closed.

It is deliberately a separate pass from the publisher: it spends nothing, it can be re-run at
any time, and a failed fetch is recorded as "unknown" rather than silently leaving a dead
campaign running.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.db.session import Ad, Boost, Event, User

log = logging.getLogger(__name__)

ACTIVE = "active"
PENDING = "pending"
SOLD = "sold"
CONTINGENT = "contingent"
OFFLINE = "offline"
UNKNOWN = "unknown"

SOLD_MARKERS = ("sold", "no longer available", "off market", "off-market")
PENDING_MARKERS = ("pending", "under contract", "contingent", "in contract")
ACTIVE_MARKERS = ("for sale", "listed", "active", "new listing")


def classify(status_code: int, html: str) -> str:
    """Meta-independent read of a listing page: sold, pending, active, offline or unknown."""
    if status_code == 0 or status_code >= 500:
        return UNKNOWN
    if status_code in (404, 410):
        return OFFLINE
    if status_code >= 400:
        return UNKNOWN
    body = (html or "").lower()
    # "sold" is the word that matters, but estate-agent pages keep "Sold STC" in a badge on
    # homes that are still being marketed; a page that also says "for sale" is treated as
    # active and the agent is asked, rather than silently killing a live campaign.
    if any(marker in body for marker in SOLD_MARKERS) and not any(
            marker in body for marker in ACTIVE_MARKERS):
        return SOLD
    if any(marker in body for marker in PENDING_MARKERS):
        return PENDING
    if any(marker in body for marker in ACTIVE_MARKERS):
        return ACTIVE
    return UNKNOWN


async def read_listing(url: str, *, timeout: int = 20) -> tuple:
    """``(status_code, html)``; status 0 means the page could not be reached at all."""
    if not url:
        return 0, ""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True,
                                     headers={"User-Agent": "Resmara listing watcher"}) as c:
            resp = await c.get(url)
        return resp.status_code, resp.text[:60000]
    except Exception as exc:  # noqa: BLE001 - an unreachable page is a recorded fact
        log.warning("listing %s unreachable: %s", url, exc)
        return 0, ""


async def _pause(boost: Boost, db: Session, reason: str) -> list:
    from app.services.ad_platforms import get_platform_client
    from app.services.launch import resolve_ad_account

    ad = db.query(Ad).filter(Ad.boost_id == boost.id).first()
    owner = db.query(User).filter(User.id == boost.user_id).first()
    account = resolve_ad_account(boost, owner, db) if owner else None
    if not ad or not account:
        return [{"error": "no live ad to pause"}]
    client = get_platform_client(account)
    steps = []
    for label, object_id in (("ad", ad.meta_ad_id), ("adset", ad.meta_adset_id),
                             ("campaign", ad.meta_campaign_id)):
        if not object_id or not hasattr(client, "update_object"):
            continue
        try:
            await client.update_object(object_id, {"status": "PAUSED"})
            steps.append({label: object_id, "ok": True})
        except Exception as exc:  # noqa: BLE001
            steps.append({label: object_id, "ok": False, "error": str(exc)[:200]})
    ad.status = "paused"
    boost.paused_at = datetime.now(timezone.utc)
    return steps


async def sweep(db: Session, *, limit: int = 200) -> dict:
    """Every hour (Engine 6, section 7): read each campaign's listing status across its sources and
    act on a clear Pending or Sold. The work lives in campaign_state / listing_status now; the
    word-matching above is kept only for callers that still ask for a quick classification."""
    from app.services import campaign_state
    return await campaign_state.sweep(db, limit=limit)
