"""Engine 4's fixed rules for every post: no AI decides these (docs/engines/engine-4-brain.md).

* Hashtags (9f): Instagram 3-5, Facebook 0-2, at the end after a line break; one local tag, one
  niche real estate tag, one tag for what the post shows, the agent's own tag, and one trending tag
  only when it fits. No giant generic tags, no Fair Housing tags, rotated post to post.
* No links in Instagram captions (9c): the Instagram caption never carries a URL and ends with an
  invitation instead; the Facebook caption can carry the listing page link.
* Posting times (9f): only between 6 AM and 11 PM, the agent's local time, at the hour their
  audience is online most when Meta says so. Stored in UTC, which is what the publisher compares.
* The story arc (6) and the six post styles (4) the planner and the designer work from.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

# ------------------------------------------------------------------ hashtags
# Giant generic tags drown a post; these never go on (9f).
GENERIC_TAGS = {
    "realestate", "realtor", "realtorlife", "househunting", "dreamhome", "home", "homesweethome",
    "newhome", "forsale", "justlisted", "luxury", "luxuryrealestate", "househunt", "property",
    "investment", "homesforsale", "realestateagent", "interiordesign", "architecture", "love",
    "instagood", "photooftheday", "listing", "broker", "mortgage", "sold", "openhouse",
}
# Fair Housing applies to hashtags: nothing about who should live there.
FAIR_HOUSING_TAGS = re.compile(
    r"(family|families|kid|child|retire|senior|adult|single|couple|bachelor|christian|church|"
    r"safe|exclusive|executive|walkingdistancetochurch|nograd|student|empty ?nest|mancave|"
    r"master)", re.I)
INSTAGRAM_MAX, INSTAGRAM_MIN, FACEBOOK_MAX = 5, 3, 2

ROOM_TAGS = {
    "kitchen": "Kitchen", "living": "LivingRoom", "primary": "PrimarySuite", "bedroom": "Bedroom",
    "bath": "Bathroom", "pool": "PoolHome", "view": "ViewHome", "backyard": "Backyard",
    "front": "CurbAppeal", "exterior": "CurbAppeal", "aerial": "AerialView", "garage": "Shop",
    "office": "HomeOffice", "dining": "DiningRoom",
}


def _camel(text: str) -> str:
    return "".join(w[:1].upper() + w[1:] for w in re.findall(r"[A-Za-z0-9]+", text or ""))


def _tag(text: str) -> str:
    t = _camel(text)
    return "#" + t if t else ""


def clean_tag(tag: str) -> str:
    t = "#" + re.sub(r"[^A-Za-z0-9_]", "", str(tag or "").lstrip("#"))
    return t if len(t) > 2 else ""


def allowed(tag: str) -> bool:
    bare = tag.lstrip("#").lower()
    return bool(bare) and bare not in GENERIC_TAGS and not FAIR_HOUSING_TAGS.search(bare)


def city_of(address: str) -> str:
    """'905 Laurel Bend, Redding, CA 96001' -> 'Redding'."""
    parts = [p.strip() for p in (address or "").split(",")]
    return parts[1] if len(parts) >= 3 else (parts[-2] if len(parts) == 2 else "")


def agent_tag(kit: Dict[str, Any]) -> str:
    """The agent's own tag, the same on every post they ever make (set once on My Brand)."""
    own = clean_tag(kit.get("ownTag") or kit.get("hashtag") or "")
    if own:
        return own
    name = str(kit.get("agent") or "").strip()
    return ("#HomesWith" + _camel(name.split()[0])) if name else ""


def hashtags_for(*, index: int, room: str, address: str, kit: Dict[str, Any],
                 suggested: Optional[List[str]] = None, market: str = "") -> Tuple[List[str], List[str]]:
    """(instagram, facebook) tag lists for one post. Rotated by ``index`` so no two posts match."""
    city = city_of(address) or (market.split(",")[0].strip() if market else "")
    local = [_tag(city + " Homes"), _tag(city + " Real Estate"), _tag(city + " Living")] if city else []
    niche = [_tag(city + " Realtor"), _tag(city + " Listings"), _tag(city + " Home For Sale")] if city else []
    key = next((v for k, v in ROOM_TAGS.items() if k in (room or "").lower()), "")
    post_tag = _tag(city + " " + key) if (city and key) else ""
    own = agent_tag(kit)
    pool = [clean_tag(t) for t in (suggested or [])]
    pool = [t for t in pool if t and allowed(t)]

    ig: List[str] = []
    for t in (local[index % len(local)] if local else "",
              niche[(index + 1) % len(niche)] if niche else "",
              post_tag, own):
        if t and allowed(t) and t not in ig:
            ig.append(t)
    # Fill from the planner's own (trend-aware) suggestions, then the other local tags.
    for t in pool + local + niche:
        if len(ig) >= INSTAGRAM_MAX:
            break
        if t and allowed(t) and t not in ig and len(ig) < INSTAGRAM_MAX:
            ig.append(t)
    ig = ig[:INSTAGRAM_MAX]
    fb = [t for t in (local[0] if local else "", own) if t][:FACEBOOK_MAX]
    return ig, fb


