"""Engine 5: the listing website. One page per home at homes.resmara.com/<slug>.

Nothing is deployed per listing (docs/engines/engine-5-brain.md, section 9). The campaign build
saves a site record (`listing_sites`), and one route draws the page from it with the one template
below. The dashboard preview is the same page in a frame, so the preview and the real page can't
drift apart.

What lives here:
  * the slug (code, never the AI; it never changes)
  * build(): the words and chapters (the AI, checked), the facts, the photos, the brand snapshot,
    the share image, the checks
  * render(): the finished HTML (title and share card included, for Facebook and iMessage)
  * the page's state: built, live, pending, sold, ended (and 30 days after the end, the agent card)
  * visits and leads (form, call taps, text taps)
  * the price rules of section 3a
"""
from __future__ import annotations

import hashlib
import hmac
import html
import io
import json
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import quote

from app.core.config import settings
from app.db.session import Asset, Boost, Event, Lead, ListingSite, ListingVisit, User

log = logging.getLogger(__name__)

HOST = "homes.resmara.com"
ENDED_GRACE_DAYS = 30
PRICE_LINK_DAYS = 7
GALLERY = 8
CHAPTERS = 4

_cache: Dict[str, tuple] = {}   # slug -> (version, status, html)


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


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


# ------------------------------------------------------------------ the address (section 9)
def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def street_and_city(address: str) -> tuple:
    parts = [p.strip() for p in (address or "").split(",") if p.strip()]
    street = parts[0] if parts else (address or "listing")
    city = parts[1] if len(parts) > 1 else ""
    return street, city


def make_slug(db, address: str, boost_id: Optional[int] = None) -> str:
    """`1248 Oakridge Drive, Austin` -> `1248-oakridge-drive`; on a clash `-austin`, then `-2`, `-3`."""
    street, city = street_and_city(address)
    base = _slugify(street) or "listing"

    def free(slug: str) -> bool:
        row = db.query(ListingSite).filter(ListingSite.slug == slug).first()
        return row is None or (boost_id is not None and row.boost_id == boost_id)

    if free(base):
        return base
    with_city = f"{base}-{_slugify(city)}" if _slugify(city) else base
    if with_city != base and free(with_city):
        return with_city
    n = 2
    while not free(f"{with_city}-{n}"):
        n += 1
    return f"{with_city}-{n}"


def public_url(site_or_slug) -> str:
    slug = site_or_slug if isinstance(site_or_slug, str) else site_or_slug.slug
    base = (getattr(settings, "LISTING_SITE_BASE", "") or f"https://{HOST}").rstrip("/")
    return f"{base}/{slug}"


def tracked_url(site, content: str, medium: str = "social") -> str:
    """The link a post or the ad carries: the report knows which one brought each visitor."""
    return f"{public_url(site)}?utm_source=resmara&utm_medium={quote(medium)}&utm_content={quote(content)}"


# ------------------------------------------------------------------ finding the site
def parent_site(db, boost: Boost) -> Optional[ListingSite]:
    """The site an earlier round of this home owns, if any."""
    seen = {boost.id}
    parent_id = getattr(boost, "parent_boost_id", None)
    while parent_id and parent_id not in seen:
        seen.add(parent_id)
        site = db.query(ListingSite).filter(ListingSite.boost_id == parent_id).first()
        if site is not None:
            return site
        parent = db.query(Boost).filter(Boost.id == parent_id).first()
        parent_id = getattr(parent, "parent_boost_id", None) if parent else None
    return None


def site_for(db, boost: Boost, adopt: bool = True) -> Optional[ListingSite]:
    """This campaign's site. A new round takes over its parent's site once it's paid for, so every
    link already shared keeps working (section 9). Until then the running round keeps it."""
    site = db.query(ListingSite).filter(ListingSite.boost_id == boost.id).first()
    if site is not None or not adopt:
        return site
    if getattr(boost, "parent_boost_id", None) and not getattr(boost, "paid_at", None):
        return None
    seen = {boost.id}
    parent_id = getattr(boost, "parent_boost_id", None)
    while parent_id and parent_id not in seen:
        seen.add(parent_id)
        site = db.query(ListingSite).filter(ListingSite.boost_id == parent_id).first()
        if site is not None:
            site.boost_id = boost.id
            db.commit()
            clear_cache(site.slug)
            return site
        parent = db.query(Boost).filter(Boost.id == parent_id).first()
        parent_id = getattr(parent, "parent_boost_id", None) if parent else None
    return None


def clear_cache(slug: Optional[str] = None) -> None:
    if slug is None:
        _cache.clear()
    else:
        _cache.pop(slug, None)


def touch(db, site: ListingSite) -> None:
    """Something on the page changed: the version goes up and the cached page is dropped."""
    site.version = int(site.version or 1) + 1
    site.updated_at = _now()
    db.commit()
    clear_cache(site.slug)


# ------------------------------------------------------------------ what the page is made of
def _kit(db, boost: Boost) -> Dict[str, Any]:
    owner = db.query(User).filter(User.id == boost.user_id).first()
    kit = dict((getattr(owner, "brand", None) or {}) if owner else {})
    if owner is not None:
        kit.setdefault("agent", getattr(owner, "name", "") or "")
        kit.setdefault("email", getattr(owner, "email", "") or "")
    return kit


def brand_snapshot(kit: Dict[str, Any]) -> Dict[str, Any]:
    """The brand kit as the page uses it (section 4's table), frozen on the site record."""
    colours = {name: hexv for name, hexv in (kit.get("palette") or []) if isinstance(name, str)}
    fonts = [f for f in (kit.get("fonts") or []) if f][:2] or ["Playfair Display", "Jost"]
    if len(fonts) == 1:
        fonts.append(fonts[0])
    lines = kit.get("legal")
    if not lines:
        from app.services.brand_investigator import legal_lines
        lines = legal_lines(kit)
    legal = [l for l in (lines or []) if l and not re.search(r"equal housing", l, re.I)]
    return {
        "agent": kit.get("agent") or "", "brokerage": kit.get("company") or kit.get("brokerage") or "",
        "license": kit.get("license") or "", "phone": kit.get("phone") or "", "email": kit.get("email") or "",
        "logo": kit.get("logoUrl") or kit.get("logo") or "", "headshot": kit.get("headshotUrl") or kit.get("headshot") or "",
        "primary": colours.get("Primary") or "#12354d", "accent": colours.get("Accent") or "#d94c0d",
        "tint": colours.get("Tint") or "#eef3f7", "page": colours.get("Page") or "#ffffff",
        "text": colours.get("Text") or "#1c2733", "fonts": fonts, "legal": legal,
        "voice": kit.get("voiceOfClient") or kit.get("voice") or "",
    }


def _photos(db, boost: Boost) -> List[Asset]:
    rows = (db.query(Asset).filter(Asset.boost_id == boost.id, Asset.kind == "photo")
            .order_by(Asset.id.asc()).all())
    return [a for a in rows if a.filename]


def photo_url(filename: str, width: int = 0) -> str:
    """Photos load through the app (decided with Adam): homes.resmara.com/photos/<file>."""
    return f"/photos/{quote(filename)}" + (f"?w={width}" if width else "")


def _hero_order(photos: List[Asset], plan: Dict[str, Any]) -> List[Asset]:
    """Exteriors first for the hero, then the order the plan used them, then the rest."""
    used = []
    for p in (plan.get("posts") or []):
        if isinstance(p, dict) and p.get("photoFile"):
            used.append(str(p["photoFile"]))
    rank = {name: i for i, name in enumerate(used)}

    def key(a: Asset):
        room = (a.room or "").lower()
        exterior = 0 if ("exterior" in room or "front" in room or "aerial" in room) else 1
        return (exterior, rank.get(a.filename, 999), a.id)
    return sorted(photos, key=key)


FACT_KEYS = ("beds", "baths", "sqft", "lot", "year_built", "garage", "city")

