"""Engine 5: the listing websites, served by the app (docs/engines/engine-5-brain.md, section 9).

    homes.resmara.com/<slug>          -> the page (the host middleware in main.py maps it to /l/<slug>)
    homes.resmara.com/photos/<file>   -> a photo, passed through from storage with a long cache
    /l/<slug>/share.jpg               -> the 1200x630 share card
    /api/public/listing/<slug>/visit|lead|call|text   -> what visitors do (no sign-in)
    /api/public/price/<token>         -> the two buttons in the price email (no sign-in, 7 days)
    /api/boosts/<id>/site             -> section 3 for the agent: link, preview, numbers
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import Asset, Boost, ListingSite, User, get_db
from app.services import listing_site as ls
from app.api.leads import _require_system_token

router = APIRouter()

# Spam: the hidden trap field, and a limit per visitor and per address (section 7).
_hits: Dict[str, deque] = defaultdict(deque)


def _limited(key: str, limit: int, window: int) -> bool:
    now = time.time()
    q = _hits[key]
    while q and q[0] < now - window:
        q.popleft()
    if len(q) >= limit:
        return True
    q.append(now)
    return False


def _ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return (fwd.split(",")[0].strip() if fwd else "") or (request.client.host if request.client else "")


def _site(db: Session, slug: str) -> Optional[ListingSite]:
    return db.query(ListingSite).filter(ListingSite.slug == (slug or "").strip().lower()).first()


def _page_headers(public: bool) -> Dict[str, str]:
    return {"Cache-Control": "public, max-age=60" if public else "private, no-store"}


# ------------------------------------------------------------------ the page
@router.get("/l/{slug}", include_in_schema=False)
def listing_page(slug: str, preview: str = "", db: Session = Depends(get_db)):
    site = _site(db, slug)
    boost = db.query(Boost).filter(Boost.id == site.boost_id).first() if site else None
    if site is None or boost is None:
        return HTMLResponse(ls.not_found_page(), status_code=404)
    if ls.state(boost, site) == "closed":
        return HTMLResponse(ls.not_found_page().replace("This home isn't here", "This page is no longer available")
                            .replace("The link may be mistyped, or the listing has been taken down.", ""),
                            status_code=410)
    is_preview = bool(preview) and ls.preview_ok(site, preview)
    if not is_preview and not ls.is_public(boost):
        return HTMLResponse(ls.not_found_page(), status_code=404)
    return HTMLResponse(ls.page(db, site, boost, preview=is_preview), headers=_page_headers(not is_preview))


@router.get("/l/{slug}/share.jpg", include_in_schema=False)
def share_image(slug: str, db: Session = Depends(get_db)):
    site = _site(db, slug)
    asset = db.query(Asset).filter(Asset.id == site.share_asset_id).first() if site and site.share_asset_id else None
    raw = ls._asset_bytes(asset) if asset is not None else None
    if not raw:
        raise HTTPException(status_code=404, detail="Not Found")
    return Response(content=raw, media_type="image/jpeg",
                    headers={"Cache-Control": "public, max-age=86400"})


@router.get("/photos/{filename}", include_in_schema=False)
def listing_photo(filename: str, w: int = 0, db: Session = Depends(get_db)):
    """The website asks for each photo here; the app reads it from storage (R2, the disk or the
    copy kept on its row) and sends it on with a long cache header. Sizes come from ?w=."""
    from app.services.thumbs import preview

    safe = os.path.basename(filename)
    cache_dir = os.path.join(settings.UPLOAD_DIR, ".thumbs")
    width = 0
    if w:
        width = 640 if w <= 640 else 1200 if w <= 1200 else 1800
        cached = os.path.join(cache_dir, f"{width}-{safe}")
        if os.path.isfile(cached):
            with open(cached, "rb") as fh:
                return Response(content=fh.read(), media_type="image/jpeg",
                                headers={"Cache-Control": "public, max-age=2592000, immutable"})
    asset = db.query(Asset).filter(Asset.filename == safe).first()
    if asset is None or (asset.kind or "photo") not in ("photo", "share"):
        raise HTTPException(status_code=404, detail="Not Found")
    raw = ls._asset_bytes(asset)
    if not raw:
        raise HTTPException(status_code=404, detail="Not Found")
    out = preview(raw, width) if width else None
    if out and width:
        try:
            os.makedirs(cache_dir, exist_ok=True)
            tmp = os.path.join(cache_dir, f"{width}-{safe}.part")
            with open(tmp, "wb") as fh:
                fh.write(out)
            os.replace(tmp, os.path.join(cache_dir, f"{width}-{safe}"))
        except OSError:
            pass
    return Response(content=out or raw, media_type="image/jpeg" if out else (asset.content_type or "image/jpeg"),
                    headers={"Cache-Control": "public, max-age=2592000, immutable"})


# ------------------------------------------------------------------ what visitors do
async def _body(request: Request) -> Dict[str, Any]:
    try:
        data = await request.json()
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001 - a beacon with no body still counts as nothing
        return {}


def _live_site(db: Session, slug: str) -> ListingSite:
    site = _site(db, slug)
    boost = db.query(Boost).filter(Boost.id == site.boost_id).first() if site else None
    if site is None or boost is None or not ls.is_public(boost):
        raise HTTPException(status_code=404, detail="Not Found")
    return site


@router.post("/api/public/listing/{slug}/visit", include_in_schema=False)
async def visit(slug: str, request: Request, db: Session = Depends(get_db)):
    site = _live_site(db, slug)
    body = await _body(request)
    if _limited("v:" + _ip(request), 120, 3600):
        return {"ok": True}
    return {"ok": True, "counted": ls.record_visit(db, site, str(body.get("visitor") or ""), str(body.get("source") or ""))}


@router.post("/api/public/listing/{slug}/lead", include_in_schema=False)
async def lead(slug: str, request: Request, db: Session = Depends(get_db)):
    site = _live_site(db, slug)
    body = await _body(request)
    if str(body.get("website") or "").strip():
        return {"ok": True}                      # the trap field: a bot filled it; say nothing
    ip = _ip(request)
    if _limited("l:" + ip, 5, 3600) or _limited("lv:" + str(body.get("visitor") or ip), 3, 86400):
        return JSONResponse({"ok": False, "detail": "Too many messages. Please call instead."}, status_code=429)
    row = ls.form_lead(db, site, body, str(body.get("visitor") or ""))
    if row is None:
        return JSONResponse({"ok": False, "detail": "Please add your name and a valid email."}, status_code=422)
    return {"ok": True}


async def _tap(slug: str, kind: str, request: Request, db: Session):
    site = _live_site(db, slug)
    body = await _body(request)
    if _limited(f"t:{kind}:" + _ip(request), 30, 3600):
        return {"ok": True}
    return {"ok": True, "counted": ls.tap_lead(db, site, kind, str(body.get("visitor") or _ip(request)),
                                               str(body.get("source") or "")) is not None}


@router.post("/api/public/listing/{slug}/call", include_in_schema=False)
async def call_tap(slug: str, request: Request, db: Session = Depends(get_db)):
    return await _tap(slug, "call", request, db)


@router.post("/api/public/listing/{slug}/text", include_in_schema=False)
async def text_tap(slug: str, request: Request, db: Session = Depends(get_db)):
    return await _tap(slug, "text", request, db)


# ------------------------------------------------------------------ the price email's buttons
def _price_page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{ls.esc(title)}</title><meta name="robots" content="noindex">
<style>body{{margin:0;font:17px/1.6 system-ui,sans-serif;color:#12354d;background:#e2f0f8;display:grid;place-items:center;min-height:100vh;padding:20px}}
.card{{background:#fff;border-radius:12px;padding:32px;max-width:440px;width:100%}}h1{{font-size:24px;margin:0 0 12px}}
label{{display:block;font-weight:600;margin:18px 0 6px}}input{{width:100%;box-sizing:border-box;font:18px system-ui;padding:12px;border:1px solid #c5d6e2;border-radius:8px}}
button{{margin-top:18px;width:100%;background:#d94c0d;color:#fff;border:0;border-radius:8px;padding:14px;font:600 17px system-ui;cursor:pointer}}</style></head>
<body><div class="card">{body}</div></body></html>""")


