"""The platform rulebook (Engine 4, 9b): every ad and every caption is designed to these rules.

What it covers (checked 22 Nov 2026; refresh monthly, and add a lesson whenever Meta rejects or
limits a Resmara ad):

* Meta's Advertising Standards (Facebook, Instagram, Marketplace, Messenger).
* The housing Special Ad Category (fixed in code in ad_build: 18-65+, no gender, ZIP, exclusion or
  lookalike targeting, a 15-mile minimum radius).
* Fair Housing law: nothing about who should or shouldn't live there.
* Personal attributes: an ad must not assert or imply anything about the viewer (their finances,
  family, age, religion and so on). "Have you seen a pool like this?" is fine; "Are you a first-time
  buyer?" is not.
* No misleading claims: Meta reviews text, image, video and the landing page together; every claim
  must be true and backed by the home's file. No unverifiable superlatives.
* Text on the image: a few big words; the message lives in the ad text.
* Placement specs: 4:5 for feeds, 9:16 for Stories and Reels with words out of the top and bottom.

``check`` is the fixed, instant part (rules, not AI). ``review`` adds a model pass over what the
rules can't see; it can only flag, never approve something the rules refused.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

RULEBOOK_VERSION = "2026-11-22"

FAIR_HOUSING = [
    r"\bfamil(y|ies)\b", r"\bkids?\b", r"\bchildren\b", r"\bnursery\b", r"\bbachelor\b", r"\bsingles?\b",
    r"\bcouples?\b", r"\bretire(es|ment)?\b", r"\bseniors?\b", r"\bempty[- ]nest", r"\bsafe (neighbou?rhood|area|street)",
    r"\bexclusive\b", r"\bprivate community\b", r"\bchurch(es)?\b", r"\bsynagogue\b", r"\bmosque\b",
    r"\bchristian\b", r"\bjewish\b", r"\bmuslim\b", r"\bmaster (bed|suite|bath)", r"\bhandicap", r"\bable[- ]bodied\b",
    r"\bno (kids|children|students|section 8)\b", r"\bideal for\b", r"\bperfect for (a |your )?(young|growing|small|new)\b",
    r"\bgreat schools?\b", r"\bwalking distance to (church|temple)",
]
PERSONAL_ATTRIBUTES = [
    r"\bare you (a |an )?(first[- ]time|new|young|single|retired|divorced|pregnant|expecting|struggling|over \d+)",
    r"\byour (growing )?family\b", r"\byour kids\b", r"\byour (credit|income|debt|budget)\b",
    r"\b(tired|sick) of (renting|paying rent)\b", r"\bcan('?t| not) afford\b",
]
UNVERIFIABLE = [
    r"\bbest\b", r"\b#1\b", r"\bnumber one\b", r"\bnothing like it\b", r"\bonly one\b", r"\bunbeatable\b",
    r"\bguarantee", r"\bmost beautiful\b", r"\bcheapest\b", r"\bincredible deal\b", r"\bwon'?t last\b",
]
LIMITS = {"primaryText": 125, "headline": 40, "description": 30}
IMAGE_WORDS_MAX = 8
_FH = [re.compile(p, re.I) for p in FAIR_HOUSING]
_PA = [re.compile(p, re.I) for p in PERSONAL_ATTRIBUTES]
_UV = [re.compile(p, re.I) for p in UNVERIFIABLE]


def fair_housing_issues(text: str) -> List[str]:
    return [f"Fair Housing: “{m.group(0)}”" for rx in _FH for m in [rx.search(text or "")] if m]


def check(ad: Dict[str, Any]) -> List[str]:
    """The rules, instantly: what in this ad would break Meta's standards or the law."""
    issues: List[str] = []
    words = " ".join(str(ad.get(k) or "") for k in ("hook", "primaryText", "headline", "description"))
    issues += fair_housing_issues(words)
    issues += [f"Personal attributes: “{m.group(0)}”" for rx in _PA for m in [rx.search(words)] if m]
    issues += [f"Can't be backed up: “{m.group(0)}”" for rx in _UV for m in [rx.search(words)] if m]
    for key, cap in LIMITS.items():
        if len(str(ad.get(key) or "")) > cap:
            issues.append(f"{key} is over {cap} characters")
    if len(str(ad.get("hook") or "").split()) > IMAGE_WORDS_MAX:
        issues.append(f"the hook on the image is over {IMAGE_WORDS_MAX} words")
    if ad.get("hook") and not str(ad.get("backedBy") or "").strip():
        issues.append("the hook isn't backed by anything in the home's file")
    return issues


def fit(ad: Dict[str, Any]) -> Dict[str, Any]:
    """Trim to the limits (never rewrite meaning)."""
    out = dict(ad)
    for key, cap in LIMITS.items():
        v = str(out.get(key) or "")
        if len(v) > cap:
            cut = v[:cap].rsplit(" ", 1)[0].rstrip(",;:-")
            out[key] = cut
    return out


async def review(ad: Dict[str, Any], *, facts: str = "") -> List[str]:
    """A model reads the ad against the rulebook for what patterns can't catch. Never raises."""
    from app.core.config import settings
    from app.services import llm
    if not llm.llm_available():
        return []
    try:
        reply = await llm.chat_json(
            "You check one real estate housing ad against Meta's Advertising Standards, the housing "
            "Special Ad Category and US Fair Housing law before it is submitted. Flag anything that "
            "asserts or implies something about the viewer, describes who should live there, or makes "
            "a claim the home's facts don't support. Answer with JSON only: {\"issues\": [\"<one short "
            "line each>\"]}; an empty list when it's fine.",
            f"THE HOME'S FACTS: {facts[:3000]}\nTHE AD: {ad}",
            model=settings.OPENAI_MODEL_BRAND, max_completion_tokens=300)
        return [str(x)[:200] for x in (reply or {}).get("issues") or []][:5]
    except Exception:  # noqa: BLE001
        return []