WRITER_SYSTEM = """You write the one-page website for a home that is for sale, as the listing agent.
The website tells the story of the home in one place, like a walk through the house, not a spec
sheet. Use only what the HOME FILE, the CAMPAIGN STORY and the PHOTO INDEX say: every sentence must
be backed by them. Never invent a feature. Fair Housing: never describe the people who live nearby,
schools as good or bad, safety, crime, churches, or who the home is "perfect for"; describe the
property only. Never mention the price or any dollar amount. Write in the agent's voice.

Return ONLY a JSON object:
{
 "facts": {"beds": number or null, "baths": number or null, "sqft": number or null,
           "lot": "text like 1.2 acres" or null, "year_built": number or null,
           "garage": "text like 2-car" or null, "city": "City, ST ZIP" or null},
 "please_check": ["fact keys that came only from public research and the agent should confirm"],
 "headline": "a headline for the home, under 70 characters",
 "chapters": [{"title": "short", "text": "one paragraph, 2-4 sentences",
               "photos": ["file name from the PHOTO INDEX", "a second file name"]}],
 "note": "a short note from the agent to visitors, 1-2 sentences, first person",
 "neighborhood": [{"place": "downtown Austin", "minutes": 18}],
 "open_house": "text if the home file names an open house date and time, else null"
}
Write exactly 4 chapters, each a moment in this house (for example the arrival, the heart of the
house, the evenings, the mornings; other homes get other chapters). Each chapter uses 2 photos that
show what it describes, never a photo twice. Include neighborhood drive times ONLY when the home
file gives them; otherwise return an empty list."""


def _photo_index(photos: List[Asset]) -> str:
    rows = []
    for a in photos[:60]:
        rows.append(" | ".join(x for x in [a.filename, a.room or "", (a.see or "")[:140]] if x))
    return " ;; ".join(rows) or "none"


def writer_input(boost: Boost, kit: Dict[str, Any], photos: List[Asset]) -> str:
    plan = boost.plan if isinstance(boost.plan, dict) else {}
    story = plan.get("propertyStory") if isinstance(plan.get("propertyStory"), dict) else {}
    hooks = ((plan.get("ad") or {}).get("hooks") or []) if isinstance(plan.get("ad"), dict) else []
    return "\n".join([
        f"ADDRESS: {boost.address}",
        f"AGENT: {kit.get('agent') or ''}",
        f"VOICE OF THE CLIENT: {(kit.get('voiceOfClient') or kit.get('voice') or 'warm, clear, professional')[:600]}",
        f"HOME FILE: {(boost.property_facts or '')[:6000]}",
        f"CAMPAIGN STORY: {json.dumps(story)[:2000]}",
        f"SUMMARY: {str(plan.get('summary') or '')[:600]}",
        f"STORY ARC: {str(plan.get('storyArc') or '')[:400]}",
        f"AD HIGHLIGHTS: {json.dumps([h.get('highlight') or h.get('hook') for h in hooks if isinstance(h, dict)])[:600]}",
        f"PHOTO INDEX (file | room | what is visible): {_photo_index(photos)}",
    ])


def offline_words(boost: Boost, photos: List[Asset]) -> Dict[str, Any]:
    """No AI available (tests, simulation): a plain, true page from what the plan already says."""
    plan = boost.plan if isinstance(boost.plan, dict) else {}
    story = plan.get("propertyStory") if isinstance(plan.get("propertyStory"), dict) else {}
    diffs = [str(d) for d in (story.get("differentiators") or []) if d][:CHAPTERS]
    names = [a.filename for a in photos]
    chapters = []
    for i, d in enumerate(diffs):
        pics = names[1 + i * 2: 3 + i * 2] or names[:1]
        chapters.append({"title": d.split(".")[0][:40], "text": d, "photos": pics})
    street, city = street_and_city(boost.address)
    return {"facts": {"city": city or None}, "please_check": [],
            "headline": str(story.get("thesis") or street)[:70], "chapters": chapters,
            "note": "", "neighborhood": [], "open_house": None}


async def _ai_words(boost: Boost, kit: Dict[str, Any], photos: List[Asset]) -> Dict[str, Any]:
    from app.services import llm
    if not llm.llm_available():
        return offline_words(boost, photos)
    return await llm.chat_json(WRITER_SYSTEM, writer_input(boost, kit, photos),
                               model=settings.OPENAI_MODEL_BRAND,
                               max_completion_tokens=3000, reasoning_effort="low")


def _number(value) -> Optional[float]:
    try:
        n = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return n if n > 0 else None


def clean_words(words: Dict[str, Any], photos: List[Asset]) -> tuple:
    """Check what the AI wrote (section 9, checks before it's ready). Returns (content, checks).

    Anything that fails is dropped rather than shown broken: a chapter with a Fair Housing problem
    or no real photo, a neighborhood line that isn't a place and a time."""
    from app.services.ad_rulebook import fair_housing_issues
    names = {a.filename for a in photos}
    checks: List[str] = []
    words = words if isinstance(words, dict) else {}

    raw = words.get("facts") if isinstance(words.get("facts"), dict) else {}
    facts: Dict[str, Any] = {}
    for key in ("beds", "baths", "sqft", "year_built"):
        n = _number(raw.get(key))
        if n is not None:
            facts[key] = int(n) if key != "baths" else (int(n) if n == int(n) else n)
    for key in ("lot", "garage", "city"):
        if raw.get(key) and str(raw[key]).strip().lower() not in ("null", "none", "n/a"):
            facts[key] = str(raw[key]).strip()[:60]
    please = [k for k in (words.get("please_check") or []) if k in facts]

    def ok(text: str, where: str) -> bool:
        issues = fair_housing_issues(text or "")
        if issues:
            checks.append(f"{where} left off: Fair Housing ({', '.join(issues)[:80]})")
            return False
        if re.search(r"\$\s?\d", text or ""):
            checks.append(f"{where} left off: it named a price")
            return False
        return True

    used: set = set()
    chapters = []
    for i, ch in enumerate(words.get("chapters") or []):
        if not isinstance(ch, dict) or not str(ch.get("text") or "").strip():
            continue
        title, text = str(ch.get("title") or "").strip()[:60], str(ch.get("text")).strip()[:900]
        if not ok(title + " " + text, f"Chapter {i + 1}"):
            continue
        pics = [p for p in (ch.get("photos") or []) if p in names and p not in used][:2]
        if not pics:
            spare = [a.filename for a in photos[1:] if a.filename not in used]
            pics = spare[:1]
            if pics:
                checks.append(f"Chapter {i + 1}: its photos weren't in the home's file, so another photo was used")
        if not pics:
            checks.append(f"Chapter {i + 1} left off: no photo for it")
            continue
        used.update(pics)
        chapters.append({"title": title, "text": text, "photos": pics})
        if len(chapters) == CHAPTERS:
            break

    headline = str(words.get("headline") or "").strip()[:90]
    if headline and not ok(headline, "The headline"):
        headline = ""
    note = str(words.get("note") or "").strip()[:400]
    if note and not ok(note, "The agent's note"):
        note = ""
    hood = []
    for row in words.get("neighborhood") or []:
        if not isinstance(row, dict):
            continue
        place, minutes = str(row.get("place") or "").strip()[:60], _number(row.get("minutes"))
        if place and minutes and minutes < 180 and ok(place, "A neighborhood line"):
            hood.append({"place": place, "minutes": int(minutes)})
    open_house = str(words.get("open_house") or "").strip()[:120]
    if open_house.lower() in ("null", "none"):
        open_house = ""
    return ({"facts": facts, "please_check": please, "headline": headline, "chapters": chapters,
             "note": note, "neighborhood": hood[:6], "open_house": open_house}, checks)


def visible_facts(content: Dict[str, Any], confirmed: Optional[List[str]] = None) -> Dict[str, Any]:
    """Facts marked "please check" are never shown until the agent confirms them in review."""
    confirmed = set(confirmed or content.get("confirmed") or [])
    hold = set(content.get("please_check") or []) - confirmed
    return {k: v for k, v in (content.get("facts") or {}).items() if k not in hold}


