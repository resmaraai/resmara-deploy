"""The brand engine (Engine 2): a private investigator for the agent's real estate career.

It starts the moment they sign in with Facebook and runs in the background while the sign-up
checks run. It looks them up (their Facebook Page, Instagram, website, a web search, their
brokerage's site, the state license lookup, YouTube, Zillow, Realtor.com), then writes their
brand kit straight onto My Brand. No brand form; nothing to type.

Rules this file keeps (docs/engines/engine-2-brain.md, sections 4-6):

* Facts that print on posts are never guessed: phone, license numbers, brokerage, the legal line.
  Each needs a source. Missing stays missing (and is asked for when they start a campaign).
* Style can be a judgement (colours, fonts, voice), and anything chosen rather than found is
  marked so the agent can confirm it.
* Their own logo leads; the local office, never the national mark alone; real Google Fonts only.
* Positive only: politics, rants and anything negative never shape the voice.
* Persona, not personal information: nothing about health, religion, politics, family or home.
* The agent's own edits always win and survive Research again.
"""

from __future__ import annotations

import html
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.db.session import Event, SessionLocal, User

log = logging.getLogger("resmara.brand_investigator")

# Fields the build prints on posts: found with a source, or left empty. Never guessed.
POST_FACTS = ("phone", "license", "company", "brokerLicense")
# Fields the agent can edit; an edited field is never overwritten by Research again.
KIT_FIELDS = ("agent", "title", "phone", "email", "website", "license", "company", "brokerage", "brokerLicense",
              "market", "palette", "fonts", "voice", "voiceOfClient", "use", "avoid", "signoff",
              "logoUrl", "headshotUrl", "instagram", "ownTag")
PERSONAL_WORDS = re.compile(
    r"\b(wife|husband|son|daughter|kids?|children|grandkids?|church|faith|god|pray|prayer|cancer|"
    r"diagnos\w*|illness|politic\w*|democrat\w*|republican\w*|trump|biden|divorce\w*)\b", re.I)
GOOGLE_FONTS_SAFE = {
    "Playfair Display", "Jost", "Montserrat", "Lora", "Cormorant Garamond", "Inter", "Poppins",
    "Libre Baskerville", "Raleway", "Open Sans", "Lato", "Merriweather", "DM Serif Display",
    "DM Sans", "Nunito Sans", "Source Sans 3", "Roboto", "Work Sans", "Crimson Pro", "Marcellus",
    "Cinzel", "Josefin Sans", "Karla", "Manrope", "EB Garamond", "Prata", "Bodoni Moda", "Oswald",
    "Archivo", "Outfit", "Plus Jakarta Sans", "Space Grotesk", "Fraunces", "Spectral", "Mulish",
}

