"""The two public facts a browser needs before it can be measured.

Nothing here is secret: a GA4 measurement id (``G-XXXXXXX``) and a Clarity project id are printed
in the page source of every site that uses them. The reason they come from the server instead of
being pasted into the HTML is that a pasted id is a second copy that goes stale, and because the
console cannot then tell you whether tracking is on or off - the System page reads this endpoint.

Unset means the tag is simply not injected, and nothing else changes.
"""
from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter()


def _setting(name: str) -> str:
    """Both spellings, because every other secret on this service is RESMARA_-prefixed."""
    return (os.getenv(name) or os.getenv("RESMARA_" + name) or "").strip()


@router.get("/public/tags")
def tags() -> dict:
    return {
        "ga4": _setting("GA4_MEASUREMENT_ID"),
        "clarity": _setting("CLARITY_PROJECT_ID"),
        "meta_pixel": _setting("META_PIXEL_ID"),
    }
