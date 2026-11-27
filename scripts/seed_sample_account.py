"""Clear the test campaigns and build the sample account (resmaraai@gmail.com).

The team showed Resmara from an account full of failed test builds ("Build failed", "testing",
duplicates). This script does two jobs, deliberately in one place so the demo can be rebuilt:

    python scripts/seed_sample_account.py --clear-tests      # back up, then delete TEST accounts' boosts
    python scripts/seed_sample_account.py --seed             # build the demo book of campaigns
    python scripts/seed_sample_account.py --clear-tests --seed

The demo book is five campaigns on one brand, each at a different stage of the product:

    Awaiting approval   built, 14 posts, waiting on the agent
    Ready to go live    approved and launched, go-live date still ahead
    Active              6 of 14 posts published, live listing page, two new leads
    Paused              paused by the agent two days ago, 9 of 14 published
    Completed           all 14 published, listing sold

Rows this script owns carry ``plan["_sample"] = True``; running --seed again replaces exactly
those, so it never touches a real campaign. Everything is written through the app's own models
and ``listing_site.build(writer=offline_words)`` - no LLM call, no Meta call, no email.

Photos: each campaign imports a full gallery (20+) from a real listing page through the app's
own importer, re-encoded to a 1600 px JPEG, and a local vision model tags each photo's room so the
copy on that day names the room the picture actually shows. A 14-day campaign gets 14 DIFFERENT
photos, one per day - never the same picture twice - and the rest of the gallery stays for the
listing page. ``GALLERY_MIN`` is the floor: a run that cannot reach it for a campaign fails loudly
instead of seeding a five-photo demo.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import io
import json
import os
import sys
from datetime import date, datetime, time as dtime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ssl  # noqa: E402
import urllib.request  # noqa: E402

from PIL import Image  # noqa: E402

from app.db.session import (  # noqa: E402
    Ad, Asset, Base, Boost, Event, Lead, ListingSite, Order, Post, SessionLocal, User,
)
from app.core.testdata import is_test_user  # noqa: E402

SAMPLE_EMAIL = "resmaraai@gmail.com"

# The brand the sample account speaks in. The app's own signed-out demo kit, so a prospect who
# has seen the website recognises the same agent.
BRAND = {
    "agent": "Morgan Ellis",
    "brokerage": "Morgan & Co. Property Advisors",
    "license": "TX #0712345",
    "brokerLicense": "TX #9012345",
    "phone": "(512) 555-0148",
    "website": "https://morganandco.example",
    "market": "West Austin, Lakeway and the Hill Country",
    "brandLink": "https://instagram.com/morganellis.example",
    "instagram": "morganellis.example",
    "palette": [["Primary", "#143A50"], ["Accent", "#B8925A"], ["Text", "#2B2B2B"],
                ["Tint", "#E9E1D3"], ["Page", "#FAF7F1"]],
    "colours": "#143A50, #B8925A, #2B2B2B, #E9E1D3, #FAF7F1",
    "colour": "#143A50",
    "fonts": ["Playfair Display", "Jost"],
    "theme": "Modern",
    "voice": ("Warm. Assured. Unhurried. Speaks like a neighbour who knows the area, never "
              "like an ad."),
    "voiceOfClient": (
        "Morgan has sold homes in west Austin for eleven years. Clients describe her as calm, "
        "direct and quick to answer. She writes the way she talks: short sentences, no hard "
        "sell, and she always names the part of the house she loves most."),
    "use": ["Come walk it with me", "Room to breathe", "Slow mornings"],
    "avoid": ["Stunning", "Must-see", "Hurry!"],
    "legal": ["Morgan Ellis \u00b7 REALTOR\u00ae \u00b7 TX #0712345",
              "Morgan & Co. Property Advisors", "Equal Housing Opportunity"],
    "sources": [["Website", "morganandco.example"], ["Instagram", "@morganellis"],
                ["Brokerage", "Morgan & Co."]],
    "researched": "from your website",
    "ownTag": "#SellingWithMorgan",
}
SIGNATURE = " | ".join(BRAND["legal"])
HASHTAGS = ["#AustinRealEstate", "#WestAustinHomes", "#AustinRealtor",
            "#MorganEllisHomes", "#HomesForSaleAustin"]

# Room -> (title, kicker, overlay, opener, body, cta)
ROOMS = {
    "front exterior": (
        "Just listed", "WELCOME HOME", "The walk up",
        "Just listed in {city}.",
        "The front elevation is quiet from the street and opens up as soon as you are through "
        "the door. Mature trees, a deep porch and a drive that does not crowd the house.",
        "Message me for a private showing."),
    "living room": (
        "Where the day starts", "THE LIVING ROOM", "Room to breathe",
        "Here is the living room, photographed exactly as it looks today.",
        "Tall windows on two walls, wide oak floors and enough room that the furniture still "
        "has somewhere to go. This is the room people sit down in and stay.",
        "Ask me for a walk-through."),
    "kitchen": (
        "The kitchen island", "THE KITCHEN", "Everyone ends up here",
        "The kitchen is the heart of this house and it earns it.",
        "A long island, work surfaces that do not fight the light and sightlines through to the "
        "living room, so the cook is never in another room from everyone else.",
        "Call or text me with a time that suits."),
    "dining room": (
        "Room to gather", "THE DINING ROOM", "Dinner at seven",
        "The dining room sits in the quiet part of the plan.",
        "Bright and open with a wide window, warm floors and space for a table that actually "
        "seats the people you invite.",
        "Message me for a private showing."),
    "primary bedroom": (
        "The long view", "PRIMARY SUITE", "Slow mornings",
        "The primary suite is the whole back corner of this house.",
        "Windows on two sides, a ceiling that lets the room breathe and a bathroom that is "
        "its own part of the morning rather than a corner of the bedroom.",
        "Ask me for a walk-through."),
    "bathroom": (
        "The light in here", "PRIMARY BATH", "A quiet start",
        "A closer look at the primary bath.",
        "Deep tub, walk-in shower and a window that is only yours. The finishes are calm rather "
        "than shiny, which is why they will still look right in five years.",
        "Message me to see it in person."),
    "back garden": (
        "The back garden", "OUTSIDE", "End of the day",
        "Out back, the house gives you somewhere to end the day.",
        "A covered run of the garden, room for a table, and planting that is already grown in "
        "rather than a lawn waiting to be planted.",
        "Call or text me anytime."),
    "home office": (
        "The office", "THE STUDY", "A door that closes",
        "There is a real study behind a real door.",
        "Built-in shelving, a window at your shoulder and enough wall for two screens and a "
        "bookcase without the room feeling like a spare bedroom with a desk in it.",
        "Ask me for a walk-through."),
    "other bedroom": (
        "The second bedroom", "GUEST ROOM", "Room for everyone",
        "The second bedroom is the one guests fight over.",
        "A bright corner room with a proper closet and a window above the trees, close enough "
        "to the kitchen to hear the coffee but not the traffic.",
        "Message me for a private showing."),
    "guest room": (
        "The guest room", "GUESTS", "They can stay",
        "The guest room means people can actually stay.",
        "A quiet corner room away from the living side of the house, with its own window and "
        "closet, and a bathroom a few steps down the hall.",
        "Message me for a private showing."),
    # Rooms the vision tagger can name that have no canned paragraph: say something true about the
    # house without claiming a room it might not be.
    "other": (
        "A closer look", "THE HOUSE", "Take your time",
        "A closer look at the house, photographed the week it was listed.",
        "The kind of detail that does not photograph as a headline but is the reason people stay "
        "once they are inside.",
        "Message me for a private showing."),
    "laundry": (
        "The practical end of the house", "LAUNDRY", "Where it gets done",
        "There is a proper laundry room, not a cupboard.",
        "Room for the machines, a counter for folding and a door that closes on the noise.",
        "Ask me for a walk-through."),
    "garage": (
        "The garage", "GARAGE", "Room for the cars",
        "The garage is bigger than the photos make it look.",
        "Two bays, a wall for storage and a door straight into the house on a wet morning.",
        "Call or text me anytime."),
    "hallway": (
        "The first ten steps", "THE ENTRY", "Through the door",
        "The entry tells you how the rest of the house is going to feel.",
        "Wide enough for a bench and a coat hook, with the light following you into the rooms.",
        "Message me for a private showing."),
    "pool": (
        "The pool", "OUTSIDE", "Summer, sorted",
        "The pool sits where the afternoon sun lands.",
        "Room for loungers and a table, screened from the street and a few steps from the house.",
        "Ask me for a walk-through."),
}
ROOM_ORDER = ["front exterior", "living room", "kitchen", "dining room", "primary bedroom",
              "bathroom", "home office", "back garden", "other bedroom"]
ROOM_CYCLE = ROOM_ORDER + ["other bedroom", "living room", "kitchen", "back garden", "bathroom"]

# The agent's own clock (the brand is in Austin). publish_at is stored in UTC - the calendar
# converts it back with localTime(), which is why a 10:00 row would otherwise read 2:00 AM.
SCHEDULE_ZONE = ZoneInfo("America/Chicago")
TIMES = ["10:00", "12:00", "17:30"]


def _publish_at(day: date, hhmm: str) -> str:
    """Local schedule time -> the UTC string the server stores."""
    h, m = (int(x) for x in hhmm.split(":"))
    local = datetime(day.year, day.month, day.day, h, m, tzinfo=SCHEDULE_ZONE)
    return local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _hash() -> str:
    return hashlib.sha256(os.urandom(16)).hexdigest()[:32]


def _fetch_bytes(filename: str) -> bytes | None:
    """A photo whose bytes are not on its row (only the file on the host): ask the live app for
    it. The preview route re-encodes, so this also keeps the download small."""
    import certifi
    ctx = ssl.create_default_context(cafile=certifi.where())
    for url in (f"https://www.resmara.com/uploads/{filename}?w=1600",
                f"https://www.resmara.com/uploads/{filename}"):
        try:
            with urllib.request.urlopen(url, timeout=30, context=ctx) as r:  # noqa: S310
                return r.read()
        except Exception:  # noqa: BLE001 - try the original next
            continue
    return None


def _resize_jpeg(data: bytes) -> bytes | None:
    """1600 px on the long edge, JPEG. The detail page only ever draws this size."""
    try:
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGB")
    except Exception:  # noqa: BLE001 - a broken photo is dropped, not guessed at
        return None
    img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    img.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    return out.getvalue()


# --------------------------------------------------------------------------------------- cleaning
def backup(db, path: Path) -> dict:
    """Every row about to be deleted, minus image bytes (they are test photos, and the file would
    be hundreds of MB). Written before anything is touched."""
    boosts = db.query(Boost).all()
    ids = [b.id for b in boosts]
    dump = {
        "taken_at": datetime.now(timezone.utc).isoformat(),
        "boosts": [], "posts": [], "assets": [], "ads": [], "leads": [],
        "events": [], "orders": [], "listing_sites": [],
    }
    for b in boosts:
        dump["boosts"].append({c.name: str(getattr(b, c.name)) for c in b.__table__.columns})
    if ids:
        for model, key in ((Post, "posts"), (Ad, "ads"), (Lead, "leads"), (ListingSite, "listing_sites")):
            for row in db.query(model).filter(model.boost_id.in_(ids)).all():
                dump[key].append({c.name: str(getattr(row, c.name)) for c in row.__table__.columns})
        for row in db.query(Asset).filter(Asset.boost_id.in_(ids)).all():
            dump["assets"].append({c.name: str(getattr(row, c.name)) for c in row.__table__.columns
                                   if c.name != "data"})
        for row in db.query(Event).filter(Event.boost_id.in_(ids)).all():
            dump["events"].append({c.name: str(getattr(row, c.name)) for c in row.__table__.columns})
        for row in db.query(Order).filter(Order.boost_id.in_(ids)).all():
            dump["orders"].append({c.name: str(getattr(row, c.name)) for c in row.__table__.columns})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dump, indent=1, default=str))
    return {k: (len(v) if isinstance(v, list) else v) for k, v in dump.items()}


def clear_tests(db, *, keep_sample: bool = False, include_emails=None) -> list[str]:
    """Delete campaigns that belong to a test account. Never a person's campaign.

    The rule used to be "every campaign with no paid order", which on 24 Nov 2026 deleted a
    collaborator's real build for 892 Coggins St, Redding - 16 uploaded photos, no backup of the
    image bytes - one hour after it failed on provider credits. A demo reset must not be able to
    do that again, so the owner is checked: only an account the team marked as a test account
    (``users.is_test``) or one using a throwaway test email is cleared. A real address can still
    be cleared on purpose by naming it in ``include_emails``.
    """
    wanted = {(e or "").strip().lower() for e in (include_emails or set()) if e}
    paid = {o.boost_id for o in db.query(Order).filter(Order.status.in_(("paid", "complete"))).all()}
    owners = {u.id: u for u in db.query(User).all()}
    gone = []
    for b in db.query(Boost).all():
        if keep_sample and (b.plan or {}).get("_sample"):
            continue
        if b.id in paid:
            print(f"  keeping boost {b.id} ({b.address}): a real order exists")
            continue
        owner = owners.get(b.user_id)
        by_request = owner is not None and (owner.email or "").strip().lower() in wanted
        if not (is_test_user(owner) or by_request):
            who = owner.email if owner is not None else "no account"
            print(f"  keeping boost {b.id} ({b.address}): {who} is not a test account")
            continue
        gone.append(f"boost {b.id} · {b.address} · {b.main_status}")
        db.query(Event).filter(Event.boost_id == b.id).delete()
        db.query(Lead).filter(Lead.boost_id == b.id).delete()
        db.query(Ad).filter(Ad.boost_id == b.id).delete()
        db.query(Post).filter(Post.boost_id == b.id).delete()
        db.query(Asset).filter(Asset.boost_id == b.id).delete()
        db.query(ListingSite).filter(ListingSite.boost_id == b.id).delete()
        db.query(Order).filter(Order.boost_id == b.id).delete()
        db.delete(b)
    db.commit()
    return gone


# ----------------------------------------------------------------------------------------- photos
# A 14-day campaign needs at least one photo per day, and the demo has to LOOK like a real listing,
# so every sample campaign imports a full gallery from a real listing page (the app's own importer)
# instead of a handful of leftovers. 20+ photos each, tagged by a local vision model so the copy on
# each day names the room that photo actually shows.
GALLERY_MIN = 14          # one photo per campaign day - the whole point of the rebuild
GALLERY_SIZE = 20         # what we ask the importer for

ROOM_LABELS = (
    "front exterior, back garden, living room, kitchen, dining room, primary bedroom, bedroom, "
    "bathroom, office, laundry, garage, hallway, pool, other"
)
ROOM_MAP = {
    "bedroom": "other bedroom", "guest bedroom": "other bedroom",
    "master bedroom": "primary bedroom", "primary suite": "primary bedroom",
    "home office": "home office", "study": "home office",
    "exterior": "front exterior", "front yard": "front exterior", "backyard": "back garden",
    "yard": "back garden", "garden": "back garden", "patio": "back garden",
    "dining area": "dining room", "living area": "living room", "family room": "living room",
    "bath": "bathroom", "kitchen/dining": "kitchen",
}


def _tag_room(jpeg: bytes) -> str:
    """One word of truth about the photo, from a local vision model. No cloud call, no cost."""
    import base64
    try:
        import urllib.request as _rq
        small = io.BytesIO()
        img = Image.open(io.BytesIO(jpeg))
        img.thumbnail((640, 640))
        img.convert("RGB").save(small, "JPEG", quality=80)
        payload = json.dumps({
            "model": os.environ.get("RESMARA_TAG_MODEL", "qwen2.5vl:3b"),
            "prompt": ("This is a photo from a real-estate listing. Which part of the house is it? "
                       "Answer with exactly one of: " + ROOM_LABELS),
            "images": [base64.b64encode(small.getvalue()).decode()],
            "stream": False, "options": {"temperature": 0, "num_predict": 12},
        }).encode()
        req = _rq.Request("http://127.0.0.1:11434/api/generate", data=payload,
                          headers={"Content-Type": "application/json"})
        with _rq.urlopen(req, timeout=90) as resp:   # noqa: S310 - loopback
            said = json.loads(resp.read().decode()).get("response", "")
    except Exception:  # noqa: BLE001 - a tag is a nicety, the photo is the point
        return "other"
    said = " ".join(str(said).lower().replace("\n", " ").split()).strip(" .,:;")
    if said in ROOM_MAP:
        return ROOM_MAP[said]
    for label in sorted(list(ROOM_MAP) + list(ROOMS) + ["other"], key=len, reverse=True):
        if said == label or said.startswith(label):
            return ROOM_MAP.get(label, label)
    return "other"


async def _download(url: str) -> bytes | None:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=40, follow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}) as c:
            r = await c.get(url)
            if r.status_code != 200:
                return None
            return r.content
    except Exception:  # noqa: BLE001
        return None


async def import_photos(db, boost: Boost, user: User, listing_url: str,
                        want: int = GALLERY_SIZE) -> list[tuple[str, str]]:
    """A full gallery for this campaign, from a real listing page. Returns [(filename, room)].

    Raises when the page gives up fewer than GALLERY_MIN photos: a demo campaign with five photos
    is exactly the bug this replaces, so it is better to fail loudly than to seed it.
    """
    from app.services import photos as photos_service

    urls = await photos_service.discover(listing_url, limit=want)
    urls = [u for u in urls if u][:want]
    if len(urls) < GALLERY_MIN:
        raise SystemExit(f"gallery import for {boost.address} returned {len(urls)} photos "
                         f"from {listing_url} - need at least {GALLERY_MIN}")

    made: list[tuple[str, str]] = []
    for url in urls:
        raw = await _download(url)
        data = _resize_jpeg(raw) if raw else None
        if not data:
            continue
        room = _tag_room(data)
        name = _hash() + ".jpg"
        db.add(Asset(user_id=user.id, boost_id=boost.id, filename=name, url=f"/uploads/{name}",
                     original_name=url.rsplit("/", 1)[-1][:120], kind="photo", room=room,
                     social_score="8", shape="landscape", tags=[f"ROOM: {room}"],
                     tagged_by="sample-vision", see="", story="",
                     data=data, content_type="image/jpeg"))
        made.append((name, room))
    db.commit()
    if len(made) < GALLERY_MIN:
        raise SystemExit(f"only {len(made)} of {len(urls)} photos downloaded for {boost.address}")
    return made


# ------------------------------------------------------------------------------------------ posts
# The 14-day content arc. The copy is keyed to the DAY, not to the room: the gallery's photos are
# tagged by a vision model that can only say "kitchen" or "living room", and a campaign with four
# kitchen photos would otherwise publish four identical captions. One arc per campaign means every
# day reads differently, and the photo on that day is its own.
DAY_ARC = [
    ("Just listed", "WELCOME HOME", "The walk up",
     "Just listed in {city}.",
     "The front elevation is quiet from the street and opens up as soon as you are through the door. "
     "Mature trees, a deep porch and a drive that does not crowd the house.",
     "Message me for a private showing."),
    ("Property highlights", "WHAT YOU GET", "Worth a second look",
     "A first walk through the house, room by room.",
     "Light on two sides, floors that run the length of the plan and a layout that keeps the busy "
     "parts away from the quiet ones.",
     "Ask me for a walk-through."),
    ("Step inside", "THE ENTRY", "Through the door",
     "The entry tells you how the rest of the house is going to feel.",
     "Wide enough for a bench and a coat hook, with the light following you into the rooms.",
     "Message me for a private showing."),
    ("Room spotlight", "SPOTLIGHT", "This one",
     "The room people stop in.",
     "It is the one the photos do not do justice to: the scale only makes sense when you are standing "
     "in it, with the garden on one side and the rest of the house on the other.",
     "Call or text me with a time that suits."),
    ("The details", "THE FINISH", "Done properly",
     "The parts of a house that age well.",
     "Solid surfaces, honest materials and joinery done properly the first time - the things that are "
     "still right in ten years.",
     "Message me for a private showing."),
    ("A closer look", "UP CLOSE", "Take your time",
     "A closer look at the house, photographed the week it was listed.",
     "The kind of detail that never makes a headline but is the reason people stay once they are inside.",
     "Ask me for a walk-through."),
    ("Weekend viewing", "COME SEE IT", "Saturday morning",
     "Open this weekend, and it is worth the drive.",
     "Bring your questions - about the roof, the systems, the street - and I will have the answers or "
     "get them before you leave.",
     "Message me to book a time."),
    ("Around town", "THE AREA", "Minutes from here",
     "The house is one thing; the ten minutes around it is the other half.",
     "Coffee, groceries, the school run and the trailhead are all a short drive, and the street "
     "itself stays quiet in the evenings.",
     "Ask me anything about the area."),
    ("Design details", "THE LOOK", "Chosen, not defaulted",
     "The finishes were chosen rather than defaulted.",
     "Warm floors, neutral walls and lighting that was actually thought about, so the house takes "
     "your furniture instead of fighting it.",
     "Message me for a private showing."),
    ("Living spaces", "ROOM TO LIVE", "Everyday life",
     "This is what the plan is for: ordinary days.",
     "Somewhere to work, somewhere to gather and somewhere to be on your own without leaving the house.",
     "Call or text me anytime."),
    ("Key features", "WHAT MATTERS", "The list",
     "The short version, for the people who read the listing twice.",
     "The layout, the light, the storage and the garden - the four things that come up on every "
     "second viewing.",
     "Ask me for the full list."),
    ("Viewing reminder", "STILL AVAILABLE", "Yes, it is",
     "Still available, and the sellers are motivated.",
     "If this one has been sitting in your saved list, this is the week to walk it. Showings are easy "
     "to arrange.",
     "Message me for a private showing."),
    ("Outdoor living", "OUTSIDE", "End of the day",
     "Out back, the house gives you somewhere to end the day.",
     "A covered run of the garden, room for a table, and planting that is already grown in rather than "
     "a lawn waiting to be planted.",
     "Call or text me with a time that suits."),
    ("Final spotlight", "LAST LOOK", "One more time",
     "One more look before the weekend.",
     "If you have been waiting for a reason to see this house, this is it - the photos are good, but "
     "the house is better.",
     "Message me and I will set it up."),
]


def caption(day: int, city: str) -> tuple[str, str, str, str]:
    """The copy for one day of the arc: title, kicker, overlay, caption."""
    title, kicker, overlay, opener, body, cta = DAY_ARC[(day - 1) % len(DAY_ARC)]
    text = (f"{opener.format(city=city)} {body}\n\n{cta}\n\n{SIGNATURE}\n\n" + " ".join(HASHTAGS))
    return title, kicker, overlay, text


def build_posts(db, boost: Boost, photos: list[tuple[str, str]], spec: dict) -> list[Post]:
    """14 days of posts, ONE PHOTO PER DAY - no photo repeats inside a campaign.

    The gallery is 20+ photos, so the arc opens on the exterior and then walks the rooms; the
    photos left over stay in the gallery for the listing page. `spec['published']` of the days
    went out (the publisher stores "posted").
    """
    rows: list[Post] = []
    start = date.fromisoformat(boost.go_live_date) if boost.go_live_date else date.today()
    ordered = sorted(photos, key=lambda p: ROOM_ORDER.index(p[1]) if p[1] in ROOM_ORDER else 99)
    for i in range(14):
        day = i + 1
        filename, room = ordered[i] if i < len(ordered) else ("", ROOM_CYCLE[i])
        # Prefer the room of the photo actually shipped on that day.
        title, kicker, overlay, text = caption(day, spec["city"])
        when = start + timedelta(days=i)
        posted = day <= spec["published"]
        if not posted and spec.get("shift_days"):
            # A paused campaign's remaining posts move out by the time it has been paused, so
            # the calendar does not show five posts that were due while it was stopped.
            when += timedelta(days=int(spec["shift_days"]))
        post = Post(
            boost_id=boost.id, day=day, slot=1,
            kind="static", caption=text, hashtags="", cta=DAY_ARC[(day - 1) % len(DAY_ARC)][5],
            image_url=f"/uploads/{filename}" if filename else "",
            client_status="approved" if spec.get("approved", True) else "pending",
            publish_at=_publish_at(when, TIMES[(day - 1) % 3]),
            publish_status="posted" if posted else "scheduled",
            publish_target="both",
            title=title, kicker=kicker, overlay_text=overlay,
            photo_room="", photo_file=filename, post_type="photo",
            design_style="overlay", details_treatment="agent-card",
            fb_post_id=f"sample_fb_{boost.id}_{day}" if posted else None,
            ig_media_id=f"sample_ig_{boost.id}_{day}" if posted else None,
        )
        db.add(post)
        rows.append(post)
    db.commit()
    return rows


def build_ad(db, boost: Boost, posts: list[Post], spec: dict) -> Ad:
    ad = Ad(boost_id=boost.id, kind="photo", format="carousel",
            primary_text=(f"{boost.address.split(',')[0]} is on the market in {spec['city']}. "
                          f"{spec['facts']}. Walk the whole house before you drive over - every "
                          f"room, the back garden and the street it sits on."),
            headline=boost.address.split(",")[0],
            description=f"A {boost.campaign_days}-day campaign by Resmara",
            cta_button="Learn More", creative_asset_ids=[], card_post_ids=[p.id for p in posts[:5]],
            status=spec.get("ad_status", "draft"))
    db.add(ad)
    db.commit()
    return ad


def build_leads(db, boost: Boost, posts: list[Post], spec: dict) -> int:
    rows = [
        dict(platform="instagram", channel="Instagram", source="comment",
             platform_comment_id=f"sample-ig-{boost.id}-1", author_name="Sarah Mitchell",
             author_handle="@sarah.mitchell.atx",
             text="Is this still available? We'd love to see it this weekend.",
             permalink="https://instagram.com/p/sample", post_label=posts[2].title,
             comment_at=datetime.now(timezone.utc) - timedelta(hours=5), status="new",
             classified_by="ai", confidence=0.93, reason="asks to see the home"),
        dict(platform="manual", channel="Listing page form", source="form",
             platform_comment_id=None, author_name="Daniel Reyes", author_handle=None,
             text="Relocating from Denver in January. Could we tour this Saturday morning?",
             post_label=None, email="daniel.reyes@example.com", phone="(512) 555-0193",
             wants="showing", comment_at=datetime.now(timezone.utc) - timedelta(hours=2),
             status="new", classified_by="manual", confidence=1.0),
        dict(platform="facebook", channel="Facebook ad", source="ad_comment",
             platform_comment_id=f"sample-fb-{boost.id}-2", author_name="Priya Shah",
             author_handle=None, text="What's the asking price? And is the garden fenced?",
             post_label="The ad", comment_at=datetime.now(timezone.utc) - timedelta(days=1),
             status="handled", classified_by="ai", confidence=0.88,
             note="Called back - wants the price and a Saturday slot."),
    ]
    n = 0
    for row in rows:
        db.add(Lead(boost_id=boost.id, user_id=boost.user_id, **row))
        n += 1
    db.commit()
    return n


# ------------------------------------------------------------------------------------- the stages
STAGES = [
    dict(
        key="awaiting", address="1809 Woodland Avenue, Austin, TX 78704", city="Austin",
        facts="3 beds · 2 baths · 1,860 sq ft · $845,000", price="$845,000",
        created_days_ago=1, go_in_days=2, launched=False, published=0, approved=False,
        stage="PENDING", main_status="Awaiting approval",
        gallery="https://www.trulia.com/home/3710-riverview-dr-redding-ca-96001-15208370",
        description="Built, waiting on the agent: 14 posts, calendar not approved yet.",
    ),
    dict(
        key="ready", address="4412 Bell Mountain Drive, Austin, TX 78731", city="Austin",
        facts="4 beds · 3 baths · 2,640 sq ft · $1,150,000", price="$1,150,000",
        created_days_ago=2, go_in_days=3, launched=True, published=0, approved=True,
        stage="APPROVED", main_status="Approved",
        gallery="https://www.trulia.com/home/700-royal-oaks-dr-redding-ca-96001-15230716",
        description="Approved and launched, go-live date still ahead.",
    ),
    dict(
        key="active", address="1204 Lost Creek Boulevard, Austin, TX 78746", city="Austin",
        facts="4 beds · 3.5 baths · 3,180 sq ft · $1,285,000", price="$1,285,000",
        created_days_ago=7, go_in_days=-6, launched=True, published=6, approved=True,
        stage="LIVE", main_status="Active",
        gallery="https://www.trulia.com/home/4626-nantucket-dr-redding-ca-96001-79849568",
        listing_status="active", until_sold=True, ad_status="live", leads=True,
        description="Live: 6 of 14 posts published, listing page up, two new leads.",
    ),
    dict(
        key="paused", address="2301 Woodmont Avenue, Austin, TX 78703", city="Austin",
        facts="3 beds · 2.5 baths · 2,110 sq ft · $975,000", price="$975,000",
        created_days_ago=12, go_in_days=-10, launched=True, published=9, approved=True,
        stage="LIVE", main_status="Paused",
        gallery="https://www.trulia.com/home/5855-poppy-hills-dr-redding-ca-96003-15221909",
        listing_status="active", paused_days_ago=2, paused_reason="agent", ad_status="paused",
        shift_days=2,
        description="Paused by the agent two days ago: 9 of 14 published, 5 held.",
    ),
    dict(
        key="completed", address="5604 Highland Hills Drive, Austin, TX 78731", city="Austin",
        facts="5 beds · 4 baths · 3,720 sq ft · $1,540,000", price="$1,540,000",
        created_days_ago=22, go_in_days=-20, launched=True, published=14, approved=True,
        stage="LIVE", main_status="Completed",
        gallery="https://www.trulia.com/home/1437-casa-vereda-way-redding-ca-96003-15221053",
        listing_status="sold", paused_days_ago=6, paused_reason="sold", ad_status="live",
        description="Finished: all 14 posts published, the listing sold.",
    ),
]


async def seed(db, user: User) -> list[str]:
    from app.services.listing_site import build as build_site, offline_words

    today = date.today()
    now = datetime.now(timezone.utc)
    report = []
    for spec in STAGES:
        created = now - timedelta(days=spec["created_days_ago"])
        go_live = today + timedelta(days=spec["go_in_days"])
        boost = Boost(
            user_id=user.id, address=spec["address"], tier="bap_shoot_499",
            main_status=spec["main_status"], campaign_days=14, ad_budget_usd=50.0,
            property_facts=f"{spec['facts']} · Listed with Morgan & Co.",
            brand_profile=BRAND, stage=spec["stage"],
            go_live_date=go_live.isoformat(),
            plan={"_sample": True, "summary": spec["description"],
                  "propertyStory": {"thesis": "One walk through the home, front door to back fence.",
                                    "differentiators": ["Light on two sides", "Garden already grown in",
                                                        "Walkable to the neighbourhood shops"]},
                  "storyArc": "Arrival, the rooms you live in, then the garden at the end of the day."},
            paid_at=created, paid_amount_cents=4900, paid_source="website",
            listing_status=spec.get("listing_status"),
            until_sold=bool(spec.get("until_sold")),
            until_sold_at=created if spec.get("until_sold") else None,
            paused_at=(now - timedelta(days=spec["paused_days_ago"])) if spec.get("paused_days_ago") else None,
            paused_reason=spec.get("paused_reason"),
            photo_permission_at=created,
            created_at=created,
            launched_at=None,
        )
        if spec["launched"]:
            # Approved the day the campaign was launched (or the day before a launch still to
            # come), mid-morning rather than at the UTC hour the row was written.
            launch_day = go_live if go_live <= today else go_live - timedelta(days=1)
            boost.launched_at = datetime.combine(launch_day, dtime(15, 0), tzinfo=timezone.utc)
        db.add(boost)
        db.commit()
        db.refresh(boost)

        photos = await import_photos(db, boost, user, spec["gallery"])
        posts = build_posts(db, boost, photos, spec)
        build_ad(db, boost, posts, spec)
        if spec.get("leads"):
            build_leads(db, boost, posts, spec)
        for kind, payload in (
            ("campaign_drafted", {"address": boost.address, "days": 14}),
            ("campaign_built", {"posts": len(posts), "sample": True}),
        ):
            db.add(Event(user_id=user.id, boost_id=boost.id, event_type=kind, payload=payload,
                         created_at=created + timedelta(hours=1)))
        if spec["launched"]:
            db.add(Event(user_id=user.id, boost_id=boost.id, event_type="campaign_approved",
                         payload={"sample": True}, created_at=boost.launched_at))
        if spec.get("paused_days_ago"):
            db.add(Event(user_id=user.id, boost_id=boost.id, event_type="campaign_paused",
                         payload={"reason": spec["paused_reason"], "by": "agent", "sample": True},
                         created_at=boost.paused_at))
        db.commit()

        # The listing website, built the way the app builds it, without an LLM call.
        async def writer(b, kit, ph):  # noqa: ANN001 - matches listing_site's writer signature
            return offline_words(b, ph)

        try:
            site = await build_site(db, boost, writer=writer)
            # The agent's own price, the way the console sets it - an offline build only knows the
            # city, so without this the demo page asks the buyer about pricing.
            digits = "".join(ch for ch in spec["price"] if ch.isdigit())
            if digits:
                site.price_cents = int(digits) * 100
                site.price_mode = "agent"
                db.commit()
                from app.services.listing_site import touch as touch_site
                touch_site(db, site)
            site_url = f"/l/{site.slug}"
        except Exception as exc:  # noqa: BLE001 - the campaign is still worth having
            site_url = f"(site not built: {exc})"
        report.append(f"{spec['key']:<10} boost {boost.id:<4} {boost.address} -> {site_url}")
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clear-tests", action="store_true",
                    help="delete unpaid campaigns that belong to TEST accounts (never a person's)")
    ap.add_argument("--include-email", action="append", default=[], metavar="ADDRESS",
                    help="also clear this account's unpaid campaigns (repeatable; the deliberate way "
                         "to clear a real account)")
    ap.add_argument("--seed", action="store_true", help="(re)build the sample account's campaigns")
    ap.add_argument("--email", default=SAMPLE_EMAIL)
    args = ap.parse_args()
    if not (args.clear_tests or args.seed):
        ap.error("choose --clear-tests, --seed, or both")

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == args.email).first()
        if user is None:
            print(f"no account {args.email}")
            return 2

        # Order matters: the demo photos are copied out of the old test builds, so the sample is
        # seeded first and the test builds are removed afterwards (keeping what was just built).
        if args.seed:
            # The sample account: named for the brand it shows, marked as a test account so the
            # Team room's growth, marketing and finance counts never include demo money.
            user.name = BRAND["agent"]
            user.brand = BRAND
            user.is_test = True
            db.commit()
            replaced = 0
            for b in db.query(Boost).filter(Boost.user_id == user.id).all():
                if (b.plan or {}).get("_sample"):
                    replaced += 1
                    db.delete(b)
            db.commit()
            if replaced:
                print(f"replaced {replaced} previous sample campaigns")
            for line in asyncio.run(seed(db, user)):
                print("  +", line)
            print(f"sample account ready: {user.email} (id {user.id})")

        if args.clear_tests:
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            path = Path.home() / "resmara-backups" / f"test-campaigns-{stamp}.json"
            counts = backup(db, path)
            print(f"backup written: {path} ({counts})")
            gone = clear_tests(db, keep_sample=True, include_emails=args.include_email)
            print(f"deleted {len(gone)} test campaigns:")
            for line in gone:
                print("  -", line)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