INVESTIGATOR_PROMPT = """You are a private investigator hired to learn everything about one real estate
agent's career, so a marketing studio can build their brand kit. USE WEB SEARCH. Look them up on:
their Facebook Page, their Instagram, their website, a Google search on their name and market, their
brokerage's site (the LOCAL office), the state real estate license lookup, YouTube, Zillow and
Realtor.com. Make sure every result is really them: match their name, photo, market and license.

AGENT: {agent}
FACEBOOK PAGE: {page}
PAGE CATEGORY: {category}
PAGE ABOUT: {about}
PAGE PHONE: {phone}
PAGE WEBSITE: {website}
PAGE ADDRESS: {address}
INSTAGRAM: {instagram}
THEIR WEBSITE TEXT (may be empty): {site_text}

RULES
- Facts that print on posts are NEVER guessed: phone, the agent's license number, the brokerage
  name, the broker's license number. Give each only with the URL you found it on; the license
  number must come from the state license lookup when you can reach it. Unknown stays "".
- The brokerage is the local office ("Shasta Sotheby's International Realty"), never the national
  mark alone.
- Their own logo first (a URL), then the brokerage lockup. Never put a brokerage logo in place of theirs.
- Colours: from their own website first, then their own graphics, then the brokerage's brand (hex).
- Fonts: a headline and a body font, both real Google Fonts, chosen to fit them.
- POSITIVE ONLY: skip politics, complaints, rants, arguments, anything angry, mocking, divisive or
  sarcastic, and innuendo. Look only for how they help people, what they're proud of, how they
  celebrate clients and their community. If most of what they post is negative or political, build
  the voice from their professional pages and listings only, warm and neutral.
- PERSONA, NOT PERSONAL: never mention family members, children, home life, health, religion or
  politics, even if public.

Return ONLY one JSON object with these keys:
agent (their name as they market it), title (e.g. "REALTOR®"), phone, phone_source, email,
website, license, license_source, company, company_source, brokerLicense, brokerLicense_source,
market (areas served, short), instagram, logoUrl, logo_source, headshotUrl, colors (array of hex,
up to 5, primary first), colors_from ("their website" | "their graphics" | "brokerage"),
fonts (array of 2 Google Font names: headline, body), voiceOfClient (80 to 120 words, plain words,
describing the agent the way a colleague would brief a copywriter: personality, what it's like to
work with them, the community and areas, their main clients, how they talk online, what to stay
away from), voice (one short line), use (3 to 5 phrases they really use), avoid (3 to 5 things to
avoid), signoff (their sign-off, or ""), sources (array of {{"title": short name, "url": url}} for
every place you looked that had something on them)."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean(value: Any, limit: int = 400) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def _hex(value: Any) -> Optional[str]:
    v = str(value or "").strip()
    if re.fullmatch(r"#?[0-9a-fA-F]{6}", v):
        return ("#" + v.lstrip("#")).upper()
    return None


def scrub_personal(text: str) -> str:
    """Persona only: drop any sentence that names family, health, faith or politics."""
    parts = re.split(r"(?<=[.!?])\s+", text or "")
    return " ".join(p for p in parts if p and not PERSONAL_WORDS.search(p)).strip()


def legal_lines(kit: Dict[str, Any]) -> List[str]:
    """The closing line on every post: name, phone, license, brokerage, Equal Housing."""
    out = []
    who = " · ".join(x for x in [kit.get("agent"), kit.get("phone")] if x)
    if who:
        out.append(who)
    if kit.get("license"):
        out.append(f"License #{kit['license']}")
    company = kit.get("company") or kit.get("brokerage")
    if company:
        out.append(company + (f" · License #{kit['brokerLicense']}" if kit.get("brokerLicense") else ""))
    out.append("Equal Housing Opportunity")
    return out


def missing_post_facts(kit: Dict[str, Any]) -> List[str]:
    """What Engine 4 asks for on + Campaign before building (section 6a)."""
    out = [k for k in ("phone", "license") if not str(kit.get(k) or "").strip()]
    if not str(kit.get("company") or kit.get("brokerage") or "").strip():
        out.append("brokerage")
    return out


# --------------------------------------------------------------------------- reading
async def site_text(url: str) -> str:
    """The text of their own website's home page, for the investigator to read."""
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0 (Resmara brand research)"}) as client:
            r = await client.get(url)
        if r.status_code >= 400:
            return ""
        raw = r.text[:400_000]
    except Exception:  # noqa: BLE001 - an unreachable site is just one fewer source
        return ""
    raw = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
    head_colors = " ".join(sorted(set(re.findall(r"#[0-9a-fA-F]{6}\b", raw)))[:20])
    text = html.unescape(re.sub(r"(?s)<[^>]+>", " ", raw))
    return _clean(text, 6000) + (f" COLOURS SEEN IN THE PAGE CODE: {head_colors}" if head_colors else "")


