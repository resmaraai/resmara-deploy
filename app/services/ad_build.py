"""The one Meta ad per campaign — built to the Digital Ad Engine spec v1.3 §4.

This module is the single place that turns a Boost + its plan into the Meta payload
tree. It exists separately from ``ad_platforms`` because that module's builder shipped
with settings that must never reach a customer's ad account again:

* a **daily** $50 budget (roughly $700 across 14 days),
* US-wide targeting,
* a creative with no image,
* copy read from the wrong keys (the plan writes ``primaryText``/``ctaButton``),
* Resmara's own site as the landing page,
* every object created PAUSED, waiting for a human.

The rules here are fixed in code and are not the model's to choose (§4.4): Special Ad
Category HOUSING, OUTCOME_TRAFFIC optimising for link clicks, a lifetime budget, a
listing-radius audience of at least 15 miles, Facebook + Instagram feed only, and a
start time on the agent's go-live date. Anything that had to be defaulted is listed in
``notes`` so the campaign page and the event log can say what happened.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.core.config import settings

# --- fixed rules (spec §4.4) ------------------------------------------------

SPECIAL_AD_CATEGORY = "HOUSING"
OBJECTIVE = "OUTCOME_TRAFFIC"
OPTIMIZATION_GOAL = "LINK_CLICKS"
BILLING_EVENT = "IMPRESSIONS"
# HOUSING ad sets are refused without a bid amount ("Bid Amount Required For The Bid
# Strategy Provided", subcode 1815857). LOWEST_COST_WITH_BID_CAP + bid_amount was the
# only pair Meta accepted when this was verified live, so it stays the default.
BID_STRATEGY_DEFAULT = "LOWEST_COST_WITH_BID_CAP"
BID_CAP_CENTS = 300
DEFAULT_BUDGET_USD = 50.0
MIN_RADIUS_MILES = 15
RUN_DAYS = 14
START_HOUR_LOCAL = 8
MAX_CARDS = 5

# Meta's minimum lifetime budget for a traffic campaign; used as the floor when an agent
# edits the number. The spec leaves the exact figure to be confirmed against the account
# (§12), so it is deliberately conservative.
MIN_LIFETIME_BUDGET_USD = 5.0


def cents(usd) -> int:
    return int(round(float(usd or 0) * 100))


def street_key(address: str) -> str:
    """Normalised street address: the listing's key across campaigns and re-runs.

    "1234 Elm Street" and "1234 Elm St" are the same house, so the type suffix is dropped
    from the end (only from the end — "Court Street" keeps its name) and the rest is
    lower-cased and single-spaced. This key is what the ad campaign name, the UTM tag and
    the listing history all match on.
    """
    raw = (address or "").strip().lower()
    if not raw:
        return ""
    street = raw.split(",")[0]
    suffixes = {"st", "street", "ave", "avenue", "rd", "road", "ln", "lane", "dr", "drive",
                "ct", "court", "blvd", "boulevard", "way", "pl", "place", "ter", "terrace",
                "cir", "circle", "hwy", "highway", "pkwy", "parkway", "trl", "trail"}
    tokens = [t for t in street.replace(".", " ").split() if t]
    while len(tokens) > 1 and tokens[-1] in suffixes:
        tokens.pop()
    return " ".join(tokens)


def campaign_name(boost, campaign_no: Optional[int] = None) -> str:
    """``<street> · Resmara · <campaign no.>`` so a re-run never collides (§4.1)."""
    base = street_key(getattr(boost, "address", "") or "") or "resmara"
    number = campaign_no
    if number is None:
        number = (getattr(boost, "repeat_round", None) or 0) + 1
    return f"{base} · Resmara · {number}"


def with_utm(url: str, listing: str, medium: str = "paid") -> str:
    """Every outbound link carries the campaign tag (§3)."""
    if not url:
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query.update({"utm_source": "resmara", "utm_medium": medium,
                  "utm_campaign": street_key(listing) or "listing"})
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _local_start(go_live) -> Optional[datetime]:
    """Go-live date at 08:00 local, as an aware datetime (Meta wants an ISO timestamp)."""
    if isinstance(go_live, datetime):
        day = go_live.date()
    elif go_live:
        try:
            day = datetime.strptime(str(go_live)[:10], "%Y-%m-%d").date()
        except ValueError:
            return None
    else:
        return None
    return datetime(day.year, day.month, day.day, START_HOUR_LOCAL, tzinfo=datetime.now().astimezone().tzinfo)


def schedule(go_live) -> dict:
    """``{start_time, end_time}`` for a 14-day run, or ``{}`` when the date is unusable."""
    start = _local_start(go_live)
    if not start:
        return {}
    end = start + timedelta(days=RUN_DAYS)
    return {"start_time": start.isoformat(), "end_time": end.isoformat()}


def clamp_budget(usd) -> float:
    try:
        value = float(usd)
    except (TypeError, ValueError):
        value = DEFAULT_BUDGET_USD
    return max(MIN_LIFETIME_BUDGET_USD, round(value, 2))


def radius_targeting(geo: Optional[dict]) -> tuple:
    """Turn whatever the plan knows into Meta targeting, or say what is missing.

    ``geo`` may carry ``city_key`` (from Meta's geo search), ``latitude``/``longitude``,
    or nothing. Only the listing's own area is ever targeted: no countries, no ZIPs, no
    interests, no lookalikes, no age or gender narrowing (§4.4, §10).
    """
    notes = []
    geo = geo or {}
    city_key = str(geo.get("city_key") or "").strip()
    lat, lon = geo.get("latitude"), geo.get("longitude")
    radius = max(MIN_RADIUS_MILES, int(geo.get("radius_miles") or MIN_RADIUS_MILES))
    if city_key:
        locations = {"cities": [{"key": city_key, "radius": radius, "distance_unit": "mile"}]}
        notes.append(f"targeting: city key {city_key}, {radius} mile radius")
    elif lat is not None and lon is not None:
        locations = {"custom_locations": [{
            "latitude": float(lat), "longitude": float(lon),
            "radius": radius, "distance_unit": "mile",
        }]}
        notes.append(f"targeting: listing coordinates, {radius} mile radius")
    else:
        locations = {}
        notes.append("targeting: no city key or coordinates yet — the ad cannot be built "
                     "until the listing's location is known")
    return locations, notes


def build_ad_configs(
    boost,
    plan: Optional[dict] = None,
    *,
    page_id: str = "",
    ig_user_id: str = "",
    budget_usd=None,
    cards: Optional[list] = None,
    video: Optional[dict] = None,
    destination: Optional[str] = None,
    go_live=None,
    geo: Optional[dict] = None,
    campaign_no: Optional[int] = None,
    status: str = "ACTIVE",
    bid_strategy: Optional[str] = None,
) -> dict:
    """Build ``{campaign, adset, adcreative, ad, notes, format}``.

    ``cards`` are already-uploaded images: ``[{"image_hash", "title"?, "link"?}]``.
    ``video`` is ``{"video_id": ..., "thumbnail_url": ...}`` when the listing has one.
    With neither, the call still returns a tree but lists the reason in ``notes`` and the
    creative is left without media — callers must treat that as a failure, never ship it.
    """
    notes: list[str] = []
    plan = plan if plan is not None else (getattr(boost, "plan", None) or {})
    ad = {}
    if isinstance(plan, dict) and isinstance(plan.get("ad"), dict):
        ad = dict(plan["ad"])
    elif isinstance(getattr(boost, "ad_brief", None), dict) and boost.ad_brief:
        ad = dict(boost.ad_brief)
        notes.append("copy came from the boost's ad_brief (no plan.ad block)")

    name = campaign_name(boost, campaign_no)

    # --- budget: lifetime, not daily (§2.2 first row) ----------------------
    if budget_usd is None:
        budget_usd = getattr(boost, "ad_budget_usd", None)
    budget = clamp_budget(budget_usd if budget_usd is not None else DEFAULT_BUDGET_USD)
    lifetime_cents = cents(budget)
    notes.append(f"budget: lifetime {budget:.2f} USD for the whole {RUN_DAYS} days")

    # --- schedule ----------------------------------------------------------
    window = schedule(go_live if go_live is not None else getattr(boost, "go_live_date", None))
    if window:
        notes.append(f"schedule: {window['start_time']} → {window['end_time']}")
    else:
        notes.append("schedule: no go-live date yet — start/end times missing")

    bid = (bid_strategy or ad.get("bid_strategy") or BID_STRATEGY_DEFAULT).upper()
    bid_amount = int(ad.get("bid_amount") or BID_CAP_CENTS)

    campaign = {
        "name": name,
        "objective": OBJECTIVE,
        "status": status,
        "special_ad_categories": [SPECIAL_AD_CATEGORY],
        "lifetime_budget": lifetime_cents,
        "bid_strategy": bid,
        # A cap is required for HOUSING; with CBO it belongs on the campaign, and sending it
        # on the ad set too is refused ("Can't Set Ad Set and Campaign Budget", 1885621).
        "bid_amount": bid_amount,
    }

    # --- ad set ------------------------------------------------------------
    locations, geo_notes = radius_targeting(geo)
    notes.extend(geo_notes)
    targeting = {}
    if locations:
        targeting["geo_locations"] = locations
    # Housing defaults: everyone 18+, no gender split, no interests, no ZIP, no lookalikes.
    targeting["age_min"] = 18
    targeting["age_max"] = 65
    targeting["publisher_platforms"] = ["facebook", "instagram"]
    targeting["facebook_positions"] = ["feed"]
    targeting["instagram_positions"] = ["stream"]
    targeting["device_platforms"] = ["mobile", "desktop"]

    adset = {
        "name": f"{name} · Ad set",
        "campaign_id": None,          # filled by MetaAdsClient.create_campaign
        "billing_event": BILLING_EVENT,
        "optimization_goal": OPTIMIZATION_GOAL,
        "targeting": targeting,
        "status": status,
    }
    adset.update(window)

    # --- creative ----------------------------------------------------------
    resolved_page = page_id or ad.get("page_id") or settings.META_PAGE_ID or ""
    if not resolved_page:
        notes.append("creative: no Facebook Page on the ad account — the ad cannot be built")
    instagram = ig_user_id or settings.META_IG_ID or ""

    link = destination or getattr(boost, "destination_url", None) or ad.get("link") \
        or ad.get("landing_page_url") or getattr(boost, "listing_url", None) or ""
    if link:
        link = with_utm(link, getattr(boost, "address", "") or "")
    else:
        notes.append("creative: no destination URL — neither the launch details nor the "
                     "listing link is set")

    primary = ad.get("primaryText") or ad.get("primary_text") or ad.get("message") or ""
    headline = ad.get("headline") or ad.get("title") or ""
    description = ad.get("description") or ""
    if not primary:
        notes.append("copy: primaryText is empty on the plan")
    if not headline:
        headline = getattr(boost, "address", "") or ""
        notes.append("copy: headline defaulted to the street address")
    cta = str(ad.get("ctaButton") or ad.get("cta_button") or ad.get("cta") or "Learn more")
    cta_type = cta.strip().replace(" ", "_").upper()
    if cta_type not in ("LEARN_MORE", "SHOP_NOW", "SIGN_UP", "CONTACT_US", "MESSAGE_PAGE",
                        "BOOK_NOW", "CALL_NOW", "GET_QUOTE", "SUBSCRIBE", "DOWNLOAD"):
        cta_type = "LEARN_MORE"

    cards = [c for c in (cards or []) if isinstance(c, dict) and c.get("image_hash")][:MAX_CARDS]
    story_spec = {"page_id": resolved_page}

    if video and video.get("video_id"):
        fmt = "video"
        video_data = {
            "video_id": video["video_id"],
            "message": primary,
            "title": headline,
            "link_description": description,
            "call_to_action": {"type": cta_type, "value": {"link": link}},
        }
        if video.get("thumbnail_url"):
            video_data["image_url"] = video["thumbnail_url"]
        story_spec["video_data"] = video_data
        notes.append(f"creative: single video ad (video {video['video_id']})")
    elif cards:
        fmt = "carousel"
        children = []
        for card in cards:
            child = {"link": card.get("link") or link, "image_hash": card["image_hash"]}
            title = card.get("title") or headline
            if title:
                child["name"] = str(title)[:40]
            children.append(child)
        story_spec["link_data"] = {
            "link": link,
            "message": primary,
            "name": headline[:40],
            "description": description[:30],
            "call_to_action": {"type": cta_type},
            "child_attachments": children,
            "multi_share_end_card": False,
        }
        notes.append(f"creative: carousel of {len(children)} designed post(s)")
    else:
        fmt = "none"
        story_spec["link_data"] = {
            "link": link,
            "message": primary,
            "name": headline[:40],
            "description": description[:30],
            "call_to_action": {"type": cta_type},
        }
        notes.append("creative: NO MEDIA — no image hash and no video id, so this ad must "
                     "not be created")

    creative = {"name": f"{name} · Creative", "object_story_spec": story_spec}
    if instagram:
        creative["instagram_actor_id"] = instagram
    else:
        notes.append("creative: no Instagram account — the ad runs on Facebook only")

    ad_payload = {"name": f"{name} · Ad", "status": status}

    return {
        "campaign": campaign,
        "adset": adset,
        "adcreative": creative,
        "ad": ad_payload,
        "notes": notes,
        "format": fmt,
    }