def _expired() -> HTMLResponse:
    return _price_page("This link has expired", "<h1>This link has expired</h1><p>Price links work for 7 days. "
                       "You can set the price any time from your campaign on Resmara.</p>")


@router.get("/api/public/price/{token}", include_in_schema=False)
def price_link(token: str, do: str = "set", db: Session = Depends(get_db)):
    site = ls.site_for_token(db, token)
    if site is None:
        return _expired()
    boost = db.query(Boost).filter(Boost.id == site.boost_id).first()
    street = ls.street_and_city(boost.address if boost else "")[0]
    first = ((site.brand or {}).get("agent") or "").split(" ")[0] or "your agent"
    if do == "none":
        ls.set_no_price(db, site)
        return _price_page("Got it", f"<h1>Got it. No price on this listing.</h1><p>The website for {ls.esc(street)} "
                           f"now says “Ask {ls.esc(first)} about pricing”, and Resmara won't show a price for it "
                           "or ask about it again.</p>")
    return _price_page("What's the right price?", f"""<h1>What's the right price?</h1><p>{ls.esc(street)}</p>
<form method="post" action="/api/public/price/{ls.esc(token)}"><label for="p">Current list price</label>
<input id="p" name="price" inputmode="numeric" placeholder="$845,000" required autofocus><button>Save</button></form>""")