def meta_facts(db, user: User) -> Dict[str, Any]:
    """What the Meta connection already read off their Page (Engine 1 Part C hands it over)."""
    from app.services import meta_engine
    conn = meta_engine.connection_for(db, user.id)
    info = dict((conn.page_info if conn else None) or {})
    return {
        "agent": user.name or (conn.fb_user_name if conn else "") or "",
        "page": (conn.page_name if conn else "") or "",
        "category": info.get("category") or "",
        "about": info.get("about") or "",
        "phone": info.get("phone") or "",
        "website": info.get("website") or "",
        "address": info.get("single_line_address") or "",
        "instagram": (conn.ig_username if conn else "") or "",
        "page_picture": (conn.page_picture if conn else "") or "",
        "email": user.email if not getattr(user, "needs_email", False) else "",
    }


# --------------------------------------------------------------------------- building
def assemble(found: Dict[str, Any], facts: Dict[str, Any]) -> Dict[str, Any]:
    """The investigator's answer + Meta's facts -> the brand kit in My Brand's shape."""
    sources: List[List[str]] = []
    fact_sources: Dict[str, str] = {}

    def fact(key: str, value: Any, source: Any) -> str:
        v = _clean(value, 160)
        src = _clean(source, 300)
        if key in POST_FACTS and v and not src:
            return ""  # a fact that prints on posts with no source is a guess: left empty
        if v and src:
            fact_sources[key] = src
        return v

    kit: Dict[str, Any] = {}
    kit["agent"] = _clean(found.get("agent")) or facts.get("agent") or ""
    kit["title"] = _clean(found.get("title"), 60)
    page_phone = facts.get("phone")
    kit["phone"] = fact("phone", found.get("phone") or page_phone,
                        found.get("phone_source") or ("Your Facebook Page" if page_phone else ""))
    kit["email"] = _clean(found.get("email"), 120) or facts.get("email") or ""
    kit["website"] = _clean(found.get("website"), 200) or facts.get("website") or ""
    kit["license"] = fact("license", found.get("license"), found.get("license_source"))
    kit["company"] = fact("company", found.get("company"), found.get("company_source"))
    kit["brokerage"] = kit["company"]  # My Brand's name for it
    kit["brokerLicense"] = fact("brokerLicense", found.get("brokerLicense"), found.get("brokerLicense_source"))
    kit["market"] = _clean(found.get("market"), 160)
    kit["instagram"] = _clean(found.get("instagram"), 60).lstrip("@") or facts.get("instagram") or ""
    kit["logoUrl"] = _clean(found.get("logoUrl"), 500)
    kit["headshotUrl"] = _clean(found.get("headshotUrl"), 500) or facts.get("page_picture") or ""

    colors = [c for c in (_hex(x) for x in (found.get("colors") or [])) if c][:5]
    roles = ["Primary", "Accent", "Text", "Tint", "Page"]
    kit["palette"] = [[roles[i], c] for i, c in enumerate(colors)]
    fonts = [_clean(f, 60) for f in (found.get("fonts") or []) if _clean(f, 60)]
    fonts = [f for f in fonts if f in GOOGLE_FONTS_SAFE or re.fullmatch(r"[A-Za-z0-9 ]{3,40}", f)][:2]
    kit["fonts"] = fonts if len(fonts) == 2 else ["Playfair Display", "Jost"]

    voc = scrub_personal(_clean(found.get("voiceOfClient"), 1200))
    kit["voiceOfClient"] = voc
    kit["voice"] = scrub_personal(_clean(found.get("voice"), 200))
    kit["use"] = [_clean(x, 80) for x in (found.get("use") or []) if _clean(x, 80) and not PERSONAL_WORDS.search(str(x))][:5]
    kit["avoid"] = [_clean(x, 80) for x in (found.get("avoid") or []) if _clean(x, 80)][:5]
    kit["signoff"] = _clean(found.get("signoff"), 120)
    kit["theme"] = "Match my brand"
    kit["legal"] = legal_lines(kit)

    for s in found.get("sources") or []:
        if isinstance(s, dict) and s.get("title"):
            sources.append([_clean(s.get("title"), 60), _clean(s.get("url"), 200)])
    if facts.get("page"):
        sources.insert(0, ["Facebook Page", facts["page"]])
    if facts.get("instagram"):
        sources.insert(1, ["Instagram", "@" + facts["instagram"]])
    kit["sources"] = sources[:12]
    kit["factSources"] = fact_sources
    # Chosen rather than found: the agent confirms these on My Brand.
    kit["chosen"] = [k for k in ("palette", "fonts", "voiceOfClient", "voice") if kit.get(k)]
    if found.get("colors_from"):
        kit["coloursFrom"] = _clean(found.get("colors_from"), 40)
    kit["missing"] = missing_post_facts(kit)
    return kit