# ------------------------------------------------------------------ captions
URL_RE = re.compile(r"(https?://\S+|www\.\S+|\b[a-z0-9-]+\.(?:com|net|org|realty|homes|io|co)(?:/\S*)?)", re.I)
TAG_BLOCK = re.compile(r"(\n\s*)?((#[A-Za-z0-9_]+\s*){1,})$")
INVITATIONS = ("Comment TOUR and I'll send you the details.", "Message me for a private showing.",
               "Comment INFO and I'll send you everything on this one.")


def strip_tags(caption: str) -> str:
    """The caption body without the hashtag block at its end."""
    return TAG_BLOCK.sub("", (caption or "").rstrip()).rstrip()


def without_links(body: str) -> str:
    text = URL_RE.sub("", body or "")
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"[ \t]+([.,!?])", r"\1", text).strip()


def instagram_caption(body: str, index: int = 0) -> str:
    """No links on Instagram (9c): drop any URL, and end with an invitation instead."""
    text = without_links(body)
    if not re.search(r"\b(comment|message me|dm me|send me a message)\b", text, re.I):
        lines = text.split("\n")
        # Keep the closing contact line last: the invitation goes just before it.
        if len(lines) > 1 and ("|" in lines[-1] or "Equal Housing" in lines[-1]):
            lines.insert(len(lines) - 1, INVITATIONS[index % len(INVITATIONS)])
            text = "\n".join(lines)
        else:
            text = (text + "\n\n" + INVITATIONS[index % len(INVITATIONS)]).strip()
    return text


def has_link(text: str) -> bool:
    return bool(URL_RE.search(text or ""))


def messages(post) -> Tuple[str, str]:
    """(facebook, instagram) text for one post, each with its own tags, never doubled."""
    body = strip_tags(getattr(post, "caption", "") or "")
    ig_tags = (getattr(post, "hashtags", "") or "").strip()
    fb_tags = getattr(post, "hashtags_fb", None)
    if fb_tags is None:
        # A post built before Engine 4 has one tag list: Facebook takes at most two of it.
        fb_tags = " ".join(ig_tags.split()[:FACEBOOK_MAX])
    fb_tags = fb_tags.strip()
    fb = (body + ("\n\n" + fb_tags if fb_tags else "")).strip()
    ig_body = getattr(post, "caption_ig", None)
    # Never a link on Instagram; the invitation is written at build time (older posts just lose links).
    ig_body = ig_body.strip() if ig_body else without_links(body)
    ig = (strip_tags(ig_body) + ("\n\n" + ig_tags if ig_tags else "")).strip()
    return fb, ig


# ------------------------------------------------------------------ posting times
EARLIEST, LATEST = 6, 23  # 6 AM to 11 PM, local
DEFAULT_HOURS = (18, 9)   # evening first, then morning: when agents' audiences scroll most
STATE_TZ = {
    **{s: "America/New_York" for s in ("CT DE DC FL GA ME MD MA MI NH NJ NY NC OH PA RI SC VT VA WV IN KY".split())},
    **{s: "America/Chicago" for s in ("AL AR IL IA KS LA MN MS MO NE ND OK SD TN TX WI".split())},
    **{s: "America/Denver" for s in ("CO MT NM UT WY ID".split())},
    "AZ": "America/Phoenix",
    **{s: "America/Los_Angeles" for s in ("CA NV OR WA".split())},
    "AK": "America/Anchorage", "HI": "Pacific/Honolulu",
}