@router.post("/api/public/price/{token}", include_in_schema=False)
async def price_save(token: str, request: Request, db: Session = Depends(get_db)):
    site = ls.site_for_token(db, token)
    if site is None:
        return _expired()
    form = await request.form()
    digits = "".join(ch for ch in str(form.get("price") or "").split(".")[0] if ch.isdigit())
    if not digits or not (10_000 <= int(digits) <= 100_000_000):
        return RedirectResponse(f"/api/public/price/{token}?do=set", status_code=303)
    ls.set_agent_price(db, site, int(digits) * 100)
    return _price_page("Saved", f"<h1>Saved.</h1><p>Your website now shows {ls.esc(ls.price_text(site.price_cents))}. "
                       "Posts that haven't gone out yet say “Improved price” (never a number).</p>")


# ------------------------------------------------------------------ section 3 for the agent
def _owned(db: Session, boost_id: int, user: User) -> Boost:
    boost = db.query(Boost).filter(Boost.id == boost_id).first()
    if boost is None or boost.user_id != user.id:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return boost


def site_out(db: Session, boost: Boost, site: Optional[ListingSite]) -> Dict[str, Any]:
    if site is None:
        return {"built": False}
    return {
        "built": True, "slug": site.slug, "url": ls.public_url(site), "status": ls.state(boost, site),
        "public": ls.is_public(boost),
        "preview_url": f"/l/{site.slug}?preview={ls.preview_token(site)}",
        "price": ls.price_text(site.price_cents), "price_mode": site.price_mode, "price_hold": site.price_hold,
        "please_check": [k for k in (site.content or {}).get("please_check") or []
                         if k not in ((site.content or {}).get("confirmed") or [])],
        "facts": (site.content or {}).get("facts") or {},
        "stats": ls.stats(db, site, boost.id), "checks": site.checks or [],
    }


@router.get("/api/boosts/{boost_id}/site")
def get_site(boost_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    boost = _owned(db, boost_id, user)
    return site_out(db, boost, ls.site_for(db, boost))


@router.post("/api/boosts/{boost_id}/site/build")
async def build_site(boost_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Builds the site for a campaign that was built before Engine 5 existed, or refreshes it
    ("Refresh my website": the brand snapshot and words are taken again)."""
    boost = _owned(db, boost_id, user)
    site = await ls.build(db, boost)
    return site_out(db, boost, site)


@router.post("/api/boosts/{boost_id}/site/confirm")
async def confirm_facts(boost_id: int, request: Request, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user)):
    """Review: the agent confirms (or corrects) a "please check" fact, or sets the price."""
    boost = _owned(db, boost_id, user)
    site = ls.site_for(db, boost)
    if site is None:
        raise HTTPException(status_code=404, detail="No website yet")
    body = await _body(request)
    content = dict(site.content or {})
    facts = dict(content.get("facts") or {})
    confirmed = set(content.get("confirmed") or [])
    for key, value in (body.get("facts") or {}).items():
        if key not in ls.FACT_KEYS:
            continue
        if value in (None, ""):
            facts.pop(key, None)
        else:
            facts[key] = value
        confirmed.add(key)
    for key in body.get("confirm") or []:
        if key in ls.FACT_KEYS:
            confirmed.add(key)
    content["facts"], content["confirmed"] = facts, sorted(confirmed)
    site.content = content
    if body.get("price") not in (None, ""):
        digits = "".join(ch for ch in str(body["price"]).split(".")[0] if ch.isdigit())
        if digits:
            ls.set_agent_price(db, site, int(digits) * 100)
    if body.get("no_price"):
        ls.set_no_price(db, site)
    ls.touch(db, site)
    return site_out(db, boost, site)


@router.post("/api/admin/sites/check", include_in_schema=False)
def daily_check(db: Session = Depends(get_db), _ok: None = Depends(_require_system_token)):
    """The clock's daily look at every live website."""
    return ls.daily_check(db)
