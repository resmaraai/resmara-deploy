"""Engine 4: what Resmara learns across campaigns, so every build starts sharper.

* The hook library (section 9b): which ad hooks win, by what they're about (pool, view, kitchen...)
  and by market, across every Resmara agent. Read live from each ad's hook versions and the numbers
  the live ad audit saved on them; nothing extra is stored.
* The rulebook's lessons (9b): every time Meta rejects an ad and Resmara fixes it, the reason is
  logged (`rulebook_lesson`); the next hooks are written with those lessons in hand.
* The platform rules refresh (9b, hashtags): once a month an AI with web search re-reads the platforms'
  rules: Meta's ad standards for housing, and Instagram hashtags that are banned or restricted. The
  banned tags it finds are never used on a post.
* The trend brief (section 3): what's working on social for listing posts right now, locally and
  nationally, shared per market and refreshed weekly rather than researched inside every build.
  (Local top agents' real engagement numbers need Meta's Business Discovery, which comes with App
  Review; until then the brief is researched from the open web.)
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.db.session import Ad, Boost, Event

log = logging.getLogger("resmara.learning_library")

FEATURES = {
    "pool": r"pool|swim", "view": r"view|vista|overlook", "kitchen": r"kitchen|chef|island",
    "water": r"lake|river|creek|waterfront|ocean|pond", "land": r"acre|land|ranch|horse|barn",
    "shop": r"shop|garage|workshop|rv", "outdoor": r"yard|patio|deck|garden|outdoor",
    "light": r"light|bright|window|sun", "primary": r"primary|master suite|suite",
}
MIN_VIEWS = 500


def feature_of(text: str) -> str:
    for key, pat in FEATURES.items():
        if re.search(pat, text or "", re.I):
            return key
    return "other"


def _city(address: str) -> str:
    parts = [p.strip() for p in (address or "").split(",")]
    return (parts[1] if len(parts) >= 3 else (parts[-2] if len(parts) == 2 else "")).lower()


def hook_library(db, *, city: str = "", limit: int = 6) -> List[Dict[str, Any]]:
    """The best hooks by feature, this market first, then everywhere. Only hooks with enough views."""
    rows: List[Dict[str, Any]] = []
    for ad, address in db.query(Ad, Boost.address).join(Boost, Ad.boost_id == Boost.id).all():
        for v in ad.versions or []:
            if not isinstance(v, dict) or v.get("kind") != "hook" or not v.get("hook"):
                continue
            ins = v.get("insights") or {}
            views = float(ins.get("impressions") or 0)
            if views < MIN_VIEWS:
                continue
            clicks = float(ins.get("inline_link_clicks") or ins.get("clicks") or 0)
            rows.append({"hook": v["hook"], "feature": feature_of(f"{v.get('backedBy') or ''} {v['hook']}"),
                         "city": _city(address), "rate": clicks / views if views else 0.0, "views": int(views)})
    city = (city or "").lower()
    best: Dict[tuple, Dict[str, Any]] = {}
    for r in sorted(rows, key=lambda r: (r["city"] != city, -r["rate"])):
        key = (r["feature"], r["city"] == city)
        if key not in best:
            best[key] = r
    out = sorted(best.values(), key=lambda r: (r["city"] != city, -r["rate"]))
    return out[:limit]


def hook_library_note(db, address: str) -> str:
    rows = hook_library(db, city=_city(address))
    if not rows:
        return ""
    lines = [f"- {r['feature']}{' in this market' if r['city'] == _city(address) else ''}: "
             f"\"{r['hook']}\" ({r['rate'] * 100:.1f}% click rate on {r['views']:,} views)" for r in rows]
    return ("WHAT HAS WORKED FOR OTHER RESMARA LISTINGS (learn the shape, never copy the words, and only "
            "where it is true of THIS home):\n" + "\n".join(lines))


def rulebook_lessons(db, limit: int = 8) -> List[str]:
    """The reasons Meta gave when it rejected Resmara ads, newest first, once each."""
    seen, out = set(), []
    for e in (db.query(Event).filter(Event.event_type == "rulebook_lesson")
              .order_by(Event.id.desc()).limit(60).all()):
        reason = str((e.payload or {}).get("reason") or "").strip()
        key = reason.lower()[:80]
        if reason and key not in seen:
            seen.add(key)
            before = str((e.payload or {}).get("before") or "").strip()
            out.append(reason[:200] + (f' (it said: "{before[:100]}")' if before else ""))
        if len(out) >= limit:
            break
    return out


def lessons_note(db) -> str:
    rows = rulebook_lessons(db)
    if not rows:
        return ""
    return "META HAS REJECTED RESMARA ADS FOR THESE BEFORE - DON'T REPEAT THEM:\n" + "\n".join(f"- {r}" for r in rows)


# ---------------------------------------------------------------- the monthly platform rules refresh
RULES_PROMPT = """You keep a real estate marketing app's platform rulebook current. USE WEB SEARCH. Check, as of
today: (1) Instagram hashtags that are currently banned or restricted (posts using them are hidden), limited
to tags a real estate agent might plausibly use; (2) any change in the last few months to Meta's Advertising
Standards for housing ads (the Special Ad Category), text on images, or personal-attribute rules.
Reply with ONE JSON object: {"banned_hashtags": ["tag", ...] (without #, lowercase), "ad_rule_changes":
["one line each, with the source"], "checked": "YYYY-MM-DD"}. Report only what you found a source for."""

_CACHE: Dict[str, Any] = {}


def latest_rules(db) -> Dict[str, Any]:
    ev = (db.query(Event).filter(Event.event_type == "platform_rules").order_by(Event.id.desc()).first())
    return dict(ev.payload or {}) if ev else {}


def banned_tags(db=None) -> set:
    """The banned hashtags from the latest refresh (cached for an hour)."""
    now = datetime.utcnow()
    if _CACHE.get("at") and now - _CACHE["at"] < timedelta(hours=1):
        return _CACHE["tags"]
    tags: set = set()
    try:
        own = db
        if own is None:
            from app.db.session import SessionLocal
            own = SessionLocal()
        try:
            tags = {str(t).lower().lstrip("#") for t in latest_rules(own).get("banned_hashtags") or [] if t}
        finally:
            if db is None:
                own.close()
    except Exception:  # noqa: BLE001 - no list is never a reason to stop a post
        tags = set()
    _CACHE.update(at=now, tags=tags)
    return tags


async def refresh_platform_rules(db, *, force: bool = False) -> Dict[str, Any]:
    """Monthly (and whenever an operator asks): re-read the platform rules with web search."""
    last = (db.query(Event).filter(Event.event_type == "platform_rules").order_by(Event.id.desc()).first())
    if last is not None and not force and last.created_at and datetime.utcnow() - last.created_at < timedelta(days=28):
        return {"status": "fresh", "checked": (last.payload or {}).get("checked")}
    from app.services import llm
    if not llm.llm_available():
        return {"status": "no_model"}
    try:
        reply = await llm.responses_text(RULES_PROMPT, model=settings.research_model, reasoning_effort="low",
                                         tools=[{"type": "web_search"}])
        data = llm._json_object(reply) or {}
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "why": str(exc)[:200]}
    payload = {"banned_hashtags": sorted({re.sub(r"[^a-z0-9_]", "", str(t).lower()) for t in data.get("banned_hashtags") or []} - {""})[:200],
               "ad_rule_changes": [str(x)[:300] for x in data.get("ad_rule_changes") or []][:20],
               "checked": str(data.get("checked") or datetime.utcnow().date().isoformat())[:10]}
    db.add(Event(event_type="platform_rules", payload=payload))
    db.commit()
    _CACHE.clear()
    return {"status": "refreshed", **payload}


# ---------------------------------------------------------------- the weekly trend brief, per market
TREND_PROMPT = """You write a short trend brief for real estate listing posts on Instagram and Facebook. USE WEB
SEARCH. Part 1, LOCAL: the agents, teams and brokerages posting listings in {market} right now, and which
static formats get the most likes, comments and views there. Part 2, NATIONAL: the real estate brands and
creators doing static listing posts best right now. Learn formats, never copy: no one's designs, wording or
photos. Reply with plain text, at most 8 short lines, each a format that's working and why (for example
"full-bleed photo with a short overlaid headline outperforms boxed text"), then a line SOURCES: with the
sites you used. Write NOT SEEN for anything you couldn't find."""


async def trend_brief(db, address: str) -> str:
    """Shared per market and refreshed weekly (section 3), not run on every build."""
    market = _city(address) or "the United States"
    since = datetime.utcnow() - timedelta(days=7)
    for ev in (db.query(Event).filter(Event.event_type == "trend_brief", Event.created_at >= since)
               .order_by(Event.id.desc()).limit(50).all()):
        if (ev.payload or {}).get("market") == market:
            return str((ev.payload or {}).get("brief") or "")
    from app.services import llm
    if not llm.llm_available():
        return ""
    try:
        brief = await llm.responses_text(TREND_PROMPT.format(market=market.title()), model=settings.research_model,
                                         reasoning_effort="low", tools=[{"type": "web_search"}])
    except Exception as exc:  # noqa: BLE001 - the build's own style research still runs
        log.info("trend brief failed for %s: %s", market, exc)
        return ""
    brief = (brief or "").strip()[:2500]
    if brief:
        db.add(Event(event_type="trend_brief", payload={"market": market, "brief": brief}))
        db.commit()
    return brief
