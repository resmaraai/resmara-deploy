"""The ad (Engine 4, 9b): built differently from the posts. Its one job is to stop the scroll.

* The hook first: what's most valuable or unusual about THIS home (the pool, the view, the kitchen,
  the shop, the light), as a short, curiosity-driving line, always backed by the home's file and the
  photo it sits on. Questions and invitations are fine; unverifiable claims are not.
* Up to 3 hook versions in the same ad set and budget; Meta shifts the spend to the one people click.
* Its own graphic: the hook as a few big words over the strongest photo, plus the agent's details,
  in 4:5 for feeds and 9:16 for Stories and Reels.
* Designed to the platform rulebook (ad_rulebook), not checked against it afterwards.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional

from app.core.config import settings
from app.services import ad_rulebook, llm

log = logging.getLogger("resmara.ad_hooks")
MAX_HOOKS = 3

HOOK_PROMPT = """You write the hooks for one real estate listing ad. The ad's only job is to stop the
scroll and get the click. Find what is most valuable or unusual about THIS home from its file below
(the pool, the view, the kitchen, the shop, the light, the land) and write up to 3 different hooks,
each a short, curiosity-driving line of at most 8 words, for example "Have you seen a pool like this?"
or "This kitchen doesn't look like the rest of the house."

RULES (Meta's Advertising Standards, the housing Special Ad Category and Fair Housing law):
- Always true to the house: every hook must be backed by a fact in the file and the photo it sits on.
- No claims that can't be checked: never "best", "#1", "nothing like it anywhere", "won't last".
- Never assert or imply anything about the viewer (their finances, family, age, religion): "Are you a
  first-time buyer?" and "Perfect for your growing family" are not allowed.
- Never describe who should live there.
- Primary text at most 125 characters, headline at most 40, button Learn more.

THE HOME: {address}
THE HOME'S FILE: {research}
WHAT MAKES IT DIFFERENT: {differentiators}
PHOTOS (file | room | score | what is visible): {photos}

Answer with JSON only: {{"hooks": [{{"hook": "...", "primaryText": "...", "headline": "...",
"description": "...", "photoFile": "<a file name from PHOTOS>", "backedBy": "<the fact it rests on>"}}]}}"""


def _fallback_hooks(differentiators: List[str], address: str) -> List[Dict[str, Any]]:
    street = (address or "").split(",")[0].strip() or "this home"
    out = []
    for d in differentiators[:MAX_HOOKS]:
        d = re.sub(r"\s+", " ", str(d)).strip().rstrip(".")
        if not d:
            continue
        words = d.split()
        hook = ("Have you seen " + " ".join(words[:5]).lower() + "?") if len(words) <= 5 else ("Take a look: " + " ".join(words[:5]).lower())
        out.append({"hook": hook, "primaryText": f"{d}. See every room at {street}."[:125],
                    "headline": street[:40], "description": "", "backedBy": d})
    if not out:
        out.append({"hook": f"Take a look inside {street}", "primaryText": f"See every room at {street}."[:125],
                    "headline": street[:40], "description": "", "backedBy": "the listing"})
    return out


async def build_hooks(*, address: str, research: str, differentiators: List[str],
                      photo_index: str, learned: str = "") -> Dict[str, Any]:
    """Up to 3 hook versions that pass the rulebook. Never raises; always returns at least one."""
    raw: List[Dict[str, Any]] = []
    source = "rules"
    if llm.llm_available():
        try:
            reply = await llm.chat_json(
                "You write true-to-the-house real estate ad hooks. JSON only.",
                HOOK_PROMPT.format(address=address, research=(research or "")[:4000],
                                   differentiators="; ".join(str(d) for d in differentiators[:6]) or "not given",
                                   photos=(photo_index or "")[:3000])
                + (("\n\n" + learned[:2500]) if learned else ""),
                model=settings.OPENAI_MODEL_PLAN, max_completion_tokens=900)
            raw = [h for h in (reply or {}).get("hooks") or [] if isinstance(h, dict)]
            source = "model"
        except Exception as exc:  # noqa: BLE001 - the rules-based hook still gets an ad built
            log.warning("hook writer failed: %s", exc)
    if not raw:
        raw = _fallback_hooks(differentiators, address)
    kept, dropped = [], []
    for h in raw:
        h = ad_rulebook.fit({k: str(h.get(k) or "").strip() for k in
                             ("hook", "primaryText", "headline", "description", "photoFile", "backedBy")})
        h["ctaButton"] = "Learn more"
        issues = ad_rulebook.check(h)
        (dropped if issues else kept).append({**h, "issues": issues})
        if len(kept) >= MAX_HOOKS:
            break
    if not kept:
        safe = _fallback_hooks([], address)[0]
        kept = [{**safe, "ctaButton": "Learn more", "issues": []}]
    return {"hooks": kept, "dropped": dropped, "source": source, "rulebook": ad_rulebook.RULEBOOK_VERSION}


def hook_brief(hook: Dict[str, Any], *, shape: str, details: str, brand: Optional[Dict[str, Any]] = None) -> str:
    """The ad graphic: a few big words over the strongest photo, plus the agent's details."""
    size = "portrait 1024x1792 (9:16), keeping all words out of the top and bottom 14%" if shape == "9:16" \
        else "portrait 1024x1280 (4:5)"
    colors = [str(p[1]) for p in ((brand or {}).get("palette") or []) if isinstance(p, (list, tuple)) and len(p) > 1][:3]
    lines = [
        "Edit this real estate photograph into a scroll-stopping listing ad.",
        "Keep the photograph itself: same room, same light, same view. Do not add or remove anything.",
        f'Set exactly these words big and bold, spelled exactly as written: "{hook.get("hook", "")}". '
        "Nothing else large on the image.",
        f'In small type, the agent\'s details exactly as written: "{details}".' if details else "",
        "Minimal text: the message lives in the ad's text, not on the image.",
        ("Use these brand colours for any graphic elements: " + ", ".join(colors) + ".") if colors else "",
        f"Output a {size} PNG, opaque.",
    ]
    return "\n".join(x for x in lines if x)


async def hook_graphics(hooks: List[Dict[str, Any]], photo_for: Callable[[str], Optional[tuple]],
                        store: Callable[[bytes, str], str], *, details: str,
                        brand: Optional[Dict[str, Any]] = None) -> int:
    """Draw each hook's graphic in 4:5 and 9:16. Returns how many images were made."""
    from app.services import design
    made = 0
    for i, hook in enumerate(hooks):
        src = photo_for(hook.get("photoFile") or "")
        if not src or not src[0]:
            continue
        photo = design._to_png(src[0])
        hook["images"] = {}
        for shape in ("4:5", "9:16"):
            out = None
            if design.design_available():
                try:
                    out = await design._edit(design._photo_files(photo, "image/png", None, "", None),
                                             hook_brief(hook, shape=shape, details=details, brand=brand),
                                             model_name=design.model())
                except Exception as exc:  # noqa: BLE001
                    log.info("hook graphic %s %s fell back: %s", i, shape, exc)
            if out is None:
                colors = [p[1] for p in ((brand or {}).get("palette") or []) if len(p) > 1]
                out = design.fallback_design(photo, hook.get("hook", ""), details, colors)
            if out:
                hook["images"][shape] = store(out, f"ad-{i + 1}-{shape.replace(':', 'x')}")
                made += 1
    return made