async def build(db, boost: Boost, *, writer: Optional[Callable] = None,
                share: bool = True) -> ListingSite:
    """Build (or refresh) the site in the same build as the campaign (section 5).

    The words are retried once; if they still fail, the page goes up with the facts, the photos and
    the agent card (a safe default), and the team is told. Never raises for want of words."""
    kit = _kit(db, boost)
    plan = boost.plan if isinstance(boost.plan, dict) else {}
    photos = _hero_order(_photos(db, boost), plan)
    checks: List[str] = []
    words: Dict[str, Any] = {}
    write = writer or _ai_words
    for attempt in (1, 2):
        try:
            words = await write(boost, kit, photos)
            break
        except Exception as exc:  # noqa: BLE001 - the page still goes up
            checks.append(f"The words didn't write (try {attempt}): {str(exc)[:120]}")
            words = {}
    content, more = clean_words(words, photos)
    checks += more
    if words and len(content["chapters"]) < len([c for c in (words.get("chapters") or []) if c]):
        checks.append(f"{len(content['chapters'])} of {len(words.get('chapters') or [])} chapters kept")
    if not words:
        content = clean_words(offline_words(boost, photos), photos)[0]
        _alert_team(db, boost, "The listing website's words couldn't be written; it went up with the plan's story.")
    content["photos"] = [a.filename for a in photos]
    content["rooms"] = {a.filename: (a.room or "") for a in photos}
    video = (getattr(boost, "video_url", None) or "").strip()
    content["video"] = video if re.search(r"\.(mp4|webm|mov)(\?|$)", video, re.I) or video.startswith("/uploads/") else ""

    site = site_for(db, boost)
    if site is None and getattr(boost, "parent_boost_id", None) and not getattr(boost, "paid_at", None):
        earlier = parent_site(db, boost)
        if earlier is not None:
            # A renewal built ahead: the running round keeps the page until this one is paid for;
            # promote() swaps the new story in then.
            nxt = dict(earlier.content or {})
            nxt["next_round"] = {"boost_id": boost.id, "content": content, "brand": brand_snapshot(kit), "checks": checks}
            earlier.content = nxt
            db.commit()
            boost.destination_url = public_url(earlier)
            db.commit()
            return earlier
    if site is None:
        site = ListingSite(boost_id=boost.id, user_id=boost.user_id,
                           slug=make_slug(db, boost.address, boost.id), version=0)
        db.add(site)
    old = dict(site.content or {})
    if old.get("confirmed"):
        content["confirmed"] = old["confirmed"]
    content.pop("next_round", None)
    site.content = content
    site.brand = brand_snapshot(kit)
    site.checks = checks
    site.status = state(boost, site)
    db.commit()
    if share:
        try:
            make_share_image(db, site, boost)
        except Exception as exc:  # noqa: BLE001 - the page works without its picture
            site.checks = list(site.checks or []) + [f"Share image not made: {str(exc)[:100]}"]
    # Every post and the ad link here (section 6): the ad's destination is this page.
    boost.destination_url = public_url(site)
    touch(db, site)
    db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="listing_site_built",
                 payload={"slug": site.slug, "chapters": len(content["chapters"]), "checks": checks[:10]}))
    db.commit()
    return site


def team_email() -> str:
    owners = [a.strip() for a in (getattr(settings, "ADMIN_EMAILS", "") or "").split(",") if a.strip()]
    return owners[0] if owners else ""


def promote(db, boost: Boost) -> Optional[ListingSite]:
    """The new round is paid for: it takes over the page (same slug) with its own story."""
    site = site_for(db, boost)
    if site is None:
        return None
    content = dict(site.content or {})
    nxt = content.pop("next_round", None)
    if nxt and nxt.get("boost_id") == boost.id:
        confirmed = content.get("confirmed")
        content = dict(nxt.get("content") or {})
        if confirmed:
            content["confirmed"] = confirmed
        site.brand = nxt.get("brand") or site.brand
        site.checks = nxt.get("checks") or []
    site.content = content
    site.boost_id = boost.id
    site.status = state(boost, site)
    touch(db, site)
    return site


def _alert_team(db, boost: Boost, message: str) -> None:
    try:
        from app.services import mail
        to = team_email()
        if to:
            mail.send_email(to, f"Listing website: {boost.address}", message + f"\n\nCampaign {boost.id}.")
    except Exception:  # noqa: BLE001
        log.info("listing site alert not sent for %s", boost.id)


# ------------------------------------------------------------------ state (section 5)
def ends_on(boost: Boost) -> Optional[datetime]:
    """The last day of this round: its go-live date (else launch) + its days + any paused days."""
    from app.services.renewals import round_ends_on
    return _aware(round_ends_on(boost))


def state(boost: Boost, site: Optional[ListingSite] = None, now: Optional[datetime] = None) -> str:
    """built (locked) | live | pending | sold | ended | gone (30 days after the end: the agent card)."""
    now = now or _now()
    if not getattr(boost, "paid_at", None):
        return "built"
    status = (getattr(boost, "listing_status", None) or "").lower()
    end = ends_on(boost)
    finished = (boost.stage or "").upper() == "COMPLETE" or (end is not None and end <= now)
    if finished and not getattr(boost, "until_sold", False) or status == "sold":
        ended = _aware(getattr(site, "ended_at", None)) or end or now
        if ended + timedelta(days=ENDED_GRACE_DAYS) <= now:
            return "gone"
        return "sold" if status == "sold" else "ended"
    if status in ("pending", "contingent"):
        return "pending"
    return "live"


def is_public(boost: Boost) -> bool:
    """The link works once the campaign is unlocked (section 5)."""
    return bool(getattr(boost, "paid_at", None))


# ------------------------------------------------------------------ price (section 3a)
def price_text(cents: Optional[int]) -> str:
    return f"${cents // 100:,}" if cents else ""


def apply_price_readings(db, site: ListingSite, readings: Dict[str, Optional[int]],
                         *, send: bool = True) -> str:
    """Readings by source, in cents (None = the source shows no price). Returns what happened.

    Shown only when every source that has a price agrees. A new number, or sources that disagree,
    takes the price off at once; when the new number can't be agreed, one email asks the agent."""
    if site.price_mode == "none":
        return "agent_chose_no_price"
    prices = {k: v for k, v in (readings or {}).items() if v}
    site.price_seen = {k: v for k, v in (readings or {}).items()}
    agreed = None
    if prices and len(set(prices.values())) == 1:
        agreed = next(iter(prices.values()))
    previous = site.price_cents
    if site.price_mode == "agent":
        # The agent set it. A source that now agrees with them hands it back to automatic.
        if agreed and agreed == previous:
            site.price_mode, site.price_hold = "auto", None
            db.commit()
            return "agrees_with_agent"
        if agreed and agreed != previous:
            return suspect_price_change(db, site, "the listing shows a different price", send=send)
        return "agent_price_kept"
    if agreed:
        changed = previous and agreed != previous
        site.price_cents, site.price_hold = agreed, None
        touch(db, site)
        return "price_changed" if changed else "price_shown"
    if prices:   # sources disagree
        return suspect_price_change(db, site, "the listing sites show different prices", send=send)
    if previous:
        site.price_cents, site.price_hold = None, "no price found online"
        touch(db, site)
        return "price_removed"
    return "no_price"


def suspect_price_change(db, site: ListingSite, why: str, *, send: bool = True,
                         boost: Optional[Boost] = None) -> str:
    """Something suggests the price changed and no new number can be agreed: off it comes, and one
    email per change asks the agent (Set a new price / Don't show a price)."""
    if site.price_mode == "none":
        return "agent_chose_no_price"
    already = site.price_hold is not None and site.price_cents is None
    site.price_cents, site.price_hold = None, why[:200]
    if site.price_mode == "agent":
        site.price_mode = "auto"
    touch(db, site)
    if already and site.price_email_at:
        return "price_held"
    if send:
        boost = boost or db.query(Boost).filter(Boost.id == site.boost_id).first()
        send_price_email(db, site, boost, why)
    return "price_held_email"