def merge(existing: Dict[str, Any], fresh: Dict[str, Any]) -> Dict[str, Any]:
    """The agent's changes always win and survive Research again."""
    existing = dict(existing or {})
    edited = set(existing.get("edited") or [])
    out = dict(existing)
    for k, v in fresh.items():
        if k in edited:
            continue
        out[k] = v
    out["edited"] = sorted(edited)
    out["legal"] = legal_lines(out)
    out["missing"] = missing_post_facts(out)
    return out


async def investigate(db, user: User) -> Dict[str, Any]:
    """Look the agent up and return their kit. Never raises for a missing source."""
    from app.services import llm
    facts = meta_facts(db, user)
    text = await site_text(facts.get("website") or "")
    found: Dict[str, Any] = {}
    note = ""
    if llm.llm_available():
        prompt = INVESTIGATOR_PROMPT.format(
            agent=facts["agent"] or "unknown", page=facts["page"] or "none", category=facts["category"] or "",
            about=_clean(facts["about"], 800), phone=facts["phone"] or "", website=facts["website"] or "none",
            address=facts["address"] or "", instagram=("@" + facts["instagram"]) if facts["instagram"] else "none",
            site_text=_clean(text, 4000))
        try:
            reply = await llm.responses_text(prompt, model=settings.research_model, reasoning_effort="low",
                                             tools=[{"type": "web_search"}])
            found = llm._json_object(reply) or {}
        except Exception as exc:  # noqa: BLE001 - a failed search still leaves Meta's facts
            note = f"The web search didn't answer ({type(exc).__name__}); built from your Facebook Page."
    else:
        note = "Built from your Facebook Page; the web investigation runs once the AI is configured."
    kit = assemble(found if isinstance(found, dict) else {}, facts)
    d = _now()
    kit["researched"] = f"{d.day} {d.strftime('%b %Y')}"
    if note:
        kit["note"] = note
    return kit


async def build_for_user(user_id: int, *, reason: str = "signup") -> Dict[str, Any]:
    """Background job: investigate and save the kit on My Brand. Own session; never raises."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            return {}
        current = dict(user.brand or {})
        current["build"] = {"status": "running", "started": _now().isoformat(), "reason": reason}
        user.brand = current
        db.commit()
        try:
            kit = await investigate(db, user)
            merged = merge(user.brand or {}, kit)
            merged["build"] = {"status": "done", "finished": _now().isoformat(), "reason": reason}
            user.brand = merged
            db.add(Event(user_id=user.id, event_type="brand_built",
                         payload={"reason": reason, "missing": merged.get("missing"),
                                  "sources": len(merged.get("sources") or [])}))
        except Exception as exc:  # noqa: BLE001
            log.warning("brand build failed for user %s: %s", user_id, exc)
            failed = dict(user.brand or {})
            failed["build"] = {"status": "failed", "finished": _now().isoformat(), "reason": reason}
            user.brand = failed
        db.commit()
        return dict(user.brand or {})
    finally:
        db.close()


def build_status(user: User) -> Dict[str, Any]:
    brand = dict(user.brand or {})
    return {"build": brand.get("build") or {"status": "not_started"}, "brand": brand,
            "missing": missing_post_facts(brand)}