def local_zone(address: str) -> ZoneInfo:
    """The listing's time zone from its state (the agent's audience is local to the listing)."""
    m = re.search(r",\s*([A-Z]{2})\b(?:\s+\d{5})?\s*$", (address or "").strip())
    name = STATE_TZ.get(m.group(1)) if m else None
    try:
        return ZoneInfo(name or "America/Los_Angeles")
    except Exception:  # noqa: BLE001
        return ZoneInfo("America/Los_Angeles")


def clamp_hour(hour: int) -> int:
    return max(EARLIEST, min(LATEST - 1, int(hour)))


def best_hours(online: Optional[Dict[int, float]] = None) -> Tuple[int, int]:
    """The two best local hours to post inside 6 AM-11 PM, from Meta's 'online followers' when known."""
    if online:
        ranked = sorted(((v, h) for h, v in online.items() if EARLIEST <= int(h) < LATEST), reverse=True)
        if ranked:
            first = int(ranked[0][1])
            second = next((int(h) for _, h in ranked[1:] if abs(int(h) - first) >= 6), DEFAULT_HOURS[1])
            return clamp_hour(first), clamp_hour(second)
    return DEFAULT_HOURS


def publish_at(day_date: date, slot: int, address: str, hours: Tuple[int, int] = DEFAULT_HOURS) -> str:
    """When a post goes out, as a naive UTC ISO string (what the publisher compares with utcnow)."""
    hour = clamp_hour(hours[0] if slot == 1 else hours[1])
    local = datetime.combine(day_date, time(hour, 0), tzinfo=local_zone(address))
    return local.astimezone(timezone.utc).replace(tzinfo=None).isoformat()


# ------------------------------------------------------------------ the story and the styles
STORY_ARC = (
    "STORY ARC (Engine 4, approved by Adam; fit it to THIS home, skip what it doesn't have): "
    "Day 1 just listed: the hero exterior, or the listing video if there is one. Day 2 highlights: the 3 "
    "or 4 things that make this home special. Days 3 to 6 room spotlights: kitchen, living, primary "
    "suite, the standout feature (pool, view, shop). Day 7 report day: a lifestyle moment. Day 8 the "
    "neighbourhood: local spots and commute, only from the research. Day 9 a note from the agent, in "
    "their voice. Days 10 and 11 more spotlights: outdoor space, details, a collage. Day 12 a question "
    "post that invites comments. Day 13 an open house or showing invite if one is set, otherwise last "
    "chance to see it this week. Day 14 a final spotlight. Facts marked please check are never stated "
    "as fact. No room on two days in a row.")

POST_STYLES = (
    ("full_photo", "full photo with the words overlaid on a soft gradient"),
    ("framed", "framed or boxed text panel over the photo"),
    ("collage", "a collage of 2 to 4 of the home's photos"),
    ("editorial", "minimal editorial: small refined type, lots of air"),
    ("bold_type", "bold typographic: a few big words carry the post"),
    ("magazine", "magazine cover: masthead-style title and a cover line"),
)
DETAIL_TREATMENTS = (
    "a slim footer bar", "a small signature line", "a corner mark", "built into the layout",
)


def style_plan(n: int, liked: Optional[Dict[str, int]] = None, avoid: Optional[List[str]] = None,
               last: Optional[List[str]] = None, seed: int = 0) -> List[str]:
    """One style per post: about two thirds the styles they've liked, one third new; never the same
    style twice in a row, and never the same sequence as their last campaign."""
    keys = [k for k, _ in POST_STYLES if k not in set(avoid or [])] or [k for k, _ in POST_STYLES]
    liked = {k: v for k, v in (liked or {}).items() if k in keys and v > 0}
    familiar = sorted(liked, key=lambda k: -liked[k]) or keys[:3]
    fresh = [k for k in keys if k not in familiar] or keys
    out: List[str] = []
    turns = {"familiar": seed, "fresh": seed}
    for i in range(n):
        which = "fresh" if (i % 3 == 2) else "familiar"
        pool = fresh if which == "fresh" else familiar
        k = pool[turns[which] % len(pool)]
        turns[which] += 1
        if out and k == out[-1]:
            alt = [x for x in keys if x != out[-1]]
            k = alt[(i + seed) % len(alt)]
        out.append(k)
    if last and out == list(last)[:n]:
        out = out[1:] + out[:1]
        for i in range(1, len(out)):
            if out[i] == out[i - 1]:
                out[i] = next(x for x in keys if x != out[i - 1])
    return out


def style_words(key: str) -> str:
    return dict(POST_STYLES).get(key, POST_STYLES[0][1])