def new_price_token(db, site: ListingSite) -> str:
    site.price_token = secrets.token_urlsafe(24)
    site.price_token_at = _now()
    db.commit()
    return site.price_token


def site_for_token(db, token: str) -> Optional[ListingSite]:
    if not token:
        return None
    site = db.query(ListingSite).filter(ListingSite.price_token == token).first()
    if site is None or not site.price_token_at:
        return None
    if _aware(site.price_token_at) + timedelta(days=PRICE_LINK_DAYS) < _now():
        return None
    return site


def app_base() -> str:
    return (getattr(settings, "PUBLIC_BASE_URL", "") or "https://www.resmara.com").rstrip("/")


def send_price_email(db, site: ListingSite, boost: Boost, why: str) -> bool:
    from app.services import mail
    owner = db.query(User).filter(User.id == site.user_id).first()
    if owner is None or not owner.email:
        return False
    token = new_price_token(db, site)
    street = street_and_city(boost.address)[0] if boost else "your listing"
    first = (site.brand or {}).get("agent", "").split(" ")[0] or "there"
    body = (f"Hi {first},\n\nWe noticed a price change on {street}.\n\n"
            f"{why[:1].upper() + why[1:]}, but we can't find the new price online yet, so your website "
            f"isn't showing a price right now.\n\nWould you like us to update it?\n\n"
            f"Set a new price: {app_base()}/api/public/price/{token}?do=set\n"
            f"Don't show a price: {app_base()}/api/public/price/{token}?do=none\n\n"
            f"Both links work for 7 days and don't need you to sign in.\n\n- Resmara")
    ok = mail.send_email(owner.email, f"We noticed a price change on {street}", body)
    site.price_email_at = _now()
    db.add(Event(user_id=site.user_id, boost_id=site.boost_id, event_type="price_email",
                 payload={"sent": bool(ok), "why": why[:200]}))
    db.commit()
    return bool(ok)


def set_agent_price(db, site: ListingSite, cents: int) -> None:
    """The agent saved a new price: shown at once, and the posts still to go out are told (no numbers)."""
    previous = site.price_cents
    site.price_cents, site.price_mode, site.price_hold = int(cents), "agent", None
    touch(db, site)
    boost = db.query(Boost).filter(Boost.id == site.boost_id).first()
    if boost is not None:
        plan = dict(boost.plan or {})
        plan["price_update"] = {"at": _now().isoformat(), "words": "Improved price",
                                "lower": bool(previous and cents < previous)}
        boost.plan = plan
        db.commit()
        mark_price_posts(db, boost)


PRICE_WORDS = re.compile(r"\b(priced|price|pricing|offered at|listed at)\b", re.I)


def mark_price_posts(db, boost: Boost) -> int:
    """Posts not out yet that talk about pricing get the new wording ("Improved price", never a
    number, never "reduced"). The sentence about price is replaced; nothing else changes."""
    from app.db.session import Post
    n = 0
    rows = db.query(Post).filter(Post.boost_id == boost.id,
                                 Post.publish_status.in_(("scheduled", "held"))).all()
    for post in rows:
        for field in ("caption", "caption_ig"):
            text = getattr(post, field, None) or ""
            if not PRICE_WORDS.search(text):
                continue
            parts = re.split(r"(?<=[.!?])\s+", text)
            parts = ["Improved price." if PRICE_WORDS.search(p) and not p.startswith("#") else p for p in parts]
            setattr(post, field, " ".join(dict.fromkeys(parts)))
            n += 1
    db.commit()
    return n


def set_no_price(db, site: ListingSite) -> None:
    site.price_cents, site.price_mode, site.price_hold = None, "none", None
    touch(db, site)


# ------------------------------------------------------------------ visits and leads (section 7)
def record_visit(db, site: ListingSite, visitor: str, source: str = "") -> bool:
    visitor = re.sub(r"[^A-Za-z0-9_-]", "", visitor or "")[:64]
    if not visitor:
        return False
    day = _now().strftime("%Y-%m-%d")
    exists = db.query(ListingVisit).filter(ListingVisit.site_id == site.id, ListingVisit.visitor == visitor,
                                           ListingVisit.day == day).first()
    if exists:
        return False
    db.add(ListingVisit(site_id=site.id, visitor=visitor, day=day, source=(source or "")[:80] or None))
    try:
        db.commit()
    except Exception:  # noqa: BLE001 - a double tap raced the unique key
        db.rollback()
        return False
    return True


def source_label(db, boost_id: int, source: str) -> Optional[str]:
    """`ad` -> "Your ad"; `post-12` -> "Your day 3 post": which post or ad brought this lead."""
    source = (source or "").strip()
    if source == "ad" or source.startswith("ad-"):
        return "Your ad"
    m = re.fullmatch(r"post-(\d+)", source)
    if m:
        from app.db.session import Post
        post = db.query(Post).filter(Post.id == int(m.group(1)), Post.boost_id == boost_id).first()
        return f"Your day {post.day} post" if post is not None and post.day else "One of your posts"
    return None


def tap_lead(db, site: ListingSite, kind: str, visitor: str, source: str = "") -> Optional[Lead]:
    """A Call or Text tap: one lead per visitor per day, no email (section 7)."""
    if kind not in ("call", "text"):
        return None
    visitor = re.sub(r"[^A-Za-z0-9_-]", "", visitor or "")[:64] or "anon"
    since = _now() - timedelta(days=1)
    dup = db.query(Lead).filter(Lead.boost_id == site.boost_id, Lead.source == kind,
                                Lead.visitor == visitor, Lead.created_at >= since).first()
    if dup is not None:
        return None
    label = "Listing page call button" if kind == "call" else "Listing page text button"
    lead = Lead(boost_id=site.boost_id, user_id=site.user_id, platform="website", source=kind,
                channel=label, visitor=visitor, author_name=f"{'Call' if kind == 'call' else 'Text'} from your listing page",
                text=f"Tapped {'Call' if kind == 'call' else 'Text'} on your listing page.",
                post_label=source_label(db, site.boost_id, source), classified_by="website", status="new")
    db.add(lead)
    db.commit()
    return lead


def form_lead(db, site: ListingSite, body: Dict[str, Any], visitor: str = "") -> Optional[Lead]:
    """The form: stored on the campaign and emailed to the agent straight away."""
    name = str(body.get("name") or "").strip()[:120]
    email = str(body.get("email") or "").strip()[:160]
    if not name or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return None
    wants = str(body.get("wants") or "showing").lower()
    wants = wants if wants in ("showing", "question", "similar") else "showing"
    message = str(body.get("message") or "").strip()[:2000]
    lead = Lead(boost_id=site.boost_id, user_id=site.user_id, platform="website", source="web",
                channel="Listing page form", author_name=name, email=email,
                phone=str(body.get("phone") or "").strip()[:40] or None, wants=wants,
                visitor=re.sub(r"[^A-Za-z0-9_-]", "", visitor or "")[:64] or None,
                text=message or {"showing": "I'd like to schedule a showing.",
                                 "question": "I have a question about this home.",
                                 "similar": "I'd like to hear about similar homes."}[wants],
                post_label=source_label(db, site.boost_id, str(body.get("source") or "")),
                classified_by="website", status="new")
    db.add(lead)
    db.commit()
    email_form_lead(db, site, lead)
    return lead


