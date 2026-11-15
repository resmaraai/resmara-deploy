"""The brand engine: read the agent's own Page, then propose a kit (Brand Engine v1.0 §4).

The old flow asked the agent to type eight fields into a form and hoped they came back. The spec
says the kit is built automatically from what the Meta connection already knows, and the agent
confirms it. Two rules here make that safe:

  * **Facts come from Meta, proposals come from the model.** Name, category, about, phone, website
    and logo URL are read off the Page; voice, palette, typeface and tagline are suggestions and
    are returned as `proposed`, never merged silently into the saved brand.
  * **It says when it could not read.** A token without `pages_read_engagement` cannot see the
    Page; that is reported with Meta's own message instead of a blank kit that looks like a
    successful build.
"""

from __future__ import annotations

import logging
import os

import httpx

from app.services.design import brand_from_meta  # one implementation of the proposal step
from app.services.token_health import _base

log = logging.getLogger("resmara.brand_engine")

FIELDS = ("name,category,about,description,phone,website,location,picture{url}")


async def _get(path: str, params: dict, token: str) -> dict:
    url = f"{_base().rstrip('/')}/{path.lstrip('/')}"
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.get(url, params={**params, "access_token": token})
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        return {"ok": False, "reason": f"HTTP {resp.status_code} and not JSON"}
    if resp.status_code >= 400 or (isinstance(body, dict) and body.get("error")):
        err = (body.get("error") or {}) if isinstance(body, dict) else {}
        return {"ok": False, "status": resp.status_code,
                "reason": err.get("message") or f"HTTP {resp.status_code}"}
    return {"ok": True, "body": body}


async def read_page(token: str) -> dict:
    """The agent's first Page as Meta describes it, plus its business portfolio if there is one.

    ``/me/accounts`` is what a user token is allowed to list. An agent with no Page gets a reason
    that says so - "you have no Facebook Page" is a different problem from "the permission is
    missing", and the setup session depends on telling them apart.
    """
    listed = await _get("me/accounts", {"fields": "id,name,category,access_token", "limit": 25}, token)
    if not listed.get("ok"):
        return listed
    pages = (listed["body"].get("data") or [])
    if not pages:
        return {"ok": False, "reason": "This Facebook account has no Page yet - Resmara posts as a "
                                       "Page, so one is needed before a brand can be read."}
    # Prefer a Page we can actually read the fields from; the first with a name is the default.
    chosen = next((p for p in pages if p.get("name")), pages[0])
    page_token = chosen.get("access_token") or token
    detail = await _get(str(chosen.get("id")), {"fields": FIELDS}, page_token)
    if not detail.get("ok"):
        return {"ok": False, "reason": f"the Page was found but could not be read: {detail.get('reason')}",
                "page_id": chosen.get("id")}
    page = detail["body"]
    page.setdefault("name", chosen.get("name"))
    business = {}
    extra = await _get(str(chosen.get("id")), {"fields": "business{id,name}"}, page_token)
    if extra.get("ok"):
        business = extra["body"].get("business") or {}
    return {"ok": True, "page": page, "business": business, "page_id": chosen.get("id"),
            "pages": [{"id": p.get("id"), "name": p.get("name")} for p in pages]}
