"""Free geocoding for the ad's listing radius (spec §4.4).

Meta's ad targeting needs either a city key from its own geo search or a latitude/longitude
pair, and Resmara has neither: nothing in the build up to now looked a listing address up.
OpenStreetMap's Nominatim is free and keyless, which matters because the whole product is
built to run without another paid account. Its usage policy asks for one request a second and
a real User-Agent, both honoured here, and a result is cached on the boost so a campaign is
geocoded once, not on every build.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import httpx

log = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "Resmara/1.0 (listing ad geo lookup; support@resmara.com)"

_last_call = 0.0


def _throttle() -> None:
    """Nominatim allows one call a second; stay under it rather than get blocked."""
    global _last_call
    wait = 1.1 - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


def geocode(address: str, *, timeout: int = 15) -> Optional[dict]:
    """``{latitude, longitude, display_name}`` for an address, or None.

    None is a normal answer (a rural address, a network blip): the caller keeps the campaign
    buildable and asks the agent to pin the listing instead of inventing coordinates.
    """
    address = (address or "").strip()
    if not address:
        return None
    _throttle()
    try:
        with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
            resp = client.get(NOMINATIM_URL, params={
                "q": address, "format": "jsonv2", "limit": 1, "addressdetails": 0,
            })
        if resp.status_code >= 400:
            log.warning("nominatim %s for %r", resp.status_code, address)
            return None
        rows = resp.json() or []
    except Exception as exc:  # noqa: BLE001 - geocoding must never break a build
        log.warning("geocode failed for %r: %s", address, exc)
        return None
    if not rows:
        return None
    row = rows[0]
    try:
        return {
            "latitude": float(row["lat"]),
            "longitude": float(row["lon"]),
            "display_name": row.get("display_name") or "",
        }
    except (KeyError, TypeError, ValueError):
        return None


def for_boost(boost, db=None) -> dict:
    """The geo block for a boost, cached in ``boost.property_facts['geo']``."""
    facts = getattr(boost, "property_facts", None)
    try:
        facts = dict(facts) if isinstance(facts, dict) else {}
    except Exception:  # noqa: BLE001 - a malformed column must not stop a build
        facts = {}
    cached = facts.get("geo")
    if isinstance(cached, dict) and cached.get("latitude") is not None:
        return cached
    found = geocode(getattr(boost, "address", "") or "")
    if not found:
        return {}
    facts["geo"] = found
    try:
        boost.property_facts = facts
        if db is not None:
            db.commit()
    except Exception as exc:  # noqa: BLE001
        log.warning("could not cache geo on boost %s: %s", getattr(boost, "id", "?"), exc)
    return found