def email_form_lead(db, site: ListingSite, lead: Lead) -> bool:
    from app.services import mail
    owner = db.query(User).filter(User.id == site.user_id).first()
    boost = db.query(Boost).filter(Boost.id == site.boost_id).first()
    if owner is None or not owner.email:
        return False
    street = street_and_city(boost.address if boost else "")[0]
    what = {"showing": "wants to schedule a showing", "question": "has a question",
            "similar": "asked about similar homes"}.get(lead.wants or "", "sent a message")
    body = (f"{lead.author_name} {what} about {street}.\n\n\"{lead.text}\"\n\n"
            f"Email: {lead.email}\n" + (f"Phone: {lead.phone}\n" if lead.phone else "")
            + f"\nReply to them directly. It's also on your campaign under Campaign leads:\n"
            f"{app_base()}/#campaign-{site.boost_id}\n\n- Resmara")
    try:
        ok = mail.send_email(owner.email, f"New lead for {street}: {lead.author_name}", body)
    except Exception as exc:  # noqa: BLE001
        ok = False
        lead.email_error = str(exc)[:300]
    if ok:
        lead.notified_at = _now()
    elif not lead.email_error:
        lead.email_error = "the email didn't send"
    db.commit()
    return bool(ok)


def stats(db, site: Optional[ListingSite], boost_id: int) -> Dict[str, Any]:
    """Visits, form leads, call leads, text leads, and which post or ad brought them (section 8)."""
    from sqlalchemy import func as f
    out = {"visits": 0, "forms": 0, "calls": 0, "texts": 0, "sources": {}}
    if site is not None:
        out["visits"] = db.query(f.count(ListingVisit.id)).filter(ListingVisit.site_id == site.id).scalar() or 0
        for source, n in (db.query(ListingVisit.source, f.count(ListingVisit.id))
                          .filter(ListingVisit.site_id == site.id).group_by(ListingVisit.source).all()):
            out["sources"][source or "direct"] = n
    for source, n in (db.query(Lead.source, f.count(Lead.id))
                      .filter(Lead.boost_id == boost_id, Lead.source.in_(("web", "call", "text")))
                      .group_by(Lead.source).all()):
        out[{"web": "forms", "call": "calls", "text": "texts"}[source]] = n
    return out


# ------------------------------------------------------------------ preview links for the agent
def _secret() -> bytes:
    return (getattr(settings, "SECRET_KEY", "") or "resmara").encode()


def preview_token(site: ListingSite) -> str:
    msg = f"{site.id}:{site.slug}".encode()
    return hmac.new(_secret(), msg, hashlib.sha256).hexdigest()[:32]


def preview_ok(site: ListingSite, token: str) -> bool:
    return bool(token) and hmac.compare_digest(preview_token(site), token)


# ------------------------------------------------------------------ the share image (section 9.4)
def make_share_image(db, site: ListingSite, boost: Boost) -> Optional[int]:
    """1200x630: the hero photo, the address and the price. Made once, kept with the assets."""
    from PIL import Image, ImageDraw, ImageFont, ImageOps

    hero = None
    names = (site.content or {}).get("photos") or []
    if names:
        asset = db.query(Asset).filter(Asset.filename == names[0]).first()
        raw = _asset_bytes(asset) if asset is not None else None
        if raw:
            try:
                hero = Image.open(io.BytesIO(raw)).convert("RGB")
            except Exception:  # noqa: BLE001
                hero = None
    brand = site.brand or {}
    canvas = Image.new("RGB", (1200, 630), brand.get("primary") or "#12354d")
    if hero is not None:
        canvas.paste(ImageOps.fit(hero, (1200, 630)), (0, 0))
    shade = Image.new("RGBA", (1200, 630), (0, 0, 0, 0))
    d = ImageDraw.Draw(shade)
    for y in range(330, 630):
        d.line([(0, y), (1200, y)], fill=(0, 0, 0, int(190 * (y - 330) / 300)))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), shade).convert("RGB")
    draw = ImageDraw.Draw(canvas)
    street, city = street_and_city(boost.address)
    big, small = ImageFont.load_default(size=64), ImageFont.load_default(size=34)
    draw.text((60, 470), street, font=big, fill="white")
    line = " · ".join(x for x in [city, price_text(site.price_cents)] if x)
    if line:
        draw.text((60, 552), line, font=small, fill="white")
    buf = io.BytesIO()
    canvas.save(buf, "JPEG", quality=86)
    data = buf.getvalue()
    filename = f"share-{site.slug}-{site.id}.jpg"
    asset = db.query(Asset).filter(Asset.id == site.share_asset_id).first() if site.share_asset_id else None
    if asset is None:
        asset = Asset(user_id=site.user_id, boost_id=site.boost_id, filename=filename,
                      url=f"/uploads/{filename}", kind="share", content_type="image/jpeg")
        db.add(asset)
    asset.data = data
    try:
        from app.services import storage
        stored = storage.put(filename, data, "image/jpeg")
        if stored:
            asset.url = stored
    except Exception:  # noqa: BLE001 - kept in the database either way
        pass
    db.commit()
    site.share_asset_id = asset.id
    db.commit()
    return asset.id


def _asset_bytes(asset: Asset) -> Optional[bytes]:
    try:
        if asset.data:
            return bytes(asset.data)
    except Exception:  # noqa: BLE001
        pass
    import os
    path = os.path.join(settings.UPLOAD_DIR, asset.filename)
    if os.path.isfile(path):
        with open(path, "rb") as fh:
            return fh.read()
    if (asset.url or "").startswith("http"):
        try:
            import httpx
            r = httpx.get(asset.url, timeout=15)
            if r.status_code == 200:
                return r.content
        except Exception:  # noqa: BLE001
            return None
    return None


# ------------------------------------------------------------------ the page (sections 3 and 4)
def page(db, site: ListingSite, boost: Boost, *, preview: bool = False) -> str:
    status = state(boost, site)
    key = (site.version, status, preview)
    hit = _cache.get(site.slug)
    if hit and hit[0] == key:
        return hit[1]
    out = render(site, boost, status=status, preview=preview)
    _cache[site.slug] = (key, out)
    return out


def _fact_rows(facts: Dict[str, Any], price: str) -> List[tuple]:
    rows = []
    if price:
        rows.append(("Price", price))
    if facts.get("beds"):
        rows.append(("Bedrooms", f"{facts['beds']}"))
    if facts.get("baths"):
        rows.append(("Bathrooms", f"{facts['baths']}"))
    if facts.get("sqft"):
        rows.append(("Living area", f"{int(facts['sqft']):,} sq ft"))
    if facts.get("lot"):
        rows.append(("Lot", str(facts["lot"])))
    if facts.get("year_built"):
        rows.append(("Year built", f"{facts['year_built']}"))
    if facts.get("garage"):
        rows.append(("Garage", str(facts["garage"])))
    return rows


EHO_SVG = ('<svg viewBox="0 0 40 40" width="28" height="28" aria-hidden="true"><path d="M20 4 3 17h4v19h26V17h4z" '
           'fill="none" stroke="currentColor" stroke-width="3"/><rect x="13" y="19" width="14" height="3.4" fill="currentColor"/>'
           '<rect x="13" y="25" width="14" height="3.4" fill="currentColor"/></svg>')


def render(site: ListingSite, boost: Boost, *, status: str = "live", preview: bool = False) -> str:
    c, b = dict(site.content or {}), dict(site.brand or {})
    facts = visible_facts(c)
    street, city_from_address = street_and_city(boost.address)
    city = facts.get("city") or city_from_address
    price = price_text(site.price_cents) if status in ("live", "built") else ""   # off market: no price
    photos = list(c.get("photos") or [])
    agent = b.get("agent") or "Your agent"
    first = agent.split(" ")[0]
    tel = re.sub(r"[^\d+]", "", b.get("phone") or "")
    off_market = status in ("pending", "sold", "ended", "gone")
    cta = "Ask about similar homes" if off_market else "Schedule a showing"
    chip = {"pending": "Pending", "sold": "Sold", "ended": "No longer available"}.get(status)
    if not chip:
        chip = "Open house" if c.get("open_house") else ("Price improved" if (boost.plan or {}).get("price_update") else "Just listed")
    banner = {"pending": "This home is under contract", "sold": "This home has sold",
              "ended": "This home is no longer available"}.get(status, "")
    fonts = b.get("fonts") or ["Playfair Display", "Jost"]
    font_href = "https://fonts.googleapis.com/css2?" + "&".join(
        "family=" + quote(f) + ":wght@400;500;700" for f in dict.fromkeys(fonts)) + "&display=swap"
    title = f"{street}, {city}" if city else street
    desc_bits = [price and f"Listed at {price}", facts.get("beds") and f"{facts['beds']} beds",
                 facts.get("baths") and f"{facts['baths']} baths",
                 facts.get("sqft") and f"{int(facts['sqft']):,} sq ft"]
    description = " · ".join(str(x) for x in desc_bits if x) or c.get("headline") or "See this home."
    share = f"/l/{site.slug}/share.jpg?v={site.version}"
    url = public_url(site)
    hero_photo = photo_url(photos[0], 1800) if photos else ""
    video = c.get("video") if not off_market else ""
    initials = "".join(w[0] for w in agent.split()[:2]).upper()
    maps = "https://www.google.com/maps/search/?api=1&query=" + quote(boost.address or "")
    rows = _fact_rows(facts, price)

    def img(name: str, w: int, cls: str = "", eager: bool = False) -> str:
        return (f'<img class="{cls}" src="{esc(photo_url(name, w))}" srcset="{esc(photo_url(name, 640))} 640w, '
                f'{esc(photo_url(name, 1200))} 1200w, {esc(photo_url(name, 1800))} 1800w" sizes="(max-width:700px) 100vw, 60vw" '
                f'alt="{esc((c.get("rooms") or {}).get(name) or street)}"{"" if eager else " loading=lazy"} decoding="async">')

    mini = " · ".join(x for x in [facts.get("beds") and f"{facts['beds']} beds", facts.get("baths") and f"{facts['baths']} baths",
                                  facts.get("sqft") and f"{int(facts['sqft']):,} sq ft", facts.get("lot")] if x)
    contact_btns = (f'<a class="btn accent" href="tel:{esc(tel)}" onclick="rmTap(&#39;call&#39;)">Call</a>'
                    f'<a class="btn light" href="sms:{esc(tel)}" onclick="rmTap(&#39;text&#39;)">Text</a>') if tel else ""
    chapters_html = ""
    for i, ch in enumerate(c.get("chapters") or []):
        pics = ch.get("photos") or []
        chapters_html += (
            f'<article class="ch{" flip" if i % 2 else ""}"><div class="ch-pics">'
            + (img(pics[0], 1200, "ch-big") if pics else "")
            + (img(pics[1], 800, "ch-small") if len(pics) > 1 else "")
            + f'</div><div class="ch-words"><span class="ch-num">{i + 1:02d}</span><h3>{esc(ch.get("title"))}</h3>'
            f'<p>{esc(ch.get("text"))}</p></div></article>')

    if status == "gone":
        body = f"""<main class="gone"><div class="gone-card">{_agent_card(b, initials)}
<h1>This home is no longer available.</h1><p>Ask about similar homes.</p>{_form(site, first, "similar", preview)}</div></main>"""
    else:
        hero_media = (f'<video class="hero-media" src="{esc(video)}" poster="{esc(hero_photo)}" autoplay muted loop playsinline></video>'
                      f'<button type="button" class="sound" onclick="rmSound(this)">Sound on</button>' if video
                      else f'<div class="hero-media zoom" style="background-image:url(\'{esc(hero_photo)}\')"></div>')
        gallery = "".join(f'<button type="button" class="g" onclick="rmView({i})">{img(n, 800)}</button>'
                          for i, n in enumerate(photos[:GALLERY]))
        hood = "".join(f'<li><b>{r["minutes"]} min</b> {esc(r["place"])}</li>' for r in (c.get("neighborhood") or []))
        body = f"""{f'<div class="banner">{esc(banner)}</div>' if banner else ''}
<section class="hero">{hero_media}<div class="hero-shade"></div><div class="hero-text">
<span class="chip">{esc(chip)}</span><h1>{esc(street)}</h1><p class="city">{esc(city)}</p>
{f'<p class="price">Listed at {esc(price)}</p>' if price else (f'<p class="price ask">Ask {esc(first)} about pricing</p>' if not off_market else '')}
<p class="mini">{esc(mini)}</p>
<div class="hero-btns"><a class="btn accent" href="#contact" onclick="rmWant(&#39;{"similar" if off_market else "showing"}&#39;)">{cta}</a>
{f'<button type="button" class="btn ghost" onclick="rmView(0)">See all {len(photos)} photos</button>' if photos else ''}</div></div></section>
{f'<section class="facts" id="details">' + "".join(f'<div><small>{esc(k)}</small><b>{esc(v)}</b></div>' for k, v in rows) + '</section>' if rows else ''}
<section class="story">{f'<h2 class="headline">{esc(c.get("headline"))}</h2>' if c.get("headline") else ''}{chapters_html}</section>
{f'<section class="gallery" id="photos"><h2>Every photo</h2><div class="grid">{gallery}</div><button type="button" class="btn dark" onclick="rmView(0)">View all photos</button></section>' if photos else ''}
{f'<section class="openhouse"><small>Open house</small><b>{esc(c.get("open_house"))}</b></section>' if c.get("open_house") and not off_market else ''}
<section class="hood" id="neighborhood"><h2>The neighborhood</h2>{f'<ul>{hood}</ul>' if hood else ''}<a class="btn dark" href="{esc(maps)}" target="_blank" rel="noopener">Open in Maps</a></section>
<section class="contact" id="contact"><div class="contact-in">
{f'<p class="note">{esc(c.get("note"))}</p>' if c.get("note") else ''}
{_agent_card(b, initials)}
<div class="contact-btns">{contact_btns}</div>
{_form(site, first, "similar" if off_market else "showing", preview)}</div></section>"""

    lightbox = "".join(f'<img data-src="{esc(photo_url(n, 1800))}" alt="">' for n in photos)
    legal = "".join(f"<span>{esc(l)}</span>" for l in (b.get("legal") or []))
    want = "similar" if off_market else "showing"
    bar = ""
    if status != "gone":
        taps = (f'<a href="tel:{esc(tel)}" onclick="rmTap(&#39;call&#39;)">Call</a>'
                f'<a href="sms:{esc(tel)}" onclick="rmTap(&#39;text&#39;)">Text</a>') if tel else ""
        bar = f'<nav class="bar">{taps}<a class="go" href="#contact" onclick="rmWant(&#39;{want}&#39;)">{esc(cta)}</a></nav>'
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(title)}</title><meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="website"><meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}"><meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{esc(url.rsplit('/', 1)[0] + share)}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
{'<meta name="robots" content="noindex">' if preview or status == "gone" else ''}
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="{esc(font_href)}">
{f'<link rel="preload" as="image" href="{esc(hero_photo)}">' if hero_photo else ''}
<style>{_css(b, fonts)}</style></head>
<body class="{esc(status)}{' preview' if preview else ''}">
{'<div class="pv">Preview: visits and leads aren’t counted here.</div>' if preview else ''}
<header class="top">{f'<img class="logo" src="{esc(b["logo"])}" alt="{esc(b.get("brokerage") or agent)}">' if b.get("logo") else f'<b class="brand">{esc(b.get("brokerage") or agent)}</b>'}
{'' if status == "gone" else '<nav class="links"><a href="#photos">Photos</a><a href="#details">Details</a><a href="#neighborhood">Neighborhood</a><a href="#contact">Contact</a></nav>'}
{'' if status == "gone" else f'<a class="btn accent small" href="#contact" onclick="rmWant(&#39;{want}&#39;)">{cta}</a>'}</header>
{body}
<footer class="foot">{legal}<span class="eho">{EHO_SVG} Equal Housing Opportunity</span>
<span>Information is believed accurate but not guaranteed. Buyers should verify all details.</span></footer>
{bar}
<div class="lb" id="lb" hidden><button type="button" class="lb-x" onclick="rmClose()" aria-label="Close">Close</button>
<button type="button" class="lb-p" onclick="rmStep(-1)" aria-label="Previous photo">Prev</button><div class="lb-track">{lightbox}</div>
<button type="button" class="lb-n" onclick="rmStep(1)" aria-label="Next photo">Next</button><span class="lb-c" id="lbc"></span></div>
<script>window.RM={json.dumps({"slug": site.slug, "preview": preview})};{_JS}</script></body></html>"""


def _agent_card(b: Dict[str, Any], initials: str) -> str:
    pic = (f'<img class="hs" src="{esc(b["headshot"])}" alt="">' if b.get("headshot")
           else f'<span class="hs initials">{esc(initials)}</span>')
    lines = "".join(f"<small>{esc(x)}</small>" for x in [b.get("brokerage"),
                    b.get("license") and f"License #{b['license']}", b.get("phone")] if x)
    return f'<div class="agent">{pic}<div><b>{esc(b.get("agent") or "")}</b>{lines}</div></div>'


def _form(site: ListingSite, first: str, wants: str, preview: bool) -> str:
    choice = ("" if wants == "similar" else
              '<div class="want"><label><input type="radio" name="wants" value="showing" checked> Schedule a showing</label>'
              '<label><input type="radio" name="wants" value="question"> Ask a question</label></div>')
    hidden = '<input type="hidden" name="wants" value="similar">' if wants == "similar" else ""
    return f"""<form class="form" onsubmit="return rmSend(this)">{choice}{hidden}
<input name="name" required placeholder="Your name" aria-label="Your name" autocomplete="name">
<input name="email" type="email" required placeholder="Email" aria-label="Email" autocomplete="email">
<input name="phone" type="tel" placeholder="Phone (optional)" aria-label="Phone" autocomplete="tel">
<textarea name="message" rows="3" placeholder="Message (optional)" aria-label="Message"></textarea>
<input name="website" tabindex="-1" autocomplete="off" aria-hidden="true" class="trap">
<button class="btn accent">Send to {esc(first)}</button>
<p class="fine">{'Preview: nothing is sent from here.' if preview else 'Your details go only to ' + esc(first) + '.'}</p></form>"""


def _css(b: Dict[str, Any], fonts: List[str]) -> str:
    return f"""
:root{{--p:{b.get('primary') or '#12354d'};--a:{b.get('accent') or '#d94c0d'};--t:{b.get('tint') or '#eef3f7'};
--bg:{b.get('page') or '#fff'};--tx:{b.get('text') or '#1c2733'};--h:'{fonts[0]}',Georgia,serif;--b:'{fonts[-1]}',system-ui,sans-serif}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:var(--bg);color:var(--tx);font:16px/1.6 var(--b)}}
img{{max-width:100%;display:block}}h1,h2,h3{{font-family:var(--h);font-weight:500;line-height:1.15;margin:0}}
a{{color:inherit}}.pv{{background:#12354d;color:#fff;text-align:center;font-size:13px;padding:6px}}
.top{{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:20px;padding:12px 28px;background:var(--bg);box-shadow:0 1px 0 rgba(0,0,0,.08)}}
.logo{{height:38px;width:auto}}.brand{{font-family:var(--h);font-size:20px}}.links{{display:flex;gap:22px;margin-left:auto;font-size:14px}}
.links a{{text-decoration:none}}.btn{{display:inline-block;border:0;border-radius:6px;padding:13px 22px;font:600 15px var(--b);text-decoration:none;cursor:pointer;text-align:center}}
.btn.small{{padding:9px 16px;font-size:14px}}.accent{{background:var(--a);color:#fff}}.dark{{background:var(--p);color:#fff}}
.ghost{{background:#fff;color:var(--p)}}.light{{background:#fff;color:var(--p)}}
.banner{{background:var(--p);color:#fff;text-align:center;padding:12px;font-weight:600;letter-spacing:.02em}}
.hero{{position:relative;min-height:86vh;display:flex;align-items:flex-end;overflow:hidden;color:#fff}}
.hero-media{{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;background-size:cover;background-position:center}}
.zoom{{animation:z 24s ease-out forwards}}@keyframes z{{from{{transform:scale(1)}}to{{transform:scale(1.08)}}}}
.hero-shade{{position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,0,0,0) 35%,rgba(0,0,0,.65))}}
.hero-text{{position:relative;padding:48px 6vw;max-width:900px}}.hero h1{{font-size:clamp(34px,6vw,64px)}}
.chip{{display:inline-block;background:var(--a);color:#fff;font-size:13px;font-weight:600;padding:5px 12px;border-radius:20px;margin-bottom:14px}}
.city{{font-size:18px;margin:6px 0 0}}.price{{font-size:24px;font-weight:600;margin:14px 0 4px}}.price.ask{{font-size:18px}}
.mini{{opacity:.92;margin:0 0 20px}}.hero-btns{{display:flex;gap:12px;flex-wrap:wrap}}
.sound{{position:absolute;right:18px;top:18px;z-index:2;background:rgba(0,0,0,.45);color:#fff;border:0;border-radius:20px;padding:8px 14px;cursor:pointer}}
.facts{{display:flex;flex-wrap:wrap;justify-content:center;gap:0;background:var(--p);color:#fff}}
.facts div{{padding:22px 28px;text-align:center;min-width:130px}}.facts small{{display:block;opacity:.8;font-size:12px;text-transform:uppercase;letter-spacing:.08em}}.facts b{{font-size:20px;font-weight:600}}
.story{{max-width:1180px;margin:0 auto;padding:80px 28px 30px}}.headline{{font-size:clamp(28px,4vw,46px);text-align:center;max-width:820px;margin:0 auto 70px}}
.ch{{display:grid;grid-template-columns:1.25fr 1fr;gap:56px;align-items:center;margin-bottom:90px}}.ch.flip .ch-pics{{order:2}}
.ch-pics{{position:relative;padding-bottom:60px}}.ch-big{{width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:4px}}
.ch-small{{position:absolute;right:-24px;bottom:0;width:45%;aspect-ratio:4/3;object-fit:cover;border:6px solid var(--bg);border-radius:4px}}
.ch.flip .ch-small{{right:auto;left:-24px}}.ch-num{{color:var(--a);font-weight:700;letter-spacing:.1em}}.ch h3{{font-size:30px;margin:8px 0 14px}}
.gallery{{max-width:1180px;margin:0 auto;padding:30px 28px 70px;text-align:center}}.gallery h2,.hood h2{{font-size:34px;margin-bottom:26px}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:26px}}.g{{border:0;padding:0;cursor:pointer;background:none}}
.g img{{width:100%;aspect-ratio:1;object-fit:cover;border-radius:3px}}
.openhouse{{background:var(--a);color:#fff;text-align:center;padding:26px}}.openhouse small{{display:block;text-transform:uppercase;letter-spacing:.1em}}.openhouse b{{font-size:22px}}
.hood{{background:var(--t);text-align:center;padding:70px 28px}}.hood ul{{list-style:none;padding:0;margin:0 auto 26px;max-width:560px;text-align:left}}
.hood li{{padding:12px 0;border-bottom:1px solid rgba(0,0,0,.1)}}.hood li b{{display:inline-block;width:90px;color:var(--p)}}
.contact{{background:var(--p);color:#fff;padding:80px 28px}}.contact-in{{max-width:620px;margin:0 auto}}
.note{{font-family:var(--h);font-size:24px;line-height:1.4;margin:0 0 28px}}
.agent{{display:flex;gap:16px;align-items:center;margin-bottom:22px}}.agent small{{display:block;opacity:.85}}.agent b{{font-size:19px}}
.hs{{width:76px;height:76px;border-radius:50%;object-fit:cover;flex:none}}.initials{{display:grid;place-items:center;background:var(--a);color:#fff;font-weight:700;font-size:24px}}
.contact-btns{{display:flex;gap:12px;margin-bottom:24px}}.contact-btns .btn{{flex:1}}
.form{{display:grid;gap:10px;background:#fff;color:var(--tx);padding:22px;border-radius:8px}}
.form input,.form textarea{{font:15px var(--b);padding:12px;border:1px solid #cfd8e0;border-radius:6px;width:100%}}
.want{{display:flex;gap:18px;font-size:15px}}.trap{{position:absolute;left:-9999px}}.fine{{font-size:13px;opacity:.7;margin:0}}
.foot{{display:flex;flex-wrap:wrap;gap:8px 22px;justify-content:center;align-items:center;padding:28px 28px 110px;font-size:12px;opacity:.8}}
.eho{{display:inline-flex;align-items:center;gap:6px}}
.bar{{display:none}}.gone{{min-height:70vh;display:grid;place-items:center;padding:60px 20px}}.gone-card{{max-width:520px}}.gone h1{{font-size:32px;margin:10px 0}}
.lb{{position:fixed;inset:0;z-index:50;background:rgba(0,0,0,.94);display:flex;align-items:center;justify-content:center}}
.lb[hidden]{{display:none}}.lb-track{{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;width:100%;height:100%}}
.lb-track img{{flex:0 0 100%;width:100%;height:100%;object-fit:contain;scroll-snap-align:center}}
.lb button{{position:absolute;z-index:2;background:rgba(255,255,255,.15);color:#fff;border:0;border-radius:6px;padding:10px 14px;cursor:pointer}}
.lb-x{{top:16px;right:16px}}.lb-p{{left:16px}}.lb-n{{right:16px}}.lb-c{{position:absolute;bottom:18px;color:#fff;font-size:14px}}
@media (max-width:760px){{.links{{display:none}}.top{{padding:12px 16px}}.top .btn{{display:none}}.brand{{font-size:18px}}.logo{{height:32px}}
.ch{{grid-template-columns:1fr;gap:22px;margin-bottom:60px}}.ch.flip .ch-pics{{order:0}}.ch-small{{right:-6px}}.ch.flip .ch-small{{left:-6px}}
.grid{{grid-template-columns:repeat(2,1fr)}}.facts div{{padding:16px 18px;min-width:33%}}.hero{{min-height:78vh}}
.bar{{display:flex;position:fixed;left:0;right:0;bottom:0;z-index:30;background:var(--bg);box-shadow:0 -2px 10px rgba(0,0,0,.12);padding:8px 8px calc(8px + env(safe-area-inset-bottom))}}
.bar a{{flex:1;text-align:center;padding:12px 4px;text-decoration:none;font-weight:600;color:var(--p)}}.bar .go{{flex:1.6;background:var(--a);color:#fff;border-radius:6px}}
.lb-p,.lb-n{{display:none}}}}
"""


_JS = r"""
(function(){
var key='rm_v',v;try{v=localStorage.getItem(key);if(!v){v=Math.random().toString(36).slice(2)+Date.now().toString(36);localStorage.setItem(key,v)}}catch(e){v='s'+Date.now().toString(36)}
var src=new URLSearchParams(location.search).get('utm_content')||new URLSearchParams(location.search).get('utm_source')||'';
var base='/api/public/listing/'+encodeURIComponent(RM.slug);
function send(path,body){if(RM.preview)return;try{var b=JSON.stringify(Object.assign({visitor:v,source:src},body||{}));if(navigator.sendBeacon){navigator.sendBeacon(base+path,new Blob([b],{type:'application/json'}))}else{fetch(base+path,{method:'POST',headers:{'Content-Type':'application/json'},body:b,keepalive:true})}}catch(e){}}
send('/visit');
window.rmTap=function(kind){send('/'+kind)};
window.rmWant=function(w){var r=document.querySelector('.form input[value="'+w+'"]');if(r)r.checked=true};
window.rmSend=function(f){
 if(RM.preview){f.querySelector('.fine').textContent='Preview: nothing is sent from here.';return false}
 var d={visitor:v,source:src};new FormData(f).forEach(function(val,k){d[k]=val});
 var btn=f.querySelector('button');btn.disabled=true;
 fetch(base+'/lead',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)}).then(function(r){if(!r.ok)throw 0;
  var n=(d.name||'').split(' ')[0];f.innerHTML='<h3>Thanks, '+n.replace(/[<>&"]/g,'')+'.</h3><p class="fine">Your message is on its way. Expect a reply soon.</p>'})
 .catch(function(){btn.disabled=false;f.querySelector('.fine').textContent='That didn’t send. Please try again, or call instead.'});
 return false};
var lb=document.getElementById('lb'),track=lb&&lb.querySelector('.lb-track'),imgs=track?track.querySelectorAll('img'):[];
function count(){var i=Math.round(track.scrollLeft/track.clientWidth);document.getElementById('lbc').textContent=(i+1)+' / '+imgs.length;
 [i-1,i,i+1,i+2].forEach(function(j){var im=imgs[j];if(im&&!im.src)im.src=im.getAttribute('data-src')})}
window.rmView=function(i){if(!imgs.length)return;lb.hidden=false;document.body.style.overflow='hidden';track.scrollLeft=i*track.clientWidth;count()};
window.rmClose=function(){lb.hidden=true;document.body.style.overflow=''};
window.rmStep=function(d){track.scrollBy({left:d*track.clientWidth,behavior:'smooth'})};
if(track)track.addEventListener('scroll',function(){clearTimeout(track._t);track._t=setTimeout(count,80)});
document.addEventListener('keydown',function(e){if(lb.hidden)return;if(e.key==='Escape')rmClose();if(e.key==='ArrowRight')rmStep(1);if(e.key==='ArrowLeft')rmStep(-1)});
window.rmSound=function(b){var vd=document.querySelector('.hero video');if(vd){vd.muted=!vd.muted;b.textContent=vd.muted?'Sound on':'Sound off'}};
})();
"""


def not_found_page() -> str:
    return """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>This home isn't here</title><meta name="robots" content="noindex"><style>body{margin:0;font:17px/1.6 system-ui,sans-serif;color:#12354d;
display:grid;place-items:center;min-height:100vh;text-align:center;padding:24px}a{display:inline-block;margin-top:14px;background:#d94c0d;color:#fff;
padding:12px 20px;border-radius:6px;text-decoration:none;font-weight:600}</style></head><body><div><h1>This home isn't here</h1>
<p>The link may be mistyped, or the listing has been taken down.</p><a href="https://www.resmara.com">Go to Resmara</a></div></body></html>"""


# ------------------------------------------------------------------ the daily check (section 9)
def daily_check(db, *, fetch_photo: Optional[Callable] = None) -> Dict[str, Any]:
    """Every live website renders and every photo it uses exists; any that doesn't is flagged."""
    flagged = []
    rows = db.query(ListingSite).all()
    for site in rows:
        boost = db.query(Boost).filter(Boost.id == site.boost_id).first()
        if boost is None or not is_public(boost):
            continue
        problems = []
        try:
            out = render(site, boost, status=state(boost, site))
            if "<title>" not in out:
                problems.append("the page didn't render")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"the page didn't render ({str(exc)[:80]})")
        names = (site.content or {}).get("photos") or []
        if names:
            have = {a.filename for a in db.query(Asset.filename).filter(Asset.filename.in_(names)).all()}
            missing = [n for n in names if n not in have]
            if missing:
                problems.append(f"{len(missing)} photo(s) missing")
        site.checked_at = _now()
        site.check_note = "; ".join(problems) or None
        if problems:
            flagged.append({"slug": site.slug, "problems": problems})
    db.commit()
    if flagged:
        try:
            from app.services import mail
            to = team_email()
            if to:
                mail.send_email(to, f"{len(flagged)} listing website(s) need a look",
                                "\n".join(f"{f['slug']}: {', '.join(f['problems'])}" for f in flagged))
        except Exception:  # noqa: BLE001
            pass
    return {"checked": len(rows), "flagged": flagged}
